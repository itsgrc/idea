# 🔧 Progetto 04 — Micro-SaaS verticale: Gestionale AI per Officine

> **Missione:** portare le officine italiane da carta+WhatsApp a un gestionale che *lavora al posto loro*. Il playbook ServiceTitan (HVAC, USA, valutata miliardi), applicato a una nicchia europea scoperta.

## Perché le officine (ma leggi `NICCHIA.md` prima di sposarla)

- ~80.000 autofficine/carrozzerie in Italia, digitalizzazione bassissima
- Workflow doloroso e ripetuto: accettazione → preventivo → attesa ricambi → consegna → incasso, tutto su carta e telefonate
- Il momento AI: *foto del danno → bozza di preventivo*, *targa → storico veicolo*, *richiamo automatico tagliandi* — cose impossibili per i gestionali legacy

## Cosa c'è in questa cartella

| File | Cosa fa |
|---|---|
| `app.py` | **Gestionale multi-tenant funzionante** (zero dipendenze: `http.server` + `sqlite3`): più officine sullo stesso server, ognuna isolata dalle altre (login email+password, token di sessione, PBKDF2). API REST per clienti, veicoli, interventi, con lavagna web inclusa. `python3 app.py --selftest` |
| `richiami.py` | **Il moat**: mina lo storico interventi di ogni veicolo per stimare quando è il prossimo tagliando/cambio gomme/revisione, e segnala i veicoli in scadenza — dati reali di quell'officina, non una regola fissa uguale per tutti. `python3 richiami.py --demo` |
| `integrazioni/notifiche.py` | SMS reale (Twilio) al cliente quando il veicolo è pronto o quando è in scadenza per un richiamo — mock finché le credenziali non sono reali |
| `NICCHIA.md` | Framework di scelta/validazione della nicchia: usalo PRIMA di scrivere altra UI |

## Prova subito

```bash
python3 app.py --selftest   # crea il db, esegue registrazione+login+isolamento dati, verifica
python3 richiami.py --demo  # popola 3 veicoli con storico finto, mostra i richiami stimati
python3 app.py              # API + lavagna web su :8000 (officina.db creato in locale)
```

Flusso coperto: **registrazione officina → login → cliente → veicolo → intervento** (`accettato → in_lavorazione → pronto → consegnato`) con preventivo, importo finale, e SMS automatico al cliente quando il veicolo è pronto. Ogni officina vede SOLO i propri dati, anche sullo stesso server.

## Il moat: richiami automatici dai dati reali, non da una regola fissa

Un gestionale generico "ricorda" solo cosa gli scrivi tu. `richiami.py` **rilegge la storia** di ogni veicolo: se un'officina ha già fatto due tagliandi alla stessa auto, calcola l'intervallo REALE tra i due (non una media di mercato) e stima quando sarà il prossimo — con tanto di indicazione della fonte (`storico_veicolo` vs `riferimento_di_mercato`, quest'ultimo dichiarato come stima indicativa, non un dato certo). Più l'officina usa Ponte, più questa lista diventa precisa: è un vantaggio che **si compone nel tempo**, non replicabile aprendo un gestionale concorrente il giorno dopo.

```bash
python3 richiami.py --demo
# 🟡 AB123CD (Panda 1.2) — Luca Bianchi ...
#    tagliando: ultimo 2025-12-22, stimato scadere il 2026-07-15 (0 giorni) — fonte: storico_veicolo
```

Il gestionale espone questa lista anche via `GET /richiami` (autenticato), pronta da collegare a un pulsante "richiama i clienti in scadenza" nella lavagna.

## Architettura evolutiva (mai riscrivere, solo aggiungere)

```
ORA (v1)                                  v2 (mese 4+)
app.py multi-tenant + richiami + SMS  →  + strato AI:
                                            - foto del danno → bozza preventivo
                                            - voce: integrazione progetto #01 (stesso numero,
                                              flusso "officina.json" già pronto in quel progetto)
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

## ✅ Cosa è completo (con dati mock) vs cosa serve da te

| Livello | Stato | Per andare live serve |
|---|---|---|
| Gestionale multi-tenant, login, lavagna web, richiami | ✅ Vero al 100%, testato (selftest + richieste HTTP reali) | Niente |
| SMS "veicolo pronto" / richiamo (`integrazioni/notifiche.py`) | 🟡 Codice vero, credenziali Twilio mock | Le tue credenziali reali in `.env` (`CONFIGURAZIONE.md`) |
| Data Processing Agreement con le officine clienti | ❌ Non esiste — è l'unico pezzo che il codice non può darti | Farlo validare da un avvocato prima del primo cliente pagante (`CONFIGURAZIONE.md`) |

Vedi `CONFIGURAZIONE.md` per la guida passo-passo.

## 🔍 Audit di sicurezza e legale — cosa è stato trovato e corretto

| Problema trovato | Rischio | Correzione |
|---|---|---|
| Versione originale (v0) non aveva alcuna autenticazione: un solo `officina.db` condiviso, nessun isolamento tra officine diverse | 🔴 Il più serio: due officine sullo stesso server avrebbero visto e potuto modificare i dati l'una dell'altra | Riscrittura multi-tenant: ogni tabella ha `officina_id`, ogni query è scoperta da `officina_da_token()`, verificato con un test che tenta esplicitamente di far leggere/modificare a un'officina i dati di un'altra (fallisce come previsto) |
| Nessun limite ai tentativi di login | Un estraneo che conosce l'email di un'officina potrebbe tentare password a raffica | Rate limit: 10 tentativi/ora per IP su `/auth/registra` e `/auth/login`, verificato con 12 richieste consecutive (le ultime due ricevono 429) |
| Vincolo di unicità della targa era globale nella v0 | Due officine diverse non avrebbero potuto registrare la stessa targa (es. la stessa auto vista da due officine indipendenti), un blocco funzionale reale | Unicità cambiata a `(officina_id, targa)`: ogni officina ha il proprio spazio, verificato inserendo la stessa targa in due officine diverse |
| Password: nessuna in v0 (non esisteva login) | — | PBKDF2-HMAC-SHA256, 200.000 iterazioni, salt casuale per officina, confronto a tempo costante in fase di verifica |
| `login()` saltava il calcolo PBKDF2 quando l'email non esisteva (`not riga or ...` in corto circuito) | Timing side-channel: un login con email inesistente rispondeva più veloce di uno con password sbagliata, permettendo di scoprire quali email sono registrate misurando i tempi di risposta | Anche con email inesistente viene calcolato un hash PBKDF2 fittizio, così il tempo di risposta è lo stesso in entrambi i casi |
| `homepage.html` dichiarava "dati su server in Europa" in modo assoluto | Claim non allineato all'architettura reale (l'SMS passa da Twilio, fornitore USA): stesso rischio di pubblicità ingannevole già trovato e corretto nel progetto 01 | Testo corretto per riferirsi a GDPR + Clausole Contrattuali Standard, coerente col progetto 01 |

Tutte le correzioni sono testate (selftest automatico + richieste HTTP reali con token validi, invalidi e assenti).

## Prima azione da fare OGGI

Porta la macchina a fare il tagliando. Mentre aspetti, guarda come gestiscono l'accettazione (carta? lavagna? WhatsApp?) e chiedi al titolare: «quanto tempo perde al giorno a rincorrere ricambi e clienti al telefono?». Quella risposta vale più di un mese di sviluppo.
