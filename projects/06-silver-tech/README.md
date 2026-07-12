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
| `checkin_simulator.py` | **Simulatore del cuore del prodotto**: 30 giorni di chiamate simulate, logica di escalation (non risponde → riprova → allerta famiglia), report settimanale ai figli. `python3 checkin_simulator.py` |
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

## Prima azione da fare OGGI

Chiama una persona che conosci con un genitore anziano che vive solo. Chiedi: «Pagheresti 29 €/mese per sapere ogni giorno che sta bene, senza dover essere tu a chiamare sempre?». Fallo con 10 persone. Se 6+ dicono sì, il concierge test parte lunedì.
