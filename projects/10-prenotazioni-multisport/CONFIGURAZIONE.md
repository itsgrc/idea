# ⚙️ Configurazione — da mock a produzione

> Tutto il codice è già pronto e testato. Questa pagina spiega esattamente cosa sostituire per passare da "SMS e depositi simulati" a "prenotazioni vere con soldi veri".

## Prerequisito: capire cosa è già vero e cosa è mock

| Componente | Stato oggi | Cosa serve per renderlo vero |
|---|---|---|
| Motore prenotazioni multi-tenant (`prenota.py`) | ✅ **Vero al 100%**, testato (selftest + richieste HTTP reali) | Niente |
| Motore rischio no-show (`rischio_noshow.py`) | ✅ **Vero al 100%** — calcolo reale sullo storico | Niente |
| Rete di disponibilità tra strutture (`rete_disponibilita.py`) | ✅ **Vero al 100%**, testato con 2 strutture | Niente — più strutture entrano, più è utile |
| SMS conferma/promemoria (`integrazioni/notifiche.py`) | 🟡 Codice vero, credenziali Twilio mock | Le tue credenziali reali in `.env` |
| Deposito via Stripe Checkout (`integrazioni/pagamenti.py`) | 🟡 Codice vero, credenziali Stripe mock | Le tue credenziali reali in `.env` |

## Passo 1 — Hosting pubblico (15 minuti)

Serve un URL pubblico HTTPS: sia per il pannello (usato dalle strutture e dai loro clienti), sia perché Stripe deve raggiungere `/webhook/stripe`. Render.com/Railway.app (piano gratuito) o un VPS con reverse proxy vanno bene.

## Passo 2 — Twilio per gli SMS (15 minuti)

Stesso procedimento degli altri progetti del portfolio che usano Twilio: account su [twilio.com](https://twilio.com), copia `Account SID`/`Auth Token`, compra un numero con capacità SMS.

## Passo 3 — Stripe per i depositi (20 minuti)

1. Crea un account su [stripe.com](https://stripe.com)
2. **Sviluppatori → Chiavi API**: copia la chiave segreta (`sk_live_...` o `sk_test_...` per provare prima)
3. **Sviluppatori → Webhook → Aggiungi endpoint**: URL `https://tuoapp.esempio.it/webhook/stripe`, evento da ascoltare `checkout.session.completed`
4. Copia il "Signing secret" del webhook appena creato
5. Metti tutto in `.env`:
   ```
   STRIPE_SECRET_KEY=sk_live_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   STRIPE_SUCCESS_URL=https://tuoapp.esempio.it/pagamento-ok
   STRIPE_CANCEL_URL=https://tuoapp.esempio.it/pagamento-annullato
   ```

**Senza questo passo il motore anti no-show funziona lo stesso** (calcola il rischio, decide se serve un deposito) ma il link di pagamento sarà un URL finto — il deposito non verrà mai incassato davvero.

## Passo 4 — Verifica finale

```bash
python3 prenota.py
# Registra una struttura, aggiungi una risorsa, prova a prenotare lo
# stesso slot più volte fino a farlo diventare "rischioso": il link di
# deposito deve essere un vero URL checkout.stripe.com, e pagarlo davvero
# deve sbloccare la prenotazione (webhook /webhook/stripe).
```

## La rete tra strutture: come attivarla davvero

`rete_disponibilita.py` cerca automaticamente in TUTTE le strutture della stessa città registrate su questo stesso database — non serve alcuna configurazione manuale di "partnership": basta che più strutture della tua zona si registrino sullo stesso deployment di Campolibero. Il modo più semplice per farlo partire: proponilo tu stesso a 2-3 centri sportivi vicini come parte del programma pilota (vedi README.md, roadmap).

## GDPR — cosa è già coperto vs cosa resta da fare

- ✅ Isolamento multi-tenant reale (una struttura non vede mai i dati di un'altra), verificato con test
- ✅ Password con PBKDF2-HMAC-SHA256, nessun timing side-channel nel login
- ✅ Webhook Stripe con validazione della firma (nessuno può fingere un pagamento mai avvenuto)
- ❌ **Da fare**: informativa privacy completa per i clienti finali (chi prenota un campo), da far validare da un avvocato prima del primo cliente pagante
- ❌ **Da fare**: procedura di cancellazione dati su richiesta di un cliente finale — vedi sotto

### Cancellazione dati su richiesta (art. 17 GDPR)

```bash
sqlite3 campolibero.db "
  DELETE FROM prenotazioni WHERE cliente_id IN (SELECT id FROM clienti WHERE telefono='+39...');
  DELETE FROM clienti WHERE telefono='+39...';
"
```

Nota: questo cancella anche lo storico usato dal motore anti no-show per quel cliente — è corretto, la cancellazione deve essere completa.
