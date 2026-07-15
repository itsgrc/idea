#!/usr/bin/env python3
"""Campolibero — prenotazioni multisport, spina dorsale (zero dipendenze).

API REST su http.server + sqlite3. Più strutture sportive sullo stesso
server (padel, calcio a 5, tennis, corsi, personal trainer, ...), ognuna
isolata dalle altre (login email+password, token di sessione — stesso
schema del progetto 04). Ogni struttura ha "risorse" (campo, sala,
istruttore) prenotabili a slot.

Uso:
    python3 prenota.py --selftest   # crea db temporaneo, esegue il flusso, verifica
    python3 prenota.py              # API su :8040 (db: campolibero.db)

Endpoints:
    POST /auth/registra  {nome, citta, email, password, telefono}  -> {token, struttura}
    POST /auth/login     {email, password}                         -> {token, struttura}
    -- tutti i seguenti richiedono header Authorization: Bearer <token> --
    POST /risorse         {nome, sport, durata_slot_min, prezzo_orario}
    GET  /risorse
    GET  /disponibilita?giorno=2026-07-20[&sport=padel]
    POST /prenotazioni    {risorsa_id, nome_cliente, telefono_cliente, inizio}
    GET  /prenotazioni?giorno=2026-07-20
    PATCH /prenotazioni/<id>  {stato: annullata|completata|no_show}
    -- pubblico, nessun token: è la rete tra strutture, il moat --
    GET  /rete?sport=padel&citta=Milano&inizio=2026-07-20T18:00
"""
import datetime
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
from rischio_noshow import valuta_rischio
from integrazioni.notifiche import invia_sms_conferma
from integrazioni.pagamenti import crea_sessione_deposito, valida_firma_stripe

DB = os.environ.get("CAMPOLIBERO_DB", "campolibero.db")
STATI = ["confermata", "in_attesa_deposito", "annullata", "completata", "no_show"]
SPORT_VALIDI = ["padel", "calcio_a_5", "tennis", "squash", "corso_fitness", "personal_trainer", "altro"]
SESSIONE_MAX_ETA_S = 30 * 24 * 3600  # 30 giorni: strumento di lavoro per il gestore, non un sito pubblico

# Finestra oraria di apertura applicata a tutte le risorse di una struttura:
# semplificazione MVP (niente orari diversi per giorno/risorsa) — dichiarata
# come tale, non nascosta.
ORARIO_APERTURA = os.environ.get("CAMPOLIBERO_APERTURA", "08:00")
ORARIO_CHIUSURA = os.environ.get("CAMPOLIBERO_CHIUSURA", "23:00")

SCHEMA = """
CREATE TABLE IF NOT EXISTS strutture (
    id INTEGER PRIMARY KEY, nome TEXT NOT NULL, citta TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, salt TEXT NOT NULL,
    telefono TEXT
);
CREATE TABLE IF NOT EXISTS risorse (
    id INTEGER PRIMARY KEY, struttura_id INTEGER NOT NULL REFERENCES strutture(id),
    nome TEXT NOT NULL, sport TEXT NOT NULL,
    durata_slot_min INTEGER NOT NULL DEFAULT 60,
    prezzo_orario REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS clienti (
    id INTEGER PRIMARY KEY, struttura_id INTEGER NOT NULL REFERENCES strutture(id),
    nome TEXT NOT NULL, telefono TEXT NOT NULL, email TEXT,
    UNIQUE(struttura_id, telefono)
);
CREATE TABLE IF NOT EXISTS prenotazioni (
    id INTEGER PRIMARY KEY, struttura_id INTEGER NOT NULL REFERENCES strutture(id),
    risorsa_id INTEGER NOT NULL REFERENCES risorse(id),
    cliente_id INTEGER NOT NULL REFERENCES clienti(id),
    inizio TEXT NOT NULL, fine TEXT NOT NULL,
    stato TEXT NOT NULL DEFAULT 'confermata',
    richiede_deposito INTEGER NOT NULL DEFAULT 0,
    importo_deposito REAL,
    deposito_pagato INTEGER NOT NULL DEFAULT 0,
    url_deposito TEXT,
    motivo_rischio TEXT,
    creata TEXT DEFAULT CURRENT_TIMESTAMP
);
"""

SESSIONI = {}

# Protezione anti-brute-force su /auth/login e /auth/registra (per IP, non
# per email: altrimenti servirebbe un contatore per ogni email mai
# tentata, anche inesistente).
LOGIN_RATE_LIMIT_MAX = int(os.environ.get("LOGIN_RATE_LIMIT", "10"))
LOGIN_RATE_LIMIT_FINESTRA_S = 3600
_login_per_ip = {}

# /rete non richiede login per design (è il punto di ingresso per i
# clienti finali, non per le strutture): senza un limite, chiunque
# potrebbe usarlo per mappare a raffica tutte le città/sport in catalogo.
RETE_RATE_LIMIT_MAX = int(os.environ.get("RETE_RATE_LIMIT", "30"))
RETE_RATE_LIMIT_FINESTRA_S = 3600
_rete_per_ip = {}


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


def registra_struttura(dati):
    for campo in ("nome", "citta", "email", "password", "telefono"):
        if not dati.get(campo):
            raise ValueError(f"campo mancante: {campo}")
    h, salt = hash_password(dati["password"])
    with db() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO strutture (nome, citta, email, password_hash, salt, telefono) VALUES (?,?,?,?,?,?)",
                (dati["nome"], dati["citta"].strip(), dati["email"].lower().strip(), h, salt, dati["telefono"]),
            )
        except sqlite3.IntegrityError:
            raise ValueError("email già registrata")
        struttura_id = cur.lastrowid
    token = secrets.token_urlsafe(32)
    SESSIONI[token] = {"struttura_id": struttura_id, "creato": time.time()}
    return {"token": token, "struttura": {"id": struttura_id, "nome": dati["nome"], "citta": dati["citta"]}}


def login(dati):
    email = (dati.get("email") or "").lower().strip()
    password = dati.get("password") or ""
    with db() as conn:
        riga = conn.execute("SELECT * FROM strutture WHERE email=?", (email,)).fetchone()
    if riga:
        ok = verifica_password(password, riga["password_hash"], riga["salt"])
    else:
        # Stesso motivo del progetto 04: calcola comunque l'hash con salt
        # fittizio, così un'email inesistente non risponde più in fretta
        # di una password sbagliata (niente timing side-channel).
        hash_password(password, salt=secrets.token_hex(16))
        ok = False
    if not ok:
        raise PermissionError("credenziali non valide")
    token = secrets.token_urlsafe(32)
    SESSIONI[token] = {"struttura_id": riga["id"], "creato": time.time()}
    return {"token": token, "struttura": {"id": riga["id"], "nome": riga["nome"], "citta": riga["citta"]}}


def struttura_da_token(headers):
    auth = headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    sessione = SESSIONI.get(auth[len("Bearer "):])
    return sessione["struttura_id"] if sessione else None


def crea_risorsa(struttura_id, dati):
    for campo in ("nome", "sport", "prezzo_orario"):
        if not dati.get(campo):
            raise ValueError(f"campo mancante: {campo}")
    if dati["sport"] not in SPORT_VALIDI:
        raise ValueError(f"sport non valido, usa uno di: {SPORT_VALIDI}")
    # "or 60" coincerebbe silenziosamente anche un 0 esplicito in 60: usare
    # "is not None" così un valore invalido viene rifiutato dal controllo
    # sotto, invece di sparire senza errore.
    durata = int(dati["durata_slot_min"]) if dati.get("durata_slot_min") is not None else 60
    # Un valore <=0 (o assurdamente alto) manda in loop infinito la
    # generazione degli slot in _slot_del_giorno — non un dettaglio
    # cosmetico, un blocco totale del processo su qualunque richiesta di
    # disponibilità che tocchi questa risorsa.
    if not (5 <= durata <= 480):
        raise ValueError("durata_slot_min deve essere tra 5 e 480 minuti")
    prezzo = float(dati["prezzo_orario"])
    if prezzo < 0:
        raise ValueError("prezzo_orario non può essere negativo")
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO risorse (struttura_id, nome, sport, durata_slot_min, prezzo_orario) VALUES (?,?,?,?,?)",
            (struttura_id, dati["nome"], dati["sport"], durata, prezzo),
        )
        riga = conn.execute("SELECT * FROM risorse WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(riga)


def lista_risorse(struttura_id):
    with db() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM risorse WHERE struttura_id=? ORDER BY id", (struttura_id,))]


def _slot_del_giorno(risorsa, giorno):
    """Genera gli slot teorici (inizio, fine) di una risorsa in un giorno,
    dentro la finestra di apertura — non ancora filtrati per disponibilità."""
    apertura = datetime.datetime.fromisoformat(f"{giorno}T{ORARIO_APERTURA}")
    chiusura = datetime.datetime.fromisoformat(f"{giorno}T{ORARIO_CHIUSURA}")
    durata = datetime.timedelta(minutes=risorsa["durata_slot_min"])
    slot = []
    cursore = apertura
    while cursore + durata <= chiusura:
        slot.append((cursore, cursore + durata))
        cursore += durata
    return slot


def disponibilita(struttura_id, giorno, sport=None):
    risorse = lista_risorse(struttura_id)
    if sport:
        risorse = [r for r in risorse if r["sport"] == sport]
    with db() as conn:
        occupate = conn.execute(
            """SELECT risorsa_id, inizio, fine FROM prenotazioni
               WHERE struttura_id=? AND stato IN ('confermata','in_attesa_deposito')
               AND date(inizio)=?""",
            (struttura_id, giorno),
        ).fetchall()
    occupate_per_risorsa = {}
    for o in occupate:
        occupate_per_risorsa.setdefault(o["risorsa_id"], []).append(
            (datetime.datetime.fromisoformat(o["inizio"]), datetime.datetime.fromisoformat(o["fine"]))
        )

    risultato = []
    for r in risorse:
        libere = []
        for inizio, fine in _slot_del_giorno(r, giorno):
            occupato = any(inizio < f and i < fine for i, f in occupate_per_risorsa.get(r["id"], []))
            if not occupato:
                libere.append(inizio.isoformat())
        risultato.append({"risorsa_id": r["id"], "nome": r["nome"], "sport": r["sport"],
                           "prezzo_orario": r["prezzo_orario"], "durata_slot_min": r["durata_slot_min"],
                           "slot_liberi": libere})
    return risultato


def _slot_libero(struttura_id, risorsa_id, inizio, fine, escludi_prenotazione_id=None):
    with db() as conn:
        q = """SELECT COUNT(*) FROM prenotazioni
               WHERE struttura_id=? AND risorsa_id=? AND stato IN ('confermata','in_attesa_deposito')
               AND inizio < ? AND ? < fine"""
        args = [struttura_id, risorsa_id, fine, inizio]
        if escludi_prenotazione_id:
            q += " AND id != ?"
            args.append(escludi_prenotazione_id)
        return conn.execute(q, args).fetchone()[0] == 0


def prenota(struttura_id, dati):
    for campo in ("risorsa_id", "nome_cliente", "telefono_cliente", "inizio"):
        if not dati.get(campo):
            raise ValueError(f"campo mancante: {campo}")
    with db() as conn:
        risorsa = conn.execute("SELECT * FROM risorse WHERE id=? AND struttura_id=?", (dati["risorsa_id"], struttura_id)).fetchone()
    if not risorsa:
        raise LookupError("risorsa non trovata")

    inizio = datetime.datetime.fromisoformat(dati["inizio"])
    fine = inizio + datetime.timedelta(minutes=risorsa["durata_slot_min"])
    if not _slot_libero(struttura_id, risorsa["id"], inizio.isoformat(), fine.isoformat()):
        raise ValueError("slot non più disponibile")

    telefono = dati["telefono_cliente"].strip()
    with db() as conn:
        cliente = conn.execute("SELECT * FROM clienti WHERE struttura_id=? AND telefono=?", (struttura_id, telefono)).fetchone()
        if cliente:
            cliente_id = cliente["id"]
        else:
            cur = conn.execute(
                "INSERT INTO clienti (struttura_id, nome, telefono, email) VALUES (?,?,?,?)",
                (struttura_id, dati["nome_cliente"], telefono, dati.get("email_cliente")),
            )
            cliente_id = cur.lastrowid

    rischio = valuta_rischio(struttura_id, telefono, risorsa["id"], inizio, db_path=DB)
    stato = "in_attesa_deposito" if rischio["richiede_deposito"] else "confermata"
    importo_deposito = round(risorsa["prezzo_orario"] * 0.3, 2) if rischio["richiede_deposito"] else None

    with db() as conn:
        cur = conn.execute(
            """INSERT INTO prenotazioni
               (struttura_id, risorsa_id, cliente_id, inizio, fine, stato, richiede_deposito, importo_deposito, motivo_rischio)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (struttura_id, risorsa["id"], cliente_id, inizio.isoformat(), fine.isoformat(),
             stato, int(rischio["richiede_deposito"]), importo_deposito, rischio["motivo"]),
        )
        prenotazione_id = cur.lastrowid

        if rischio["richiede_deposito"]:
            sessione = crea_sessione_deposito(prenotazione_id, importo_deposito, f"Deposito {risorsa['nome']}", struttura_id=struttura_id)
            url_deposito = sessione.get("url_pagamento")
            conn.execute("UPDATE prenotazioni SET url_deposito=? WHERE id=?", (url_deposito, prenotazione_id))

        riga = dict(conn.execute("SELECT * FROM prenotazioni WHERE id=?", (prenotazione_id,)).fetchone())

    try:
        invia_sms_conferma(telefono, risorsa["nome"], inizio, richiede_deposito=rischio["richiede_deposito"],
                            importo_deposito=importo_deposito, url_deposito=riga.get("url_deposito"))
    except Exception as e:
        print(f"⚠️  SMS di conferma fallito (la prenotazione resta valida): {e}")

    riga["rischio"] = rischio
    return riga


def aggiorna_stato_prenotazione(prenotazione_id, struttura_id, nuovo_stato):
    if nuovo_stato not in STATI:
        raise ValueError(f"stato non valido, usa uno di: {STATI}")
    with db() as conn:
        conn.execute(
            "UPDATE prenotazioni SET stato=? WHERE id=? AND struttura_id=?",
            (nuovo_stato, prenotazione_id, struttura_id),
        )
        riga = conn.execute("SELECT * FROM prenotazioni WHERE id=? AND struttura_id=?", (prenotazione_id, struttura_id)).fetchone()
        if not riga:
            raise LookupError("prenotazione non trovata")
        return dict(riga)


def conferma_deposito_pagato(prenotazione_id, struttura_id):
    with db() as conn:
        conn.execute(
            "UPDATE prenotazioni SET stato='confermata', deposito_pagato=1 WHERE id=? AND struttura_id=?",
            (prenotazione_id, struttura_id),
        )
        riga = conn.execute("SELECT * FROM prenotazioni WHERE id=? AND struttura_id=?", (prenotazione_id, struttura_id)).fetchone()
        if not riga:
            raise LookupError("prenotazione non trovata")
        return dict(riga)


def lista_prenotazioni(struttura_id, giorno=None):
    q = """SELECT p.*, r.nome AS risorsa, r.sport, c.nome AS cliente, c.telefono
           FROM prenotazioni p JOIN risorse r ON r.id=p.risorsa_id
           JOIN clienti c ON c.id=p.cliente_id
           WHERE p.struttura_id=?"""
    args = [struttura_id]
    if giorno:
        q += " AND date(p.inizio)=?"
        args.append(giorno)
    with db() as conn:
        return [dict(r) for r in conn.execute(q + " ORDER BY p.inizio", args)]


WEB_HTML = """<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Campolibero — prenotazioni</title><style>
:root{--bg:#F4F7F4;--card:#fff;--ink:#12261A;--muted:#5C6B60;--line:#DCE3DC;--verde:#1F9D55;--verde-scuro:#0F5C31;--giallo:#E8A93A}
@media(prefers-color-scheme:dark){:root{--bg:#0F1512;--card:#182119;--ink:#EAF0EA;--muted:#9BAAA0;--line:#293830}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,sans-serif;line-height:1.5}
header{background:var(--verde-scuro);color:#F2F7F3;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}
header b{text-transform:uppercase;letter-spacing:.04em}
#esci{background:none;border:1px solid #3E6E52;color:#DDEBE1;border-radius:6px;padding:4px 10px;font-size:12px;cursor:pointer}
main{max-width:820px;margin:0 auto;padding:16px}
.pannello{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;margin-bottom:16px}
.pannello h3{margin:0 0 10px;font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.riga{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px}
input,select{padding:9px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);font-size:14px}
button{background:var(--verde);border:0;border-radius:8px;padding:10px 16px;font-weight:700;font-size:14px;cursor:pointer;color:#fff}
.slots{display:grid;grid-template-columns:repeat(auto-fill,minmax(90px,1fr));gap:8px}
.slot{padding:10px 6px;border-radius:8px;border:1px solid var(--line);background:var(--bg);text-align:center;font-size:13px;cursor:pointer;font-weight:700}
.slot:hover{border-color:var(--verde)}
.job{display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--line);font-size:14px}
.job:last-child{border-bottom:0}
.tag{font-size:11px;font-weight:800;padding:2px 8px;border-radius:999px;text-transform:uppercase}
.t-confermata{background:#1F9D5522;color:var(--verde-scuro)}.t-in_attesa_deposito{background:#E8A93A33;color:#8A6400}
.t-annullata{background:#8A8F9422;color:var(--muted)}.t-completata{background:#1F9D5522;color:var(--verde-scuro)}.t-no_show{background:#B3261E22;color:#B3261E}
#login-box{max-width:360px;margin:60px auto;background:var(--card);border:1px solid var(--line);border-radius:10px;padding:20px}
#login-box h2{margin-top:0;font-size:16px}
#login-box input{width:100%;margin-bottom:8px}
#login-box .err{color:#B3261E;font-size:13px;min-height:18px}
#login-box .switch{text-align:center;font-size:13px;color:var(--muted);cursor:pointer;text-decoration:underline;margin-top:6px}
.hidden{display:none !important}
</style></head><body>
<header id="app-header" class="hidden"><b>🏆 Campolibero</b><button id="esci">Esci</button></header>
<main id="app-main" class="hidden">
  <div class="pannello">
    <h3>➕ Nuova risorsa</h3>
    <div class="riga">
      <input id="r-nome" placeholder="Nome (es. Campo Padel 1)">
      <select id="r-sport"></select>
      <input id="r-durata" type="number" value="60" placeholder="minuti/slot" style="width:110px">
      <input id="r-prezzo" type="number" placeholder="€/ora" style="width:90px">
      <button id="r-crea">Aggiungi</button>
    </div>
  </div>
  <div class="pannello">
    <h3>📅 Disponibilità</h3>
    <div class="riga">
      <input id="d-giorno" type="date">
      <select id="d-sport"></select>
      <button id="d-cerca">Cerca slot liberi</button>
    </div>
    <div id="d-risultati"></div>
  </div>
  <div class="pannello">
    <h3>📋 Prenotazioni di oggi</h3>
    <div id="lista-prenotazioni"></div>
  </div>
</main>
<div id="prenota-box" class="hidden" style="position:fixed;inset:0;background:#0008;display:flex;align-items:center;justify-content:center">
  <div style="background:var(--card);border-radius:10px;padding:20px;max-width:320px;width:100%">
    <h3 style="margin-top:0">Prenota lo slot</h3>
    <input id="p-nome" placeholder="Nome cliente" style="width:100%;margin-bottom:8px">
    <input id="p-telefono" placeholder="Telefono" style="width:100%;margin-bottom:8px">
    <div style="display:flex;gap:8px;justify-content:flex-end">
      <button id="p-annulla" style="background:var(--muted)">Annulla</button>
      <button id="p-conferma">Conferma</button>
    </div>
  </div>
</div>
<div id="login-box">
  <h2 id="login-titolo">Accedi alla struttura</h2>
  <div class="err" id="login-err"></div>
  <input id="l-nome" class="hidden" placeholder="Nome struttura">
  <input id="l-citta" class="hidden" placeholder="Città">
  <input id="l-email" placeholder="Email" type="email">
  <input id="l-password" placeholder="Password" type="password">
  <input id="l-telefono" class="hidden" placeholder="Telefono">
  <button id="l-submit" style="width:100%">Accedi</button>
  <div class="switch" id="l-switch">Non hai un account? Registra la tua struttura</div>
</div>
<script>
const SPORT = ["padel","calcio_a_5","tennis","squash","corso_fitness","personal_trainer","altro"];
for (const sel of [document.getElementById('r-sport'), document.getElementById('d-sport')]) {
  for (const s of SPORT) { const o=document.createElement('option'); o.value=s; o.textContent=s.replace(/_/g,' '); sel.appendChild(o); }
}
document.getElementById('d-giorno').valueAsDate = new Date();

let modoRegistrazione=false, slotSelezionato=null;
function token(){return localStorage.getItem('campolibero_token')}
function auth(opts={}){opts.headers=Object.assign({'Authorization':'Bearer '+token()},opts.headers||{});return opts}
function mostraApp(mostra){
  document.getElementById('app-header').classList.toggle('hidden',!mostra);
  document.getElementById('app-main').classList.toggle('hidden',!mostra);
  document.getElementById('login-box').classList.toggle('hidden',mostra);
}
document.getElementById('l-switch').addEventListener('click',()=>{
  modoRegistrazione=!modoRegistrazione;
  document.getElementById('login-titolo').textContent=modoRegistrazione?'Registra la tua struttura':'Accedi alla struttura';
  document.getElementById('l-submit').textContent=modoRegistrazione?'Registra':'Accedi';
  document.getElementById('l-switch').textContent=modoRegistrazione?'Hai già un account? Accedi':'Non hai un account? Registra la tua struttura';
  for (const id of ['l-nome','l-citta','l-telefono']) document.getElementById(id).classList.toggle('hidden',!modoRegistrazione);
  document.getElementById('login-err').textContent='';
});
document.getElementById('l-submit').addEventListener('click',async()=>{
  const g=id=>document.getElementById(id).value;
  const corpo=modoRegistrazione
    ?{nome:g('l-nome'),citta:g('l-citta'),email:g('l-email'),password:g('l-password'),telefono:g('l-telefono')}
    :{email:g('l-email'),password:g('l-password')};
  const res=await fetch(modoRegistrazione?'/auth/registra':'/auth/login',{method:'POST',body:JSON.stringify(corpo)});
  const dati=await res.json();
  if(!res.ok){document.getElementById('login-err').textContent=dati.errore||'errore';return}
  localStorage.setItem('campolibero_token',dati.token);
  mostraApp(true);caricaPrenotazioniOggi();
});
document.getElementById('esci').addEventListener('click',()=>{localStorage.removeItem('campolibero_token');mostraApp(false)});

document.getElementById('r-crea').addEventListener('click',async()=>{
  const g=id=>document.getElementById(id).value;
  await fetch('/risorse',auth({method:'POST',body:JSON.stringify({nome:g('r-nome'),sport:g('r-sport'),durata_slot_min:+g('r-durata'),prezzo_orario:+g('r-prezzo')})}));
  document.getElementById('r-nome').value='';document.getElementById('r-prezzo').value='';
});

document.getElementById('d-cerca').addEventListener('click',async()=>{
  const giorno=document.getElementById('d-giorno').value;
  const sport=document.getElementById('d-sport').value;
  const risorse=await (await fetch('/disponibilita?giorno='+giorno+'&sport='+sport,auth())).json();
  const el=document.getElementById('d-risultati');el.innerHTML='';
  for(const r of risorse){
    const box=document.createElement('div');box.style.marginBottom='10px';
    box.innerHTML=`<b>${r.nome}</b> <span style="color:var(--muted)">(${r.prezzo_orario}€/h)</span>`;
    const griglia=document.createElement('div');griglia.className='slots';griglia.style.marginTop='6px';
    for(const s of r.slot_liberi){
      const d=document.createElement('div');d.className='slot';d.textContent=s.slice(11,16);
      d.onclick=()=>{slotSelezionato={risorsa_id:r.risorsa_id,inizio:s};document.getElementById('prenota-box').classList.remove('hidden')};
      griglia.appendChild(d);
    }
    box.appendChild(griglia);el.appendChild(box);
  }
});
document.getElementById('p-annulla').addEventListener('click',()=>document.getElementById('prenota-box').classList.add('hidden'));
document.getElementById('p-conferma').addEventListener('click',async()=>{
  const g=id=>document.getElementById(id).value;
  const res=await fetch('/prenotazioni',auth({method:'POST',body:JSON.stringify({
    risorsa_id:slotSelezionato.risorsa_id, inizio:slotSelezionato.inizio,
    nome_cliente:g('p-nome'), telefono_cliente:g('p-telefono'),
  })}));
  const dati=await res.json();
  document.getElementById('prenota-box').classList.add('hidden');
  if(res.ok && dati.richiede_deposito){ alert('Prenotazione in attesa di deposito. Link inviato via SMS: '+dati.url_deposito); }
  document.getElementById('d-cerca').click();
  caricaPrenotazioniOggi();
});

async function caricaPrenotazioniOggi(){
  const oggi=new Date().toISOString().slice(0,10);
  const lista=await (await fetch('/prenotazioni?giorno='+oggi,auth())).json();
  const el=document.getElementById('lista-prenotazioni');el.innerHTML='';
  if(!lista.length){el.innerHTML='<p style="color:var(--muted);font-size:14px">Nessuna prenotazione per oggi.</p>';return}
  for(const p of lista){
    const d=document.createElement('div');d.className='job';
    d.innerHTML=`<span>${p.inizio.slice(11,16)} · ${p.risorsa} · ${p.cliente}</span><span class="tag t-${p.stato}">${p.stato.replace('_',' ')}</span>`;
    el.appendChild(d);
  }
}
if(token()){mostraApp(true);caricaPrenotazioniOggi()}else{mostraApp(false)}
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

    def _struttura(self):
        pulisci_sessioni()
        return struttura_da_token(self.headers)

    def _webhook_stripe(self):
        """Stripe non conosce i nostri token di sessione: l'autenticità
        della richiesta si verifica con la firma Stripe-Signature, non con
        Authorization — senza questo controllo chiunque potrebbe fingere un
        deposito mai pagato e sbloccare uno slot senza versare nulla."""
        n = int(self.headers.get("Content-Length") or 0)
        corpo_raw = self.rfile.read(n).decode("utf-8")
        cfg_mock = os.environ.get("STRIPE_WEBHOOK_SECRET", "MOCK_whsec_xxx").startswith("MOCK_")
        firma = self.headers.get("Stripe-Signature", "")
        if not cfg_mock and not valida_firma_stripe(corpo_raw, firma, os.environ.get("STRIPE_WEBHOOK_SECRET")):
            return self._json(403, {"errore": "firma Stripe non valida"})
        try:
            evento = json.loads(corpo_raw)
        except Exception:
            return self._json(400, {"errore": "corpo non valido"})
        if evento.get("type") != "checkout.session.completed":
            return self._json(200, {"ignorato": True})
        metadata = evento.get("data", {}).get("object", {}).get("metadata", {})
        try:
            prenotazione_id = int(metadata["prenotazione_id"])
            struttura_id = int(metadata["struttura_id"])
        except (KeyError, ValueError, TypeError):
            return self._json(400, {"errore": "metadata mancanti nell'evento"})
        try:
            return self._json(200, conferma_deposito_pagato(prenotazione_id, struttura_id))
        except LookupError as e:
            return self._json(404, {"errore": str(e)})

    def do_POST(self):
        import urllib.parse
        try:
            if self.path in ("/auth/registra", "/auth/login"):
                if _rate_limit_superato(_login_per_ip, self.client_address[0], LOGIN_RATE_LIMIT_MAX, LOGIN_RATE_LIMIT_FINESTRA_S):
                    return self._json(429, {"errore": "troppi tentativi, riprova più tardi"})
            if self.path == "/auth/registra":
                try:
                    return self._json(201, registra_struttura(self._body()))
                except ValueError as e:
                    return self._json(400, {"errore": str(e)})
            if self.path == "/auth/login":
                try:
                    return self._json(200, login(self._body()))
                except PermissionError as e:
                    return self._json(401, {"errore": str(e)})
            if self.path == "/webhook/stripe":
                return self._webhook_stripe()

            struttura_id = self._struttura()
            if struttura_id is None:
                return self._json(401, {"errore": "non autorizzato — serve login"})
            if self.path == "/risorse":
                return self._json(201, crea_risorsa(struttura_id, self._body()))
            if self.path == "/prenotazioni":
                return self._json(201, prenota(struttura_id, self._body()))
            self._json(404, {"errore": "endpoint sconosciuto"})
        except (ValueError, LookupError) as e:
            self._json(400, {"errore": str(e)})

    def do_PATCH(self):
        import re as _re
        m = _re.match(r"^/prenotazioni/(\d+)$", self.path)
        if not m:
            return self._json(404, {"errore": "endpoint sconosciuto"})
        struttura_id = self._struttura()
        if struttura_id is None:
            return self._json(401, {"errore": "non autorizzato — serve login"})
        try:
            dati = self._body()
            self._json(200, aggiorna_stato_prenotazione(int(m.group(1)), struttura_id, dati["stato"]))
        except LookupError as e:
            self._json(404, {"errore": str(e)})
        except (ValueError, KeyError) as e:
            self._json(400, {"errore": str(e)})

    def do_GET(self):
        import urllib.parse
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(WEB_HTML.encode())
            return

        try:
            if parsed.path == "/rete":
                if _rate_limit_superato(_rete_per_ip, self.client_address[0], RETE_RATE_LIMIT_MAX, RETE_RATE_LIMIT_FINESTRA_S):
                    return self._json(429, {"errore": "troppe richieste, riprova più tardi"})
                from rete_disponibilita import cerca_nella_rete
                sport = (qs.get("sport") or [None])[0]
                citta = (qs.get("citta") or [None])[0]
                inizio = (qs.get("inizio") or [None])[0]
                escludi = (qs.get("escludi_struttura_id") or [None])[0]
                if not (sport and citta and inizio):
                    return self._json(400, {"errore": "servono sport, citta, inizio"})
                return self._json(200, cerca_nella_rete(
                    sport, citta, datetime.datetime.fromisoformat(inizio),
                    escludi_struttura_id=int(escludi) if escludi else None,
                ))

            struttura_id = self._struttura()
            if struttura_id is None:
                return self._json(401, {"errore": "non autorizzato — serve login"})
            if parsed.path == "/risorse":
                return self._json(200, lista_risorse(struttura_id))
            if parsed.path == "/disponibilita":
                giorno = (qs.get("giorno") or [None])[0]
                sport = (qs.get("sport") or [None])[0]
                if not giorno:
                    return self._json(400, {"errore": "serve il parametro giorno"})
                return self._json(200, disponibilita(struttura_id, giorno, sport))
            if parsed.path == "/prenotazioni":
                giorno = (qs.get("giorno") or [None])[0]
                return self._json(200, lista_prenotazioni(struttura_id, giorno))
            self._json(404, {"errore": "endpoint sconosciuto"})
        except ValueError as e:
            self._json(400, {"errore": f"parametro non valido: {e}"})

    def log_message(self, fmt, *args):
        print(f"  {self.command} {self.path}")


def selftest():
    global DB
    DB = "campolibero_test.db"
    if os.path.exists(DB):
        os.remove(DB)
    SESSIONI.clear()

    reg = registra_struttura({"nome": "Padel Milano Nord", "citta": "Milano", "email": "info@padelnord.test", "password": "passwordStruttura1", "telefono": "02 1234567"})
    struttura_id = reg["struttura"]["id"]

    try:
        registra_struttura({"nome": "Altra", "citta": "Milano", "email": "info@padelnord.test", "password": "altra12345", "telefono": "02 0000000"})
        raise AssertionError("email duplicata avrebbe dovuto fallire")
    except ValueError:
        pass

    try:
        login({"email": "info@padelnord.test", "password": "sbagliata"})
        raise AssertionError("login con password sbagliata avrebbe dovuto fallire")
    except PermissionError:
        pass

    accesso = login({"email": "INFO@padelnord.test  ".strip(), "password": "passwordStruttura1"})
    assert accesso["struttura"]["id"] == struttura_id

    campo = crea_risorsa(struttura_id, {"nome": "Campo Padel 1", "sport": "padel", "durata_slot_min": 90, "prezzo_orario": 30})

    try:
        crea_risorsa(struttura_id, {"nome": "Campo X", "sport": "scacchi", "prezzo_orario": 10})
        raise AssertionError("sport non valido avrebbe dovuto fallire")
    except ValueError:
        pass

    giorno = "2026-08-10"
    disp = disponibilita(struttura_id, giorno, "padel")
    assert disp[0]["slot_liberi"], "dovrebbero esserci slot liberi il giorno scelto"
    primo_slot = disp[0]["slot_liberi"][0]

    p = prenota(struttura_id, {"risorsa_id": campo["id"], "nome_cliente": "Luca Bianchi", "telefono_cliente": "+393331112222", "inizio": primo_slot})
    assert p["stato"] in ("confermata", "in_attesa_deposito")

    # lo stesso slot ora deve risultare occupato
    disp2 = disponibilita(struttura_id, giorno, "padel")
    assert primo_slot not in disp2[0]["slot_liberi"], "lo slot appena prenotato non dovrebbe più essere libero"

    # una seconda prenotazione sullo stesso slot deve fallire (niente doppie prenotazioni)
    try:
        prenota(struttura_id, {"risorsa_id": campo["id"], "nome_cliente": "Altro Cliente", "telefono_cliente": "+393339998888", "inizio": primo_slot})
        raise AssertionError("una doppia prenotazione sullo stesso slot avrebbe dovuto fallire")
    except ValueError:
        pass

    lista = lista_prenotazioni(struttura_id, giorno)
    assert len(lista) == 1 and lista[0]["cliente"] == "Luca Bianchi"

    completata = aggiorna_stato_prenotazione(p["id"], struttura_id, "completata")
    assert completata["stato"] == "completata"

    # isolamento multi-tenant: una seconda struttura non vede nulla della prima
    reg2 = registra_struttura({"nome": "Tennis Club Roma", "citta": "Roma", "email": "info@tennisroma.test", "password": "passwordAltra1", "telefono": "06 7654321"})
    struttura_id_2 = reg2["struttura"]["id"]
    assert lista_prenotazioni(struttura_id_2) == []
    try:
        aggiorna_stato_prenotazione(p["id"], struttura_id_2, "no_show")
        raise AssertionError("una struttura non deve poter modificare la prenotazione di un'altra")
    except LookupError:
        pass

    print("Flusso: registrazione → login → risorsa → disponibilità → prenotazione → isolamento dati ✅")
    os.remove(DB)
    print("✅ SELFTEST OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        print(f"🏆 Campolibero — API su :8040 (db: {DB})")
        HTTPServer(("", 8040), Handler).serve_forever()
