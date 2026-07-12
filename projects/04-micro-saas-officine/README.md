# 🔧 Progetto 04 — Micro-SaaS verticale: Gestionale AI per Officine

> **Missione:** portare le officine italiane da carta+WhatsApp a un gestionale che *lavora al posto loro*. Il playbook ServiceTitan (HVAC, USA, valutata miliardi), applicato a una nicchia europea scoperta.

## Perché le officine (ma leggi `NICCHIA.md` prima di sposarla)

- ~80.000 autofficine/carrozzerie in Italia, digitalizzazione bassissima
- Workflow doloroso e ripetuto: accettazione → preventivo → attesa ricambi → consegna → incasso, tutto su carta e telefonate
- Il momento AI: *foto del danno → bozza di preventivo*, *targa → storico veicolo*, *richiamo automatico tagliandi* — cose impossibili per i gestionali legacy

## Cosa c'è in questa cartella

| File | Cosa fa |
|---|---|
| `app.py` | **Spina dorsale funzionante** (zero dipendenze: `http.server` + `sqlite3`): API REST per clienti, veicoli e interventi con stati. `python3 app.py --selftest` |
| `NICCHIA.md` | Framework di scelta/validazione della nicchia: usalo PRIMA di scrivere altra UI |

## Prova subito

```bash
python3 app.py --selftest   # crea il db, esegue il flusso completo, verifica
python3 app.py              # API su :8000 (officina.db creato in locale)
```

Flusso coperto dall'MVP: cliente → veicolo → intervento (`accettato → in_lavorazione → pronto → consegnato`) con preventivo e importo finale. È il 20% di funzionalità che copre l'80% delle giornate in officina.

## Architettura evolutiva (mai riscrivere, solo aggiungere)

```
ORA (v0)              v1 (mese 2)                  v2 (mese 4+)
app.py + sqlite  →  + interfaccia web mobile-first  →  + strato AI:
                    + invio SMS "auto pronta"           - foto → bozza preventivo
                    + agenda appuntamenti               - richiami tagliando automatici
                                                        - voce: integrazione progetto #01
```

## Modello di business

| Piano | Prezzo | Target |
|---|---|---|
| Base | 49 €/mese | Officina 1–2 persone |
| Pro | 99 €/mese | + SMS automatici, agenda, report |
| AI | 199 €/mese | + preventivi da foto, richiami automatici |

Obiettivo anno 1: 60 officine × ~80 €/mese medi = **~58 k€ ARR**, churn < 1,5%/mese.

## Roadmap 90 giorni

| Fase | Quando | Obiettivo | KPI di sblocco |
|---|---|---|---|
| 1. Validazione | Settimane 1–3 | 10 interviste in officina (vedi domande in `NICCHIA.md`) | 6/10 confermano il dolore |
| 2. Pilota | Settimane 4–8 | v1 usata DAVVERO da 3 officine amiche (gratis) | Usata tutti i giorni per 2 settimane |
| 3. Paganti | Settimane 9–13 | Convertire i piloti + waiting list | 10 officine paganti o in lista |

## Prima azione da fare OGGI

Porta la macchina a fare il tagliando. Mentre aspetti, guarda come gestiscono l'accettazione (carta? lavagna? WhatsApp?) e chiedi al titolare: «quanto tempo perde al giorno a rincorrere ricambi e clienti al telefono?». Quella risposta vale più di un mese di sviluppo.
