#!/usr/bin/env python3
"""Adapter SMS — proposta al professionista e conferma al cliente (zero dipendenze).

Stesso pattern degli altri progetti del portfolio: finché le credenziali
Twilio in .env restano "MOCK_..." (default), l'invio è SIMULATO (loggato,
nessuna chiamata di rete). Con credenziali vere, la stessa funzione invia
un SMS vero — solo urllib della libreria standard.
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


def invia_sms_proposta(telefono_professionista, richiesta):
    urgenza_label = "🚨 URGENTE" if richiesta["urgenza"] == "urgente" else "Nuova richiesta"
    testo = (
        f"{urgenza_label} — {richiesta['categoria']} a {richiesta['citta']}: {richiesta['descrizione']}. "
        f"Accetti? Rispondi dall'app ProntoCasa entro il tempo indicato, altrimenti passa al prossimo disponibile."
    )
    return _invia_sms(telefono_professionista, testo)


def invia_sms_conferma_cliente(telefono_cliente, professionista):
    testo = (
        f"Il tuo {professionista['categoria']} è confermato: {professionista['nome']}, "
        f"{professionista['telefono']}. Ti contatterà a breve."
    )
    return _invia_sms(telefono_cliente, testo)


if __name__ == "__main__":
    print(invia_sms_proposta("+393331234567", {
        "categoria": "idraulico", "citta": "Milano", "descrizione": "perdita rubinetto", "urgenza": "urgente",
    }))
