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

| # | Progetto | Cartella | Fase | Prototipo | Ultimo avanzamento | Primo KPI da sbloccare |
|---|---|---|---|---|---|---|
| 1 | 🎙️ Voice AI Receptionist | [`01-voice-receptionist/`](01-voice-receptionist/) | 🟢 Sviluppo attivo | ✅ `node server.js` → demo web su :3000 | Demo chat nel browser + 2° settore (officine) | 3 piloti firmati in 30 gg |
| 2 | 🛠️ Servizio Produttizzato AI | [`02-servizio-produttizzato/`](02-servizio-produttizzato/) | 🟢 Sviluppo attivo | ✅ `python3 scout.py --demo` | Motore matching bandi↔azienda + report cliente | 1° cliente pagante in 14 gg |
| 3 | ⚖️ AI Act Compliance | [`03-ai-act-compliance/`](03-ai-act-compliance/) | 🟢 Sviluppo attivo | ✅ `python3 registro.py --demo` | Registro multi-sistema + gap analysis (il deliverable dell'audit) | 5 audit venduti entro ago 2026 |
| 4 | 🔧 Micro-SaaS Officine | [`04-micro-saas-officine/`](04-micro-saas-officine/) | 🟡 Fondamenta | ✅ `python3 app.py` → lavagna web su :8000 | Interfaccia web usabile (accettazione + stati) | 10 officine in waiting list |
| 5 | 🎓 Prodotti Digitali | [`05-prodotti-digitali/`](05-prodotti-digitali/) | 🟡 Fondamenta | ✅ `python3 calendario.py` | Numero Zero scritto + 6 post pronti | 1.000 follower in 60 gg |
| 6 | 👵 Silver Tech | [`06-silver-tech/`](06-silver-tech/) | 🔵 Incubazione | ✅ flusso reale sul motore del #1 | `FLOW=../06-silver-tech/flows/filodiretto.json node ../01-voice-receptionist/server.js --demo` | 20 famiglie in pilota |
| 7 | 🏗️ Agent Infra (AgentLens) | [`07-agent-infra/`](07-agent-infra/) | 🔵 Incubazione | ✅ `python3 dashboard.py tracce.jsonl` | Dashboard HTML (anteprima del prodotto cloud) | 50 stelle GitHub / 10 utenti |
| 8 | 🏢 Roll-up PMI + AI | [`08-rollup-pmi/`](08-rollup-pmi/) | 🔵 Incubazione | ✅ `python3 pipeline.py --demo` | CRM pipeline con score + template LOI | 1 LOI firmata |
| 9 | 🩺 Vertical AI Legale/Sanità | [`09-vertical-ai-legale/`](09-vertical-ai-legale/) | ⚪ Validazione | ✅ `python3 tracker.py --demo` | Scoreboard interviste con go/no-go automatico | 15 interviste + 1 pilot |

**Legenda fasi:** ⚪ Validazione → 🔵 Incubazione → 🟡 Fondamenta → 🟢 Sviluppo attivo → 🚀 Sul mercato

## 🌐 Le homepage

Ogni progetto ha la sua **homepage completa** (`homepage.html` nella cartella del progetto): identità visiva propria, copy di vendita, prezzi, FAQ e note legali prudenziali (nessuna testimonianza inventata, nessuna promessa di risultato, disclaimer di settore, zero cookie). Prima di metterle online su un dominio reale: **[LEGAL-CHECKLIST.md](LEGAL-CHECKLIST.md)**.

| # | Progetto | Nome pubblico (provvisorio) | Homepage |
|---|---|---|---|
| 1 | Voice AI | **Rispondo** | [`homepage.html`](01-voice-receptionist/homepage.html) |
| 2 | Servizio bandi | **TrovaBandi** | [`homepage.html`](02-servizio-produttizzato/homepage.html) |
| 3 | AI Act | **Conforme** | [`homepage.html`](03-ai-act-compliance/homepage.html) |
| 4 | SaaS officine | **Ponte** | [`homepage.html`](04-micro-saas-officine/homepage.html) |
| 5 | Knowledge | **Cantiere Aperto** | [`homepage.html`](05-prodotti-digitali/homepage.html) |
| 6 | Silver tech | **FiloDiretto** | [`homepage.html`](06-silver-tech/homepage.html) |
| 7 | Agent infra | **AgentLens** | [`homepage.html`](07-agent-infra/homepage.html) |
| 8 | Roll-up PMI | **Continuità** | [`homepage.html`](08-rollup-pmi/homepage.html) |
| 9 | Vertical AI | **Perizia** | [`homepage.html`](09-vertical-ai-legale/homepage.html) |

## Principi di sviluppo del portfolio

1. **Zero dipendenze finché possibile** — ogni prototipo gira con `node` o `python3` liofilizzati, niente `npm install` per provare l'idea. La velocità di iterazione È il vantaggio competitivo.
2. **Ogni riga di codice deve avvicinare un cliente pagante** — niente architetture per utenti che non esistono.
3. **Il prototipo si butta, l'apprendimento resta** — questi sono attrezzi per vendere e imparare, non il prodotto finale.
4. **Condividere lo stack** — il motore conversazionale di #01 è progettato per essere riusato da #06; il tracer di #07 si usa in tutti i progetti AI.
