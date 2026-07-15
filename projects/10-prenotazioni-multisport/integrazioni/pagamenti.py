#!/usr/bin/env python3
"""Adapter pagamenti — deposito via Stripe Checkout (zero dipendenze).

Quando rischio_noshow.py chiede un deposito, questo modulo crea una
sessione di pagamento Stripe Checkout (una richiesta HTTPS + Basic Auth
con la chiave segreta — zero SDK, solo urllib) e ritorna l'URL a cui
mandare il cliente via SMS. Nessun bisogno di Stripe.js lato client: il
cliente paga su una pagina ospitata da Stripe, poi torna sul sito.

Finché STRIPE_SECRET_KEY resta "MOCK_..." (default), nessuna chiamata
reale: viene restituito un URL finto, utile per provare il flusso.

Conferma del pagamento: Stripe manda un webhook (evento
"checkout.session.completed") a POST /webhook/stripe — la firma va
validata con STRIPE_WEBHOOK_SECRET (vedi valida_firma_stripe), altrimenti
chiunque potrebbe fingere un pagamento mai avvenuto e sbloccare uno slot.
"""
import base64
import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request


def _config():
    return {
        "secret_key": os.environ.get("STRIPE_SECRET_KEY", "MOCK_sk_test_xxx"),
        "webhook_secret": os.environ.get("STRIPE_WEBHOOK_SECRET", "MOCK_whsec_xxx"),
        "success_url": os.environ.get("STRIPE_SUCCESS_URL", "MOCK_https://tuoapp.esempio.it/pagamento-ok"),
        "cancel_url": os.environ.get("STRIPE_CANCEL_URL", "MOCK_https://tuoapp.esempio.it/pagamento-annullato"),
    }


def _e_mock(cfg):
    return any(str(v).startswith("MOCK_") for v in cfg.values())


def crea_sessione_deposito(prenotazione_id, importo_eur, descrizione, struttura_id=None):
    """Ritorna {"simulato": bool, "url_pagamento": str, ...}."""
    cfg = _config()
    if _e_mock(cfg):
        url_finta = f"https://checkout.stripe.com/MOCK/{prenotazione_id}"
        print(f"💳 [SIMULATO — credenziali Stripe mock] sessione di deposito {importo_eur}€ per prenotazione #{prenotazione_id}: {url_finta}")
        return {"simulato": True, "url_pagamento": url_finta}

    corpo = urllib.parse.urlencode({
        "mode": "payment",
        "success_url": cfg["success_url"],
        "cancel_url": cfg["cancel_url"],
        "line_items[0][price_data][currency]": "eur",
        "line_items[0][price_data][product_data][name]": descrizione,
        "line_items[0][price_data][unit_amount]": int(round(importo_eur * 100)),
        "line_items[0][quantity]": 1,
        "metadata[prenotazione_id]": prenotazione_id,
        "metadata[struttura_id]": struttura_id or "",
    }).encode()
    auth = base64.b64encode(f"{cfg['secret_key']}:".encode()).decode()
    req = urllib.request.Request(
        "https://api.stripe.com/v1/checkout/sessions",
        data=corpo,
        headers={"Authorization": f"Basic {auth}", "Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            dati = json.loads(res.read().decode())
            return {"simulato": False, "url_pagamento": dati.get("url"), "session_id": dati.get("id")}
    except urllib.error.HTTPError as e:
        return {"simulato": False, "errore": e.read().decode()}


def valida_firma_stripe(corpo_raw, header_stripe_signature, webhook_secret, tolleranza_s=300):
    """Porting dell'algoritmo Stripe (documentato pubblicamente): il
    payload firmato è "<timestamp>.<corpo>", HMAC-SHA256 con il webhook
    secret, confronto a tempo costante. Rifiuta anche eventi troppo
    vecchi (replay attack) oltre la tolleranza."""
    if not header_stripe_signature or not webhook_secret:
        return False
    parti = dict(p.split("=", 1) for p in header_stripe_signature.split(",") if "=" in p)
    timestamp = parti.get("t")
    firma_ricevuta = parti.get("v1")
    if not timestamp or not firma_ricevuta:
        return False
    if abs(time.time() - int(timestamp)) > tolleranza_s:
        return False
    payload_firmato = f"{timestamp}.{corpo_raw}"
    firma_attesa = hmac.new(webhook_secret.encode("utf-8"), payload_firmato.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(firma_attesa, firma_ricevuta)


if __name__ == "__main__":
    print(crea_sessione_deposito(1, 9.0, "Deposito prenotazione Campo Padel 1"))
