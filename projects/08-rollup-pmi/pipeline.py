#!/usr/bin/env python3
"""Continuità — pipeline di acquisizione (CRM minimale, zero dipendenze).

Il roll-up si vince con la pipeline: tanti target visti, pochi scelti bene.
Questo strumento tiene il registro dei target (JSON), calcola lo score di
attrattività con gli stessi criteri della due diligence, e genera il report
di pipeline con le prossime azioni.

Stadi:  contatto → nda → dati_ricevuti → valutazione → loi → due_diligence → closing → (persa)

Uso:
    python3 pipeline.py --demo             # pipeline di esempio
    python3 pipeline.py pipeline.json      # la tua pipeline reale
"""
import json
import sys
import datetime

STADI = ["contatto", "nda", "dati_ricevuti", "valutazione", "loi", "due_diligence", "closing", "persa"]

DEMO = [
    {
        "azienda": "Studio Amministrazioni Alfa",
        "settore": "amministrazione condomini",
        "fonte": "commercialista Bianchi",
        "stadio": "valutazione",
        "fatturato": 320000, "ebitda_rettificato": 55000,
        "eta_titolare": 64, "orizzonte_uscita_anni": 2,
        "concentrazione_top_cliente_pct": 8,
        "anni_medi_clienti": 11,
        "ore_automatizzabili_pct": 45,
        "secondo_in_azienda": True,
        "prossima_azione": "chiamata coi 2 clienti storici (pretesto: indagine soddisfazione)",
        "scadenza_azione": "2026-07-20"
    },
    {
        "azienda": "Agenzia Pratiche Beta",
        "settore": "pratiche auto",
        "fonte": "annuncio + visita diretta",
        "stadio": "nda",
        "fatturato": 210000, "ebitda_rettificato": 38000,
        "eta_titolare": 61, "orizzonte_uscita_anni": 1,
        "concentrazione_top_cliente_pct": 30,
        "anni_medi_clienti": 6,
        "ore_automatizzabili_pct": 60,
        "secondo_in_azienda": False,
        "prossima_azione": "ricevere bilanci 3 anni dopo firma NDA",
        "scadenza_azione": "2026-07-18"
    },
    {
        "azienda": "Paghe & Persone Gamma",
        "settore": "elaborazione paghe",
        "fonte": "commercialista Bianchi",
        "stadio": "contatto",
        "fatturato": 480000, "ebitda_rettificato": 95000,
        "eta_titolare": 58, "orizzonte_uscita_anni": 4,
        "concentrazione_top_cliente_pct": 12,
        "anni_medi_clienti": 9,
        "ore_automatizzabili_pct": 55,
        "secondo_in_azienda": True,
        "prossima_azione": "primo caffè esplorativo",
        "scadenza_azione": "2026-07-25"
    },
    {
        "azienda": "Servizi Delta",
        "settore": "disbrigo pratiche",
        "fonte": "annuncio",
        "stadio": "persa",
        "fatturato": 150000, "ebitda_rettificato": 12000,
        "eta_titolare": 67, "orizzonte_uscita_anni": 0,
        "concentrazione_top_cliente_pct": 55,
        "anni_medi_clienti": 3,
        "ore_automatizzabili_pct": 30,
        "secondo_in_azienda": False,
        "prossima_azione": "—",
        "scadenza_azione": "",
        "nota": "persa di proposito: top client 55% = red flag da checklist"
    },
]


def score(t):
    """Score 0–100 con i criteri della due diligence. Ritorna (punti, note)."""
    punti, note = 0, []

    margine = t["ebitda_rettificato"] / t["fatturato"]
    if margine >= 0.15:
        punti += 20; note.append(f"margine {margine:.0%} ✓")
    elif margine >= 0.08:
        punti += 10; note.append(f"margine {margine:.0%} ~")
    else:
        note.append(f"margine {margine:.0%} ✗")

    c = t["concentrazione_top_cliente_pct"]
    if c <= 20:
        punti += 20; note.append(f"top client {c}% ✓")
    elif c <= 35:
        punti += 8; note.append(f"top client {c}% ⚠")
    else:
        note.append(f"top client {c}% 🚩 RED FLAG")

    if t["anni_medi_clienti"] >= 8:
        punti += 15; note.append(f"clienti da {t['anni_medi_clienti']} anni ✓")
    elif t["anni_medi_clienti"] >= 4:
        punti += 8

    a = t["ore_automatizzabili_pct"]
    if a >= 50:
        punti += 20; note.append(f"AI-fication {a}% ✓✓")
    elif a >= 30:
        punti += 12; note.append(f"AI-fication {a}% ✓")
    else:
        note.append(f"AI-fication {a}% ✗ (sotto soglia 30%)")

    if t["secondo_in_azienda"]:
        punti += 15; note.append("c'è un secondo ✓")
    else:
        note.append("tutto sul titolare ⚠")

    if 1 <= t["orizzonte_uscita_anni"] <= 3:
        punti += 10; note.append("uscita 1–3 anni ✓")

    return punti, note


def report(targets):
    oggi = datetime.date.today()
    attivi = [t for t in targets if t["stadio"] != "persa"]
    righe = [
        "# 🏢 Pipeline acquisizioni — Continuità",
        f"\n*{oggi.strftime('%d/%m/%Y')} · target attivi: {len(attivi)} / totali visti: {len(targets)}*\n",
        "| Azienda | Settore | Stadio | Score | EBITDA rett. | Prossima azione | Entro |",
        "|---|---|---|---|---|---|---|",
    ]
    valutati = sorted(targets, key=lambda t: (t["stadio"] == "persa", -score(t)[0]))
    for t in valutati:
        s, _ = score(t)
        badge = "🟢" if s >= 70 else ("🟡" if s >= 50 else "🔴")
        stadio = f"{STADI.index(t['stadio'])+1}/7 {t['stadio']}" if t["stadio"] != "persa" else "❌ persa"
        ritardo = ""
        if t.get("scadenza_azione"):
            giorni = (datetime.date.fromisoformat(t["scadenza_azione"]) - oggi).days
            ritardo = f"{t['scadenza_azione']}" + (" ⚠️ SCADUTA" if giorni < 0 else f" ({giorni} gg)")
        righe.append(f"| {t['azienda']} | {t['settore']} | {stadio} | {badge} {s} | {t['ebitda_rettificato']:,} € | {t['prossima_azione']} | {ritardo} |")

    righe.append("\n## Dettaglio score\n")
    for t in valutati:
        if t["stadio"] == "persa":
            righe.append(f"**{t['azienda']}** — ❌ persa" + (f" · {t.get('nota','')}" if t.get("nota") else ""))
            continue
        s, note = score(t)
        righe.append(f"**{t['azienda']}** — {s}/100 · " + " · ".join(note))

    righe += [
        "\n## Regole della pipeline",
        "- Score < 50: non investire altro tempo, dirlo con gentilezza e chiedere un referral.",
        "- Nessuna offerta senza EBITDA **rettificato** verificato (mai quello dichiarato).",
        "- Ogni target attivo DEVE avere una prossima azione con scadenza. Pipeline senza azioni = pipeline morta.",
        "- Obiettivo di fase: 10 visti → 3 valutati → 1 LOI (vedi LOI-TEMPLATE.md).",
    ]
    return "\n".join(righe)


def main():
    if "--demo" in sys.argv:
        targets = DEMO
    elif len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            targets = json.load(f)
    else:
        sys.exit("Uso: python3 pipeline.py --demo | pipeline.json")
    print(report(targets))


if __name__ == "__main__":
    main()
