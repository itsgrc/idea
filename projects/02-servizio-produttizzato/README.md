# 🛠️ Progetto 02 — Servizio Produttizzato potenziato da AI

> **Missione:** vendere un risultato a prezzo fisso, erogarlo con l'80% del lavoro automatizzato. Cashflow in 14 giorni, zero capitale.

## La nicchia scelta per partire

**Risposta a bandi e gare per PMI** (in alternativa: preventivi per artigiani — stesso playbook).
Perché: le PMI italiane lasciano sul tavolo miliardi di fondi (PNRR, bandi regionali, bandi camerali) perché *leggere e rispondere a un bando richiede 20–40 ore che il titolare non ha*. L'AI riduce quelle ore dell'80%. Il valore è enorme e misurabile: o vinci il bando o no.

**L'offerta:** «Ti troviamo i bandi giusti e prepariamo la domanda. Fisso mensile + success fee.»

## Cosa c'è in questa cartella

| File | Cosa fa |
|---|---|
| `OFFERTA.md` | One-pager dell'offerta: pacchetti, prezzi, garanzia |
| `outreach/email-templates.md` | Sequenze email/LinkedIn pronte (primo contatto, follow-up, referral) |
| `roi_pitch.py` | Generatore di pitch con ROI ipotetico per il primo contatto a freddo. `python3 roi_pitch.py --esempio` |
| `bandi.json` | **Database di bandi REALI**, non più segnaposto: Nuova Sabatini (MIMIT), Voucher Doppia Transizione Lombardia 2026 (Unioncamere), Formazione Fondi Interprofessionali — ognuno con fonte ufficiale verificabile e data di verifica |
| `scout.py` | Motore di matching bandi↔azienda sul database reale. `python3 scout.py --demo` |
| `verifica_freschezza.py` | **Il guardiano della disciplina**: segnala bandi scaduti, in scadenza o non riverificati da troppo tempo. `python3 verifica_freschezza.py` |
| `campagna.py` | **Mail-merge**: da un CSV di prospect a email personalizzate con il bando migliore e il contributo calcolato correttamente (mai un numero inventato). `python3 campagna.py --demo` |

## Il moat: dati reali disciplinati, non una lista che marcisce

**Il problema di ogni "lista di bandi":** chiunque può copiarne una il primo giorno. Il valore di un abbonamento RADAR sta nel tenerla viva — e questo richiede una disciplina che la maggior parte dei concorrenti non ha voglia di mantenere.

**1. `verifica_freschezza.py`** — ogni bando ha una `data_verifica`. Lo script segnala (con exit code diverso da zero, pronto per un cron) le voci scadute, in scadenza entro 20 giorni, o non riverificate da oltre 30. Regola della casa: **un database con un bando scaduto dentro è peggio di nessun database** — un cliente che lo scopre non si fida più. Nessun concorrente che vende "liste di bandi" a 50 € automatizza questo controllo.

**2. `campagna.py` + distinzione `tipo_calcolo`** — il dettaglio che separa un servizio serio da uno che promette numeri a caso: non tutti i bandi si calcolano come "% dell'investimento". La Nuova Sabatini copre gli *interessi* su un finanziamento (6-9% reale, non il 100% dichiarato), la Formazione dipende dal *monte salari* non dall'investimento in macchinari. Il generatore di email **si rifiuta di inventare un numero** quando il bando non lo permette, e lo dice al cliente in chiaro — è la differenza tra un consulente che sa di cosa parla e un generatore di spam.

```bash
python3 verifica_freschezza.py    # controllo di disciplina prima di ogni invio
python3 scout.py --demo           # report per il cliente demo, sui 3 bandi reali
python3 campagna.py --demo        # 4 email pronte, numeri corretti per tipo di bando
```

## Il processo produttivo (dove entra l'AI)

```
1. SCOUTING     AI legge le nuove pubblicazioni di bandi (feed regioni/CCIAA/MIMIT)
                e li matcha col profilo cliente               [90% automatizzato]
2. QUALIFICA    Scheda di 1 pagina per il cliente: requisiti, importo,
                probabilità, scadenza                          [80% automatizzato]
3. DOMANDA      L'AI prepara la bozza (progetto, budget, formulari)
                partendo dai documenti del cliente             [70% automatizzato]
4. REVISIONE    Umano: controllo finale e invio                [il tuo 20%]
```

Ogni cliente in più costa ~2 ore/mese di lavoro umano → 20+ clienti gestibili da soli.

## Roadmap 90 giorni

| Fase | Quando | Obiettivo | KPI di sblocco |
|---|---|---|---|
| 1. Primo cliente | Giorni 1–14 | 1 cliente pagante (anche a 200 €/mese) | Contratto firmato |
| 2. Processo | Giorni 15–45 | SOP scritte, pipeline AI per scouting attiva | 5 clienti, < 3 h/cliente/mese |
| 3. Scala | Giorni 46–90 | 10–15 clienti, primo collaboratore part-time | 5 k€/mese ricorrenti |

## Sinergia di portfolio

I processi e i dati di questo servizio sono il **prototipo vivente del micro-SaaS #04**: dopo 6 mesi sai esattamente quale software costruire, e hai già i primi 15 clienti a cui venderlo.

## Prima azione da fare OGGI

Apri LinkedIn, cerca 10 titolari di PMI manifatturiere della tua regione, manda il template n.1 di `outreach/email-templates.md`. Obiettivo: 2 call fissate entro venerdì.
