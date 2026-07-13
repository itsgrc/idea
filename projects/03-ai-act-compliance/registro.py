#!/usr/bin/env python3
"""Conforme — Registro dei Sistemi AI aziendale (il deliverable dell'audit).

Evoluzione di classifica.py: da un sistema alla volta al registro completo
dell'azienda. Gestisce il censimento in un JSON, classifica ogni sistema con
le stesse regole del questionario, e genera i due deliverable dell'audit:

  1. REGISTRO-<azienda>.md   — il Registro dei Sistemi AI pronto per ispezione
  2. gap analysis            — cosa manca, ordinato per urgenza

Uso:
    python3 registro.py --demo         # azienda di esempio con 4 sistemi
    python3 registro.py censimento.json
"""
import json
import sys
import datetime

from classifica import PRATICHE_PROIBITE, ALTO_RISCHIO, RISCHIO_TRASPARENZA, OBBLIGHI

DEMO = {
    "azienda": "Esempio SpA",
    "dipendenti": 800,
    "responsabile_registro": "Direzione IT / DPO",
    "sistemi": [
        {
            "nome": "TalentMatch — screening CV",
            "fornitore": "SaaS di terze parti",
            "ruolo": "deployer",
            "funzione": "Selezione del personale: ranking automatico dei candidati",
            "dati": "Dati personali dei candidati",
            "risposte": {"lavoro": True},
            "presidi": {"doc_tecnica_fornitore": False, "sorveglianza_umana": True, "log_attivi": False, "personale_formato": False}
        },
        {
            "nome": "Chatbot assistenza clienti",
            "fornitore": "Sviluppo interno",
            "ruolo": "provider",
            "funzione": "Risposte automatiche ai clienti sul sito",
            "dati": "Conversazioni, dati di contatto",
            "risposte": {"interagisce": True},
            "presidi": {"disclosure_ai": True, "log_attivi": True}
        },
        {
            "nome": "Manutenzione predittiva linea 2",
            "fornitore": "Modulo del gestionale MES",
            "ruolo": "deployer",
            "funzione": "Previsione guasti dei macchinari",
            "dati": "Dati macchina, nessun dato personale",
            "risposte": {},
            "presidi": {}
        },
        {
            "nome": "Generatore immagini marketing",
            "fornitore": "SaaS di terze parti",
            "ruolo": "deployer",
            "funzione": "Creazione di immagini per campagne",
            "dati": "Prompt di marketing",
            "risposte": {"contenuti_sintetici": True},
            "presidi": {"marcatura_contenuti": False}
        }
    ]
}

ICONE = {"PROIBITO": "🟥", "ALTO RISCHIO": "🟧", "RISCHIO TRASPARENZA": "🟨", "RISCHIO MINIMO": "🟩"}
ORDINE = {"PROIBITO": 0, "ALTO RISCHIO": 1, "RISCHIO TRASPARENZA": 2, "RISCHIO MINIMO": 3}


def classifica_sistema(risposte):
    """Stessa logica del questionario, in forma non interattiva."""
    for chiave, _testo, nota in PRATICHE_PROIBITE:
        if risposte.get(chiave):
            return "PROIBITO", nota
    for chiave, _testo, nota in ALTO_RISCHIO:
        if risposte.get(chiave):
            return "ALTO RISCHIO", nota
    for chiave, _testo, nota in RISCHIO_TRASPARENZA:
        if risposte.get(chiave):
            return "RISCHIO TRASPARENZA", nota
    return "RISCHIO MINIMO", None


PRESIDI_RICHIESTI = {
    "ALTO RISCHIO": [
        ("doc_tecnica_fornitore", "Documentazione tecnica del fornitore acquisita (Art. 11)", "🔴 urgente"),
        ("sorveglianza_umana", "Sorveglianza umana definita: chi può bloccare l'output (Art. 14)", "🔴 urgente"),
        ("log_attivi", "Log delle decisioni attivi e conservati (Art. 12)", "🔴 urgente"),
        ("personale_formato", "Personale utilizzatore formato — AI literacy (Art. 4)", "🟠 alta"),
    ],
    "RISCHIO TRASPARENZA": [
        ("disclosure_ai", "Informativa 'stai parlando con un'AI' attiva (Art. 50.1)", "🟠 alta"),
        ("marcatura_contenuti", "Contenuti generati marcati come sintetici (Art. 50.2)", "🟠 alta"),
    ],
}


def gap_analysis(sistema, livello):
    gaps = []
    for chiave, descrizione, urgenza in PRESIDI_RICHIESTI.get(livello, []):
        if chiave in sistema.get("presidi", {}) or livello == "ALTO RISCHIO" or (livello == "RISCHIO TRASPARENZA" and chiave in ("disclosure_ai", "marcatura_contenuti")):
            if not sistema.get("presidi", {}).get(chiave, False):
                # Il presidio è pertinente solo se il sistema lo richiede davvero:
                # per la trasparenza, solo quello corrispondente alla risposta data.
                if livello == "RISCHIO TRASPARENZA":
                    if chiave == "disclosure_ai" and not sistema["risposte"].get("interagisce"):
                        continue
                    if chiave == "marcatura_contenuti" and not (sistema["risposte"].get("contenuti_sintetici") or sistema["risposte"].get("deepfake")):
                        continue
                gaps.append((urgenza, descrizione))
    return gaps


def genera(censimento):
    oggi = datetime.date.today().isoformat()
    prossima = (datetime.date.today() + datetime.timedelta(days=90)).isoformat()

    valutati = []
    for s in censimento["sistemi"]:
        livello, riferimento = classifica_sistema(s.get("risposte", {}))
        valutati.append((s, livello, riferimento, gap_analysis(s, livello)))
    valutati.sort(key=lambda v: ORDINE[v[1]])

    tot_gap = sum(len(g) for *_, g in valutati)
    n_alto = sum(1 for _, l, *_ in valutati if l == "ALTO RISCHIO")

    r = [
        f"# 📒 Registro dei Sistemi AI — {censimento['azienda']}",
        "",
        f"- **Responsabile del registro:** {censimento['responsabile_registro']}",
        f"- **Data revisione:** {oggi} · **Prossima revisione:** {prossima}",
        f"- **Sistemi censiti:** {len(valutati)} · di cui **alto rischio: {n_alto}** · azioni aperte: **{tot_gap}**",
        "",
        "## Registro",
        "",
        "| ID | Sistema | Fornitore | Ruolo | Classificazione | Riferimento | Azioni aperte |",
        "|----|---------|-----------|-------|-----------------|-------------|---------------|",
    ]
    for i, (s, livello, riferimento, gaps) in enumerate(valutati, 1):
        rif = riferimento or "—"
        r.append(f"| AI-{i:03d} | {s['nome']} | {s['fornitore']} | {s['ruolo']} | {ICONE[livello]} {livello} | {rif} | {len(gaps)} |")

    r += ["", "## Piano di adeguamento (gap analysis)", ""]
    if tot_gap == 0:
        r.append("Nessuna azione aperta sui presidi verificati. ✅")
    for i, (s, livello, _rif, gaps) in enumerate(valutati, 1):
        if not gaps:
            continue
        r.append(f"### AI-{i:03d} · {s['nome']} — {ICONE[livello]} {livello}")
        for urgenza, descrizione in sorted(gaps):
            r.append(f"- [ ] {urgenza} — {descrizione}")
        r.append("")

    r += [
        "## Obblighi di riferimento per livello",
        "",
    ]
    for livello in ["ALTO RISCHIO", "RISCHIO TRASPARENZA"]:
        if any(l == livello for _, l, *_ in valutati):
            r.append(f"**{ICONE[livello]} {livello}**")
            r += [f"- {o}" for o in OBBLIGHI[livello]]
            r.append("")

    r += [
        "---",
        "*Registro generato dallo strumento di audit e da validare con i professionisti abilitati partner. ",
        "Non costituisce consulenza legale. La classificazione va rivista a ogni modifica sostanziale dei sistemi.*",
    ]
    return "\n".join(r)


def main():
    if "--demo" in sys.argv:
        censimento = DEMO
    elif len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            censimento = json.load(f)
    else:
        sys.exit("Uso: python3 registro.py --demo | censimento.json")

    testo = genera(censimento)
    print(testo)
    nome = f"REGISTRO-{censimento['azienda'].split()[0].lower()}-{datetime.date.today().isoformat()}.md"
    with open(nome, "w") as f:
        f.write(testo + "\n")
    print(f"\n💾 Salvato: {nome}", file=sys.stderr)


if __name__ == "__main__":
    main()
