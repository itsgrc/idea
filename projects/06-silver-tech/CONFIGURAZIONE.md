# ⚙️ Configurazione — da mock a produzione

> Tutto il codice è già pronto e testato. Questa pagina spiega esattamente cosa serve per passare da "chiamate simulate" a "FiloDiretto chiama davvero ogni mattina".

## Prerequisito: capire cosa è già vero e cosa è mock

| Componente | Stato oggi | Cosa serve per renderlo vero |
|---|---|---|
| Motore conversazionale (riuso del progetto 01, `flows/filodiretto.json`) | ✅ **Vero**, testato con l'engine reale del progetto 01 | Niente — è già lo stesso motore |
| Chiamata uscente quotidiana (`integrazioni/chiamata_uscente.py`) | ✅ Codice vero, credenziali Twilio mock | Le tue credenziali Twilio in `.env` |
| Rilevamento "non risponde" + webhook stato chiamata (`dashboard.py`) | ✅ **Vero**, testato (firma Twilio validata/rifiutata correttamente) | Un hosting pubblico |
| Pattern tracker (`pattern_tracker.py`) | ✅ **Vero al 100%** — legge il log eventi reale | Niente |
| Dashboard famiglia + consenso GDPR | ✅ **Vero**, testato end-to-end | Niente |

## Passo 1 — Hosting pubblico (15 minuti)

Twilio deve raggiungere sia il webhook del progetto 01 (per la conversazione) sia `/voice/stato-chiamata` di questo `dashboard.py` (per sapere se l'assistito ha risposto). Stesso hosting del progetto 01 va benissimo — sono due processi Node/Python che possono girare sulla stessa macchina.

## Passo 2 — Twilio: stesso account del progetto 01

Se hai già configurato il progetto 01, riusa lo stesso `TWILIO_ACCOUNT_SID`/`TWILIO_AUTH_TOKEN` — è letteralmente lo stesso stack, come promesso. Serve solo un secondo numero (o lo stesso, se dedicato) per non mischiare le chiamate in arrivo dello studio con quelle in uscita di FiloDiretto.

## Passo 3 — Configura chi chiamare e dove

```
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+39...
FILODIRETTO_NUMERO_ASSISTITO=+39... (il telefono fisso/cellulare dell'assistito)
FILODIRETTO_WEBHOOK_URL=https://tuoapp.onrender.com/voice/incoming
FILODIRETTO_STATUS_CALLBACK_URL=https://tuoapp-dashboard.onrender.com/voice/stato-chiamata
FILODIRETTO_PUBLIC_URL=https://tuoapp-dashboard.onrender.com
```
**`FILODIRETTO_PUBLIC_URL` deve essere IDENTICO al dominio di `FILODIRETTO_STATUS_CALLBACK_URL`**: la firma Twilio si verifica sull'URL esatto, come nel progetto 01.

## Passo 4 — Programma la chiamata quotidiana

Un cron job (o un timer systemd) che esegue lo script ogni giorno alla stessa ora — la puntualità è parte del prodotto (MVP-SPEC.md: «la familiarità è la feature»):

```bash
# crontab -e
0 10 * * * cd /percorso/06-silver-tech && python3 integrazioni/chiamata_uscente.py >> chiamate.log 2>&1
```

## Passo 5 — Il consenso PRIMA di attivare

Il servizio si rifiuta di mostrare qualunque dato finché il consenso non è registrato (`dashboard.py` risponde 403 su `/stato` e `/report-settimanale` senza di esso). Raccoglilo durante la prima chiamata/visita di persona, poi registralo:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # genera FILODIRETTO_ACCESS_TOKEN, mettilo in .env

curl -X POST https://tuoapp-dashboard.onrender.com/consenso \
  -H "X-Access-Token: IL_TUO_TOKEN" \
  -d '{"nome_assistito":"Maria Rossi","chi_raccoglie":"Anna Rossi (figlia)","data_raccolta":"2026-07-15"}'
```

## Passo 6 — Dai il link alla famiglia

`https://tuoapp-dashboard.onrender.com/?token=IL_TUO_TOKEN` — un link privato, non una password da ricordare: è pensato per essere salvato nei preferiti del telefono del figlio/della figlia. Non condividerlo oltre la cerchia familiare: chi ha il link vede lo stato di salute dell'assistito.

## Passo 7 — Verifica finale

```bash
# Con .env compilato, in due terminali separati:
cd ../01-voice-receptionist && FLOW=../06-silver-tech/flows/filodiretto.json node server.js
cd ../06-silver-tech && python3 dashboard.py
# Poi:
python3 integrazioni/chiamata_uscente.py
# Deve partire davvero la chiamata; a fine giornata /stato deve riflettere l'esito.
```

## GDPR — cosa è già coperto vs cosa resta da fare

- ✅ Consenso esplicito obbligatorio prima che il servizio mostri dati (tecnico, non solo su carta)
- ✅ Minimizzazione: si registrano solo eventi classificati (sì/no, tipo di segnale), mai l'audio o la trascrizione integrale
- ✅ Accesso alla dashboard protetto da token dedicato (dati particolari ex art. 9 GDPR)
- ❌ **Da fare**: l'informativa privacy completa per l'assistito, e un DPA con l'eventuale RSA/comune se venduto B2B2C — fanne validare le bozze da un avvocato prima del primo cliente pagante
- ❌ **Da fare**: la classificazione formale AI Act del servizio (probabile "rischio trasparenza", da verificare con gli strumenti del progetto 03 — `classifica.py --demo` è un buon punto di partenza)
