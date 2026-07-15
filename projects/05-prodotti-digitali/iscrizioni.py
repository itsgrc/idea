#!/usr/bin/env python3
"""Iscrizioni newsletter — double opt-in reale (zero dipendenze).

Colma il vuoto più ovvio di "Cantiere Aperto": la newsletter esisteva solo
come testo (`NUMERO-ZERO.md`), senza alcun modo per qualcuno di iscriversi
davvero. Questo backend (http.server + sqlite3, libreria standard) riceve
l'iscrizione, invia un'email di conferma con link (double opt-in — lo
richiede il GDPR/la prassi anti-spam: un'email da sola non è consenso
verificato) e gestisce la disiscrizione con un token dedicato.

Endpoints:
    POST /iscrivi     {email}          -> invia email di conferma
    GET  /conferma?token=...           -> conferma l'iscrizione
    GET  /disiscrivi?token=...         -> cancella l'iscrizione (immediata)
    GET  /iscritti      [richiede X-Api-Key: NEWSLETTER_API_KEY]
                                        -> lista email confermate (per l'invio)

Uso:
    python3 iscrizioni.py             # serve su :8020
    python3 iscrizioni.py --demo      # iscrizione + conferma + disiscrizione, mostra il flusso
"""
import datetime
import hmac
import json
import os
import re
import secrets
import smtplib
import sqlite3
import sys
import urllib.parse
from email.mime.text import MIMEText
from http.server import BaseHTTPRequestHandler, HTTPServer

DB = os.environ.get("NEWSLETTER_DB", "newsletter.db")
PORTA = int(os.environ.get("NEWSLETTER_PORT", "8020"))
EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

# Stessa logica del LEAD_API_KEY nel progetto 03: senza chiave, chiunque
# scoprisse l'URL potrebbe scaricare l'intera lista email degli iscritti.
NEWSLETTER_API_KEY = os.environ.get("NEWSLETTER_API_KEY", "MOCK_cambia_questa_chiave_prima_di_andare_live")

RATE_LIMIT_MAX = int(os.environ.get("NEWSLETTER_RATE_LIMIT", "5"))
RATE_LIMIT_FINESTRA_S = 3600
_iscrizioni_per_ip = {}

# Le iscrizioni MAI confermate (double opt-in non completato) non sono
# consenso: non vanno tenute all'infinito. Data minimization (GDPR art. 5).
PENDING_MAX_ETA_GIORNI = 7

SCHEMA = """
CREATE TABLE IF NOT EXISTS iscritti (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    stato TEXT NOT NULL DEFAULT 'in_attesa',
    token_conferma TEXT NOT NULL,
    token_disiscrizione TEXT NOT NULL,
    iscritto_il TEXT DEFAULT CURRENT_TIMESTAMP,
    confermato_il TEXT
);
"""


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def rate_limit_superato(ip):
    ora = datetime.datetime.now().timestamp()
    invii = [t for t in _iscrizioni_per_ip.get(ip, []) if ora - t < RATE_LIMIT_FINESTRA_S]
    invii.append(ora)
    _iscrizioni_per_ip[ip] = invii
    return len(invii) > RATE_LIMIT_MAX


def richiesta_autorizzata(handler):
    """Come in lead_capture.py (progetto 03): con la chiave ancora al
    valore MOCK_, l'accesso è SEMPRE negato, perché questo è codice
    pubblico e un default "reale" sarebbe un segreto letto da chiunque."""
    if NEWSLETTER_API_KEY.startswith("MOCK_"):
        return False
    fornita = handler.headers.get("X-Api-Key", "")
    return hmac.compare_digest(fornita, NEWSLETTER_API_KEY)


def smtp_config():
    return {
        "host": os.environ.get("SMTP_HOST", "MOCK_smtp.esempio.it"),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER", "MOCK_info@cantiereaperto.test"),
        "password": os.environ.get("SMTP_PASSWORD", "MOCK_password"),
        "mittente": os.environ.get("SMTP_MITTENTE", "MOCK_info@cantiereaperto.test"),
    }


def e_mock(cfg):
    return any(str(v).startswith("MOCK_") for v in cfg.values())


def url_base():
    return os.environ.get("NEWSLETTER_PUBLIC_URL", "http://localhost:8020")


def _invia_email(destinatario, oggetto, corpo):
    cfg = smtp_config()
    if e_mock(cfg):
        print(f"📧 [SIMULATO — credenziali SMTP mock] a {destinatario}:\n   oggetto: {oggetto}\n   {corpo}\n")
        return
    msg = MIMEText(corpo, "plain", "utf-8")
    msg["Subject"] = oggetto
    msg["From"] = cfg["mittente"]
    msg["To"] = destinatario
    with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
        server.starttls()
        server.login(cfg["user"], cfg["password"])
        server.send_message(msg)


def pulisci_pendenti():
    """Cancella le iscrizioni mai confermate oltre PENDING_MAX_ETA_GIORNI:
    un'email da sola non è consenso, quindi non ha senso conservarla a
    tempo indeterminato in attesa di una conferma che potrebbe non arrivare mai."""
    soglia = (datetime.datetime.now() - datetime.timedelta(days=PENDING_MAX_ETA_GIORNI)).isoformat()
    with db() as conn:
        conn.execute("DELETE FROM iscritti WHERE stato='in_attesa' AND iscritto_il < ?", (soglia,))


def iscrivi(email):
    email = email.lower().strip()
    if not email or not EMAIL_REGEX.match(email):
        raise ValueError("email mancante o non valida")
    pulisci_pendenti()
    token_conferma = secrets.token_urlsafe(24)
    token_disiscrizione = secrets.token_urlsafe(24)
    with db() as conn:
        esistente = conn.execute("SELECT * FROM iscritti WHERE email=?", (email,)).fetchone()
        if esistente and esistente["stato"] == "confermato":
            return {"gia_iscritto": True}
        if esistente:
            conn.execute(
                "UPDATE iscritti SET token_conferma=?, iscritto_il=CURRENT_TIMESTAMP WHERE email=?",
                (token_conferma, email),
            )
        else:
            conn.execute(
                "INSERT INTO iscritti (email, token_conferma, token_disiscrizione) VALUES (?,?,?)",
                (email, token_conferma, token_disiscrizione),
            )
    link = f"{url_base()}/conferma?token={urllib.parse.quote(token_conferma)}"
    try:
        _invia_email(
            email,
            "Conferma la tua iscrizione a Cantiere Aperto",
            f"Un click per confermare l'iscrizione (double opt-in, come richiede il GDPR):\n\n{link}\n\n"
            "Se non hai richiesto tu questa iscrizione, ignora questa email: senza conferma, "
            f"i tuoi dati vengono cancellati automaticamente entro {PENDING_MAX_ETA_GIORNI} giorni.",
        )
    except Exception as e:
        # La riga in "in_attesa" è già salvata: un SMTP momentaneamente giù
        # non deve far sembrare fallita l'intera richiesta all'utente, che
        # ha comunque fatto la sua parte correttamente.
        print(f"⚠️  invio email di conferma fallito (l'iscrizione resta in attesa): {e}")
    return {"in_attesa_di_conferma": True}


def conferma(token):
    with db() as conn:
        riga = conn.execute("SELECT * FROM iscritti WHERE token_conferma=?", (token,)).fetchone()
        if not riga:
            raise LookupError("token non valido o già usato")
        conn.execute(
            "UPDATE iscritti SET stato='confermato', confermato_il=CURRENT_TIMESTAMP WHERE id=?",
            (riga["id"],),
        )
    return {"confermato": True, "email": riga["email"]}


def disiscrivi(token):
    with db() as conn:
        riga = conn.execute("SELECT * FROM iscritti WHERE token_disiscrizione=?", (token,)).fetchone()
        if not riga:
            raise LookupError("token non valido")
        # Cancellazione immediata, non solo cambio di stato: la disiscrizione
        # è già una richiesta di cancellazione (art. 17 GDPR), non serve che
        # l'utente lo chieda una seconda volta con un modulo separato.
        conn.execute("DELETE FROM iscritti WHERE id=?", (riga["id"],))
    return {"disiscritto": True}


def lista_confermati():
    with db() as conn:
        return [dict(r) for r in conn.execute("SELECT email, confermato_il FROM iscritti WHERE stato='confermato' ORDER BY confermato_il")]


class Handler(BaseHTTPRequestHandler):
    def _json(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(body, ensure_ascii=False).encode())

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        if self.path == "/iscrivi":
            if rate_limit_superato(self.client_address[0]):
                return self._json(429, {"errore": "troppe richieste, riprova più tardi"})
            n = int(self.headers.get("Content-Length") or 0)
            try:
                corpo = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                return self._json(400, {"errore": "corpo non valido"})
            try:
                return self._json(200, iscrivi(str(corpo.get("email", ""))))
            except ValueError as e:
                return self._json(400, {"errore": str(e)})
        self._json(404, {"errore": "endpoint sconosciuto"})

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        if parsed.path in ("/", "/homepage.html"):
            try:
                with open(os.path.join(os.path.dirname(__file__), "homepage.html"), "rb") as f:
                    html = f.read()
            except FileNotFoundError:
                return self._json(404, {"errore": "homepage.html non trovato"})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html)
            return
        if parsed.path == "/conferma":
            token = (qs.get("token") or [""])[0]
            try:
                return self._json(200, conferma(token))
            except LookupError as e:
                return self._json(404, {"errore": str(e)})
        if parsed.path == "/disiscrivi":
            token = (qs.get("token") or [""])[0]
            try:
                return self._json(200, disiscrivi(token))
            except LookupError as e:
                return self._json(404, {"errore": str(e)})
        if parsed.path == "/iscritti":
            if not richiesta_autorizzata(self):
                return self._json(401, {"errore": "non autorizzato — serve l'header X-Api-Key con NEWSLETTER_API_KEY"})
            return self._json(200, lista_confermati())
        self._json(404, {"errore": "endpoint sconosciuto"})

    def log_message(self, fmt, *args):
        print(f"  {self.command} {self.path}")


def demo():
    global DB
    DB = "newsletter-demo.db"
    if os.path.exists(DB):
        os.remove(DB)

    print("1) iscrizione:")
    iscrivi("lettore@esempio.test")
    with db() as conn:
        riga = conn.execute("SELECT * FROM iscritti WHERE email='lettore@esempio.test'").fetchone()
    print(f"   stato dopo l'iscrizione: {riga['stato']}")

    print("\n2) conferma (click sul link nell'email):")
    ris = conferma(riga["token_conferma"])
    print(f"   {ris}")

    print("\n3) lista iscritti confermati (endpoint /iscritti):")
    print(f"   {lista_confermati()}")

    print("\n4) disiscrizione (click sul link 'annulla iscrizione'):")
    with db() as conn:
        riga2 = conn.execute("SELECT * FROM iscritti WHERE email='lettore@esempio.test'").fetchone()
    ris2 = disiscrivi(riga2["token_disiscrizione"])
    print(f"   {ris2}")
    print(f"   lista dopo la disiscrizione: {lista_confermati()}")

    os.remove(DB)
    print("\n✅ DEMO OK — double opt-in + disiscrizione funzionano end-to-end")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        print(f"📬 Iscrizioni Cantiere Aperto su :{PORTA}")
        HTTPServer(("", PORTA), Handler).serve_forever()
