# 🎙️ Progetto 01 — Voice AI Receptionist per PMI locali

> **Missione:** nessuna PMI italiana deve più perdere un cliente per una chiamata senza risposta.

## Cosa c'è in questa cartella

| File | Cosa fa |
|---|---|
| `server.js` | **Motore conversazionale funzionante** (zero dipendenze): macchina a stati che gestisce la telefonata — saluto, intento, raccolta dati, conferma appuntamento. Provalo subito: `node server.js --demo` |
| `flows/dentista.json` | Il flusso conversazionale per la prima nicchia (studi dentistici), configurabile senza toccare codice |
| `GO-TO-MARKET.md` | Playbook di vendita: come firmare i primi 3 piloti in 30 giorni |

## Prova subito

```bash
node server.js --demo     # conversazione interattiva nel terminale
node server.js --test     # conversazione scriptata automatica (per CI)
node server.js            # avvia l'API HTTP su :3000
```

## Architettura (MVP → produzione)

```
FASE MVP (questa repo)          FASE PRODUZIONE (settimana 3-4)
┌────────────────────┐          ┌─────────┐   ┌──────────────┐
│ server.js          │          │ Telefono │──▶│ Twilio/Vonage│
│  ├─ state machine  │   ═══▶   └─────────┘   │  (SIP/PSTN)  │
│  ├─ session store  │                        └──────┬───────┘
│  └─ intent matcher │                        STT ──▶ LLM (Claude) ──▶ TTS
│     (keyword→LLM)  │                               │
└────────────────────┘                        stessa state machine
                                              + calendario (Google/Cal.com)
                                              + notifica WhatsApp al titolare
```

Il punto geniale: **la logica di business (stati, regole, escalation) vive nel JSON del flusso, non nel provider**. Cambiare Twilio↔Vonage o un modello LLM con un altro non tocca il prodotto.

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
