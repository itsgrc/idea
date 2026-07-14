#!/usr/bin/env python3
"""Invio — spedisce davvero le email generate da campagna.py, via SMTP.

campagna.py produce testo. Questo script lo spedisce per posta elettronica
reale — smtplib della libreria standard, zero dipendenze esterne. Con
credenziali SMTP ancora mock (.env non configurato), resta in DRY-RUN:
stampa cosa avrebbe inviato, non tocca la rete. Con credenziali vere,
invia davvero — e SOLO se richiami esplicitamente con --conferma, per
non spedire mai per errore durante un test.

Uso:
    python3 invio.py --demo                       # dry-run sulla campagna demo
    python3 invio.py campagna-2026-07-14.md        # dry-run su un file reale
    python3 invio.py campagna-2026-07-14.md --conferma   # invio VERO (richiede .env)
"""
import os
import re
import smtplib
import sys
from email.mime.text import MIMEText


def leggi_config():
    return {
        "host": os.environ.get("SMTP_HOST", "MOCK_smtp.esempio.it"),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": os.environ.get("SMTP_USER", "MOCK_info@tuastudio.it"),
        "password": os.environ.get("SMTP_PASSWORD", "MOCK_password"),
        "mittente": os.environ.get("SMTP_MITTENTE", "MOCK_info@tuastudio.it"),
    }


def e_mock(config):
    return any(str(v).startswith("MOCK_") for v in config.values())


def estrai_email(testo_campagna):
    """Spacchetta il file campagna-*.md nei singoli messaggi (uno per prospect).
    L'indirizzo email arriva dal CSV originale (campagna.py lo stampa tra
    < >): nessun indirizzo indovinato, solo quello che il titolare ha
    davvero fornito nel proprio elenco contatti."""
    blocchi = testo_campagna.split("=" * 66)
    messaggi = []
    for b in blocchi:
        m = re.search(r"A:\s*(.+?)\s*<(.+?)>\s*—\s*(.+)\nOggetto:\s*(.+)\n-{10,}\n(.+)", b, re.S)
        if m:
            destinatario_nome, indirizzo, azienda, oggetto, corpo = m.groups()
            messaggi.append({
                "destinatario_nome": destinatario_nome.strip(),
                "indirizzo": indirizzo.strip(),
                "azienda": azienda.strip(),
                "oggetto": oggetto.strip(),
                "corpo": corpo.strip(),
            })
    return messaggi


def invia(config, messaggio, a_indirizzo):
    msg = MIMEText(messaggio["corpo"], "plain", "utf-8")
    msg["Subject"] = messaggio["oggetto"]
    msg["From"] = config["mittente"]
    msg["To"] = a_indirizzo
    with smtplib.SMTP(config["host"], config["port"]) as server:
        server.starttls()
        server.login(config["user"], config["password"])
        server.send_message(msg)


DEMO_CAMPAGNA = """
==================================================================
A: Sig. Rossi <rossi@esempio-mecc.test> — Meccanica Rossi Srl
Oggetto: 10.000 € potenziali per Meccanica Rossi Srl
------------------------------------------------------------------
Buongiorno Sig. Rossi,

email di esempio generata da campagna.py --demo.
==================================================================
"""


def main():
    if "--demo" in sys.argv:
        testo = DEMO_CAMPAGNA
    else:
        percorso = next((a for a in sys.argv[1:] if not a.startswith("--")), None)
        if not percorso:
            sys.exit("Uso: python3 invio.py --demo | campagna.md [--conferma]")
        with open(percorso, encoding="utf-8") as f:
            testo = f.read()

    config = leggi_config()
    messaggi = estrai_email(testo)
    conferma = "--conferma" in sys.argv

    print(f"\n📤 {len(messaggi)} email trovate nel file.\n")

    if e_mock(config):
        print("🟡 DRY-RUN — credenziali SMTP ancora MOCK (vedi .env.example): nessuna email verrà inviata davvero.\n")
    elif not conferma:
        print("🟡 DRY-RUN — credenziali reali rilevate ma manca --conferma: aggiungi --conferma per inviare davvero.\n")
    else:
        print("🔴 INVIO REALE — le email partiranno per davvero.\n")

    for m in messaggi:
        azione = "invierei" if (e_mock(config) or not conferma) else "sto inviando"
        print(f"  → {azione} a {m['destinatario_nome']} <{m['indirizzo']}> — oggetto: \"{m['oggetto']}\"")
        if not e_mock(config) and conferma:
            invia(config, m, m["indirizzo"])

    print(f"\n{'✅ Simulazione completata (nessuna email reale inviata).' if (e_mock(config) or not conferma) else '✅ Invio reale completato.'}")


if __name__ == "__main__":
    main()
