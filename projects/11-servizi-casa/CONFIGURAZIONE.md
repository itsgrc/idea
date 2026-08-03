# ⚙️ Configurazione — da mock a produzione

> Tutto il codice è già pronto e testato. Questa pagina spiega esattamente cosa sostituire per passare da "SMS simulati" a "professionisti contattati davvero".

## Prerequisito: capire cosa è già vero e cosa è mock

| Componente | Stato oggi | Cosa serve per renderlo vero |
|---|---|---|
| Motore multi-professionista, pannello web | ✅ **Vero al 100%**, testato (selftest + richieste HTTP reali) | Niente |
| Motore di affidabilità (`affidabilita.py`) | ✅ **Vero al 100%** — calcolo reale sullo storico | Niente |
| Dispacciamento a cascata (`dispacciamento.py`) | ✅ **Vero al 100%**, testato con cascata reale (proposta scaduta → passa al successivo) | Niente |
| SMS proposta/conferma (`integrazioni/notifiche.py`) | 🟡 Codice vero, credenziali Twilio mock | Le tue credenziali reali in `.env` |

## Passo 1 — Hosting pubblico (15 minuti)

Serve un URL pubblico HTTPS raggiungibile sia dai professionisti (per gestire disponibilità e proposte) sia dai clienti finali (per inviare richieste senza account). Render.com/Railway.app (piano gratuito) o un VPS vanno bene.

## Passo 2 — Twilio per gli SMS (15 minuti)

Stesso procedimento degli altri progetti del portfolio: account su [twilio.com](https://twilio.com), copia `Account SID`/`Auth Token`, compra un numero con capacità SMS, mettili in `.env`.

## Passo 3 — Il tick periodico per la cascata

`controlla_scadute()` viene già chiamato opportunisticamente a ogni nuova richiesta e a ogni risposta ricevuta — sufficiente per un volume basso/medio. Per un volume più alto, aggiungi anche un cron che lo richiama ogni minuto così le proposte scadute avanzano anche senza nuovo traffico:

```bash
# crontab -e
* * * * * cd /percorso/11-servizi-casa && python3 -c "from dispacciamento import controlla_scadute; controlla_scadute()"
```

## Passo 4 — Verifica finale

```bash
python3 prontocasa.py
# Registra un professionista, invia una richiesta dalla pagina pubblica:
# deve arrivare davvero l'SMS. Fai scadere una proposta (o aspetta il
# timeout) e verifica che la cascata passi al professionista successivo.
```

## GDPR e responsabilità — cosa è già coperto vs cosa resta da fare

- ✅ Le richieste dei clienti finali sono protette da un codice casuale (non dal solo id sequenziale): impedisce che chiunque scorra gli id e legga nome/telefono di ogni cliente
- ✅ Nessuna risposta API espone mai password_hash o salt
- ✅ Isolamento tra professionisti: uno non può rispondere alle proposte di un altro né modificare richieste non sue (verificato con test)
- ❌ **Da fare**: informativa privacy completa per clienti finali e professionisti, da far validare da un avvocato prima del primo utente reale
- ❌ **Da fare**: un Data Processing Agreement se ProntoCasa tratta dati per conto di professionisti come attività autonome (verificare con un legale chi è titolare del trattamento in questo modello a due lati)

### Cancellazione dati su richiesta (art. 17 GDPR)

```bash
# Cancellare tutte le richieste di un cliente (per telefono)
sqlite3 prontocasa.db "
  DELETE FROM proposte WHERE richiesta_id IN (SELECT id FROM richieste WHERE cliente_telefono='+39...');
  DELETE FROM richieste WHERE cliente_telefono='+39...';
"
# Cancellare un professionista (mantiene lo storico aggregato delle
# richieste passate, ma rimuove i suoi dati identificativi)
sqlite3 prontocasa.db "DELETE FROM professionisti WHERE email='...';"
```

## Nota importante — verifica dei requisiti professionali

Il codice richiede una dichiarazione esplicita (`dichiarazione_requisiti`) al momento della registrazione, ma **non verifica in alcun modo** che un professionista possieda davvero le abilitazioni di legge (es. DM 37/08 per impianti elettrici/idraulici, iscrizione ad albi/camere di commercio). Prima di andare in produzione con clienti reali, valuta con un legale se e come integrare una verifica documentale (upload di certificazioni, controllo partita IVA/camera di commercio) — il rischio altrimenti ricade sulla piattaforma in caso di lavori svolti da chi dichiara il falso.
