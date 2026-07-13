# 🏗️ Cantiere Aperto — Numero Zero

*Il diario di chi sta lanciando 9 business in pubblico. Numeri veri, fallimenti compresi.*

---

Ciao, e benvenuto nel cantiere.

Questa newsletter documenta un esperimento: **lanciare 9 progetti di business AI-first, in ordine di priorità, con regole scritte prima di iniziare** — e raccontare tutto, anche quello che di solito si nasconde.

Il numero zero è la fotografia di partenza. Da sabato prossimo, i numeri veri.

## 📈 NUMERI VERI — Lo stato del cantiere, oggi

| Voce | Valore |
|---|---|
| Progetti in portfolio | 9 |
| Prototipi funzionanti | 8 (tutti a zero dipendenze, tutti testati) |
| Homepage pronte | 9 |
| Clienti paganti | **0** |
| Euro incassati | **0 €** |
| Euro spesi | ~0 € (solo tempo) |

Sì, zero clienti e zero euro: ogni storia di business inizia esattamente da qui. La differenza è che questa la leggi dall'inizio.

**Le regole del cantiere** (scritte prima di partire, per non barare dopo):
1. Si sviluppa in ordine di classifica: un progetto avanza solo se centra il suo KPI di fase, altrimenti la cassa va al successivo.
2. Regola dei 90 giorni: primo cliente pagante entro 90 giorni, o l'idea si cambia.
3. Ogni riga di codice deve avvicinare un cliente pagante.

## 🔧 COME SI FA — Un receptionist AI a zero dipendenze

Il progetto n.1 è un'assistente vocale per studi dentistici. Il prototipo è una macchina a stati di ~250 righe di JavaScript senza alcuna libreria: la logica di business vive in un file JSON (stati, intenti, azioni), il codice la esegue e basta.

Perché è la scelta giusta per un MVP:
- **Cambiare fornitore non tocca il prodotto**: il flusso è nel JSON, non nel provider di telefonia o nel modello AI.
- **La demo gira ovunque**: terminale, browser, domani il telefono. Stesso motore.
- **Il secondo settore è costato un file**: il flusso per le officine è un JSON nuovo, zero codice nuovo.

La lezione replicabile: *prima di aggiungere una dipendenza, chiediti se 50 righe tue la sostituiscono. All'inizio, quasi sempre sì.*

## 💡 L'ANALISI — Perché partire dal telefono

Di tutte le 9 idee analizzate (classifica completa nel repository), la migliore per rapporto tempi/costi/acquisizione è la più antica del mondo: rispondere al telefono. I dati di settore indicano che i voice agent che coprono le chiamate perse producono risparmi del 60–80% rispetto a un servizio di segreteria tradizionale, e il mercato cresce a ritmi del 35–40% annuo. Ma il motivo vero è un altro: **il ROI si dimostra con un numero che il cliente capisce in tre secondi** («questo mese: 11 appuntamenti fissati mentre eri chiuso»). Quando il valore si spiega da solo, la vendita è corta. È il criterio numero uno per scegliere da dove partire.

## ❌ L'ERRORE — Quello che abbiamo già sbagliato

Abbiamo passato una giornata a discutere il nome perfetto per il progetto 4 prima di avere UN cliente. Il nome non fa fatturato; le 10 interviste alle officine sì — e infatti sono diventate il KPI della fase 1. La lezione: *l'ordine delle cose conta più delle cose.*

## 📬 La settimana prossima

Il primo test sul campo: quante chiamate perdono davvero gli studi dentistici della zona? (metodo: chiamarli all'ora di pranzo e contare — costo: zero, valore: la prima slide di vendita).

A sabato,
*il Cantiere*

---

*Cantiere Aperto è gratuita. Nessuna promessa di guadagno: documentiamo un percorso, i risultati dipendono da mille variabili — la maggior parte delle quali scopriremo insieme. Le fonti dei dati citati sono nel repository pubblico del progetto.*
