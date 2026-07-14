# ⚙️ Configurazione — da mock a produzione

## Cosa è già vero e cosa è mock

| Componente | Stato oggi | Cosa serve per renderlo vero |
|---|---|---|
| Classificatore, Registro, scadenzario | ✅ **Vero** | Niente |
| Assessment self-service (`assessment.html`) | ✅ **Vero**, verificato con 5 scenari | Un hosting pubblico per pubblicarlo |
| Backend lead capture (`lead_capture.py`) | ✅ **Vero**, salvataggio reale testato | Hosting + notifica email reale |
| Notifica nuovo lead via email | 🟡 Mock (logga soltanto) | Credenziali SMTP reali (vedi .env.example) |
| Partner legale per validare gli audit | ❌ Non esiste | Serve trovarlo e negoziare — vedi `PARTNERSHIP-LEGALE-TEMPLATE.md` |

## Passo 1 — Avvia il backend in locale (1 minuto)

```bash
python3 lead_capture.py
# apri http://localhost:8010 nel browser: è l'assessment servito dal backend
```

Fai il questionario, richiedi l'audit inserendo un'email: il lead finisce in `lead.jsonl` e vedi la notifica (simulata) in console.

**Prima di vedere i lead serve una chiave** (protezione obbligatoria: `/leads` contiene email e classificazioni dei prospect):
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # genera una chiave vera
LEAD_API_KEY=<chiave-generata> python3 lead_capture.py
curl -H "X-Api-Key: <chiave-generata>" http://localhost:8010/leads
```
Senza `LEAD_API_KEY` configurata (resta al valore `MOCK_...`), `/leads` risponde sempre 401 — nessuna chiave funziona, di proposito: è il comportamento sicuro di default.

## Cancellazione dei lead (diritto all'oblio, Art. 17 GDPR)

`lead.jsonl` è un file di testo semplice: per cancellare il lead di una persona che lo richiede,
```bash
grep -v "email-da-rimuovere@esempio.it" lead.jsonl > lead_tmp.jsonl && mv lead_tmp.jsonl lead.jsonl
```
Per un volume più alto di richieste, vale la pena costruire uno script dedicato — a questo volume iniziale, il comando sopra è sufficiente e va eseguito entro i termini di legge (di norma 30 giorni) dalla richiesta.

## Passo 2 — Credenziali SMTP per la notifica reale (10 minuti)

Stessa procedura del progetto TrovaBandi (vedi `../02-servizio-produttizzato/CONFIGURAZIONE.md` per i dettagli Gmail/provider professionale). Compila `.env` con le tue credenziali e `NOTIFICA_LEAD_A` con l'email che vuoi ricevere.

## Passo 3 — Hosting pubblico (15 minuti)

Stesse opzioni del progetto Rispondo: Render.com o Railway.app, piano gratuito per iniziare. Una volta online, l'URL pubblico è la pagina da linkare nella tua strategia di content marketing (LinkedIn, webinar, ecc.) — il modulo "Richiedi l'audit" funziona automaticamente perché il backend gira sullo stesso dominio.

## Passo 4 — Il partner legale (il pezzo che il codice non può darti)

Leggi `PARTNERSHIP-LEGALE-TEMPLATE.md` e usalo come base per la prima conversazione con 3-5 studi legali. Finché questo pezzo manca, posiziona il servizio esplicitamente come "pre-assessment" (già corretto in tutte le pagine) — non promettere mai una classificazione legalmente opponibile senza la firma di un professionista abilitato.

## Manutenzione dello scadenzario normativo

`scadenzario.py` contiene le date del Digital Omnibus verificate al 14/07/2026. **La normativa europea si evolve**: quando emergono nuovi sviluppi (nuovi pacchetti, sentenze, decreti attuativi italiani), aggiorna `CALENDARIO` in `scadenzario.py` e la relativa nota nel `README.md`. È esattamente questo aggiornamento continuo — non il codice in sé — il vero vantaggio competitivo del progetto.
