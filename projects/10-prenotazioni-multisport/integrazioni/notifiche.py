#!/usr/bin/env python3
"""Adapter SMS — conferma prenotazione e promemoria (zero dipendenze).

Stesso pattern usato nei progetti 04 e 06: finché le credenziali Twilio in
.env restano "MOCK_..." (default), l'invio è SIMULATO (loggato, nessuna
chiamata di rete). Con credenziali vere, la stessa funzione invia un SMS
vero — solo urllib della libreria standard, zero dipendenze npm/pip.
"""
import base64
import os
import urllib.error
import urllib.parse
import urllib.request


def _config():
    return {
        "account_sid": os.environ.get("TWILIO_ACCOUNT_SID", "MOCK_ACCOUNT_SID"),
        "auth_token": os.environ.get("TWILIO_AUTH_TOKEN", "MOCK_AUTH_TOKEN"),
        "numero_da": os.environ.get("TWILIO_NUMERO_SMS", "MOCK_+390000000000"),
    }


def _e_mock(cfg):
    return any(str(v).startswith("MOCK_") for v in cfg.values())


def _invia_sms(numero_a, testo):
    cfg = _config()
    if _e_mock(cfg):
        print(f"📵 [SIMULATO — credenziali Twilio mock] SMS a {numero_a}:\n   \"{testo}\"")
        return {"simulato": True, "testo": testo}

    corpo = urllib.parse.urlencode({"From": cfg["numero_da"], "To": numero_a, "Body": testo}).encode()
    auth = base64.b64encode(f"{cfg['account_sid']}:{cfg['auth_token']}".encode()).decode()
    req = urllib.request.Request(
        f"https://api.twilio.com/2010-04-01/Accounts/{cfg['account_sid']}/Messages.json",
        data=corpo,
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return {"simulato": False, "status": res.status, "body": res.read().decode()}
    except urllib.error.HTTPError as e:
        return {"simulato": False, "status": e.code, "body": e.read().decode()}


def invia_sms_conferma(telefono, nome_risorsa, inizio, richiede_deposito=False, importo_deposito=None, url_deposito=None):
    quando = inizio.strftime("%A %d/%m alle %H:%M")
    if richiede_deposito:
        link = f" {url_deposito}" if url_deposito else ""
        testo = (
            f"Prenotazione {nome_risorsa} per {quando} in attesa di conferma: "
            f"versa un deposito di {importo_deposito}€ per bloccare lo slot.{link}"
        )
    else:
        testo = f"Prenotazione confermata: {nome_risorsa}, {quando}. A presto!"
    return _invia_sms(telefono, testo)


def invia_sms_promemoria(telefono, nome_risorsa, inizio):
    quando = inizio.strftime("%H:%M")
    testo = f"Promemoria: oggi alle {quando} hai {nome_risorsa}. Ti aspettiamo!"
    return _invia_sms(telefono, testo)


if __name__ == "__main__":
    import datetime
    print(invia_sms_conferma("+393331234567", "Campo Padel 1", datetime.datetime.now() + datetime.timedelta(days=1)))
