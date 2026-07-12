# 🩺 Progetto 09 — Vertical AI Agent: Legale/Sanità

> **Missione:** l'unico progetto "da unicorno" del portfolio. Si entra solo dalla porta giusta: una micro-nicchia dove vincere è possibile, poi si allarga. Fase attuale: VALIDAZIONE — vietato scrivere codice.

## Il beachhead scelto: perizie medico-legali assicurative

Perché questa micro-nicchia e non "AI per avvocati" (dove Harvey ha già vinto) o "AI per ospedali" (cicli di vendita triennali):

- **Volume enorme e ripetitivo:** centinaia di migliaia di sinistri/anno in Italia con danno alla persona richiedono una valutazione medico-legale. Ogni pratica: leggere cartelle cliniche (50–500 pagine), estrarre lesioni, applicare le tabelle (Milano/Roma), scrivere la perizia.
- **Il dolore è di chi paga:** compagnie assicurative e studi peritali pagano medici legali 300–800 € a perizia e aspettano settimane. Un agente che pre-processa la cartella e prepara la bozza taglia il 60–70% del tempo.
- **Difendibile:** serve dominio (tabelle, giurisprudenza, prassi liquidative italiane) che nessun player US ha. I dati di ogni pratica processata migliorano il sistema: moat cumulativo.
- **Porta d'ingresso regolatoria gestibile:** supporto alla decisione di un professionista (il medico legale firma sempre) → posizionamento AI Act più leggero del diagnostico puro. Il progetto #03 fa la classificazione formale — sinergia.

## Cosa c'è in questa cartella

| File | Cosa fa |
|---|---|
| `VALIDAZIONE.md` | Il piano di validazione completo: 15 interviste (script incluso), criteri go/no-go, design del pilot a pagamento |

## Le regole di questa fase (per non bruciare capitale)

1. **Niente codice fino a 15 interviste fatte.** Il rischio n.1 non è tecnico, è di mercato: capire chi decide l'acquisto tra compagnia, studio peritale e singolo medico legale.
2. **Il pilot si vende, non si regala** (5–15 k€): un pilot gratuito in questo settore significa "non urgente" e muore nel cassetto.
3. **Cercare il co-founder di dominio:** un medico legale o un ex-liquidatore senior. Questo progetto senza insider non si fa — è un criterio go/no-go, non un nice-to-have.

## Percorso a tappe (solo dopo la validazione)

```
Beachhead: perizie RC auto (volume massimo, standardizzazione massima)
    → perizie infortunistica sul lavoro
    → responsabilità medica (valore per pratica 10x)
    → altre giurisdizioni EU (le tabelle cambiano, il motore no)
```

## KPI di fase

| Fase | KPI go/no-go |
|---|---|
| 1. Interviste (mese 1–2) | 15 interviste; ≥ 8 confermano dolore + budget |
| 2. Pilot design (mese 3) | 1 compagnia o studio peritale firma un pilot PAGATO |
| 3. Seed (mese 6+) | Pilot con metriche → raccolta 0,5–2 M€ (Smart&Start / CDP / business angel di settore) |

## Prima azione da fare OGGI

Trova su LinkedIn 5 medici legali e 5 responsabili sinistri di compagnie. Messaggio: «Sto studiando come l'AI può ridurre i tempi delle perizie medico-legali. 20 minuti del suo tempo in cambio dei risultati completi della ricerca?». Le prime 3 risposte definiranno il progetto più di qualunque business plan.
