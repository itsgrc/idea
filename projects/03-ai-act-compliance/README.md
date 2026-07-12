# ⚖️ Progetto 03 — Compliance-as-a-Service per l'EU AI Act

> **Missione:** trasformare il panico normativo di agosto 2026 in un business ricorrente. La legge è il nostro reparto marketing.

## Il momento

L'enforcement dell'EU AI Act per i sistemi ad **alto rischio** scatta ad **agosto 2026**. Multe fino al 7% del fatturato globale. La maggior parte delle aziende italiane mid-market non sa nemmeno *quali* dei suoi sistemi ricadono nel regolamento. Il primo prodotto è esattamente questo: **dirglielo**.

## Cosa c'è in questa cartella

| File | Cosa fa |
|---|---|
| `classifica.py` | **Il prodotto, versione 0**: questionario CLI che classifica un sistema AI nei livelli di rischio dell'AI Act (proibito / alto rischio / rischio trasparenza / minimo) e genera il report con gli obblighi. `python3 classifica.py --demo` |
| `templates/registro-sistemi-ai.md` | Il "Registro dei Sistemi AI" — primo deliverable che ogni cliente deve avere, pronto da compilare |

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

- **Studi legali** che non hanno competenza tecnica: tu fai la parte tecnica, loro la legale, si divide la fee.
- **Associazioni di categoria** (Confindustria territoriali, CNA): un webinar "AI Act: siete pronti?" = 30 lead in un'ora.
- **Software house** che devono certificare i propri prodotti per i clienti enterprise.

## Prima azione da fare OGGI

Esegui `python3 classifica.py --demo`, poi fai il questionario su 3 aziende che conosci. Se almeno una risulta "alto rischio" (probabile: basta un software HR), hai il tuo primo prospect e la tua prima case study.
