# 🎙️ Progetto 01 — Voice AI Receptionist per PMI locali

> **Missione:** nessuna PMI italiana deve più perdere un cliente per una chiamata senza risposta.

## Cosa c'è in questa cartella

| File | Cosa fa |
|---|---|
| `server.js` | **Motore conversazionale funzionante** (zero dipendenze): macchina a stati che gestisce la telefonata — saluto, intento, raccolta dati, conferma appuntamento. Ogni evento finisce in un log JSONL (`eventi.jsonl`). Provalo: `node server.js --demo` |
| `flows/dentista.json`, `flows/officina.json` | I flussi conversazionali per le due nicchie, configurabili senza toccare codice |
| `valori/*.json` | Il valore economico (€) di ogni evento, per flusso — lo configura il titolare in onboarding |
| `valore.js` | **Il motore di ROI**: legge il log eventi e genera il report che chiude la vendita al giorno 30 del pilota. `node valore.js --demo` |
| `suggerimenti.js` | **Il motore di auto-apprendimento**: analizza le richieste non capite e propone i nuovi intenti da aggiungere, con lo snippet JSON pronto. `node suggerimenti.js --demo` |
| `simulatore.js` | Genera chiamate simulate (deterministiche) per popolare le demo di `valore.js`/`suggerimenti.js` senza aspettare un pilota reale |
| `GO-TO-MARKET.md` | Playbook di vendita: come firmare i primi 3 piloti in 30 giorni |

## Il moat: due motori che nessun wrapper generico Twilio+GPT ha

**1. Il motore di ROI (`valore.js`)** — la differenza tra vendere "minuti di AI" e vendere "soldi recuperati". Ogni evento del flusso (appuntamento fissato, urgenza gestita) ha un valore economico configurato col cliente in onboarding. Il report non dice "23 chiamate gestite": dice **"4.740 € di valore recuperato, il servizio ne costa 300, ritorno 15,8×"** — il numero esatto che il GO-TO-MARKET.md prescrive di mostrare il giorno 30 del pilota. Costruirlo richiede l'infrastruttura di logging strutturato che questo motore già ha; un concorrente che assembla Twilio + un LLM a mano normalmente non la costruisce finché non gliela chiede un cliente arrabbiato.

**2. Il motore di auto-apprendimento (`suggerimenti.js`)** — ogni volta che un chiamante dice qualcosa che il flusso non riconosce, il testo esatto finisce nel log. Lo script raggruppa questi "buchi" per parola ricorrente e genera lo snippet JSON pronto da incollare nel flusso. Risultato: **il flusso migliora da solo, chiamata dopo chiamata**, e i dati accumulati (quali domande fanno davvero i pazienti di QUEL dentista) non sono replicabili da un concorrente che parte da zero — sono un vantaggio che si compone nel tempo, non un pitch deck.

```bash
node simulatore.js            # genera 25 chiamate simulate (deterministiche)
node valore.js --demo         # → 4.740 € recuperati, ROI 15,8×
node suggerimenti.js --demo   # → "aggiungi l'intento parcheggio (3 volte)" + snippet pronto
```

## Prova subito

```bash
node server.js --demo     # conversazione interattiva nel terminale
node server.js --test     # conversazione scriptata automatica (per CI)
node server.js            # avvia l'API HTTP su :3000
```

## Architettura — completa, con credenziali mock

```
Telefono ──▶ Twilio (numero MOCK) ──▶ POST /voice/incoming ──▶ server.js
                                              │                (state machine)
                                              ▼
                                     TwiML: <Say> + <Gather>
                                              │
Chiamante parla ──▶ Twilio STT ──▶ POST /voice/gather/:id ──▶ ricevi()
                                              │
                                              ▼
                              integrazioni/notifiche.js (WhatsApp titolare)
                              integrazioni/calendario.js (evento Google Calendar)
                              [entrambe MOCK finché le credenziali in .env lo sono]
```

Il punto geniale: **la logica di business (stati, regole, escalation) vive nel JSON del flusso, non nel provider**. Cambiare Twilio↔Vonage o un modello LLM con un altro non tocca il prodotto. Il webhook (`integrazioni/telefonia.js`) è già testato con richieste HTTP che replicano esattamente il formato Twilio — verificato end-to-end: chiamata in arrivo → conversazione completa → conferma appuntamento → notifica WhatsApp + evento calendario (mock).

## ✅ Cosa è completo (con dati mock) vs cosa serve da te

| Livello | Stato | Per andare live serve |
|---|---|---|
| Motore, flussi, ROI, apprendimento | ✅ Vero al 100% | Niente |
| Webhook telefonico (`integrazioni/telefonia.js`) | ✅ Codice vero, testato | Un numero Twilio reale puntato all'URL (`CONFIGURAZIONE.md`) |
| Notifiche WhatsApp, Google Calendar | 🟡 Codice vero, credenziali mock | Le tue credenziali reali in `.env` (`CONFIGURAZIONE.md`) |
| Contratto pilota, privacy policy | 📄 Bozze da template | Revisione di un avvocato |

Vedi `CONFIGURAZIONE.md` per la guida passo-passo (account Twilio, hosting, Google Calendar) e `.env.example` per tutte le variabili.

## Roadmap 90 giorni

| Fase | Quando | Obiettivo | KPI di sblocco |
|---|---|---|---|
| 1. Demo vendibile | Settimana 1–2 | Demo telefonica reale su numero di prova | Demo che regge 10 chiamate di fila |
| 2. Piloti | Settimana 3–6 | 3 studi dentistici in pilota gratuito 30 gg | 3 piloti firmati |
| 3. Conversione | Settimana 7–10 | Piloti → paganti a 250–350 €/mese | 2 su 3 convertiti |
| 4. Ripetibilità | Settimana 11–13 | Onboarding nuovo cliente < 2 ore | 10 clienti, churn 0 |

## KPI del prodotto (da mostrare al cliente ogni mese)

- 📞 Chiamate gestite fuori orario / nel weekend
- 📅 Appuntamenti fissati dall'AI
- 💶 **Valore recuperato** = appuntamenti × valore medio prestazione (il numero che vende)

## Prima azione da fare OGGI

Chiama 5 studi dentistici della tua zona alle 13:30 (ora di pranzo). Conta quanti non rispondono. Quel numero è la tua prima slide di vendita.
