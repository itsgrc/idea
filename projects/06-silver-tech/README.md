# 👵 Progetto 06 — Silver Tech: "FiloDiretto"

> **Missione:** nessun anziano solo deve passare inosservato per giorni. Nessun figlio lontano deve vivere con l'ansia. Il paese più vecchio d'Europa merita il miglior prodotto del mondo per questo.

## Il prodotto (v1: zero hardware — la mossa geniale)

**FiloDiretto**: una telefonata AI gentile, ogni giorno alla stessa ora, all'anziano che vive solo. Due minuti di conversazione: «Come sta oggi? Ha preso le medicine? Ha mangiato?». Se qualcosa non va — o se non risponde per due volte — parte l'allerta ai familiari.

Perché è geniale:
- **Zero hardware, zero installazione, zero apprendimento**: il telefono fisso che l'anziano usa da 40 anni È il dispositivo. I competitor vendono sensori, wearable, tablet — tutte cose che i nonni non vogliono.
- **Riusa lo stack del progetto #01** (voice AI): stesso motore, flusso diverso. Il costo marginale di sviluppo è vicino a zero.
- **Il cliente pagante (il figlio 45-60enne) non è l'utente (il genitore 80enne)**: si vende con il marketing digitale normale a chi il digitale lo usa.

## Cosa c'è in questa cartella

| File | Cosa fa |
|---|---|
| `checkin_simulator.py` | Simulatore con dati casuali: usalo per progettare/vendere il servizio prima di avere un cliente. `python3 checkin_simulator.py` |
| `pattern_tracker.py` | **Il moat**: la stessa analisi di escalation, ma sui dati REALI prodotti dal motore del progetto 01. `python3 pattern_tracker.py --demo` |
| `dashboard.py` | Dashboard famiglia (stato di oggi + report settimanale) + webhook Twilio per rilevare le chiamate senza risposta + consenso GDPR obbligatorio. `python3 dashboard.py --demo` |
| `integrazioni/chiamata_uscente.py` | Origina la chiamata quotidiana vera via Twilio (mock finché le credenziali non sono reali) — il pezzo che il progetto 01 (solo chiamate in arrivo) non aveva |
| `flows/filodiretto.json` | Il flusso conversazionale: riuso diretto della macchina a stati del progetto 01, zero codice nuovo nel motore |
| `MVP-SPEC.md` | Specifica completa dell'MVP: flusso chiamata, regole di escalation, dashboard famiglia, GDPR |

## Modello di business

| Piano | Prezzo | Include |
|---|---|---|
| Base | 29 €/mese | 1 chiamata/giorno + alert + report settimanale |
| Sereno | 49 €/mese | 2 chiamate/giorno + promemoria farmaci + linea diretta famiglia |
| B2B2C | Contratti | Comuni, RSA "leggere", cooperative di assistenza domiciliare |

Confronto che vende: la teleassistenza tradizionale (bottone SOS) costa 20–35 €/mese ed è *passiva* (funziona solo se l'anziano la attiva nel momento peggiore). FiloDiretto è *proattivo*: si accorge lui che qualcosa non va.

## Roadmap 90 giorni

| Fase | Quando | Obiettivo | KPI di sblocco |
|---|---|---|---|
| 1. Concierge test | Settimane 1–4 | 10 famiglie, chiamate fatte DA UN UMANO (validare il servizio, non la tech) | 8/10 famiglie vogliono continuare |
| 2. Automazione | Settimane 5–9 | Stack #01 adattato, chiamate AI con supervisione | 90% chiamate senza intervento umano |
| 3. Pilota pagante | Settimane 10–13 | 20 famiglie a 29 €/mese | churn 0 nel primo mese |

## Il vantaggio Italia

14 milioni di over-65 (24% della popolazione), il 30%+ vive solo, figli spesso in un'altra città. Sanità pubblica sotto pressione = i comuni CERCANO soluzioni a basso costo (i contratti B2B2C sono il moltiplicatore). Validato in Italia → l'export in Spagna/Germania/Giappone è naturale.

## Il moat: lo stesso motore del progetto 01, con un pezzo che nessun altro riuso avrebbe dato gratis

"Riusa lo stack del progetto #01" non è solo una frase nel business plan: `flows/filodiretto.json` gira DAVVERO sulla stessa macchina a stati di `server.js` (verificato: la stessa chiamata che dice «sono caduta e ho un dolore forte» fa scattare `allerta_famiglia_immediata`, che include nell'alert le parole esatte dette dall'assistito, non solo un evento generico). L'unico pezzo che il progetto 01 non aveva — perché gestisce solo chiamate IN ARRIVO — è originare la chiamata: `integrazioni/chiamata_uscente.py` lo aggiunge riusando lo stesso account Twilio.

`pattern_tracker.py` è il moat vero e proprio: **non inventa un report, lo calcola dagli eventi reali** prodotti da quella stessa infrastruttura, giorno dopo giorno, famiglia per famiglia — è un vantaggio che si accumula nel tempo con QUELLA famiglia specifica, non replicabile aprendo un concorrente il giorno dopo.

```bash
python3 pattern_tracker.py --demo
# 🟡 2026-07-09 — segnale debole — da tenere d'occhio
# 🟢 2026-07-10 — tutto bene
# ...
# ⚠️ 3 segnali deboli negli ultimi 7 giorni: vale la pena una chiamata in più.
```

## Prima azione da fare OGGI

Chiama una persona che conosci con un genitore anziano che vive solo. Chiedi: «Pagheresti 29 €/mese per sapere ogni giorno che sta bene, senza dover essere tu a chiamare sempre?». Fallo con 10 persone. Se 6+ dicono sì, il concierge test parte lunedì.

## ✅ Cosa è completo (con dati mock) vs cosa serve da te

| Livello | Stato | Per andare live serve |
|---|---|---|
| Motore conversazionale, pattern tracker, dashboard famiglia, consenso GDPR | ✅ Vero al 100%, testato (motore reale del progetto 01 + richieste HTTP reali) | Niente |
| Chiamata uscente quotidiana, webhook stato chiamata | ✅ Codice vero, credenziali Twilio mock | Le tue credenziali reali in `.env` (`CONFIGURAZIONE.md`) |
| Informativa privacy completa, DPA per contratti B2B2C | ❌ Non esiste — è l'unico pezzo che il codice non può darti | Farla validare da un avvocato prima del primo cliente pagante |
| Classificazione formale AI Act del servizio | 📄 Da fare con gli strumenti del progetto 03 | `cd ../03-ai-act-compliance && python3 classifica.py --demo` |

Vedi `CONFIGURAZIONE.md` per la guida passo-passo.

## 🔍 Audit di sicurezza e legale — cosa è stato trovato e corretto

| Problema trovato | Rischio | Correzione |
|---|---|---|
| Il progetto 01 gestisce solo chiamate in arrivo: non esisteva alcun modo di originare la chiamata quotidiana verso l'assistito | 🔴 L'intero prodotto ("il sistema chiama ogni giorno") non aveva ancora nessun codice per farlo davvero | `integrazioni/chiamata_uscente.py`: chiamata uscente reale via Twilio, mock finché le credenziali non sono reali |
| L'allerta famiglia per un segnale forte non includeva le parole esatte dette dall'assistito (il campo salvato non esisteva nel flusso) | Un familiare che riceve l'alert non saprebbe cosa è successo davvero, solo che "è successo qualcosa" — bug funzionale grave per l'unica azione realmente urgente del prodotto | Aggiunto `salva_in` allo stato `valuta_benessere` del flusso: l'alert ora cita testualmente cosa ha detto l'assistito, verificato con un test end-to-end |
| Nessuna dashboard/API proteggeva l'accesso a dati particolari (ex art. 9 GDPR: segnali di malessere, assunzione farmaci) | 🔴 Il rischio più serio dei tre progetti nuovi: chiunque scoprisse l'URL leggerebbe lo stato di salute di un anziano | Token d'accesso dedicato per famiglia, confronto a tempo costante, **mock = accesso sempre negato** (stesso principio già applicato a `LEAD_API_KEY`/`NEWSLETTER_API_KEY`) |
| Nessun controllo impediva di consultare i dati prima che il consenso dell'assistito fosse stato raccolto | Violazione della base giuridica del trattamento (consenso esplicito, dichiarato come requisito in MVP-SPEC.md ma non fatto rispettare tecnicamente | `/stato` e `/report-settimanale` rispondono 403 finché `POST /consenso` non è stato chiamato — non solo una casella da spuntare in un modulo cartaceo |
| Il webhook di stato chiamata Twilio non validava la firma della richiesta | Chiunque avrebbe potuto forgiare un "no-answer" falso (o nasconderne uno vero) senza che fosse davvero Twilio a inviarlo | Porting Python della stessa validazione HMAC-SHA1 del progetto 01, verificata con firme corrette e contraffatte |
| `MVP-SPEC.md` e `homepage.html` dichiaravano "i dati non lasciano l'Europa"/"infrastruttura europea" in modo assoluto | Stesso claim non allineato all'uso di Twilio (fornitore USA) già trovato e corretto nei progetti 01 e 04 | Testo corretto per riferirsi a GDPR + Clausole Contrattuali Standard |
| Nessun limite alla conservazione degli eventi (segnali di malessere, dati particolari ex art. 9) — sarebbero rimasti per sempre | Violazione del principio di limitazione della conservazione (GDPR art. 5.1.e): il report e il rilevamento pattern guardano solo 7 giorni indietro, non c'è motivo per conservare oltre | `pattern_tracker.pulisci_eventi_vecchi()`: cancellazione automatica degli eventi oltre 90 giorni, eseguita a ogni consultazione della dashboard, verificata con un test che inserisce un evento vecchio e uno recente |

Tutte le correzioni sono testate (richieste HTTP reali: consenso assente/token errato/token corretto, firma Twilio valida/non valida, evento "non risponde" tracciato end-to-end).
