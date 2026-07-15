# ⚙️ Configurazione — da mock a produzione

> Tutto il codice è già pronto e testato. Questa pagina spiega esattamente cosa sostituire per passare da "SMS simulati" a "SMS veri". Nessuna riga di codice da scrivere.

## Prerequisito: capire cosa è già vero e cosa è mock

| Componente | Stato oggi | Cosa serve per renderlo vero |
|---|---|---|
| Gestionale multi-tenant, login, isolamento dati (`app.py`) | ✅ **Vero**, testato (selftest + richieste HTTP reali) | Niente — è già pronto |
| Richiami automatici (`richiami.py`, `GET /richiami`) | ✅ **Vero**, calcolo reale sullo storico | Niente — più dati accumula l'officina, più preciso diventa |
| SMS "veicolo pronto" / richiamo (`integrazioni/notifiche.py`) | 🟡 Mock (logga soltanto) | Credenziali Twilio reali |

## Passo 1 — Hosting pubblico (15 minuti)

Le officine devono poter raggiungere il gestionale da un URL pubblico HTTPS (da telefono/tablet in officina). Opzioni più semplici:
- **Render.com / Railway.app** (piano gratuito sufficiente per iniziare)
- Un piccolo VPS con un reverse proxy (nginx + certificato Let's Encrypt) se preferisci gestirlo tu

## Passo 2 — Account Twilio per l'SMS (15 minuti)

1. Crea un account su [twilio.com](https://twilio.com)
2. Console → **Account → API keys & tokens**: copia `Account SID` e `Auth Token`
3. Console → **Phone Numbers → Buy a number**: un numero con capacità "SMS" (anche italiano, +39)
4. Copia i valori in `.env`:
   ```
   TWILIO_ACCOUNT_SID=AC...
   TWILIO_AUTH_TOKEN=...
   TWILIO_NUMERO_SMS=+39...
   ```

**Fatto questo, l'SMS "veicolo pronto" e i richiami tagliando partono davvero** quando lo stato di un intervento passa a `pronto` (via `PATCH /interventi/<id>`) o quando lanci `python3 richiami.py --officina <id>` e invii tu i richiami trovati.

## Passo 3 — Login e sicurezza

- Ogni officina si registra da sola (`POST /auth/registra` o dal pulsante "Registra la tua officina" nella lavagna web) — non serve un admin per crearle.
- Le password sono già hashate con PBKDF2-HMAC-SHA256 (200.000 iterazioni) + salt casuale: non serve alcuna configurazione, ma **non condividere mai `officina.db`** senza prima valutare cosa contiene (vedi sezione GDPR sotto).
- Il rate limit di login (`LOGIN_RATE_LIMIT`, default 10 tentativi/ora per IP) protegge da tentativi di indovinare la password: alzalo solo se hai un motivo specifico, mai disattivarlo.

## Passo 4 — Verifica finale

```bash
# Con .env compilato:
python3 app.py
# Registra un'officina di prova, crea un intervento, portalo a "pronto":
# deve arrivare davvero l'SMS al numero del cliente.
```

## GDPR — chi tratta i dati di chi

Attenzione alla distinzione: **tu (chi opera Ponte) sei il fornitore del software; l'officina è titolare del trattamento dei dati dei SUOI clienti** (nome, telefono, targa). Questo significa:
- L'officina deve avere una propria informativa privacy verso i propri clienti (non è compito del software generarla, ma è compito tuo ricordarglielo in fase di onboarding).
- Tu, come fornitore, sei probabilmente **responsabile del trattamento** (art. 28 GDPR) per conto dell'officina: prima di avere clienti paganti, serve un accordo scritto (Data Processing Agreement) con ciascuna officina — non è incluso in questa cartella perché varia da giurisdizione a giurisdizione: fallo validare da un avvocato prima del primo cliente pagante.

### Cancellazione dati su richiesta (art. 17 GDPR — diritto all'oblio)

Se un cliente di un'officina chiede la cancellazione dei propri dati, l'officina (o tu per suo conto) deve poter cancellare **cliente + relativi veicoli e interventi**:

```bash
sqlite3 officina.db "
  DELETE FROM interventi WHERE veicolo_id IN (SELECT id FROM veicoli WHERE cliente_id = <ID_CLIENTE>);
  DELETE FROM veicoli WHERE cliente_id = <ID_CLIENTE>;
  DELETE FROM clienti WHERE id = <ID_CLIENTE>;
"
```

Nota: questo cancella anche lo storico usato da `richiami.py` per quel cliente — è corretto, la cancellazione deve essere completa, non parziale.

## Legale — da far rivedere PRIMA del primo cliente pagante

- Contratto SaaS con l'officina (termini di servizio + SLA minimo)
- Data Processing Agreement (DPA) — vedi sezione GDPR sopra
- Termini per l'invio SMS (l'officina deve avere il consenso del proprio cliente a ricevere SMS — di norma implicito nell'accettazione del veicolo, ma va scritto nella sua informativa)

Nessuno di questi sostituisce una consulenza legale vera: sono punti da coprire, non un documento pronto all'uso.
