# 🎓 Progetto 05 — Prodotti Digitali / Knowledge Business

> **Missione:** trasformare ciò che impariamo costruendo gli altri 8 progetti in un asset che vende da solo. Qui la distribuzione È il prodotto.

## Il posizionamento (l'unico che ha senso per noi)

Non "un altro corso sull'AI". Il posizionamento è: **"Costruisco in pubblico 9 business AI-first e documento tutto"** — numeri veri, fallimenti inclusi. Il portfolio stesso è il contenuto: ogni settimana di lavoro sui progetti #1–4 genera materiale che nessun guru può copiare, perché è vissuto.

```
I progetti (#1-4) ──▶ contenuti (build in public) ──▶ audience ──▶ prodotti digitali
      ▲                                                              │
      └────────────────── lead per i servizi (#1 #2 #3) ◀───────────┘
```

Doppio guadagno: i prodotti digitali monetizzano l'audience E l'audience porta clienti ai progetti principali.

## Cosa c'è in questa cartella

| File | Cosa fa |
|---|---|
| `calendario.py` | **Generatore del calendario editoriale 90 giorni**: rotazione dei pilastri, format e call-to-action già assegnati, output markdown pronto. `python3 calendario.py` |
| `generatore_numero.py` | **Il moat**: legge i dati REALI degli altri progetti del portfolio (chiamate gestite, bandi in catalogo, scadenze normative, officine attive) e compone la sezione "Numeri veri" della newsletter. `python3 generatore_numero.py` |
| `iscrizioni.py` | Backend di iscrizione reale con double opt-in (conferma via email, disiscrizione con cancellazione immediata) — colma il vuoto "la newsletter non aveva un modulo vero". `python3 iscrizioni.py --demo` |
| `FUNNEL.md` | Il funnel completo: da contenuto gratuito a prodotto, con i prezzi |

## I 4 pilastri di contenuto (rotazione settimanale)

1. **📈 Numeri veri** — «Il voice AI questa settimana: 12 demo, 2 piloti, 0 €» (il pilastro che costruisce fiducia)
2. **🔧 Come si fa** — tutorial pratico estratto dal lavoro reale della settimana
3. **💡 Analisi** — mercati, opportunità, l'angolo italiano (riuso dell'analisi in questa repo!)
4. **❌ Errori** — cosa è andato storto e la lezione (il pilastro che nessuno ha il coraggio di fare)

## Scala dei prodotti (in ordine di lancio)

| Quando | Prodotto | Prezzo | Nota |
|---|---|---|---|
| Da subito | Newsletter settimanale | Gratis | L'asset: la lista email è tua, l'algoritmo no |
| Follower > 1.000 | Template pack (i file di questa repo, confezionati) | 29–49 € | Costo marginale zero |
| Iscritti > 500 | Workshop live «Lancia il tuo voice AI in 2 settimane» | 149 € | Valida il corso senza registrarlo |
| Dopo 2 workshop | Corso completo registrato | 390 € | Solo dopo che il live ha venduto |
| Mese 6+ | Community a pagamento | 39 €/mese | Solo se la domanda emerge da sola |

## Roadmap 90 giorni

| Fase | Quando | Obiettivo | KPI di sblocco |
|---|---|---|---|
| 1. Ritmo | Settimane 1–4 | 3 post/settimana LinkedIn + newsletter, zero vendite | 12 post pubblicati (il ritmo conta più dei numeri) |
| 2. Trazione | Settimane 5–9 | Raddoppio dei follower, primi 200 iscritti newsletter | 1.000 follower |
| 3. Primo prodotto | Settimane 10–13 | Template pack in vendita | Prime 20 vendite |

## Il moat: "numeri veri" che nessun altro può copiare, perché nessun altro ha i sistemi dietro

Chiunque può scrivere "costruisco in pubblico". Quello che non si può copiare in un weekend sono **4 sistemi reali che girano dietro le quinte** (progetti 01-04) da cui `generatore_numero.py` estrae, ogni settimana, la sezione più importante della newsletter — con la fonte di ogni numero dichiarata esplicitamente (reale o dimostrativo, mai confuso):

```bash
python3 generatore_numero.py
# 📈 NUMERI VERI — lo stato del cantiere, 15/07/2026
# - Rispondo (voce AI): 25 chiamate gestite, 4740€ di valore stimato recuperato...
# - TrovaBandi: 4 bandi in catalogo (2 a fondo perduto), ultima verifica 2026-07-14
# - Conforme (EU AI Act): prossima scadenza normativa — "..." tra 18 giorni
# - Ponte (gestionale officine): 0 officine attive, 0€ incassati...
```

Il punto geniale: **questo numero cresce da solo, ogni settimana che i progetti 01-04 restano in funzione**. Un concorrente che "scrive contenuti sull'AI" può copiare il formato del post in un pomeriggio; non può copiare 4 sistemi con mesi di storico dietro.

## Prima azione da fare OGGI

Esegui `python3 calendario.py`, prendi il post del giorno 1 e pubblicalo su LinkedIn entro stasera. Il primo post è: «Ho analizzato 9 idee di business per il 2026. Le sto lanciando tutte, in pubblico. Ecco la classifica →» *(hai già tutto il materiale: è il README di questa repo).*

## ✅ Cosa è completo (con dati mock) vs cosa serve da te

| Livello | Stato | Per andare live serve |
|---|---|---|
| Calendario editoriale, generatore numeri veri | ✅ Vero al 100% | Niente |
| Iscrizione con double opt-in (`iscrizioni.py`) | ✅ Codice vero, testato (demo + richieste HTTP reali) | Un hosting pubblico + le tue credenziali SMTP in `.env` (`CONFIGURAZIONE.md`) |
| Motore di invio bulk della newsletter | ❌ Non esiste — resta manuale | Incollare l'output in un client email o un servizio come Buttondown/Mailchimp |
| Informativa privacy per l'iscrizione | 📄 Promessa nel footer, da scrivere | Farla validare da un avvocato prima di attivare il modulo su un dominio pubblico |

Vedi `CONFIGURAZIONE.md` per la guida passo-passo.

## 🔍 Audit di sicurezza e legale — cosa è stato trovato e corretto

| Problema trovato | Rischio | Correzione |
|---|---|---|
| La newsletter non aveva alcun modulo di iscrizione reale (solo un placeholder "in arrivo") | Il pilastro "numeri veri" della strategia editoriale non aveva alcun modo di acquisire davvero iscritti | `iscrizioni.py`: backend reale con double opt-in, collegato al form nella homepage |
| `GET /iscritti` esporrebbe la lista email se non protetto | 🔴 Stesso rischio già trovato nel progetto 03: chiunque scoprisse l'URL leggerebbe tutti gli iscritti | Stessa protezione: chiave API con confronto a tempo costante, **mock = accesso sempre negato** |
| `POST /iscrivi` senza limite | Chiunque potrebbe inondarlo di iscrizioni false, riempiendo il database e spammando caselle email altrui con email di conferma indesiderate | Rate limit: 5 richieste/ora per IP |
| Nessun limite alla conservazione delle iscrizioni mai confermate | Email raccolte senza consenso verificato conservate a tempo indeterminato (violazione data minimization, GDPR art. 5) | Cancellazione automatica delle iscrizioni "in attesa" oltre 7 giorni |
| `generatore_numero.py`: rischio di mescolare dati demo e reali senza distinzione | Minerebbe alla radice la promessa "numeri veri" della newsletter — l'errore di credibilità più grave possibile per QUESTO prodotto specifico | Ogni numero riporta esplicitamente la propria fonte (reale/demo); verificato eseguendo lo script sia con dati reali presenti sia assenti |
| Un errore SMTP durante `POST /iscrivi` avrebbe fatto fallire l'intera richiesta, anche se l'iscrizione era già salvata nel database | L'utente avrebbe visto un errore anche quando la sua iscrizione era di fatto già registrata (in attesa di conferma) | L'invio email è isolato in un blocco try/except, come nel progetto 03: un SMTP momentaneamente irraggiungibile non fa fallire la richiesta |

Tutte le correzioni sono testate (demo end-to-end + richieste HTTP reali con chiave assente, mock, e rate limit superato).
