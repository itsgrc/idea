# 🏗️ Progetto 07 — AgentLens: osservabilità per agenti AI

> **Missione:** quando un agente AI sbaglia in produzione, oggi nessuno sa dirti *perché*. AgentLens è la scatola nera che risponde. I "picks and shovels" della corsa all'oro degli agenti.

## La nicchia (iper-specifica, di proposito)

Non "observability AI" generica (lì si perde contro i giganti). La nicchia: **tracciamento decisionale per agenti in produzione presso PMI e software house europee** — chi ha 1–20 agenti in produzione, non 10.000, e deve rispondere a domande tipo:

- «Perché l'agente ha detto QUESTO al cliente?» (accountability)
- «Quanto mi è costato l'agente questo mese, per cliente?» (unit economics)
- «Quale versione del prompt performa meglio?» (iterazione)
- «Dimostrami cosa ha fatto il sistema» (→ **sinergia col progetto #03**: i log obbligatori dell'AI Act, Art. 12!)

L'angolo geniale: **l'AI Act rende i log degli agenti un obbligo di legge in Europa**. AgentLens non vende "nice to have" da sviluppatori: vende conformità + debugging insieme. Nessun competitor US ha questo posizionamento.

## Cosa c'è in questa cartella

| File | Cosa fa |
|---|---|
| `agentlens.py` | **La libreria, versione 0** (zero dipendenze, un file): tracer che registra ogni step dell'agente (LLM call, tool call, decisioni, costi) su JSONL + report CLI con latenze, costi ed errori. |
| `demo.py` | Un finto agente strumentato con AgentLens: `python3 demo.py` genera tracce e stampa il report |

## Prova subito

```bash
python3 demo.py                        # esegue l'agente demo e genera tracce
python3 agentlens.py report tracce.jsonl   # il report che il cliente guarda
```

## Strategia go-to-market (developer-first)

```
1. OPEN SOURCE il tracer (questo file) — MIT license, zero friction
2. I progetti #01, #02, #03 del portfolio lo usano in produzione → dogfooding
3. Contenuto tecnico (→ progetto #05): "come tracciamo i nostri agenti"
4. SI PAGA per: dashboard hosted, retention lunga, report AI Act pronti
   per l'audit, alert. Pricing: 49-499 €/mese per team.
```

## KPI di fase (incubazione: investire poco finché il segnale non arriva)

| Fase | KPI di sblocco |
|---|---|
| 1. Segnale | 50 stelle GitHub o 10 progetti esterni che lo usano |
| 2. Prodotto | 5 team sulla dashboard hosted in beta |
| 3. Ricavo | 10 team paganti (~2 k€ MRR) |

**Regola:** finché il KPI 1 non scatta, AgentLens riceve solo le ore che avanzano — è un progetto di incubazione, il dogfooding interno lo tiene vivo a costo zero.

## Prima azione da fare OGGI

Strumenta il receptionist del progetto #01 con `agentlens.py` (3 righe). Da domani ogni demo ai dentisti genera anche il materiale di vendita di QUESTO progetto. Un lavoro, due prodotti.
