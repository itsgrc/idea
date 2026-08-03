# 🛠️ Progetto 11 — Servizi per la casa: "ProntoCasa"

> **Missione:** trovare un idraulico, un elettricista o un muratore non deve significare chiamare cinque numeri sperando che qualcuno risponda. ProntoCasa contatta subito il professionista giusto — non tutti insieme, il migliore per primo.

## Il prodotto: un'app semplice per due tipi di utenti

**Chi cerca un servizio** (idraulico, elettricista, muratore, imbianchino, falegname, fabbro, giardiniere, traslocatore, climatizzazione, pulizie...) non ha bisogno di un account: può prima **sfogliare il registro dei professionisti** disponibili in zona — cosa fanno davvero e quanto costano (sopralluogo + tariffa oraria dichiarati da loro, mai i contatti diretti prima di un abbinamento) — poi descrive il problema e ProntoCasa fa il resto. **Chi offre il servizio** si registra una volta con i propri servizi e tariffe indicative, imposta la disponibilità, e riceve le richieste che il motore di affidabilità ritiene adatte a lui.

## Cosa c'è in questa cartella

| File | Cosa fa |
|---|---|
| `prontocasa.py` | **Motore funzionante** (zero dipendenze: `http.server` + `sqlite3`): registrazione/login professionisti (PBKDF2) con servizi e tariffe dichiarate, registro pubblico sfogliabile (`GET /professionisti`), richieste pubbliche senza account, pannello web incluso. `python3 prontocasa.py --selftest` |
| `affidabilita.py` | **Moat #1**: calcola il punteggio di ogni professionista da fatti reali (risposta, accettazione, completamento) — mai da stelline soggettive. `python3 affidabilita.py --demo` |
| `dispacciamento.py` | **Moat #2**: contatta il migliore disponibile, e se non risponde in tempo passa automaticamente al successivo — in cascata, senza intervento umano. `python3 dispacciamento.py --demo` |
| `integrazioni/notifiche.py` | SMS reale (Twilio) al professionista contattato e al cliente quando qualcuno accetta — mock finché le credenziali non sono reali |

## Prova subito

```bash
python3 prontocasa.py --selftest       # registrazione → richiesta → dispacciamento → accettazione → completamento
python3 affidabilita.py --demo         # due professionisti, storico diverso, punteggio diverso
python3 dispacciamento.py --demo       # un professionista non risponde → la cascata passa al successivo in automatico
python3 prontocasa.py                  # pannello + API su :8050 (prontocasa.db in locale)
```

## Il doppio moat: perché non è "un altro elenco di artigiani"

**1. Il motore di affidabilità (`affidabilita.py`)** — niente stelline: il punteggio di ogni professionista viene calcolato da tre fatti registrati dalla piattaforma stessa — risponde in tempo? Tra chi risponde, accetta? Tra chi accetta, completa il lavoro invece di sparire? Un professionista nuovo parte da un punteggio neutro (0.5), non penalizzato per mancanza di storico ma nemmeno avvantaggiato: il punteggio si guadagna lavorando bene, non si compra.

```bash
python3 affidabilita.py --demo
# 📊 Mario (risponde e completa sempre): {'punteggio': 0.94, ...}
# 📊 Luigi (spesso non risponde, non completa): {'punteggio': 0.3, ...}
```

**2. Il dispacciamento a cascata (`dispacciamento.py`)** — un allagamento non aspetta un preventivo via email. Il motore contatta SUBITO il candidato migliore disponibile; se scade il tempo (10 minuti per le urgenze, 3 ore per il resto) senza risposta, passa automaticamente al successivo — fino a 5 candidati, poi lo dice chiaramente invece di lasciare il cliente in attesa indefinita.

```bash
python3 dispacciamento.py --demo
# 👤 Proposta #1 inviata al professionista #1
# ⏰ Scadenza forzata nel passato — eseguo controlla_scadute()...
# 👤 Cascata: proposta #2 inviata automaticamente al professionista #2
# ✅ Il secondo professionista accetta: richiesta ora 'assegnata'
```

Nessun concorrente che vende "un elenco di artigiani" ha questi due motori: entrambi richiedono uno storico reale di richieste passate sulla stessa piattaforma — non si copiano in un weekend.

## Modello di business

| Chi | Prezzo | Include |
|---|---|---|
| Chi cerca un servizio | Gratis | Nessun account, dispacciamento automatico, SMS di conferma |
| Professionista · Base | 19 €/mese | Ricevi richieste nella tua categoria/città, nessuna commissione sui lavori |
| Professionista · Priorità | 39 €/mese | + priorità nella cascata a parità di punteggio, statistiche dettagliate |

## Roadmap 90 giorni

| Fase | Quando | Obiettivo | KPI di sblocco |
|---|---|---|---|
| 1. Validazione | Settimane 1–3 | 10 interviste a professionisti (quante chiamate perse a settimana?) | 6/10 confermano il dolore |
| 2. Massa critica locale | Settimane 4–8 | 5+ professionisti per categoria nella STESSA città (serve alla cascata) | 5 professionisti attivi, 1 città |
| 3. Paganti | Settimane 9–13 | Convertire i professionisti al piano a pagamento | 5 abbonamenti attivi |

**Perché "stessa città" è nel KPI di fase 2**: il dispacciamento a cascata vale poco con un solo professionista per categoria — serve massa critica locale prima di aspettarsi risultati, stessa lezione già scritta per Campolibero (progetto 10).

## ✅ Cosa è completo (con dati mock) vs cosa serve da te

| Livello | Stato | Per andare live serve |
|---|---|---|
| Motore, doppio moat, pannello web | ✅ Vero al 100%, testato (selftest + richieste HTTP reali) | Niente |
| SMS proposta/conferma | 🟡 Codice vero, credenziali Twilio mock | Le tue credenziali reali in `.env` (`CONFIGURAZIONE.md`) |
| Verifica delle abilitazioni professionali | ❌ Solo autodichiarazione — il codice non verifica nulla | Valutare con un legale se serve verifica documentale prima del lancio |
| Informativa privacy, DPA | ❌ Non esiste | Farla scrivere/validare da un avvocato prima del primo utente reale |

Vedi `CONFIGURAZIONE.md` per la guida passo-passo.

## 🔍 Audit di sicurezza — cosa è stato trovato e corretto (durante la costruzione, non dopo)

| Problema trovato | Rischio | Correzione |
|---|---|---|
| Le scritture su sqlite3 in `dispacciamento.py` non venivano mai confermate (`commit()`) prima di chiudere la connessione | 🔴 Il più serio: ogni proposta creata dal dispacciamento spariva silenziosamente, mai visibile al professionista — il prodotto centrale non funzionava affatto | Riscritto con `with conn:` (commit automatico a fine blocco, anche sui `return` anticipati), verificato: la proposta ora risulta visibile subito dopo la creazione |
| `GET /richieste/<id>/stato` era protetto solo dall'id numerico sequenziale | 🔴 Chiunque avrebbe potuto scorrere gli id (1, 2, 3...) e leggere nome e telefono di ogni cliente che ha mai fatto una richiesta | Aggiunto un codice casuale (`secrets.token_urlsafe`) generato alla creazione, richiesto come parametro oltre all'id; verificato che senza codice o con codice sbagliato la richiesta risulti "non trovata" |
| `POST /disponibilita` restituiva l'intera riga del professionista, incluso `password_hash` e `salt` | L'hash della password non ha alcun motivo di lasciare mai il server — superficie di attacco inutile | La query ora seleziona solo i campi che il client deve vedere |
| Nessun limite ai tentativi di login/registrazione, né a `POST /richieste` (pubblico, senza account) | Un estraneo avrebbe potuto tentare password a raffica, o inondare l'endpoint pubblico facendo scattare SMS reali a raffica verso professionisti veri | Rate limit: 10 tentativi/ora per IP su entrambi, verificato con richieste consecutive (le ultime ricevono 429) |
| Nessun controllo che un professionista rispondesse solo alle proposte indirizzate a lui, o modificasse solo le proprie richieste assegnate | Un professionista avrebbe potuto accettare/rifiutare proposte altrui, o segnare come completata una richiesta non sua | Verifica di proprietà esplicita in `rispondi_proposta()` e `aggiorna_stato_richiesta()`, verificata con un secondo professionista che tenta l'azione su una proposta/richiesta non sua (403 in entrambi i casi) |
| Timing side-channel nel login (stesso pattern dei progetti 04/10) | Un'email inesistente avrebbe risposto più veloce di una password sbagliata | Hash PBKDF2 calcolato comunque con salt fittizio anche per email inesistenti |

Tutte le correzioni sono testate con richieste HTTP reali pensate apposta per riprodurre ogni problema prima del fix, non solo lette nel codice.

## Prima azione da fare OGGI

Chiama 5 idraulici/elettricisti/muratori della tua zona e chiedi: «quante richieste perdi a settimana perché non riesci a rispondere in tempo, o perché il cliente ha già chiamato qualcun altro?». È la tua prima slide di vendita — e la controprova che "rispondere per primo" vale più di "essere nell'elenco".
