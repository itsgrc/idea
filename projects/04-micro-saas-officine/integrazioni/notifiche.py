#!/usr/bin/env python3
"""Adapter SMS — avvisa il cliente via Twilio quando il veicolo è pronto.

Stesso pattern del progetto 01 (notifiche.js): finché le credenziali in
.env sono ancora "MOCK_..." (default), l'invio è SIMULATO (loggato in
console, nessuna chiamata di rete, nessun credito speso). Con credenziali
Twilio vere, la stessa funzione fa una vera richiesta HTTPS — zero
dipendenze esterne, solo urllib della libreria standard.

Uso tipico (da app.py, quando uno stato passa a "pronto"):
    from integrazioni.notifiche import invia_sms_pronto
    invia_sms_pronto(intervento)
"""
import base64
import json
import os
import urllib.request
import urllib.parse
import urllib.error


def _config():
    return {
        "account_sid": os.environ.get("TWILIO_ACCOUNT_SID", "MOCK_ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"),
        "auth_token": os.environ.get("TWILIO_AUTH_TOKEN", "MOCK_authtoken"),
        "numero_da": os.environ.get("TWILIO_NUMERO_SMS", "MOCK_+15551234567"),
    }


def _e_mock(cfg):
    return any(str(v).startswith("MOCK_") for v in cfg.values())


def _invia_sms(numero_a, testo):
    """Ritorna sempre {"simulato": bool, ...} così chi chiama sa se è
    successo davvero o solo stato loggato."""
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


def invia_sms_pronto(intervento):
    """intervento: dict con almeno targa, modello, telefono (del cliente)."""
    testo = (
        f"Ciao! Il tuo veicolo {intervento.get('modello', '')} (targa {intervento.get('targa', '')}) "
        f"è pronto per il ritiro. Ti aspettiamo in officina."
    )
    return _invia_sms(intervento.get("telefono"), testo)


def invia_sms_richiamo(veicolo, tipo_intervento, giorni_da_ultimo):
    """Usato da richiami.py per il promemoria di tagliando/revisione."""
    testo = (
        f"Ciao! Sono passati {giorni_da_ultimo} giorni dall'ultimo {tipo_intervento} "
        f"del tuo veicolo (targa {veicolo.get('targa', '')}). Vuoi prenotare un controllo?"
    )
    return _invia_sms(veicolo.get("telefono"), testo)


if __name__ == "__main__":
    print(json.dumps(invia_sms_pronto({
        "targa": "AB123CD", "modello": "Panda 1.2", "telefono": "+393331234567",
    }), ensure_ascii=False, indent=2))
