#!/usr/bin/env python3
"""Scadenzario — il calendario normativo REALE incrociato col Registro del cliente.

Il 29 giugno 2026 il Consiglio UE ha approvato il pacchetto "Digital Omnibus":
gli obblighi per i sistemi ad alto rischio sono stati RINVIATI (Allegato III
standalone: da agosto 2026 a dicembre 2027; Allegato I integrati in prodotti:
ad agosto 2028). Molti consulenti e articoli online, scritti prima di giugno
2026, ripetono ancora la scadenza vecchia. Sapere la data giusta — e sapere
COSA è invece rimasto invariato (trasparenza, art. 50, agosto 2026: fra poche
settimane) — è un vantaggio informativo reale, non un trucco di marketing:
richiede monitorare gli sviluppi normativi in tempo quasi reale.

Uso:
    python3 scadenzario.py --demo              scadenzario sul Registro di esempio
    python3 scadenzario.py censimento.json     scadenzario su un Registro reale
"""
import json
import sys
import datetime

from classifica import PRATICHE_PROIBITE, ALTO_RISCHIO, RISCHIO_TRASPARENZA
from registro import DEMO, classifica_sistema

# Fonte: pacchetto "Digital Omnibus", approvato dal Parlamento UE il 16/06/2026
# (423 favorevoli) e dal Consiglio UE il 29/06/2026. Verificato il 14/07/2026.
CALENDARIO = [
    {
        "data": "2025-02-02",
        "titolo": "Pratiche vietate (Art. 5)",
        "riguarda": "PROIBITO",
        "nota": "già in vigore da oltre un anno — sanzioni fino al 7% del fatturato mondiale.",
    },
    {
        "data": "2025-08-02",
        "titolo": "Obblighi modelli AI general-purpose (GPAI)",
        "riguarda": None,
        "nota": "già in vigore — riguarda chi fornisce o integra in produzione modelli come GPT, Claude, Gemini.",
    },
    {
        "data": "2026-08-02",
        "titolo": "Obblighi di trasparenza (Art. 50)",
        "riguarda": "RISCHIO TRASPARENZA",
        "nota": "NON rinviato dal Digital Omnibus — resta in vigore alla data originale.",
    },
    {
        "data": "2026-12-02",
        "titolo": "Nuovo divieto: contenuti intimi non consensuali generati da AI",
        "riguarda": None,
        "nota": "introdotto dal Digital Omnibus stesso, in vigore da questa data.",
    },
    {
        "data": "2027-12-02",
        "titolo": "Obblighi alto rischio — sistemi standalone (Allegato III)",
        "riguarda": "ALTO RISCHIO",
        "nota": "RINVIATO dal 02/08/2026 al 02/12/2027 dal Digital Omnibus (Consiglio UE, 29/06/2026).",
    },
    {
        "data": "2028-08-02",
        "titolo": "Obblighi alto rischio — sistemi integrati in prodotti (Allegato I)",
        "riguarda": "ALTO RISCHIO",
        "nota": "RINVIATO dal 02/08/2027 al 02/08/2028 dal Digital Omnibus.",
    },
]


def prossime_tappe(oggi=None):
    oggi = oggi or datetime.date.today()
    tappe = []
    for voce in CALENDARIO:
        d = datetime.date.fromisoformat(voce["data"])
        giorni = (d - oggi).days
        tappe.append({**voce, "giorni": giorni, "passata": giorni < 0})
    return tappe


def scadenzario_per_registro(censimento, oggi=None):
    oggi = oggi or datetime.date.today()
    livelli_presenti = set()
    for s in censimento["sistemi"]:
        livello, _rif = classifica_sistema(s.get("risposte", {}))
        livelli_presenti.add(livello)

    tappe = prossime_tappe(oggi)
    rilevanti = [t for t in tappe if t["riguarda"] is None or t["riguarda"] in livelli_presenti]
    return rilevanti, livelli_presenti


def stampa(censimento, oggi=None):
    oggi = oggi or datetime.date.today()
    rilevanti, livelli = scadenzario_per_registro(censimento, oggi)

    print(f"\n{'═' * 70}")
    print(f"📅 SCADENZARIO EU AI ACT — {censimento['azienda']}")
    print(f"{'═' * 70}")
    print(f"Aggiornato al Digital Omnibus (Consiglio UE, 29/06/2026) · oggi: {oggi.strftime('%d/%m/%Y')}")
    print(f"Livelli di rischio presenti nel vostro Registro: {', '.join(sorted(livelli)) or 'nessuno classificato'}\n")

    for t in rilevanti:
        stato = "✅ già in vigore" if t["passata"] else f"⏳ tra {t['giorni']} giorni"
        urgente = " 🔴 IMMINENTE" if 0 <= t["giorni"] <= 60 else ""
        print(f"{t['data']}  {stato}{urgente}")
        print(f"   {t['titolo']}")
        print(f"   {t['nota']}\n")

    print("─" * 70)
    print("💡 PERCHÉ IL RINVIO NON È UN MOTIVO PER ASPETTARE")
    print("─" * 70)
    print("Chi aspetta dicembre 2027 per l'alto rischio arriverà con la")
    print("documentazione tecnica, il sistema di gestione del rischio e la")
    print("sorveglianza umana da costruire IN FRETTA, mentre i concorrenti che")
    print("hanno iniziato ora avranno già tutto pronto — e il mid-market che")
    print("legge ancora 'scadenza agosto 2026' sui blog vecchi penserà di")
    print("avere già sforato: è il momento migliore per parlargli con i dati")
    print("giusti, prima che lo sappiano tutti.")
    print(f"{'═' * 70}\n")


def main():
    if "--demo" in sys.argv:
        censimento = DEMO
    elif len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            censimento = json.load(f)
    else:
        sys.exit("Uso: python3 scadenzario.py --demo | censimento.json")
    stampa(censimento)


if __name__ == "__main__":
    main()
