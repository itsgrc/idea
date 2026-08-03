#!/usr/bin/env python3
"""ProntoCasa — trova subito idraulici, elettricisti, muratori e altri
artigiani (zero dipendenze).

API REST su http.server + sqlite3. I professionisti si registrano e
gestiscono la propria disponibilità (login, PBKDF2). I clienti finali
NON hanno bisogno di account: inviano una richiesta con categoria, città
e descrizione, e il motore di dispacciamento (vedi dispacciamento.py)
contatta in automatico il professionista più affidabile disponibile.

Uso:
    python3 prontocasa.py --selftest   # crea db temporaneo, esegue il flusso, verifica
    python3 prontocasa.py              # API su :8050 (db: prontocasa.db)

Endpoints:
    POST /auth/registra  {nome, categoria, citta, telefono, email, password,
                           dichiarazione_requisiti}          -> {token, professionista}
    POST /auth/login     {email, password}                   -> {token, professionista}
    -- richiedono Authorization: Bearer <token> --
    POST /disponibilita  {disponibile: bool}
    GET  /le-mie-proposte
    POST /proposte/<id>/rispondi  {esito: accettata|rifiutata}
    PATCH /richieste/<id>  {stato: completata}
    GET  /affidabilita   (la propria)
    -- pubblici, nessun token (il cliente finale non ha un account) --
    POST /richieste      {cliente_nome, cliente_telefono, categoria, citta, descrizione, urgenza?}
                         -> include "codice": conservalo, serve per consultare lo stato
    GET  /richieste/<id>/stato?codice=...
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from affidabilita import calcola_affidabilita
from dispacciamento import avvia_dispatch, rispondi_proposta, controlla_scadute
from integrazioni.notifiche import invia_sms_conferma_cliente

DB = os.environ.get("PRONTOCASA_DB", "prontocasa.db")
SESSIONE_MAX_ETA_S = 30 * 24 * 3600  # 30 giorni: strumento di lavoro, non un sito pubblico

CATEGORIE_VALIDE = [
    "idraulico", "elettricista", "muratore", "imbianchino", "falegname",
    "fabbro", "giardiniere", "traslocatore", "climatizzazione", "pulizie", "altro",
]
URGENZE_VALIDE = ["normale", "urgente"]
STATI_RICHIESTA = ["in_attesa", "assegnata", "completata", "annullata", "nessun_professionista"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS professionisti (
    id INTEGER PRIMARY KEY, nome TEXT NOT NULL, categoria TEXT NOT NULL,
    citta TEXT NOT NULL, telefono TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL, salt TEXT NOT NULL,
    disponibile INTEGER NOT NULL DEFAULT 1,
    dichiarazione_requisiti INTEGER NOT NULL DEFAULT 0,
    creato TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS richieste (
    id INTEGER PRIMARY KEY, codice TEXT NOT NULL UNIQUE,
    cliente_nome TEXT NOT NULL, cliente_telefono TEXT NOT NULL,
    categoria TEXT NOT NULL, citta TEXT NOT NULL, descrizione TEXT NOT NULL,
    urgenza TEXT NOT NULL DEFAULT 'normale',
    stato TEXT NOT NULL DEFAULT 'in_attesa',
    professionista_assegnato_id INTEGER REFERENCES professionisti(id),
    creata TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS proposte (
    id INTEGER PRIMARY KEY, richiesta_id INTEGER NOT NULL REFERENCES richieste(id),
    professionista_id INTEGER NOT NULL REFERENCES professionisti(id),
    ordine INTEGER NOT NULL,
    stato TEXT NOT NULL DEFAULT 'in_attesa',
    inviata TEXT DEFAULT CURRENT_TIMESTAMP,
    risposta TEXT,
    scadenza TEXT NOT NULL
);
"""

SESSIONI = {}

LOGIN_RATE_LIMIT_MAX = int(os.environ.get("LOGIN_RATE_LIMIT", "10"))
LOGIN_RATE_LIMIT_FINESTRA_S = 3600
_login_per_ip = {}

# /richieste è pubblico per design (il cliente finale non ha un account):
# senza un limite, chiunque potrebbe inondarlo di richieste false, facendo
# scattare SMS reali a raffica verso professionisti veri.
RICHIESTE_RATE_LIMIT_MAX = int(os.environ.get("RICHIESTE_RATE_LIMIT", "10"))
RICHIESTE_RATE_LIMIT_FINESTRA_S = 3600
_richieste_per_ip = {}


def _rate_limit_superato(mappa, ip, massimo, finestra_s):
    ora = time.time()
    tentativi = [t for t in mappa.get(ip, []) if ora - t < finestra_s]
    tentativi.append(ora)
    mappa[ip] = tentativi
    if len(mappa) > 10_000:
        for ip_vecchio in list(mappa):
            if all(ora - t > finestra_s for t in mappa[ip_vecchio]):
                del mappa[ip_vecchio]
    return len(tentativi) > massimo


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), 200_000)
    return h.hex(), salt


def verifica_password(password, hash_atteso, salt):
    h, _ = hash_password(password, salt)
    return hmac.compare_digest(h, hash_atteso)


def pulisci_sessioni():
    ora = time.time()
    for t in [t for t, s in SESSIONI.items() if ora - s["creato"] > SESSIONE_MAX_ETA_S]:
        del SESSIONI[t]


def registra_professionista(dati):
    for campo in ("nome", "categoria", "citta", "telefono", "email", "password"):
        if not dati.get(campo):
            raise ValueError(f"campo mancante: {campo}")
    if dati["categoria"] not in CATEGORIE_VALIDE:
        raise ValueError(f"categoria non valida, usa una di: {CATEGORIE_VALIDE}")
    if not dati.get("dichiarazione_requisiti"):
        raise ValueError(
            "serve dichiarare sotto la propria responsabilità di possedere i requisiti "
            "e le abilitazioni di legge per la categoria scelta"
        )
    h, salt = hash_password(dati["password"])
    with db() as conn:
        try:
            cur = conn.execute(
                """INSERT INTO professionisti
                   (nome, categoria, citta, telefono, email, password_hash, salt, dichiarazione_requisiti)
                   VALUES (?,?,?,?,?,?,?,1)""",
                (dati["nome"], dati["categoria"], dati["citta"].strip(), dati["telefono"],
                 dati["email"].lower().strip(), h, salt),
            )
        except sqlite3.IntegrityError:
            raise ValueError("email già registrata")
        professionista_id = cur.lastrowid
    token = secrets.token_urlsafe(32)
    SESSIONI[token] = {"professionista_id": professionista_id, "creato": time.time()}
    return {"token": token, "professionista": {"id": professionista_id, "nome": dati["nome"], "categoria": dati["categoria"]}}


def login(dati):
    email = (dati.get("email") or "").lower().strip()
    password = dati.get("password") or ""
    with db() as conn:
        riga = conn.execute("SELECT * FROM professionisti WHERE email=?", (email,)).fetchone()
    if riga:
        ok = verifica_password(password, riga["password_hash"], riga["salt"])
    else:
        # Nessun timing side-channel: calcola comunque un hash con salt
        # fittizio, così un'email inesistente non risponde più veloce di
        # una password sbagliata (stesso principio dei progetti 04/10).
        hash_password(password, salt=secrets.token_hex(16))
        ok = False
    if not ok:
        raise PermissionError("credenziali non valide")
    token = secrets.token_urlsafe(32)
    SESSIONI[token] = {"professionista_id": riga["id"], "creato": time.time()}
    return {"token": token, "professionista": {"id": riga["id"], "nome": riga["nome"], "categoria": riga["categoria"]}}


def professionista_da_token(headers):
    auth = headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    sessione = SESSIONI.get(auth[len("Bearer "):])
    return sessione["professionista_id"] if sessione else None


def imposta_disponibilita(professionista_id, disponibile):
    # SELECT solo i campi che il client deve vedere: password_hash e salt
    # non hanno alcun motivo di lasciare mai il server, in nessuna risposta.
    with db() as conn:
        conn.execute("UPDATE professionisti SET disponibile=? WHERE id=?", (1 if disponibile else 0, professionista_id))
        riga = conn.execute(
            "SELECT id, nome, categoria, citta, telefono, email, disponibile FROM professionisti WHERE id=?",
            (professionista_id,),
        ).fetchone()
        return dict(riga)


def crea_richiesta(dati):
    for campo in ("cliente_nome", "cliente_telefono", "categoria", "citta", "descrizione"):
        if not dati.get(campo):
            raise ValueError(f"campo mancante: {campo}")
    if dati["categoria"] not in CATEGORIE_VALIDE:
        raise ValueError(f"categoria non valida, usa una di: {CATEGORIE_VALIDE}")
    urgenza = dati.get("urgenza") or "normale"
    if urgenza not in URGENZE_VALIDE:
        raise ValueError(f"urgenza non valida, usa una di: {URGENZE_VALIDE}")
    codice = secrets.token_urlsafe(16)
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO richieste (codice, cliente_nome, cliente_telefono, categoria, citta, descrizione, urgenza) VALUES (?,?,?,?,?,?,?)",
            (codice, dati["cliente_nome"], dati["cliente_telefono"].strip(), dati["categoria"], dati["citta"].strip(), dati["descrizione"], urgenza),
        )
        richiesta_id = cur.lastrowid
    avvia_dispatch(richiesta_id, db_path=DB)
    with db() as conn:
        return dict(conn.execute("SELECT * FROM richieste WHERE id=?", (richiesta_id,)).fetchone())


def stato_richiesta(richiesta_id, codice):
    """Endpoint pubblico (il cliente finale non ha un account): protetto
    dal codice casuale ricevuto alla creazione, non dal solo id numerico
    sequenziale — altrimenti chiunque potrebbe scorrere gli id ed
    esfiltrare nome e telefono di ogni cliente che ha mai fatto una richiesta."""
    with db() as conn:
        riga = conn.execute("SELECT * FROM richieste WHERE id=?", (richiesta_id,)).fetchone()
        if not riga or not hmac.compare_digest(riga["codice"], codice or ""):
            raise LookupError("richiesta non trovata")
        return dict(riga)


def le_mie_proposte(professionista_id):
    with db() as conn:
        righe = conn.execute(
            """SELECT p.*, r.categoria, r.citta, r.descrizione, r.urgenza, r.cliente_nome
               FROM proposte p JOIN richieste r ON r.id=p.richiesta_id
               WHERE p.professionista_id=? ORDER BY p.inviata DESC""",
            (professionista_id,),
        ).fetchall()
        return [dict(r) for r in righe]


def aggiorna_stato_richiesta(richiesta_id, professionista_id, nuovo_stato):
    if nuovo_stato not in STATI_RICHIESTA:
        raise ValueError(f"stato non valido, usa uno di: {STATI_RICHIESTA}")
    with db() as conn:
        riga = conn.execute("SELECT * FROM richieste WHERE id=?", (richiesta_id,)).fetchone()
        if not riga:
            raise LookupError("richiesta non trovata")
        if riga["professionista_assegnato_id"] != professionista_id:
            raise PermissionError("questa richiesta non è assegnata a te")
        conn.execute("UPDATE richieste SET stato=? WHERE id=?", (nuovo_stato, richiesta_id))
        return dict(conn.execute("SELECT * FROM richieste WHERE id=?", (richiesta_id,)).fetchone())


WEB_HTML = """<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ProntoCasa — trova subito chi ti serve</title><style>
:root{--bg:#F5F6F8;--card:#fff;--ink:#1A1E27;--muted:#5C6474;--line:#DDE1E8;--blu:#2A5FD9;--blu-scuro:#1A3E99;--arancio:#E8752A}
@media(prefers-color-scheme:dark){:root{--bg:#12141A;--card:#1B1E27;--ink:#E9ECF3;--muted:#9AA2B4;--line:#2C3140}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,sans-serif;line-height:1.5}
header{background:var(--blu-scuro);color:#F0F3FF;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}
header b{text-transform:uppercase;letter-spacing:.04em}
.tabs{display:flex;gap:8px;padding:12px 16px 0;max-width:640px;margin:0 auto}
.tab{flex:1;text-align:center;padding:10px;border-radius:8px 8px 0 0;background:var(--card);border:1px solid var(--line);border-bottom:0;cursor:pointer;font-weight:700;font-size:13px;color:var(--muted)}
.tab.attiva{color:var(--blu);background:var(--bg)}
main{max-width:640px;margin:0 auto;padding:0 16px 16px}
.pannello{background:var(--card);border:1px solid var(--line);border-radius:0 10px 10px 10px;padding:16px}
.hidden{display:none !important}
label{display:block;font-size:12px;color:var(--muted);margin:10px 0 4px;font-weight:700;text-transform:uppercase;letter-spacing:.03em}
input,select,textarea{width:100%;padding:10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);font-size:15px;font-family:inherit}
textarea{resize:vertical;min-height:60px}
.urgenza{display:flex;gap:8px;margin-top:6px}
.urgenza button{flex:1;padding:10px;border-radius:8px;border:1px solid var(--line);background:var(--bg);color:var(--ink);font-weight:700;cursor:pointer}
.urgenza button.sel{background:var(--arancio);color:#fff;border-color:var(--arancio)}
button.principale{width:100%;margin-top:16px;background:var(--blu);color:#fff;border:0;border-radius:8px;padding:13px;font-weight:800;font-size:15px;cursor:pointer}
.esito{margin-top:14px;padding:12px;border-radius:8px;background:var(--bg);border:1px solid var(--line);font-size:14px}
.job{background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:12px;margin-bottom:10px}
.job b{display:block;margin-bottom:4px}
.job .meta{font-size:12.5px;color:var(--muted);margin-bottom:8px}
.job .azioni{display:flex;gap:8px}
.job button{flex:1;padding:9px;border-radius:6px;border:0;font-weight:700;cursor:pointer}
.job .ok{background:#1F9D55;color:#fff}.job .no{background:#B3261E;color:#fff}
.stat{display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--line);font-size:14px}
.stat:last-child{border-bottom:0}
#login-box input{margin-bottom:8px}
.switch{text-align:center;font-size:13px;color:var(--muted);cursor:pointer;text-decoration:underline;margin-top:10px}
.err{color:#B3261E;font-size:13px;min-height:18px}
.toggle-disp{display:flex;align-items:center;gap:10px;margin-bottom:14px;padding:10px;background:var(--bg);border-radius:8px}
</style></head><body>
<header><b>🛠️ ProntoCasa</b><span id="chi-sono"></span></header>
<div class="tabs">
  <div class="tab attiva" id="tab-cliente">Ho bisogno di un servizio</div>
  <div class="tab" id="tab-prof">Sono un professionista</div>
</div>
<main>

<div id="pannello-cliente" class="pannello">
  <label>Che servizio ti serve?</label>
  <select id="c-categoria"></select>
  <label>Città</label>
  <input id="c-citta" placeholder="es. Milano">
  <label>Descrivi il problema</label>
  <textarea id="c-descrizione" placeholder="es. perdita d'acqua sotto il lavandino"></textarea>
  <label>Quanto è urgente?</label>
  <div class="urgenza">
    <button id="u-normale" class="sel">Può aspettare</button>
    <button id="u-urgente">Urgente, ora</button>
  </div>
  <label>Il tuo nome</label>
  <input id="c-nome" placeholder="Nome e cognome">
  <label>Il tuo telefono</label>
  <input id="c-telefono" placeholder="+39...">
  <button class="principale" id="c-invia">Trova qualcuno adesso</button>
  <div id="c-esito" class="esito hidden"></div>
</div>

<div id="pannello-prof" class="pannello hidden">
  <div id="prof-login">
    <div class="err" id="l-err"></div>
    <input id="l-nome" class="hidden" placeholder="Nome e cognome">
    <select id="l-categoria" class="hidden"></select>
    <input id="l-citta" class="hidden" placeholder="Città">
    <input id="l-telefono" class="hidden" placeholder="Telefono">
    <input id="l-email" placeholder="Email" type="email">
    <input id="l-password" placeholder="Password" type="password">
    <label id="l-dich-label" class="hidden" style="display:flex;align-items:center;gap:8px;font-weight:400;text-transform:none;margin-top:10px">
      <input type="checkbox" id="l-dichiarazione" style="width:auto"> Dichiaro di possedere i requisiti e le abilitazioni di legge per la mia categoria
    </label>
    <button class="principale" id="l-submit">Accedi</button>
    <div class="switch" id="l-switch">Non hai un account? Registrati</div>
  </div>
  <div id="prof-dashboard" class="hidden">
    <div class="toggle-disp">
      <input type="checkbox" id="p-disponibile" checked>
      <label style="margin:0;text-transform:none;font-weight:600">Disponibile a ricevere richieste ora</label>
    </div>
    <div id="p-affidabilita" class="esito"></div>
    <h3 style="font-size:14px;color:var(--muted);text-transform:uppercase;margin:16px 0 8px">Le tue richieste</h3>
    <div id="p-proposte"></div>
    <div class="switch" id="p-esci">Esci</div>
  </div>
</div>
</main>
<script>
const CATEGORIE = [
  ["idraulico","Idraulico"], ["elettricista","Elettricista"], ["muratore","Muratore"],
  ["imbianchino","Imbianchino"], ["falegname","Falegname"], ["fabbro","Fabbro"],
  ["giardiniere","Giardiniere"], ["traslocatore","Traslocatore"], ["climatizzazione","Climatizzazione"],
  ["pulizie","Pulizie"], ["altro","Altro"],
];
for (const sel of [document.getElementById('c-categoria'), document.getElementById('l-categoria')]) {
  for (const [v, label] of CATEGORIE) { const o=document.createElement('option'); o.value=v; o.textContent=label; sel.appendChild(o); }
}

let urgenza = 'normale';
document.getElementById('u-normale').addEventListener('click', () => { urgenza='normale'; document.getElementById('u-normale').classList.add('sel'); document.getElementById('u-urgente').classList.remove('sel'); });
document.getElementById('u-urgente').addEventListener('click', () => { urgenza='urgente'; document.getElementById('u-urgente').classList.add('sel'); document.getElementById('u-normale').classList.remove('sel'); });

document.getElementById('tab-cliente').addEventListener('click', () => mostraTab('cliente'));
document.getElementById('tab-prof').addEventListener('click', () => mostraTab('prof'));
function mostraTab(quale){
  document.getElementById('tab-cliente').classList.toggle('attiva', quale==='cliente');
  document.getElementById('tab-prof').classList.toggle('attiva', quale==='prof');
  document.getElementById('pannello-cliente').classList.toggle('hidden', quale!=='cliente');
  document.getElementById('pannello-prof').classList.toggle('hidden', quale!=='prof');
}

document.getElementById('c-invia').addEventListener('click', async () => {
  const g = id => document.getElementById(id).value;
  const esito = document.getElementById('c-esito');
  esito.classList.remove('hidden'); esito.textContent = 'Invio in corso…';
  const res = await fetch('/richieste', { method:'POST', body: JSON.stringify({
    cliente_nome:g('c-nome'), cliente_telefono:g('c-telefono'), categoria:g('c-categoria'),
    citta:g('c-citta'), descrizione:g('c-descrizione'), urgenza,
  })});
  const dati = await res.json();
  if (!res.ok) { esito.textContent = dati.errore || 'Qualcosa non ha funzionato, riprova.'; return; }
  esito.innerHTML = dati.stato === 'nessun_professionista'
    ? `Nessun professionista disponibile in questo momento a ${g('c-citta')}. Riprova più tardi.`
    : `✅ Richiesta inviata! Stiamo contattando il professionista più adatto — riceverai un SMS di conferma appena qualcuno accetta.`;
});

let token = null;
let modoRegistrazione = false;
document.getElementById('l-switch').addEventListener('click', () => {
  modoRegistrazione = !modoRegistrazione;
  for (const id of ['l-nome','l-categoria','l-citta','l-telefono','l-dich-label']) document.getElementById(id).classList.toggle('hidden', !modoRegistrazione);
  document.getElementById('l-submit').textContent = modoRegistrazione ? 'Registrati' : 'Accedi';
  document.getElementById('l-switch').textContent = modoRegistrazione ? 'Hai già un account? Accedi' : 'Non hai un account? Registrati';
});
document.getElementById('l-submit').addEventListener('click', async () => {
  const g = id => document.getElementById(id).value;
  const err = document.getElementById('l-err'); err.textContent = '';
  const corpo = modoRegistrazione
    ? { nome:g('l-nome'), categoria:g('l-categoria'), citta:g('l-citta'), telefono:g('l-telefono'), email:g('l-email'), password:g('l-password'), dichiarazione_requisiti: document.getElementById('l-dichiarazione').checked }
    : { email:g('l-email'), password:g('l-password') };
  const res = await fetch(modoRegistrazione ? '/auth/registra' : '/auth/login', { method:'POST', body: JSON.stringify(corpo) });
  const dati = await res.json();
  if (!res.ok) { err.textContent = dati.errore || 'errore'; return; }
  token = dati.token;
  document.getElementById('chi-sono').textContent = 'Ciao, ' + dati.professionista.nome;
  document.getElementById('prof-login').classList.add('hidden');
  document.getElementById('prof-dashboard').classList.remove('hidden');
  caricaDashboard();
});
document.getElementById('p-esci').addEventListener('click', () => {
  token = null;
  document.getElementById('chi-sono').textContent = '';
  document.getElementById('prof-dashboard').classList.add('hidden');
  document.getElementById('prof-login').classList.remove('hidden');
});
document.getElementById('p-disponibile').addEventListener('change', async (e) => {
  await fetch('/disponibilita', { method:'POST', headers:{'Authorization':'Bearer '+token}, body: JSON.stringify({ disponibile: e.target.checked }) });
});

async function caricaDashboard(){
  const auth = { headers: { 'Authorization': 'Bearer ' + token } };
  const [affidabilita, proposte] = await Promise.all([
    fetch('/affidabilita', auth).then(r => r.json()),
    fetch('/le-mie-proposte', auth).then(r => r.json()),
  ]);
  const a = document.getElementById('p-affidabilita');
  a.innerHTML = `<div class="stat"><span>Punteggio affidabilità</span><b>${Math.round(affidabilita.punteggio*100)}%</b></div>` +
    (affidabilita.n_proposte === 0 ? '<div class="stat"><span>Nessuno storico ancora — punteggio neutro di partenza</span></div>' :
      `<div class="stat"><span>Tasso di risposta</span><span>${Math.round(affidabilita.tasso_risposta*100)}%</span></div>
       <div class="stat"><span>Tasso di accettazione</span><span>${Math.round(affidabilita.tasso_accettazione*100)}%</span></div>
       <div class="stat"><span>Tasso di completamento</span><span>${Math.round(affidabilita.tasso_completamento*100)}%</span></div>`);

  const el = document.getElementById('p-proposte'); el.innerHTML = '';
  if (!proposte.length) { el.innerHTML = '<p style="color:var(--muted);font-size:14px">Nessuna richiesta ricevuta ancora.</p>'; }
  for (const p of proposte) {
    const d = document.createElement('div'); d.className = 'job';
    const urgLabel = p.urgenza === 'urgente' ? '🚨 URGENTE' : 'Normale';
    d.innerHTML = `<b>${p.categoria} — ${p.citta}</b><div class="meta">${urgLabel} · ${p.descrizione} · stato: ${p.stato}</div>`;
    if (p.stato === 'in_attesa') {
      const azioni = document.createElement('div'); azioni.className = 'azioni';
      const accetta = document.createElement('button'); accetta.className = 'ok'; accetta.textContent = 'Accetta';
      const rifiuta = document.createElement('button'); rifiuta.className = 'no'; rifiuta.textContent = 'Rifiuta';
      accetta.onclick = async () => { await rispondi(p.id, 'accettata'); };
      rifiuta.onclick = async () => { await rispondi(p.id, 'rifiutata'); };
      azioni.appendChild(accetta); azioni.appendChild(rifiuta); d.appendChild(azioni);
    }
    el.appendChild(d);
  }
}
async function rispondi(propostaId, esito){
  await fetch('/proposte/' + propostaId + '/rispondi', { method:'POST', headers:{'Authorization':'Bearer '+token}, body: JSON.stringify({ esito }) });
  caricaDashboard();
}
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _json(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body, ensure_ascii=False).encode())

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def _professionista(self):
        pulisci_sessioni()
        return professionista_da_token(self.headers)

    def do_POST(self):
        try:
            if self.path in ("/auth/registra", "/auth/login"):
                if _rate_limit_superato(_login_per_ip, self.client_address[0], LOGIN_RATE_LIMIT_MAX, LOGIN_RATE_LIMIT_FINESTRA_S):
                    return self._json(429, {"errore": "troppi tentativi, riprova più tardi"})
            if self.path == "/auth/registra":
                try:
                    return self._json(201, registra_professionista(self._body()))
                except ValueError as e:
                    return self._json(400, {"errore": str(e)})
            if self.path == "/auth/login":
                try:
                    return self._json(200, login(self._body()))
                except PermissionError as e:
                    return self._json(401, {"errore": str(e)})

            if self.path == "/richieste":
                if _rate_limit_superato(_richieste_per_ip, self.client_address[0], RICHIESTE_RATE_LIMIT_MAX, RICHIESTE_RATE_LIMIT_FINESTRA_S):
                    return self._json(429, {"errore": "troppe richieste, riprova più tardi"})
                controlla_scadute(db_path=DB)
                return self._json(201, crea_richiesta(self._body()))

            m = re.match(r"^/proposte/(\d+)/rispondi$", self.path)
            if m:
                professionista_id = self._professionista()
                if professionista_id is None:
                    return self._json(401, {"errore": "non autorizzato — serve login"})
                controlla_scadute(db_path=DB)
                dati = self._body()
                esito = dati.get("esito")
                if esito not in ("accettata", "rifiutata"):
                    return self._json(400, {"errore": "esito deve essere 'accettata' o 'rifiutata'"})
                return self._json(200, rispondi_proposta(int(m.group(1)), professionista_id, esito, db_path=DB))

            if self.path == "/disponibilita":
                professionista_id = self._professionista()
                if professionista_id is None:
                    return self._json(401, {"errore": "non autorizzato — serve login"})
                dati = self._body()
                return self._json(200, imposta_disponibilita(professionista_id, bool(dati.get("disponibile"))))

            self._json(404, {"errore": "endpoint sconosciuto"})
        except (ValueError, LookupError) as e:
            self._json(400, {"errore": str(e)})
        except PermissionError as e:
            self._json(403, {"errore": str(e)})

    def do_PATCH(self):
        m = re.match(r"^/richieste/(\d+)$", self.path)
        if not m:
            return self._json(404, {"errore": "endpoint sconosciuto"})
        professionista_id = self._professionista()
        if professionista_id is None:
            return self._json(401, {"errore": "non autorizzato — serve login"})
        try:
            dati = self._body()
            self._json(200, aggiorna_stato_richiesta(int(m.group(1)), professionista_id, dati.get("stato")))
        except LookupError as e:
            self._json(404, {"errore": str(e)})
        except PermissionError as e:
            self._json(403, {"errore": str(e)})
        except ValueError as e:
            self._json(400, {"errore": str(e)})

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(WEB_HTML.encode())
            return
        try:
            m = re.match(r"^/richieste/(\d+)/stato$", parsed.path)
            if m:
                qs = urllib.parse.parse_qs(parsed.query)
                codice = (qs.get("codice") or [None])[0]
                return self._json(200, stato_richiesta(int(m.group(1)), codice))

            professionista_id = self._professionista()
            if professionista_id is None:
                return self._json(401, {"errore": "non autorizzato — serve login"})
            if parsed.path == "/le-mie-proposte":
                return self._json(200, le_mie_proposte(professionista_id))
            if parsed.path == "/affidabilita":
                return self._json(200, calcola_affidabilita(professionista_id, DB))
            self._json(404, {"errore": "endpoint sconosciuto"})
        except LookupError as e:
            self._json(404, {"errore": str(e)})
        except ValueError as e:
            self._json(400, {"errore": str(e)})

    def log_message(self, fmt, *args):
        print(f"  {self.command} {self.path}")


def selftest():
    global DB
    DB = "prontocasa_test.db"
    if os.path.exists(DB):
        os.remove(DB)
    SESSIONI.clear()

    reg = registra_professionista({
        "nome": "Mario Rossi", "categoria": "idraulico", "citta": "Milano",
        "telefono": "+393331112222", "email": "mario@idraulico.test", "password": "passwordMario123",
        "dichiarazione_requisiti": True,
    })
    professionista_id = reg["professionista"]["id"]

    try:
        registra_professionista({
            "nome": "Altro", "categoria": "idraulico", "citta": "Milano", "telefono": "1",
            "email": "mario@idraulico.test", "password": "altrapassword1", "dichiarazione_requisiti": True,
        })
        raise AssertionError("email duplicata avrebbe dovuto fallire")
    except ValueError:
        pass

    try:
        registra_professionista({
            "nome": "Senza Dichiarazione", "categoria": "idraulico", "citta": "Milano", "telefono": "1",
            "email": "altro@test.test", "password": "passwordaltro1",
        })
        raise AssertionError("senza dichiarazione requisiti avrebbe dovuto fallire")
    except ValueError:
        pass

    try:
        login({"email": "mario@idraulico.test", "password": "sbagliata"})
        raise AssertionError("login con password sbagliata avrebbe dovuto fallire")
    except PermissionError:
        pass

    accesso = login({"email": "MARIO@idraulico.test  ".strip(), "password": "passwordMario123"})
    assert accesso["professionista"]["id"] == professionista_id

    richiesta = crea_richiesta({
        "cliente_nome": "Anna Verdi", "cliente_telefono": "+393339998888",
        "categoria": "idraulico", "citta": "Milano", "descrizione": "perdita sotto il lavandino", "urgenza": "urgente",
    })
    assert richiesta["stato"] == "in_attesa"

    proposte = le_mie_proposte(professionista_id)
    assert len(proposte) == 1 and proposte[0]["stato"] == "in_attesa"

    esito = rispondi_proposta(proposte[0]["id"], professionista_id, "accettata", db_path=DB)
    assert esito["stato"] == "assegnata"

    completata = aggiorna_stato_richiesta(richiesta["id"], professionista_id, "completata")
    assert completata["stato"] == "completata"

    # un professionista non può completare una richiesta non sua
    reg2 = registra_professionista({
        "nome": "Altro Idraulico", "categoria": "idraulico", "citta": "Milano",
        "telefono": "+393330001111", "email": "altro2@idraulico.test", "password": "passwordAltra12",
        "dichiarazione_requisiti": True,
    })
    try:
        aggiorna_stato_richiesta(richiesta["id"], reg2["professionista"]["id"], "annullata")
        raise AssertionError("un professionista non deve poter modificare una richiesta non sua")
    except PermissionError:
        pass

    affidabilita_mario = calcola_affidabilita(professionista_id, DB)
    assert affidabilita_mario["n_proposte"] == 1
    assert affidabilita_mario["tasso_completamento"] == 1.0

    print("Flusso: registrazione → login → richiesta → dispacciamento → accettazione → completamento ✅")
    os.remove(DB)
    print("✅ SELFTEST OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        print(f"🛠️  ProntoCasa — API su :8050 (db: {DB})")
        HTTPServer(("", 8050), Handler).serve_forever()
