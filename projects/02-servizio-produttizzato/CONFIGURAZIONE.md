# ⚙️ Configurazione — da mock a produzione

## Cosa è già vero e cosa è mock

| Componente | Stato oggi | Cosa serve per renderlo vero |
|---|---|---|
| Motore di matching (`scout.py`) | ✅ **Vero** | Niente |
| Database bandi (`bandi.json`) | ✅ **4 bandi reali verificati**, fonti ufficiali | Ampliarlo con altre regioni/temi (richiede ricerca e verifica manuale — vedi sotto) |
| Guardiano di freschezza (`verifica_freschezza.py`) | ✅ **Vero** | Niente — eseguilo prima di ogni invio |
| Monitor raggiungibilità (`monitor.py`) | ✅ **Vero** (logica HTTP standard) | Un cron settimanale su un hosting reale |
| Mail-merge (`campagna.py`) | ✅ **Vero** | Il tuo CSV di prospect reali (con consenso) |
| Invio email (`invio.py`) | 🟡 Mock (dry-run) | Credenziali SMTP reali + flag `--conferma` |

## Passo 1 — Credenziali SMTP (10 minuti)

**Opzione A — Gmail (per iniziare, gratis):**
1. Attiva la verifica in due passaggi sul tuo account Google
2. [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) → crea una password per l'app "Mail"
3. `.env`:
   ```
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=tuonome@gmail.com
   SMTP_PASSWORD=<password per l'app, 16 caratteri>
   SMTP_MITTENTE=tuonome@gmail.com
   ```

**Opzione B — email professionale del tuo dominio (consigliata per un servizio a pagamento):**
Usa le credenziali SMTP fornite dal tuo provider (Aruba, Register.it, Google Workspace, ecc.) — di solito in "Impostazioni → Client di posta" del pannello webmail.

## Passo 2 — Il tuo CSV di prospect reali

Copia `prospects_esempio.csv`, sostituisci le righe con contatti veri (con il loro consenso a essere contattati), **includi la colonna `email` con indirizzi reali**. Poi:

```bash
python3 verifica_freschezza.py         # controllo di disciplina PRIMA di ogni invio
python3 campagna.py prospects_reali.csv
python3 invio.py campagna-<data>.md    # dry-run: controlla che sia tutto giusto
python3 invio.py campagna-<data>.md --conferma   # invio VERO, solo quando sei sicuro
```

## Passo 3 — Ampliare il database bandi

`bandi.json` oggi ha 4 bandi **reali e verificati**. Per aggiungerne altri:

1. Cerca bandi ufficiali per regione/tema (portali: `bandi.regione.<regione>.it`, Unioncamere locale, MIMIT, SIMEST)
2. **Verifica che siano ancora aperti** — durante la costruzione di questo database abbiamo scartato 3 bandi 2026 dall'aspetto promettente perché già scaduti (uno di novembre 2025, due di maggio/giugno 2026): è la ragione per cui questo passo richiede sempre una verifica umana, non un automatismo
3. Aggiungi la voce in `bandi.json` con `data_verifica` di oggi, `fonte` come URL diretto al bando (non alla homepage dell'ente)
4. Se il bando è a fondo perduto con percentuale sull'investimento: `tipo_calcolo: "fondo_perduto"`. Se copre interessi su un finanziamento, o dipende da un parametro diverso dall'investimento (monte salari, ecc.): `tipo_calcolo: "interessi_subsidy"` o `"non_quantificabile"` + un campo `nota_calcolo` che spieghi perché — **mai forzare un numero che non è corretto**

## Passo 4 — Automazione (opzionale, quando hai un hosting)

```bash
# crontab -e, esempio: ogni lunedì alle 8:00
0 8 * * 1 cd /percorso/progetto && python3 verifica_freschezza.py && python3 monitor.py
```

## Legale

- P.IVA (anche regime forfettario, si apre in 24 ore) prima del primo incasso
- Il servizio consiste in informazione e supporto: non promettere mai l'ottenimento del contributo (dipende dall'ente erogante) — vedi le clausole già nella homepage e nell'offerta
