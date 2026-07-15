# 🏆 Progetto 10 — Prenotazioni Multisport: "Campolibero"

> **Missione:** ogni centro sportivo italiano perde soldi in due modi silenziosi — lo slot prenotato e mai occupato, e il cliente che se ne va perché "pieno" senza sapere che il campo del vicino era libero. Campolibero risolve entrambi con i dati, non con un calendario in più.

## Il prodotto: un pannello di prenotazione semplice, con due cervelli sotto

Padel, calcio a 5, tennis, corsi, personal trainer: qualunque "risorsa" prenotabile a slot (campo, sala, istruttore) nello stesso pannello, gestito da una o più strutture sportive. Per il gestore: accettazione in 30 secondi, riepilogo del giorno. Per il cliente: un link, uno slot, un SMS di conferma. Nessuna app da scaricare.

## Cosa c'è in questa cartella

| File | Cosa fa |
|---|---|
| `prenota.py` | **Motore multi-tenant funzionante** (zero dipendenze: `http.server` + `sqlite3`): più strutture sullo stesso server, isolate tra loro (login, PBKDF2). Gestisce risorse, disponibilità, prenotazioni, pannello web incluso. `python3 prenota.py --selftest` |
| `rischio_noshow.py` | **Moat #1**: decide caso per caso se chiedere un deposito, incrociando lo storico del cliente e quello della fascia oraria — mai un deposito ai clienti affidabili. `python3 rischio_noshow.py --demo` |
| `rete_disponibilita.py` | **Moat #2**: quando la struttura richiesta è piena, cerca in tempo reale un posto nelle altre strutture della stessa città. `python3 rete_disponibilita.py --demo` |
| `integrazioni/notifiche.py` | SMS di conferma e promemoria via Twilio — mock finché le credenziali non sono reali |
| `integrazioni/pagamenti.py` | Deposito via Stripe Checkout (link di pagamento, zero SDK) — mock finché le credenziali non sono reali |

## Prova subito

```bash
python3 prenota.py --selftest         # registrazione → login → prenotazione → isolamento dati, verificato
python3 rischio_noshow.py --demo      # slot storicamente rischioso → deposito richiesto; slot pulito → nessun deposito
python3 rete_disponibilita.py --demo  # struttura piena → trova il primo posto libero nella rete
python3 prenota.py                    # pannello + API su :8040 (campolibero.db in locale)
```

## Il doppio moat: perché non è "un altro Calendly per palestre"

**1. Il motore anti no-show (`rischio_noshow.py`)** — il problema che nessun calendario generico affronta. La soluzione ovvia (deposito sempre) scoraggia i clienti buoni; quella opposta (mai deposito) regala gli slot a chi salta sempre. Il motore incrocia due storici reali — *questo cliente* ha già saltato prenotazioni qui? *Questa fascia oraria*, in QUESTA struttura, ha uno storico di no-show alto? — e decide solo quando serve davvero:

```bash
python3 rischio_noshow.py --demo
# 📅 Cliente nuovo, lunedì mattina alle 8 (slot storicamente rischioso):
#    {'punteggio': 0.75, 'richiede_deposito': True, 'motivo': 'questa fascia oraria ha uno storico di no-show del 75%...'}
# 🌆 Cliente nuovo, stesso campo ma orario serale (nessuno storico negativo):
#    {'punteggio': 0.1, 'richiede_deposito': False, ...}
```

Nessun concorrente che vende "un calendario" ha l'interesse né lo storico per farlo: serve mesi di prenotazioni accumulate PROPRIO in quella struttura. Più Campolibero viene usato, più la stima diventa precisa — un vantaggio che si compone nel tempo, non un algoritmo che si copia in un weekend.

**2. La rete di disponibilità (`rete_disponibilita.py`)** — un effetto rete vero, non solo una funzione furba: il suo valore cresce con il numero di strutture iscritte nella stessa città. Un singolo concorrente con "solo un calendario" non può replicarlo da solo, per definizione — servono ALTRE strutture reali sulla stessa piattaforma:

```bash
python3 rete_disponibilita.py --demo
# 🔎 Campo A (Padel Centro) pieno il 2026-08-10 — cerco nella rete di Milano per le 18:00...
#    ✅ Padel Navigli — Campo Centrale alle 18:30 (32.0€/h, 0.5h dall'orario richiesto)
```

## Modello di business

| Piano | Prezzo | Include |
|---|---|---|
| Base | 39 €/mese | Prenotazioni illimitate, SMS di conferma, 1-2 risorse |
| Struttura | 79 €/mese | + motore anti no-show, risorse illimitate, riepilogo giornaliero |
| Rete | 129 €/mese | + rete di disponibilità con le altre strutture della zona |

## Roadmap 90 giorni

| Fase | Quando | Obiettivo | KPI di sblocco |
|---|---|---|---|
| 1. Validazione | Settimane 1–3 | 10 interviste a gestori di centri sportivi (no-show quanto costa davvero?) | 6/10 confermano il dolore |
| 2. Massa critica locale | Settimane 4–8 | 3+ strutture della STESSA città (serve per la rete) | 3 strutture in pilota nella stessa zona |
| 3. Paganti | Settimane 9–13 | Convertire il pilota | 3 strutture pagante, prima rete attiva davvero |

**Perché "stessa città" è nel KPI di fase 2, non un dettaglio**: la rete di disponibilità vale zero con una sola struttura. Il primo pilota deve concentrarsi geograficamente, non disperdersi — è la lezione di disciplina già scritta per gli altri progetti del portfolio applicata qui.

## ✅ Cosa è completo (con dati mock) vs cosa serve da te

| Livello | Stato | Per andare live serve |
|---|---|---|
| Motore prenotazioni, doppio moat, pannello web | ✅ Vero al 100%, testato (selftest + richieste HTTP reali) | Niente |
| SMS conferma/promemoria | 🟡 Codice vero, credenziali Twilio mock | Le tue credenziali reali in `.env` |
| Deposito via Stripe Checkout | 🟡 Codice vero, credenziali Stripe mock | Le tue credenziali reali in `.env` (`CONFIGURAZIONE.md`) |
| Informativa privacy per i clienti finali | ❌ Non esiste — è l'unico pezzo che il codice non può darti | Farla validare da un avvocato prima del primo cliente pagante |

Vedi `CONFIGURAZIONE.md` per la guida passo-passo.

## 🔍 Audit di sicurezza e legale — cosa è stato trovato e corretto

| Problema trovato | Rischio | Correzione |
|---|---|---|
| `durata_slot_min` non validato: un valore ≤0 manda in loop infinito la generazione degli slot | 🔴 Il più serio: bastava un valore sbagliato (anche per errore, non solo malizia) per bloccare il processo su ogni richiesta di disponibilità che toccasse quella risorsa | Validazione 5–480 minuti in `crea_risorsa()`, riprodotto e verificato con un test diretto della funzione di generazione slot prima e dopo il fix |
| `durata_slot_min: 0` esplicito veniva silenziosamente sostituito con 60 (`0 or 60` in Python coincide 0 con "assente") | Un valore invalido spariva senza errore invece di essere rifiutato — comportamento silenzioso, difficile da diagnosticare | Sostituito con un controllo esplicito su `None`, così 0 arriva alla validazione e viene rifiutato con un messaggio chiaro |
| Nessun limite ai tentativi di login/registrazione | Un estraneo che conosce l'email di una struttura potrebbe tentare password a raffica | Rate limit: 10 tentativi/ora per IP, verificato con 12 richieste consecutive (le ultime due 429) |
| `GET /rete` pubblico senza alcun limite | Chiunque avrebbe potuto usarlo per interrogare a raffica tutte le combinazioni città/sport in catalogo | Rate limit: 30 richieste/ora per IP |
| Parametri data/ora malformati (`giorno`, `inizio`) causavano un'eccezione non gestita invece di un errore HTTP pulito | Richieste malformate avrebbero potuto interrompere la risposta invece di ricevere un 400 | `do_GET` avvolto in un blocco che converte `ValueError` in risposta 400, verificato con parametri invalidi |
| Timing side-channel in `login()` (stesso pattern già trovato nel progetto 04) | Un'email inesistente rispondeva più veloce di una password sbagliata, rivelando quali email sono registrate | Hash PBKDF2 calcolato comunque con salt fittizio anche per email inesistenti |
| Webhook Stripe senza validazione della firma | Chiunque avrebbe potuto fingere un deposito mai pagato e sbloccare una prenotazione senza versare nulla | Porting Python dell'algoritmo di firma Stripe (HMAC-SHA256, tolleranza anti-replay), verificato con firme valide e contraffatte |

Tutte le correzioni sono testate (richieste HTTP reali, incluse quelle pensate apposta per riprodurre ogni problema prima del fix).

## Prima azione da fare OGGI

Chiama 3 centri sportivi (padel, calcio a 5, tennis — anche diversi sport) della tua zona e chiedi al gestore: «quanti slot a settimana restano vuoti per gente che prenota e non si presenta?». Se la risposta è "parecchi", hai il tuo primo prospect — e il secondo e il terzo, per far partire davvero la rete.
