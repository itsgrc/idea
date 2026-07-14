#!/usr/bin/env python3
"""Lead Capture — serve assessment.html e riceve davvero i contatti.

Colma il vuoto "lead-gen" segnalato in Control Room: prima l'assessment
finiva in un mailto (nessun dato salvato se il chiamante non invia
manualmente). Ora un server minimale (zero dipendenze: http.server della
libreria standard) serve la pagina e riceve i lead via POST /lead,
salvandoli in un log JSONL e — con credenziali SMTP reali — inviando una
notifica email vera al titolare. Con credenziali ancora mock, la notifica
è simulata (loggata), il salvataggio del lead invece è SEMPRE reale.

Uso:
    python3 lead_capture.py            # serve su :8010
    python3 lead_capture.py --demo     # invia un lead di prova e mostra il log
"""
import json
import os
import smtplib
import sys
import datetime
from email.mime.text import MIMEText
from http.server import BaseHTTPRequestHandler, HTTPServer

LEAD_LOG = os.environ.get("LEAD_LOG", "lead.jsonl")
PORTA = int(os.environ.get("LEAD_PORT", "8010"))


def smtp_config():
    return {
        "host": os.environ.get("SMTP_HOST", "MOCK_smtp.esempio.it"),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER", "MOCK_info@tuostudio.it"),
        "password": os.environ.get("SMTP_PASSWORD", "MOCK_password"),
        "mittente": os.environ.get("SMTP_MITTENTE", "MOCK_info@tuostudio.it"),
        "destinatario": os.environ.get("NOTIFICA_LEAD_A", "MOCK_te@tuostudio.it"),
    }


def e_mock(cfg):
    return any(str(v).startswith("MOCK_") for v in cfg.values())


def notifica_nuovo_lead(lead):
    cfg = smtp_config()
    corpo = (
        f"Nuovo lead dall'assessment EU AI Act:\n\n"
        f"Email: {lead.get('email')}\n"
        f"Classificazione: {lead.get('livello')}\n"
        f"Riferimento: {lead.get('riferimento') or 'n/d'}\n"
        f"Ricevuto: {lead.get('quando')}\n"
    )
    if e_mock(cfg):
        print(f"📧 [SIMULATO — credenziali SMTP mock] notifica nuovo lead:\n{corpo}")
        return
    msg = MIMEText(corpo, "plain", "utf-8")
    msg["Subject"] = f"Nuovo lead assessment — {lead.get('livello', 'n/d')}"
    msg["From"] = cfg["mittente"]
    msg["To"] = cfg["destinatario"]
    with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
        server.starttls()
        server.login(cfg["user"], cfg["password"])
        server.send_message(msg)


def salva_lead(lead):
    lead["ricevuto_il"] = datetime.datetime.now().isoformat()
    with open(LEAD_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(lead, ensure_ascii=False) + "\n")


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
        if self.path == "/lead":
            n = int(self.headers.get("Content-Length") or 0)
            try:
                lead = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                return self._json(400, {"errore": "corpo non valido"})
            if not lead.get("email"):
                return self._json(400, {"errore": "email mancante"})
            salva_lead(lead)
            try:
                notifica_nuovo_lead(lead)
            except Exception as e:
                print(f"⚠️  notifica email fallita (il lead è comunque salvato): {e}")
            return self._json(200, {"ok": True})
        self._json(404, {"errore": "endpoint sconosciuto"})

    def do_GET(self):
        if self.path in ("/", "/assessment.html"):
            try:
                with open(os.path.join(os.path.dirname(__file__), "assessment.html"), "rb") as f:
                    html = f.read()
            except FileNotFoundError:
                return self._json(404, {"errore": "assessment.html non trovato"})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html)
            return
        if self.path == "/leads":
            leads = []
            if os.path.exists(LEAD_LOG):
                with open(LEAD_LOG, encoding="utf-8") as f:
                    leads = [json.loads(r) for r in f if r.strip()]
            return self._json(200, leads)
        self._json(404, {"errore": "endpoint sconosciuto"})

    def log_message(self, fmt, *args):
        print(f"  {self.command} {self.path}")


def demo():
    global LEAD_LOG
    LEAD_LOG = "lead-demo.jsonl"
    if os.path.exists(LEAD_LOG):
        os.remove(LEAD_LOG)
    lead = {
        "email": "titolare@esempio-azienda.test",
        "livello": "ALTO RISCHIO",
        "riferimento": "Allegato III.4 — il caso più comune nelle PMI",
        "pagina": "assessment.html",
        "quando": datetime.datetime.now().isoformat(),
    }
    salva_lead(lead)
    notifica_nuovo_lead(lead)
    print(f"\n💾 Lead salvato in {LEAD_LOG}:")
    with open(LEAD_LOG) as f:
        print(f.read())
    os.remove(LEAD_LOG)


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        print(f"⚖️  Conforme — assessment + lead capture su :{PORTA}")
        HTTPServer(("", PORTA), Handler).serve_forever()
