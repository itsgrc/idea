# ⚖️ Progetto 03 — Compliance-as-a-Service per l'EU AI Act

> **Missione:** trasformare l'incertezza normativa in un business ricorrente. La legge è il nostro reparto marketing — e sapere leggerla meglio dei concorrenti è il prodotto.

## Il momento (aggiornato al Digital Omnibus, 29/06/2026)

Il 29 giugno 2026 il Consiglio UE ha **rinviato** gli obblighi per i sistemi ad **alto rischio** dal 2 agosto 2026 al **2 dicembre 2027** (pacchetto "Digital Omnibus"). Molti contenuti online, scritti prima di questa data, ripetono ancora la scadenza vecchia. Nel frattempo gli obblighi di **trasparenza (art. 50) restano invariati e scadono ad agosto 2026** — tra poche settimane. La maggior parte delle aziende italiane mid-market non sa nemmeno *quali* dei suoi sistemi ricadono nel regolamento, né quale delle due scadenze le riguarda davvero. Il primo prodotto è esattamente questo: **dirglielo, con la data giusta**.

## Cosa c'è in questa cartella

| File | Cosa fa |
|---|---|
| `classifica.py` | **Il prodotto, versione 0**: questionario CLI che classifica un sistema AI nei livelli di rischio dell'AI Act e genera il report con gli obblighi — date aggiornate al Digital Omnibus. `python3 classifica.py --demo` |
| `registro.py` | Il Registro dei Sistemi AI multi-sistema con gap analysis. `python3 registro.py --demo` |
| `scadenzario.py` | **Il calendario normativo reale**, incrociato col Registro del cliente. `python3 scadenzario.py --demo` |
| `assessment.html` | **Lo strumento self-service** per il sito: stessa logica di `classifica.py` in JavaScript puro, zero backend, con lead capture. Aprilo nel browser |
| `templates/registro-sistemi-ai.md` | Il "Registro dei Sistemi AI" — primo deliverable che ogni cliente deve avere, pronto da compilare |

## Il moat: sapere la data giusta quando tutti ripetono quella sbagliata

La maggior parte dei contenuti online sull'AI Act — scritti prima di giugno 2026 — ripete ancora "scadenza agosto 2026 per l'alto rischio". Chi tiene il calendario normativo aggiornato in tempo reale ha un vantaggio che non si copia con un articolo: richiede monitorare gli sviluppi settimana dopo settimana, non una volta e basta.

**`scadenzario.py`** trasforma questo vantaggio in un deliverable: incrocia il Registro del cliente con la timeline corretta e produce l'argomento di vendita esatto — *"il rinvio non è un motivo per aspettare: la trasparenza scade comunque ad agosto 2026, e chi si prepara ora arriva pronto quando gli altri saranno in affanno a fine 2027."*

**`assessment.html`** chiude il vuoto "lead-gen" segnalato in Control Room: prima l'unico modo di provare il classificatore era il terminale. Ora è una pagina che si apre nel browser, senza installare nulla, con la stessa logica di `classifica.py` — verificata con un harness di test headless prima di essere pubblicata (5 scenari, tutti corretti).

```bash
python3 scadenzario.py --demo    # "trasparenza tra 19 giorni 🔴 IMMINENTE, alto rischio rinviato di 16 mesi"
open assessment.html             # (o doppio clic) — il questionario self-service
```

## Il funnel prodotto (dal gratis al ricorrente)

```
1. ASSESSMENT GRATUITO (classifica.py in versione web, 10 minuti)
   «Scopri in 10 minuti se rischi fino al 7% del fatturato»
                    │  lead qualificato
                    ▼
2. AUDIT COMPLETO (3–15 k€ una tantum)
   Registro sistemi AI + classificazione formale + gap analysis + piano
                    │  il report scade: il registro va MANTENUTO
                    ▼
3. MONITORAGGIO CONTINUO (500–5.000 €/mese)
   Registro aggiornato, nuovi sistemi classificati, alert su modifiche
   normative, documentazione pronta per le ispezioni
```

Il punto geniale: **l'audit una tantum crea l'obbligo del ricorrente** — il registro è un documento vivo per legge (art. 72: monitoraggio post-market), quindi il churn strutturale è bassissimo.

## Cliente target

Mid-market italiano 100–5.000 dipendenti che **usa** AI (HR screening, credit scoring, manutenzione predittiva, chatbot clienti) — non che la produce. Le Big4 li ignorano, i tool americani non parlano italiano né conoscono i decreti attuativi.

## Roadmap 90 giorni

| Fase | Quando | Obiettivo | KPI di sblocco |
|---|---|---|---|
| 1. Credibilità | Settimane 1–3 | Assessment web pubblicato + 2 articoli LinkedIn "cosa cambia ad agosto" | 50 assessment completati |
| 2. Primi audit | Settimane 4–8 | Convertire gli assessment in audit | 3 audit venduti (≥ 9 k€ totali) |
| 3. Ricorrente | Settimane 9–13 | Convertire gli audit in monitoraggio | 2 contratti mensili firmati |

## Partnership che moltiplicano (non vendere da soli)

- **Studi legali** che non hanno competenza tecnica: tu fai la parte tecnica, loro la legale, si divide la fee. Vedi `PARTNERSHIP-LEGALE-TEMPLATE.md` per la bozza di accordo con cui iniziare la conversazione.
- **Associazioni di categoria** (Confindustria territoriali, CNA): un webinar "la scadenza è cambiata, ecco cosa fare davvero" = 30 lead in un'ora.
- **Software house** che devono certificare i propri prodotti per i clienti enterprise.

## ✅ Cosa è completo (con dati mock) vs cosa serve da te

| Livello | Stato | Per andare live serve |
|---|---|---|
| Classificatore, Registro, scadenzario, assessment | ✅ Vero al 100% | Niente |
| Backend lead capture (`lead_capture.py`) | ✅ Codice vero, salvataggio testato | Un hosting pubblico |
| Notifica nuovo lead via email | 🟡 Codice SMTP vero, credenziali mock | Le tue credenziali in `.env` (`CONFIGURAZIONE.md`) |
| Partner legale per validare gli audit | ❌ Non esiste — è l'unico pezzo che il codice non può darti | Negoziarlo con uno studio vero (`PARTNERSHIP-LEGALE-TEMPLATE.md`) |

Vedi `CONFIGURAZIONE.md` per la guida passo-passo.

## 🔍 Audit di sicurezza e legale — cosa è stato trovato e corretto

| Problema trovato | Rischio | Correzione |
|---|---|---|
| **`GET /leads` non richiedeva alcuna autenticazione** | 🔴 Il più serio dei tre progetti: chiunque scoprisse l'URL poteva leggere email e classificazione di rischio AI Act di ogni prospect | Endpoint protetto da chiave API (`LEAD_API_KEY`), confronto a tempo costante; **con la chiave ancora al valore mock, l'accesso è sempre negato** (di proposito: essendo codice pubblico, un default "reale" sarebbe un segreto noto a chiunque legga il sorgente) |
| `POST /lead` validava solo che l'email non fosse vuota, non che fosse un indirizzo valido | Dati sporchi nel database lead, bypassabile aggirando la validazione JavaScript lato client | Validazione server-side con regex, difesa in profondità |
| Nessuna procedura documentata per cancellare un lead su richiesta | Rischio di non poter evadere una richiesta di cancellazione (Art. 17 GDPR) nei tempi di legge | Procedura documentata in `CONFIGURAZIONE.md` |
| `assessment.html` dichiarava "nessun dato inviato a un server" in modo assoluto, ma il modulo di contatto invia davvero l'email al backend | Incoerenza tra due punti della stessa pagina | Testo allineato: il calcolo resta nel browser, l'invio avviene solo se l'utente lo richiede esplicitamente |
| `POST /lead` accettava richieste illimitate | Chiunque poteva inondarlo di lead falsi, riempiendo il database e — con SMTP reale — spammando la casella email del titolare | Rate limit: 5 richieste/ora per IP |

Tutte le correzioni sono testate (richieste HTTP reali con chiave assente, chiave mock, chiave reale corretta e chiave reale sbagliata).

## Prima azione da fare OGGI

Esegui `python3 classifica.py --demo`, poi fai il questionario su 3 aziende che conosci. Se almeno una risulta "alto rischio" (probabile: basta un software HR), hai il tuo primo prospect e la tua prima case study.
