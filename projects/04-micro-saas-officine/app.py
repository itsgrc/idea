#!/usr/bin/env python3
"""Gestionale officina — multi-tenant, con autenticazione (zero dipendenze).

API REST su http.server + sqlite3. Più officine sullo stesso server, ognuna
vede solo i propri dati (login con email+password, token di sessione).
Flusso quotidiano: cliente → veicolo → intervento con stati (accettato →
in_lavorazione → pronto → consegnato).

Uso:
    python3 app.py --selftest   # crea db temporaneo, esegue il flusso, verifica
    python3 app.py              # API su :8000 (db: officina.db)

Endpoints:
    POST /auth/registra  {nome, email, password, telefono}  -> {token, officina}
    POST /auth/login     {email, password}                  -> {token, officina}
    -- tutti i seguenti richiedono header Authorization: Bearer <token> --
    POST /clienti        {nome, telefono}
    POST /veicoli        {cliente_id, targa, modello}
    POST /interventi     {veicolo_id, descrizione, preventivo, tipo?}
    PATCH /interventi/<id>  {stato} | {importo_finale}
    GET  /interventi?stato=pronto
    GET  /riepilogo      # il numero che il titolare guarda la sera
    GET  /richiami       # veicoli in scadenza/scaduti per tagliando ecc. (vedi richiami.py)
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
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from integrazioni.notifiche import invia_sms_pronto  # noqa: E402

DB = os.environ.get("OFFICINA_DB", "officina.db")
STATI = ["accettato", "in_lavorazione", "pronto", "consegnato"]
SESSIONE_MAX_ETA_S = 30 * 24 * 3600  # 30 giorni: strumento di lavoro, non un sito pubblico

SCHEMA = """
CREATE TABLE IF NOT EXISTS officine (
    id INTEGER PRIMARY KEY, nome TEXT NOT NULL, email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL, salt TEXT NOT NULL, telefono TEXT
);
CREATE TABLE IF NOT EXISTS clienti (
    id INTEGER PRIMARY KEY, officina_id INTEGER NOT NULL REFERENCES officine(id),
    nome TEXT NOT NULL, telefono TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS veicoli (
    id INTEGER PRIMARY KEY, officina_id INTEGER NOT NULL REFERENCES officine(id),
    cliente_id INTEGER NOT NULL REFERENCES clienti(id),
    targa TEXT NOT NULL, modello TEXT NOT NULL,
    UNIQUE(officina_id, targa)
);
CREATE TABLE IF NOT EXISTS interventi (
    id INTEGER PRIMARY KEY, officina_id INTEGER NOT NULL REFERENCES officine(id),
    veicolo_id INTEGER NOT NULL REFERENCES veicoli(id),
    descrizione TEXT NOT NULL, tipo TEXT NOT NULL DEFAULT 'generico',
    stato TEXT NOT NULL DEFAULT 'accettato',
    preventivo REAL, importo_finale REAL,
    creato TEXT DEFAULT CURRENT_TIMESTAMP, aggiornato TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

# Sessioni in memoria: token -> {officina_id, creato}. Per uno strumento
# gestito da poche persone per officina è sufficiente; non richiede
# infrastruttura extra (Redis, ecc.) per restare a zero dipendenze.
SESSIONI = {}

# Protezione anti-brute-force su /auth/login: senza limite, chiunque potrebbe
# tentare password a raffica contro un'email nota. Per IP, non per email, per
# non dover tenere un contatore per ogni email mai tentata (anche inesistente).
LOGIN_RATE_LIMIT_MAX = int(os.environ.get("LOGIN_RATE_LIMIT", "10"))
LOGIN_RATE_LIMIT_FINESTRA_S = 3600
_login_per_ip = {}


def login_rate_limit_superato(ip):
    ora = time.time()
    tentativi = [t for t in _login_per_ip.get(ip, []) if ora - t < LOGIN_RATE_LIMIT_FINESTRA_S]
    tentativi.append(ora)
    _login_per_ip[ip] = tentativi
    # pulizia periodica della mappa stessa, altrimenti diventa lei una perdita di memoria
    if len(_login_per_ip) > 10_000:
        for ip_vecchio in list(_login_per_ip):
            if all(ora - t > LOGIN_RATE_LIMIT_FINESTRA_S for t in _login_per_ip[ip_vecchio]):
                del _login_per_ip[ip_vecchio]
    return len(tentativi) > LOGIN_RATE_LIMIT_MAX


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
    scaduti = [t for t, s in SESSIONI.items() if ora - s["creato"] > SESSIONE_MAX_ETA_S]
    for t in scaduti:
        del SESSIONI[t]


def registra_officina(dati):
    for campo in ("nome", "email", "password", "telefono"):
        if not dati.get(campo):
            raise ValueError(f"campo mancante: {campo}")
    h, salt = hash_password(dati["password"])
    with db() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO officine (nome, email, password_hash, salt, telefono) VALUES (?,?,?,?,?)",
                (dati["nome"], dati["email"].lower().strip(), h, salt, dati["telefono"]),
            )
        except sqlite3.IntegrityError:
            raise ValueError("email già registrata")
        officina_id = cur.lastrowid
    token = secrets.token_urlsafe(32)
    SESSIONI[token] = {"officina_id": officina_id, "creato": time.time()}
    return {"token": token, "officina": {"id": officina_id, "nome": dati["nome"]}}


def login(dati):
    email = (dati.get("email") or "").lower().strip()
    password = dati.get("password") or ""
    with db() as conn:
        riga = conn.execute("SELECT * FROM officine WHERE email=?", (email,)).fetchone()
    if riga:
        ok = verifica_password(password, riga["password_hash"], riga["salt"])
    else:
        # Email inesistente: calcola comunque un hash PBKDF2 (con salt
        # fittizio, scartato) così il tempo di risposta è lo stesso di
        # un'email esistente con password sbagliata — altrimenti il tempo
        # di risposta rivelerebbe quali email sono registrate (timing
        # side-channel), permettendo di enumerarle da fuori.
        hash_password(password, salt=secrets.token_hex(16))
        ok = False
    if not ok:
        raise PermissionError("credenziali non valide")
    token = secrets.token_urlsafe(32)
    SESSIONI[token] = {"officina_id": riga["id"], "creato": time.time()}
    return {"token": token, "officina": {"id": riga["id"], "nome": riga["nome"]}}


def officina_da_token(headers):
    auth = headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[len("Bearer "):]
    sessione = SESSIONI.get(token)
    return sessione["officina_id"] if sessione else None


def crea(tabella, campi, dati, officina_id):
    mancanti = [c for c in campi if c not in dati]
    if mancanti:
        raise ValueError(f"campi mancanti: {', '.join(mancanti)}")
    with db() as conn:
        colonne = ["officina_id", *campi]
        valori = [officina_id, *[dati[c] for c in campi]]
        cur = conn.execute(
            f"INSERT INTO {tabella} ({','.join(colonne)}) VALUES ({','.join('?' * len(colonne))})",
            valori,
        )
        riga = conn.execute(f"SELECT * FROM {tabella} WHERE id=? AND officina_id=?", (cur.lastrowid, officina_id)).fetchone()
        return dict(riga)


def aggiorna_intervento(iid, dati, officina_id):
    consentiti = {}
    if "stato" in dati:
        if dati["stato"] not in STATI:
            raise ValueError(f"stato non valido, usa uno di: {STATI}")
        consentiti["stato"] = dati["stato"]
    if "importo_finale" in dati:
        consentiti["importo_finale"] = float(dati["importo_finale"])
    if not consentiti:
        raise ValueError("niente da aggiornare (stato o importo_finale)")
    with db() as conn:
        set_sql = ", ".join(f"{k}=?" for k in consentiti) + ", aggiornato=CURRENT_TIMESTAMP"
        conn.execute(f"UPDATE interventi SET {set_sql} WHERE id=? AND officina_id=?", [*consentiti.values(), iid, officina_id])
        riga = conn.execute("SELECT * FROM interventi WHERE id=? AND officina_id=?", (iid, officina_id)).fetchone()
        if not riga:
            raise LookupError("intervento non trovato")
        return dict(riga)


def dettaglio_intervento(iid, officina_id):
    """Come lista_interventi ma per un solo id: usato per comporre l'SMS
    di avviso (serve targa/modello/telefono, non solo i campi di interventi)."""
    with db() as conn:
        riga = conn.execute(
            """SELECT i.*, v.targa, v.modello, c.nome AS cliente, c.telefono
               FROM interventi i JOIN veicoli v ON v.id=i.veicolo_id
               JOIN clienti c ON c.id=v.cliente_id
               WHERE i.id=? AND i.officina_id=?""",
            (iid, officina_id),
        ).fetchone()
        return dict(riga) if riga else None


def lista_interventi(officina_id, stato=None):
    q = """SELECT i.*, v.targa, v.modello, c.nome AS cliente, c.telefono
           FROM interventi i JOIN veicoli v ON v.id=i.veicolo_id
           JOIN clienti c ON c.id=v.cliente_id
           WHERE i.officina_id=?"""
    args = [officina_id]
    if stato:
        q += " AND i.stato=?"
        args.append(stato)
    with db() as conn:
        return [dict(r) for r in conn.execute(q + " ORDER BY i.creato", args)]


def riepilogo(officina_id):
    with db() as conn:
        per_stato = {s: conn.execute("SELECT COUNT(*) FROM interventi WHERE stato=? AND officina_id=?", (s, officina_id)).fetchone()[0] for s in STATI}
        incassato = conn.execute("SELECT COALESCE(SUM(importo_finale),0) FROM interventi WHERE stato='consegnato' AND officina_id=?", (officina_id,)).fetchone()[0]
        in_corso = conn.execute("SELECT COALESCE(SUM(preventivo),0) FROM interventi WHERE stato!='consegnato' AND officina_id=?", (officina_id,)).fetchone()[0]
    return {"per_stato": per_stato, "incassato": incassato, "valore_in_officina": in_corso}


WEB_HTML = """<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ponte — Lavagna officina</title><style>
:root{--bg:#F4F4F2;--card:#fff;--ink:#1B1D1F;--muted:#5C6166;--line:#DCDDDA;--y:#F5B301;--dark:#232629}
@media(prefers-color-scheme:dark){:root{--bg:#151719;--card:#1E2124;--ink:#EAEBEC;--muted:#9CA1A7;--line:#33373B}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,sans-serif;line-height:1.5}
header{background:var(--dark);color:#F2F3F4;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}
header b{text-transform:uppercase;letter-spacing:.04em}header b i{color:var(--y);font-style:normal}
#riep{font-family:ui-monospace,Menlo,monospace;font-size:12.5px;color:#C9CCCF}
#esci{background:none;border:1px solid #4A4E52;color:#C9CCCF;border-radius:6px;padding:4px 10px;font-size:12px;cursor:pointer}
main{max-width:760px;margin:0 auto;padding:16px}
form{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px}
form h3{grid-column:1/-1;margin:0 0 2px;font-size:13px;text-transform:uppercase;letter-spacing:.06em}
input{padding:10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);font-size:15px}
input.full{grid-column:1/-1}
button{grid-column:1/-1;background:var(--y);border:0;border-radius:8px;padding:12px;font-weight:800;font-size:15px;text-transform:uppercase;cursor:pointer;color:#1B1D1F}
.job{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin-bottom:10px;display:grid;grid-template-columns:auto 1fr auto;gap:10px;align-items:center}
.plate{font-family:ui-monospace,Menlo,monospace;background:var(--ink);color:var(--bg);border-radius:4px;padding:3px 8px;font-weight:700;font-size:13px}
.job .d{font-size:14px}.job .d small{display:block;color:var(--muted);font-size:12.5px}
.job select{padding:8px;border-radius:8px;border:1px solid var(--line);background:var(--bg);color:var(--ink);font-weight:700;font-size:13px}
.s-accettato{border-left:5px solid #8A8F94}.s-in_lavorazione{border-left:5px solid var(--y)}
.s-pronto{border-left:5px solid #3E7A4E}.s-consegnato{opacity:.55;border-left:5px solid #3E7A4E}
#login-box{max-width:360px;margin:60px auto;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:20px}
#login-box h2{margin-top:0;font-size:16px;text-transform:uppercase;letter-spacing:.04em}
#login-box input{width:100%;margin-bottom:8px}
#login-box .err{color:#B3261E;font-size:13px;min-height:18px}
#login-box .switch{text-align:center;font-size:13px;color:var(--muted);cursor:pointer;text-decoration:underline;margin-top:6px}
.hidden{display:none !important}
</style></head><body>
<header id="app-header" class="hidden"><b>🔧 <i>PONTE</i> — lavagna officina</b>
  <span style="display:flex;align-items:center;gap:10px"><span id="riep"></span><button id="esci">Esci</button></span></header>
<main id="app-main" class="hidden">
<form id="nuovo"><h3>➕ Nuova accettazione (30 secondi)</h3>
<input id="nome" placeholder="Cliente" required><input id="tel" placeholder="Telefono" required>
<input id="targa" placeholder="Targa" required><input id="modello" placeholder="Modello" required>
<input id="descr" class="full" placeholder="Lavoro da fare" required>
<input id="prev" class="full" placeholder="Preventivo €" type="number" step="1" required>
<button>Accetta veicolo</button></form>
<div id="lista"></div>
</main>
<div id="login-box">
  <h2 id="login-titolo">Accedi alla tua officina</h2>
  <div class="err" id="login-err"></div>
  <input id="l-nome" class="hidden" placeholder="Nome officina">
  <input id="l-email" placeholder="Email" type="email">
  <input id="l-password" placeholder="Password" type="password">
  <input id="l-telefono" class="hidden" placeholder="Telefono">
  <button id="l-submit">Accedi</button>
  <div class="switch" id="l-switch">Non hai un account? Registra la tua officina</div>
</div>
<script>
const STATI=["accettato","in_lavorazione","pronto","consegnato"];
let modoRegistrazione=false;
function token(){return localStorage.getItem('ponte_token')}
function auth(opts={}){opts.headers=Object.assign({'Authorization':'Bearer '+token()},opts.headers||{});return opts}
function mostraApp(mostra){
  document.getElementById('app-header').classList.toggle('hidden',!mostra);
  document.getElementById('app-main').classList.toggle('hidden',!mostra);
  document.getElementById('login-box').classList.toggle('hidden',mostra);
}
document.getElementById('l-switch').addEventListener('click',()=>{
  modoRegistrazione=!modoRegistrazione;
  document.getElementById('login-titolo').textContent=modoRegistrazione?'Registra la tua officina':'Accedi alla tua officina';
  document.getElementById('l-submit').textContent=modoRegistrazione?'Registra':'Accedi';
  document.getElementById('l-switch').textContent=modoRegistrazione?'Hai già un account? Accedi':'Non hai un account? Registra la tua officina';
  document.getElementById('l-nome').classList.toggle('hidden',!modoRegistrazione);
  document.getElementById('l-telefono').classList.toggle('hidden',!modoRegistrazione);
  document.getElementById('login-err').textContent='';
});
document.getElementById('l-submit').addEventListener('click',async()=>{
  const g=id=>document.getElementById(id).value;
  const corpo=modoRegistrazione
    ?{nome:g('l-nome'),email:g('l-email'),password:g('l-password'),telefono:g('l-telefono')}
    :{email:g('l-email'),password:g('l-password')};
  const res=await fetch(modoRegistrazione?'/auth/registra':'/auth/login',{method:'POST',body:JSON.stringify(corpo)});
  const dati=await res.json();
  if(!res.ok){document.getElementById('login-err').textContent=dati.errore||'errore';return}
  localStorage.setItem('ponte_token',dati.token);
  mostraApp(true);carica();
});
document.getElementById('esci').addEventListener('click',()=>{localStorage.removeItem('ponte_token');mostraApp(false)});
async function carica(){
  const jobs=await (await fetch('/interventi',auth())).json();
  const r=await (await fetch('/riepilogo',auth())).json();
  document.getElementById('riep').textContent=
    `in officina: ${jobs.filter(j=>j.stato!=='consegnato').length} · valore: ${r.valore_in_officina}€ · incassato: ${r.incassato}€`;
  const el=document.getElementById('lista');el.innerHTML='';
  jobs.sort((a,b)=>STATI.indexOf(a.stato)-STATI.indexOf(b.stato));
  for(const j of jobs){
    const d=document.createElement('div');d.className='job s-'+j.stato;
    d.innerHTML=`<span class="plate">${j.targa}</span>
      <span class="d">${j.modello} — ${j.descrizione}<small>${j.cliente} · ${j.telefono} · prev. ${j.preventivo}€</small></span>`;
    const sel=document.createElement('select');
    for(const s of STATI){const o=document.createElement('option');o.value=s;o.textContent=s.replace('_',' ');if(s===j.stato)o.selected=true;sel.appendChild(o)}
    sel.onchange=async()=>{await fetch('/interventi/'+j.id,auth({method:'PATCH',body:JSON.stringify({stato:sel.value})}));carica()};
    d.appendChild(sel);el.appendChild(d);
  }
}
document.getElementById('nuovo').addEventListener('submit',async e=>{
  e.preventDefault();const g=id=>document.getElementById(id).value;
  const c=await (await fetch('/clienti',auth({method:'POST',body:JSON.stringify({nome:g('nome'),telefono:g('tel')})}))).json();
  const v=await (await fetch('/veicoli',auth({method:'POST',body:JSON.stringify({cliente_id:c.id,targa:g('targa'),modello:g('modello')})}))).json();
  await fetch('/interventi',auth({method:'POST',body:JSON.stringify({veicolo_id:v.id,descrizione:g('descr'),preventivo:+g('prev')})}));
  e.target.reset();carica();
});
if(token()){mostraApp(true);carica()}else{mostraApp(false)}
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

    def _officina(self):
        """Risolve l'officina dal token Bearer, o None se assente/non valido.
        Ogni route sotto /auth deve chiamarla e rifiutare con 401 se None:
        è l'unico punto che impedisce a un token di un'officina di leggere
        o modificare i dati di un'altra."""
        pulisci_sessioni()
        return officina_da_token(self.headers)

    def do_POST(self):
        try:
            if self.path in ("/auth/registra", "/auth/login"):
                if login_rate_limit_superato(self.client_address[0]):
                    return self._json(429, {"errore": "troppi tentativi, riprova più tardi"})
            if self.path == "/auth/registra":
                try:
                    return self._json(201, registra_officina(self._body()))
                except ValueError as e:
                    return self._json(400, {"errore": str(e)})
            if self.path == "/auth/login":
                try:
                    return self._json(200, login(self._body()))
                except PermissionError as e:
                    return self._json(401, {"errore": str(e)})

            officina_id = self._officina()
            if officina_id is None:
                return self._json(401, {"errore": "non autorizzato — serve login"})
            if self.path == "/clienti":
                return self._json(201, crea("clienti", ["nome", "telefono"], self._body(), officina_id))
            if self.path == "/veicoli":
                return self._json(201, crea("veicoli", ["cliente_id", "targa", "modello"], self._body(), officina_id))
            if self.path == "/interventi":
                dati = self._body()
                dati.setdefault("tipo", "generico")
                return self._json(201, crea("interventi", ["veicolo_id", "descrizione", "preventivo", "tipo"], dati, officina_id))
            self._json(404, {"errore": "endpoint sconosciuto"})
        except Exception as e:
            self._json(400, {"errore": str(e)})

    def do_PATCH(self):
        m = re.match(r"^/interventi/(\d+)$", self.path)
        if not m:
            return self._json(404, {"errore": "endpoint sconosciuto"})
        officina_id = self._officina()
        if officina_id is None:
            return self._json(401, {"errore": "non autorizzato — serve login"})
        try:
            iid = int(m.group(1))
            dati = self._body()
            diventa_pronto = dati.get("stato") == "pronto"
            risultato = aggiorna_intervento(iid, dati, officina_id)
            if diventa_pronto:
                try:
                    dettaglio = dettaglio_intervento(iid, officina_id)
                    if dettaglio:
                        invia_sms_pronto(dettaglio)
                except Exception as e:
                    print(f"⚠️  SMS 'veicolo pronto' fallito (l'aggiornamento è comunque salvato): {e}")
            self._json(200, risultato)
        except LookupError as e:
            self._json(404, {"errore": str(e)})
        except Exception as e:
            self._json(400, {"errore": str(e)})

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(WEB_HTML.encode())
            return
        officina_id = self._officina()
        if officina_id is None:
            return self._json(401, {"errore": "non autorizzato — serve login"})
        if self.path.startswith("/interventi"):
            stato = None
            if "stato=" in self.path:
                stato = self.path.split("stato=")[1].split("&")[0]
            return self._json(200, lista_interventi(officina_id, stato))
        if self.path == "/riepilogo":
            return self._json(200, riepilogo(officina_id))
        if self.path == "/richiami":
            from richiami import genera_richiami
            return self._json(200, genera_richiami(officina_id))
        self._json(404, {"errore": "endpoint sconosciuto"})

    def log_message(self, fmt, *args):
        print(f"  {self.command} {self.path}")


def selftest():
    global DB
    DB = "officina_test.db"
    if os.path.exists(DB):
        os.remove(DB)
    SESSIONI.clear()

    reg = registra_officina({"nome": "Officina Rossi", "email": "rossi@esempio.test", "password": "correcthorsebatterystaple", "telefono": "051 1234567"})
    officina_id = reg["officina"]["id"]

    # email duplicata deve essere rifiutata
    try:
        registra_officina({"nome": "Altra", "email": "rossi@esempio.test", "password": "altra12345", "telefono": "051 0000000"})
        raise AssertionError("email duplicata avrebbe dovuto fallire")
    except ValueError:
        pass

    # login con password sbagliata deve essere rifiutato
    try:
        login({"email": "rossi@esempio.test", "password": "sbagliata"})
        raise AssertionError("login con password sbagliata avrebbe dovuto fallire")
    except PermissionError:
        pass

    accesso = login({"email": "ROSSI@esempio.test  ".strip(), "password": "correcthorsebatterystaple"})
    assert accesso["officina"]["id"] == officina_id

    # una seconda officina non deve MAI vedere i dati della prima (isolamento multi-tenant)
    reg2 = registra_officina({"nome": "Officina Verdi", "email": "verdi@esempio.test", "password": "unaltrapassword1", "telefono": "051 9876543"})
    officina_id_2 = reg2["officina"]["id"]

    c = crea("clienti", ["nome", "telefono"], {"nome": "Luca Bianchi", "telefono": "333 1234567"}, officina_id)
    v = crea("veicoli", ["cliente_id", "targa", "modello"], {"cliente_id": c["id"], "targa": "AB123CD", "modello": "Panda 1.2"}, officina_id)
    i = crea("interventi", ["veicolo_id", "descrizione", "preventivo", "tipo"], {"veicolo_id": v["id"], "descrizione": "Tagliando + pastiglie", "preventivo": 280, "tipo": "tagliando"}, officina_id)
    for stato in ["in_lavorazione", "pronto"]:
        aggiorna_intervento(i["id"], {"stato": stato}, officina_id)
    aggiorna_intervento(i["id"], {"stato": "consegnato", "importo_finale": 295}, officina_id)

    # stessa targa in un'altra officina deve essere permessa (unicità è per-officina)
    c2 = crea("clienti", ["nome", "telefono"], {"nome": "Altro Cliente", "telefono": "333 7654321"}, officina_id_2)
    v2 = crea("veicoli", ["cliente_id", "targa", "modello"], {"cliente_id": c2["id"], "targa": "AB123CD", "modello": "Punto"}, officina_id_2)
    assert v2["targa"] == "AB123CD"

    r = riepilogo(officina_id)
    pronti = lista_interventi(officina_id, "consegnato")
    assert r["incassato"] == 295, r
    assert pronti[0]["cliente"] == "Luca Bianchi", pronti

    # l'officina 2 non deve vedere l'incasso/gli interventi dell'officina 1
    r2 = riepilogo(officina_id_2)
    assert r2["incassato"] == 0, r2
    assert lista_interventi(officina_id_2, "consegnato") == []

    try:
        aggiorna_intervento(i["id"], {"stato": "pronto"}, officina_id_2)
        raise AssertionError("un'officina non deve poter modificare l'intervento di un'altra")
    except LookupError:
        pass

    print("Flusso multi-tenant: registrazione → login → isolamento dati ✅")
    print(f"Riepilogo serale (officina Rossi): {json.dumps(r, ensure_ascii=False)}")
    os.remove(DB)
    print("✅ SELFTEST OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        print(f"🔧 Gestionale officina su :8000 (db: {DB})")
        HTTPServer(("", 8000), Handler).serve_forever()
