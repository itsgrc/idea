# ⚙️ Configurazione — da mock a produzione

> Tutto il codice è già pronto e testato. Questa pagina spiega esattamente cosa sostituire per passare da "email simulate" a "newsletter vera".

## Prerequisito: capire cosa è già vero e cosa è mock

| Componente | Stato oggi | Cosa serve per renderlo vero |
|---|---|---|
| Iscrizione con double opt-in (`iscrizioni.py`) | ✅ **Vero**, testato (demo + richieste HTTP reali) | Un hosting pubblico + credenziali SMTP |
| Generatore "Numeri veri" (`generatore_numero.py`) | ✅ **Vero al 100%** — legge dati reali dagli altri progetti | Niente — più i progetti 01-04 vengono usati, più diventa ricco |
| Invio della newsletter vera e propria | 📄 Manuale (copia-incolla in un servizio di invio) | Vedi nota sotto |

## Passo 1 — Hosting pubblico (15 minuti)

Serve un URL pubblico HTTPS sia per la pagina di iscrizione sia per i link `/conferma` e `/disiscrivi` dentro le email — devono essere aperti da chi li riceve, non da `localhost`. Render.com/Railway.app (piano gratuito) o un piccolo VPS vanno bene.

## Passo 2 — Credenziali SMTP (10 minuti)

Qualsiasi provider SMTP va bene (Gmail con "app password", provider transazionali come chi già usi per i progetti 01-03). Copia in `.env`:
```
SMTP_HOST=smtp.tuoprovider.it
SMTP_PORT=587
SMTP_USER=...
SMTP_PASSWORD=...
SMTP_MITTENTE=info@tuodominio.it
NEWSLETTER_PUBLIC_URL=https://tuoapp.onrender.com
```
**`NEWSLETTER_PUBLIC_URL` deve essere l'URL pubblico reale**: è quello che finisce nel link di conferma dentro l'email. Se lo lasci a `localhost`, chi riceve l'email non potrà mai confermare l'iscrizione.

## Passo 3 — Genera e proteggi la chiave per `/iscritti`

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```
Mettila in `NEWSLETTER_API_KEY`. Senza questo passo, l'endpoint resta chiuso di proposito (vedi commento nel codice) — quindi **non riuscirai a scaricare la lista iscritti finché non lo fai**, non è un bug.

## Passo 4 — Comporre e inviare il numero settimanale

```bash
python3 generatore_numero.py                    # sezione "Numeri veri" coi dati di oggi
python3 calendario.py > CALENDARIO.md           # calendario editoriale 90 giorni
curl -H "X-Api-Key: $NEWSLETTER_API_KEY" https://tuoapp.onrender.com/iscritti  # lista destinatari
```
L'invio vero e proprio (comporre l'email finale e spedirla a tutta la lista) resta manuale — non c'è ancora un motore di invio bulk in questa cartella: con poche centinaia di iscritti, incollare l'output di `generatore_numero.py` in un client email o in un servizio come Buttondown/Mailchimp è più veloce che costruirne uno.

## Passo 5 — Verifica finale

```bash
# Con .env compilato:
python3 iscrizioni.py
# Iscriviti con un'email vera dalla homepage: deve arrivare davvero
# l'email di conferma, e il click sul link deve confermare l'iscrizione.
```

## GDPR — cosa è già coperto

- **Double opt-in**: nessuna email finisce nella lista attiva senza click di conferma esplicito (art. 4(11), consenso libero e inequivocabile).
- **Data minimization**: le iscrizioni mai confermate vengono cancellate automaticamente dopo 7 giorni (non è consenso, non ha senso conservarle).
- **Diritto all'oblio**: il link di disiscrizione cancella immediatamente il record, non lo marca soltanto come "disiscritto" — non serve una richiesta separata.
- **Cosa NON è coperto**: l'informativa privacy completa da mostrare in fase di iscrizione. Il footer di `homepage.html` la promette "al momento dell'attivazione" — scrivila (o fanne validare una bozza da un avvocato) prima di attivare il modulo su un dominio pubblico.
