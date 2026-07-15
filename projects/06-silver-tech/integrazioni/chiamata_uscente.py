#!/usr/bin/env python3
"""Chiamata uscente — l'unico pezzo che il progetto 01 non aveva ancora.

Il progetto 01 (Rispondo) gestisce chiamate IN ARRIVO: qualcuno chiama lo
studio. FiloDiretto ha bisogno del contrario: È il sistema a chiamare
l'assistito, ogni giorno alla stessa ora. Twilio gestisce questo con la
stessa identica infrastruttura (lo stesso account, lo stesso numero, lo
stesso webhook `/voice/incoming` di telefonia.js che genera il TwiML) —
serve solo originare la chiamata (`Calls.create`) invece di aspettarla, e
sapere cosa fare se l'assistito non risponde.

Uso tipico: uno scheduler (cron/systemd timer) esegue questo script ogni
giorno all'ora configurata:
    0 10 * * * cd /percorso/filodiretto && python3 integrazioni/chiamata_uscente.py

Con credenziali ancora mock: nessuna chiamata reale, solo un log di cosa
sarebbe successo (stesso pattern di tutti gli altri adapter del portfolio).
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def _config():
    return {
        "account_sid": os.environ.get("TWILIO_ACCOUNT_SID", "MOCK_ACCOUNT_SID"),
        "auth_token": os.environ.get("TWILIO_AUTH_TOKEN", "MOCK_AUTH_TOKEN"),
        "numero_da": os.environ.get("TWILIO_PHONE_NUMBER", "MOCK_+390000000000"),
        "numero_assistito": os.environ.get("FILODIRETTO_NUMERO_ASSISTITO", "MOCK_+393339998877"),
        "webhook_url": os.environ.get("FILODIRETTO_WEBHOOK_URL", "MOCK_https://tuoapp.esempio.it/voice/incoming"),
        "status_callback_url": os.environ.get("FILODIRETTO_STATUS_CALLBACK_URL", "MOCK_https://tuoapp.esempio.it/voice/stato-chiamata"),
    }


def _e_mock(cfg):
    return any(str(v).startswith("MOCK_") for v in cfg.values())


def avvia_chiamata_quotidiana():
    """Ritorna sempre {"simulato": bool, ...}: chi chiama (lo scheduler)
    deve sempre poter distinguere una chiamata vera da una loggata soltanto."""
    cfg = _config()
    if _e_mock(cfg):
        print(
            f"📵 [SIMULATO — credenziali Twilio mock] chiamata a {cfg['numero_assistito']} "
            f"con webhook {cfg['webhook_url']}"
        )
        return {"simulato": True}

    corpo = urllib.parse.urlencode({
        "To": cfg["numero_assistito"],
        "From": cfg["numero_da"],
        "Url": cfg["webhook_url"],
        "StatusCallback": cfg["status_callback_url"],
        # Vogliamo sapere in particolare i casi in cui NON risponde: sono
        # esattamente quelli che fanno scattare l'escalation (MVP-SPEC.md).
        "StatusCallbackEvent": "completed",
    }).encode()
    auth = base64.b64encode(f"{cfg['account_sid']}:{cfg['auth_token']}".encode()).decode()
    req = urllib.request.Request(
        f"https://api.twilio.com/2010-04-01/Accounts/{cfg['account_sid']}/Calls.json",
        data=corpo,
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            return {"simulato": False, "status": res.status, "body": res.read().decode()}
    except urllib.error.HTTPError as e:
        return {"simulato": False, "status": e.code, "body": e.read().decode()}


if __name__ == "__main__":
    print(json.dumps(avvia_chiamata_quotidiana(), ensure_ascii=False, indent=2))
