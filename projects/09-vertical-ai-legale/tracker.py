#!/usr/bin/env python3
"""Perizia — tracker della validazione (interviste → evidenze → go/no-go).

La fase attuale vieta di scrivere codice prodotto: questo è codice di
DISCIPLINA. Registra le interviste, aggancia ogni risposta alle 3 ipotesi
di VALIDAZIONE.md e calcola in automatico dove siamo rispetto ai criteri
go/no-go. Alla quindicesima intervista, la decisione è già scritta.

Ipotesi (da VALIDAZIONE.md):
  H1  il collo di bottiglia è il tempo sulla cartella clinica
  H2  chi paga è compagnia/studio peritale, e ha budget
  H3  la bozza AI è professionalmente accettabile (con revisione)

Uso:
    python3 tracker.py --demo             # scoreboard con dati di esempio
    python3 tracker.py interviste.json    # la tua validazione reale
"""
import json
import sys

SOGLIE = {"interviste_min": 15, "h1_conferme_min": 8, "h2_conferme_min": 8, "h3_conferme_min": 8}

DEMO = [
    {"chi": "medico legale, fiduciario compagnia", "data": "2026-07-02",
     "h1": "si", "h2": "si", "h3": "condizionato",
     "citazione": "Il 60% del mio tempo è leggere carte, non fare il medico.",
     "insight": "Firmerebbe bozze SOLO con fonti citate pagina per pagina."},
    {"chi": "responsabile sinistri, compagnia media", "data": "2026-07-04",
     "h1": "si", "h2": "si", "h3": "non_chiesto",
     "citazione": "Ogni giorno di attesa perizia su un RC è costo vivo.",
     "insight": "Budget: già pagano fee per accelerare le pratiche urgenti."},
    {"chi": "titolare studio peritale (8 medici)", "data": "2026-07-08",
     "h1": "si", "h2": "condizionato", "h3": "si",
     "citazione": "Se mi raddoppi le pratiche evase a parità di medici, parliamo di cifre serie.",
     "insight": "Comprerebbe lo studio, non il singolo medico: pricing per pratica."},
    {"chi": "medico legale libero professionista", "data": "2026-07-10",
     "h1": "no", "h2": "no", "h3": "no",
     "citazione": "Il problema mio non è il tempo, è che le compagnie pagano poco.",
     "insight": "ATTENZIONE: il libero professionista NON è il compratore."},
    {"chi": "avvocato di parte danneggiata", "data": "2026-07-11",
     "h1": "si", "h2": "non_chiesto", "h3": "non_chiesto",
     "citazione": "Le perizie arrivano tardi e spesso con date sbagliate: le contestiamo apposta.",
     "insight": "L'accuratezza delle date/fonti è anche un argomento DIFENSIVO per le compagnie."},
]

VOTI = {"si": 1, "condizionato": 0.5, "no": 0, "non_chiesto": None}


def valuta(interviste):
    n = len(interviste)
    print(f"\n🔬 PERIZIA — Scoreboard validazione   ({n}/{SOGLIE['interviste_min']} interviste)")
    print("═" * 66)

    esito = {}
    for h, etichetta in [("h1", "H1 · collo di bottiglia = lettura cartelle"),
                         ("h2", "H2 · compagnie/studi pagano"),
                         ("h3", "H3 · bozza accettabile con revisione")]:
        voti = [VOTI[i[h]] for i in interviste if VOTI[i[h]] is not None]
        conferme = sum(voti)
        chieste = len(voti)
        soglia = SOGLIE[f"{h}_conferme_min"]
        # proiezione: al ritmo attuale, a 15 interviste dove arriviamo?
        proiezione = conferme / max(chieste, 1) * SOGLIE["interviste_min"]
        stato = "🟢 in rotta" if proiezione >= soglia else ("🟡 incerta" if proiezione >= soglia * 0.7 else "🔴 a rischio")
        esito[h] = proiezione >= soglia
        barra = "█" * int(conferme) + "░" * max(0, soglia - int(conferme))
        print(f"{etichetta}")
        print(f"   {barra}  {conferme:.1f} conferme su {chieste} chieste · proiezione a 15: {proiezione:.1f}/{soglia} · {stato}\n")

    print("─" * 66)
    print("📌 Citazioni da usare nel pitch (oro colato):")
    for i in interviste:
        if VOTI.get(i["h1"]) == 1 or VOTI.get(i["h2"]) == 1:
            print(f'   «{i["citazione"]}» — {i["chi"]}')

    print("\n⚠️  Insight che cambiano il progetto:")
    for i in interviste:
        if "ATTENZIONE" in i["insight"] or "SOLO" in i["insight"]:
            print(f"   • {i['insight']} ({i['chi']})")

    print("\n" + "═" * 66)
    if n < SOGLIE["interviste_min"]:
        mancanti = SOGLIE["interviste_min"] - n
        print(f"VERDETTO: ancora {mancanti} interviste prima della decisione.")
        print(f"          Proiezione attuale: {'GO' if all(esito.values()) else 'NO-GO'} — ma si decide coi dati, non con le proiezioni.")
    else:
        go = all(esito.values())
        print(f"VERDETTO: {'🟢 GO — procedere col pilot a pagamento' if go else '🔴 NO-GO — archiviare e travasare i learnings su #02/#03'}")
    print("═" * 66)
    print("Regola: ogni intervista si registra ENTRO 24h, o i dettagli evaporano.\n")


def main():
    if "--demo" in sys.argv:
        interviste = DEMO
    elif len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            interviste = json.load(f)
    else:
        sys.exit("Uso: python3 tracker.py --demo | interviste.json")
    valuta(interviste)


if __name__ == "__main__":
    main()
