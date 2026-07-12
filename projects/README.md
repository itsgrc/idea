# 🏭 Portfolio Progetti — Dashboard Operativa

> Ogni progetto ha la sua cartella con: README operativo, roadmap 90 giorni, KPI e — dove il codice è il cuore — **un prototipo funzionante a zero dipendenze, eseguibile subito**.

## Il Flywheel (perché il portfolio è più forte dei singoli progetti)

```
  #02 Servizio produttizzato ──(dati + processi)──▶ #04 Micro-SaaS verticale
        │                                                │
     (cassa)                                          (cassa)
        ▼                                                ▼
  #01 Voice AI ──(stesso stack vocale)──▶ #06 Silver Tech
        │
  #03 AI Act Compliance ──(credibilità regolatoria)──▶ #09 Vertical AI sanità/legale
        │
  #07 Agent Infra ◀──(strumenti usati da tutti i progetti AI del portfolio)
        │
  #08 Roll-up PMI ◀──(l'AI di #01/#02/#04 è ciò che alza i margini delle aziende comprate)
```

**Regola del portfolio:** si sviluppa in ordine di classifica. Un progetto avanza di fase solo se raggiunge il suo KPI di fase; altrimenti si ferma e la cassa va al successivo.

## Stato progetti

| # | Progetto | Cartella | Fase | Prototipo | Primo KPI da sbloccare |
|---|---|---|---|---|---|
| 1 | 🎙️ Voice AI Receptionist | [`01-voice-receptionist/`](01-voice-receptionist/) | 🟢 Sviluppo attivo | ✅ `node server.js --demo` | 3 piloti firmati in 30 gg |
| 2 | 🛠️ Servizio Produttizzato AI | [`02-servizio-produttizzato/`](02-servizio-produttizzato/) | 🟢 Sviluppo attivo | ✅ `python3 roi_pitch.py` | 1° cliente pagante in 14 gg |
| 3 | ⚖️ AI Act Compliance | [`03-ai-act-compliance/`](03-ai-act-compliance/) | 🟢 Sviluppo attivo | ✅ `python3 classifica.py --demo` | 5 audit venduti entro ago 2026 |
| 4 | 🔧 Micro-SaaS Officine | [`04-micro-saas-officine/`](04-micro-saas-officine/) | 🟡 Fondamenta | ✅ `python3 app.py --selftest` | 10 officine in waiting list |
| 5 | 🎓 Prodotti Digitali | [`05-prodotti-digitali/`](05-prodotti-digitali/) | 🟡 Fondamenta | ✅ `python3 calendario.py` | 1.000 follower in 60 gg |
| 6 | 👵 Silver Tech | [`06-silver-tech/`](06-silver-tech/) | 🔵 Incubazione | ✅ `python3 checkin_simulator.py` | 20 famiglie in pilota |
| 7 | 🏗️ Agent Infra (AgentLens) | [`07-agent-infra/`](07-agent-infra/) | 🔵 Incubazione | ✅ `python3 demo.py` | 50 stelle GitHub / 10 utenti |
| 8 | 🏢 Roll-up PMI + AI | [`08-rollup-pmi/`](08-rollup-pmi/) | 🔵 Incubazione | ✅ `python3 valuta.py --esempio` | 1 LOI firmata |
| 9 | 🩺 Vertical AI Legale/Sanità | [`09-vertical-ai-legale/`](09-vertical-ai-legale/) | ⚪ Validazione | 📋 kit interviste | 15 interviste + 1 pilot |

**Legenda fasi:** ⚪ Validazione → 🔵 Incubazione → 🟡 Fondamenta → 🟢 Sviluppo attivo → 🚀 Sul mercato

## Principi di sviluppo del portfolio

1. **Zero dipendenze finché possibile** — ogni prototipo gira con `node` o `python3` liofilizzati, niente `npm install` per provare l'idea. La velocità di iterazione È il vantaggio competitivo.
2. **Ogni riga di codice deve avvicinare un cliente pagante** — niente architetture per utenti che non esistono.
3. **Il prototipo si butta, l'apprendimento resta** — questi sono attrezzi per vendere e imparare, non il prodotto finale.
4. **Condividere lo stack** — il motore conversazionale di #01 è progettato per essere riusato da #06; il tracer di #07 si usa in tutti i progetti AI.
