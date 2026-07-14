#!/usr/bin/env python3
"""Classificatore di rischio EU AI Act — il prodotto, versione 0.

Questionario guidato che classifica un sistema AI nei livelli di rischio del
Regolamento (UE) 2024/1689 e genera un report markdown con gli obblighi.

NOTA LEGALE: strumento di pre-assessment divulgativo, non consulenza legale.
La classificazione formale richiede analisi caso per caso (ed è esattamente
ciò che si vende nell'audit completo).

Uso:
    python3 classifica.py           # questionario interattivo
    python3 classifica.py --demo    # esempio precompilato (software HR screening)
"""
import sys
import datetime

# ---------------------------------------------------------------- domande
# Ogni domanda: (chiave, testo, note). Risposte attese: s/n.
PRATICHE_PROIBITE = [
    ("manipolazione", "Il sistema usa tecniche subliminali o manipolative per distorcere il comportamento delle persone causando danni?", "Art. 5.1.a"),
    ("vulnerabilita", "Sfrutta vulnerabilità di età, disabilità o condizione sociale?", "Art. 5.1.b"),
    ("social_scoring", "Fa social scoring generalizzato delle persone per conto di autorità o aziende?", "Art. 5.1.c"),
    ("biometria_realtime", "Fa identificazione biometrica remota in tempo reale in spazi pubblici (fuori dalle eccezioni di legge)?", "Art. 5.1.h"),
    ("emozioni_lavoro_scuola", "Riconosce le emozioni sul luogo di lavoro o a scuola?", "Art. 5.1.f"),
]

ALTO_RISCHIO = [
    ("biometria", "Identificazione/categorizzazione biometrica delle persone?", "Allegato III.1"),
    ("infrastrutture", "Componente di sicurezza in infrastrutture critiche (acqua, energia, trasporti)?", "Allegato III.2"),
    ("istruzione", "Determina accesso, valutazione o sorveglianza in ambito educativo?", "Allegato III.3"),
    ("lavoro", "Usato per selezione del personale, valutazione candidati, promozioni, licenziamenti o assegnazione compiti?", "Allegato III.4 — il caso più comune nelle PMI"),
    ("servizi_essenziali", "Decide accesso a servizi essenziali: credit scoring, assicurazioni vita/salute, prestazioni pubbliche, emergenze?", "Allegato III.5"),
    ("law_enforcement", "Usato da forze dell'ordine (valutazione rischio reati, poligrafi, analisi prove)?", "Allegato III.6"),
    ("migrazione", "Usato per controllo migrazione, asilo o frontiere?", "Allegato III.7"),
    ("giustizia", "Assiste autorità giudiziarie o influenza elezioni?", "Allegato III.8"),
]

RISCHIO_TRASPARENZA = [
    ("interagisce", "Interagisce direttamente con persone (chatbot, assistente vocale)?", "Art. 50.1"),
    ("contenuti_sintetici", "Genera contenuti sintetici (testo, immagini, audio, video)?", "Art. 50.2"),
    ("deepfake", "Genera o manipola immagini/audio/video di persone reali (deepfake)?", "Art. 50.4"),
]

OBBLIGHI = {
    "PROIBITO": [
        "❌ Il sistema rientra nelle pratiche VIETATE dall'Art. 5: va dismesso o modificato radicalmente.",
        "Sanzione prevista: fino a 35 M€ o 7% del fatturato mondiale annuo.",
        "Applicabile già da febbraio 2025.",
    ],
    "ALTO RISCHIO": [
        "Sistema di gestione del rischio documentato (Art. 9)",
        "Governance dei dati: qualità e rappresentatività dei dataset (Art. 10)",
        "Documentazione tecnica completa prima dell'immissione (Art. 11 + Allegato IV)",
        "Registrazione automatica degli eventi / log (Art. 12)",
        "Trasparenza e istruzioni per gli utilizzatori (Art. 13)",
        "Sorveglianza umana effettiva (Art. 14)",
        "Accuratezza, robustezza, cybersicurezza (Art. 15)",
        "Se sei DEPLOYER: valutazione d'impatto sui diritti fondamentali ove richiesta (Art. 27)",
        "Monitoraggio post-market e segnalazione incidenti (Artt. 72-73)",
        "⏰ Enforcement per i sistemi Allegato III (standalone): RINVIATO al 2 dicembre 2027 dal pacchetto",
        "   'Digital Omnibus' (approvato dal Consiglio UE il 29/06/2026). Per i sistemi ad alto rischio",
        "   integrati in prodotti (Allegato I) il rinvio è al 2 agosto 2028. Sanzioni quando in vigore:",
        "   fino a 15 M€ o 3% del fatturato. Il rinvio NON è un motivo per aspettare: vedi scadenzario.py.",
    ],
    "RISCHIO TRASPARENZA": [
        "Informare chiaramente le persone che stanno interagendo con un'AI (Art. 50.1)",
        "Marcare i contenuti generati come sintetici, in formato machine-readable (Art. 50.2)",
        "Etichettare esplicitamente i deepfake (Art. 50.4)",
        "⏰ In vigore dal 2 agosto 2026 — NON rinviato dal Digital Omnibus, a differenza dell'alto rischio.",
    ],
    "RISCHIO MINIMO": [
        "Nessun obbligo specifico oltre alle norme generali (GDPR, sicurezza prodotti).",
        "Consigliato comunque: censire il sistema nel Registro AI aziendale — la classificazione va rifatta a ogni modifica sostanziale.",
    ],
}

DEMO_RISPOSTE = {
    "nome_sistema": "TalentMatch (screening CV fornitore esterno)",
    "azienda": "Esempio SpA (800 dipendenti)",
    "risposte": {"lavoro": True, "interagisce": True},
}


def chiedi_sn(testo, nota, precompilate=None, chiave=None):
    if precompilate is not None:
        risposta = precompilate.get(chiave, False)
        print(f"  {testo}  [{nota}]  → {'SÌ' if risposta else 'no'}")
        return risposta
    while True:
        r = input(f"  {testo}  [{nota}]  (s/n): ").strip().lower()
        if r in ("s", "si", "sì", "y"):
            return True
        if r in ("n", "no"):
            return False
        print("  Rispondi s o n.")


def classifica(precompilate=None):
    if precompilate:
        nome = precompilate["nome_sistema"]
        azienda = precompilate["azienda"]
        risposte = precompilate["risposte"]
    else:
        azienda = input("Nome azienda: ").strip() or "Azienda"
        nome = input("Nome del sistema AI da valutare: ").strip() or "Sistema AI"
        risposte = None

    print(f"\n═══ Valutazione: {nome} ═══\n")
    print("— Sezione 1: pratiche proibite (Art. 5)")
    for chiave, testo, nota in PRATICHE_PROIBITE:
        if chiedi_sn(testo, nota, risposte, chiave):
            return nome, azienda, "PROIBITO", nota

    print("\n— Sezione 2: alto rischio (Allegato III)")
    for chiave, testo, nota in ALTO_RISCHIO:
        if chiedi_sn(testo, nota, risposte, chiave):
            return nome, azienda, "ALTO RISCHIO", nota

    print("\n— Sezione 3: obblighi di trasparenza (Art. 50)")
    for chiave, testo, nota in RISCHIO_TRASPARENZA:
        if chiedi_sn(testo, nota, risposte, chiave):
            return nome, azienda, "RISCHIO TRASPARENZA", nota

    return nome, azienda, "RISCHIO MINIMO", None


def report(nome, azienda, livello, riferimento):
    oggi = datetime.date.today().isoformat()
    icone = {"PROIBITO": "🟥", "ALTO RISCHIO": "🟧", "RISCHIO TRASPARENZA": "🟨", "RISCHIO MINIMO": "🟩"}
    righe = [
        f"# Report di pre-assessment EU AI Act",
        f"",
        f"- **Azienda:** {azienda}",
        f"- **Sistema valutato:** {nome}",
        f"- **Data:** {oggi}",
        f"- **Classificazione:** {icone[livello]} **{livello}**"
        + (f" (criterio determinante: {riferimento})" if riferimento else ""),
        f"",
        f"## Obblighi applicabili",
        f"",
    ]
    righe += [f"- {o}" for o in OBBLIGHI[livello]]
    righe += [
        "",
        "## Prossimo passo consigliato",
        "",
        "Questo è un pre-assessment automatico. Per la classificazione formale,",
        "il registro completo dei sistemi AI e il piano di adeguamento: audit",
        "completo (2 settimane, deliverable pronti per ispezione).",
        "",
        "*Documento generato con lo strumento di pre-assessment — non costituisce consulenza legale.*",
    ]
    return "\n".join(righe)


def main():
    demo = "--demo" in sys.argv
    nome, azienda, livello, rif = classifica(DEMO_RISPOSTE if demo else None)
    testo = report(nome, azienda, livello, rif)
    print("\n" + testo)
    nome_file = f"report-{nome.split()[0].lower().strip('()')}-{datetime.date.today().isoformat()}.md"
    with open(nome_file, "w") as f:
        f.write(testo + "\n")
    print(f"\n💾 Report salvato: {nome_file}")


if __name__ == "__main__":
    main()
