#!/usr/bin/env python3
"""FiloDiretto — simulatore del check-in giornaliero (zero dipendenze).

Simula 30 giorni di chiamate quotidiane a un anziano e mostra la logica di
escalation che È il prodotto: quando riprovare, quando allertare la famiglia,
cosa scrivere nel report settimanale. Serve a progettare (e vendere) il
servizio prima di collegare la telefonia vera.

Uso:
    python3 checkin_simulator.py            # simulazione 30 giorni
    python3 checkin_simulator.py --seed 7   # scenario riproducibile
"""
import random
import sys

# Esiti possibili di una chiamata, con probabilità realistiche stimate
ESITI = [
    ("ok", 0.80, "Risponde, sta bene, conversazione normale"),
    ("no_risposta", 0.10, "Non risponde al telefono"),
    ("segnale_debole", 0.07, "Risponde ma riferisce un problema lieve (stanchezza, non ha mangiato...)"),
    ("segnale_forte", 0.03, "Risponde e riferisce un problema serio (caduta, dolore, confusione)"),
]

REGOLE = """
REGOLE DI ESCALATION (il cuore del prodotto)
────────────────────────────────────────────
1. no_risposta      → riprova dopo 30 min. Seconda mancata risposta → 🚨 ALLERTA famiglia
2. segnale_debole   → nota nel report + domanda di follow-up domani ("ieri mi diceva che...")
3. segnale_forte    → 🚨 ALLERTA famiglia IMMEDIATA con trascrizione
4. 3 segnali deboli in 7 giorni → ⚠️ avviso famiglia ("pattern da tenere d'occhio")
"""


def estrai_esito(rng):
    r = rng.random()
    cumulata = 0
    for nome, prob, descrizione in ESITI:
        cumulata += prob
        if r <= cumulata:
            return nome, descrizione
    return ESITI[0][0], ESITI[0][2]


def simula(giorni=30, seed=None):
    rng = random.Random(seed)
    print(REGOLE)
    print(f"📞 Simulazione: {giorni} giorni di chiamate alle 10:00 alla sig.ra Maria (82 anni)\n")

    allerte, deboli_settimana, eventi = 0, [], []
    for giorno in range(1, giorni + 1):
        esito, descrizione = estrai_esito(rng)
        riga = f"Giorno {giorno:2d} · "

        if esito == "no_risposta":
            secondo, _ = estrai_esito(rng)
            if secondo == "no_risposta":
                riga += "❌ nessuna risposta ×2 → 🚨 ALLERTA FAMIGLIA (SMS+chiamata al figlio)"
                allerte += 1
            else:
                riga += "📵 nessuna risposta, ok al secondo tentativo (+30 min)"
        elif esito == "segnale_forte":
            riga += f"🚨 ALLERTA IMMEDIATA — {descrizione}"
            allerte += 1
        elif esito == "segnale_debole":
            deboli_settimana.append(giorno)
            riga += f"⚠️ segnale debole — {descrizione}"
            recenti = [g for g in deboli_settimana if giorno - g < 7]
            if len(recenti) >= 3:
                riga += "  → ⚠️ pattern: avviso famiglia"
                deboli_settimana = []
        else:
            riga += "✅ tutto bene"

        eventi.append(riga)
        print(riga)

        if giorno % 7 == 0:
            ok = sum("✅" in e for e in eventi[-7:])
            print(f"\n  💌 REPORT SETTIMANALE AI FIGLI — settimana {giorno // 7}")
            print(f"     Mamma ha risposto {ok}/7 giorni senza problemi.")
            print(f"     Umore medio: buono. Prossimo promemoria: ricetta medico giovedì.\n")

    print(f"\n{'═' * 60}")
    print(f"📊 In {giorni} giorni: {allerte} allerte reali alla famiglia.")
    print("Il valore del prodotto: tutti gli ALTRI giorni, in cui il figlio")
    print("NON ha dovuto pensarci — e lo sapeva comunque.")


if __name__ == "__main__":
    seed = None
    if "--seed" in sys.argv:
        seed = int(sys.argv[sys.argv.index("--seed") + 1])
    simula(seed=seed)
