# ⚙️ Configurazione — da mock a produzione

> Tutto il codice è già pronto e testato. Questa pagina spiega **esattamente** cosa sostituire, in che ordine, per passare da "tutto simulato" a "riceve chiamate vere". Nessuna riga di codice da scrivere.

## Prerequisito: capire cosa è già vero e cosa è mock

| Componente | Stato oggi | Cosa serve per renderlo vero |
|---|---|---|
| Motore conversazionale (`server.js`) | ✅ **Vero**, funzionante | Niente — è già pronto |
| Webhook Twilio (`integrazioni/telefonia.js`) | ✅ **Vero**, testato con richieste HTTP simulate | Solo un numero Twilio reale che punti a questo URL |
| Notifiche WhatsApp (`integrazioni/notifiche.js`) | 🟡 Mock (logga soltanto) | Credenziali Twilio + numero WhatsApp |
| Calendario (`integrazioni/calendario.js`) | 🟡 Mock (logga soltanto) | Progetto Google Cloud + OAuth2 |
| Contratto pilota, privacy policy | 📄 Bozze da template | Revisione di un avvocato |

## Passo 1 — Hosting pubblico (15 minuti)

Twilio deve poter raggiungere il tuo server su un URL pubblico HTTPS. Opzioni più semplici:
- **Render.com / Railway.app** (piano gratuito sufficiente per iniziare): collega il repo, deploy automatico, ottieni un URL tipo `https://tuoapp.onrender.com`
- **ngrok** (solo per test locali): `ngrok http 3000` → URL temporaneo per provare prima di un deploy vero

## Passo 2 — Account Twilio e numero di telefono (20 minuti)

1. Crea un account su [twilio.com](https://twilio.com) (gratuito, credito di prova incluso)
2. Console → **Account → API keys & tokens**: copia `Account SID` e `Auth Token`
3. Console → **Phone Numbers → Buy a number**: scegli un numero italiano (+39) con capacità "Voice"
4. Sul numero appena comprato, sezione **Voice Configuration → A call comes in**:
   - Webhook: `https://tuoapp.onrender.com/voice/incoming`
   - Metodo: `HTTP POST`
5. Copia i 3 valori in `.env`:
   ```
   TWILIO_ACCOUNT_SID=AC...
   TWILIO_AUTH_TOKEN=...
   TWILIO_PHONE_NUMBER=+39...
   PUBLIC_URL=https://tuoapp.onrender.com
   ```
   **`PUBLIC_URL` deve essere IDENTICO all'URL messo nel webhook Twilio** (stesso schema, stesso dominio, nessuno slash finale): il server lo usa per verificare la firma `X-Twilio-Signature` e rifiutare richieste che non arrivano davvero da Twilio. Se le due cose non combaciano, ogni chiamata reale verrà rifiutata con 403 — se questo succede, la prima cosa da controllare è che `PUBLIC_URL` sia scritto esattamente come nella console Twilio.

**Fatto questo, il telefono squilla davvero e la conversazione funziona** — anche prima di configurare WhatsApp o calendario (le Azioni continuano a simulare finché non fai anche i passi 3-4).

## Passo 3 — WhatsApp al titolare (10 minuti, opzionale ma consigliato)

1. Console Twilio → **Messaging → Try it out → Send a WhatsApp message**: attiva il Sandbox (per test) o richiedi l'approvazione WhatsApp Business (per produzione, richiede alcuni giorni)
2. Copia il numero sandbox/approvato in `TWILIO_WHATSAPP_FROM`
3. Il titolare deve "attivare" il sandbox mandando il messaggio di join al numero Twilio (una tantum, solo in modalità test)
4. Metti il suo numero vero in `NOTIFICHE_NUMERO_TITOLARE`
5. Imposta `INTEGRAZIONI_ATTIVE=1`

## Passo 4 — Google Calendar (15 minuti, opzionale)

1. [console.cloud.google.com](https://console.cloud.google.com) → crea un progetto → **API e servizi → Libreria** → attiva "Google Calendar API"
2. **Credenziali → Crea credenziali → ID client OAuth 2.0** (tipo "App desktop")
3. Copia Client ID e Client Secret in `.env`
4. Ottieni un refresh token (una tantum): usa [OAuth 2.0 Playground](https://developers.google.com/oauthplayground) selezionando lo scope `https://www.googleapis.com/auth/calendar.events`, autorizza col account Google del titolare, copia il refresh token
5. `GOOGLE_CALENDAR_ID` è di solito l'email del calendario (o "primary" per il calendario principale dell'account)

## Passo 5 — Verifica finale

```bash
# Con .env compilato e INTEGRAZIONI_ATTIVE=1:
node server.js
# Chiama il numero Twilio da un telefono vero.
# Se tutto funziona: la conversazione risponde, e a fine chiamata
# arriva davvero il WhatsApp e/o l'evento calendario.
```

## Legale — da far rivedere PRIMA del primo cliente pagante

- `CONTRATTO-PILOTA-TEMPLATE.md` — bozza dell'accordo di pilota, da far validare da un avvocato
- `PRIVACY-POLICY-TEMPLATE.md` — bozza informativa privacy per il consenso alla registrazione/trattamento delle chiamate

Nessuno di questi due sostituisce una consulenza legale vera: sono un punto di partenza strutturato, non un documento pronto all'uso.
