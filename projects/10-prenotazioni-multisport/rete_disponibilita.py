#!/usr/bin/env python3
"""Rete di disponibilità — il secondo moat di Campolibero (zero dipendenze).

Il problema: un cliente chiama/apre l'app della struttura A, il campo che
vuole è pieno all'orario che vuole lui — e se ne va, magari verso un
concorrente che non usa Campolibero. Un calendario da solo non risolve
niente: "pieno" è un vicolo cieco.

La soluzione: se più strutture della stessa città usano Campolibero,
questo modulo cerca lo stesso sport nelle ALTRE strutture della zona e
propone lo slot libero più vicino all'orario richiesto — un cliente che
non trova posto in un posto lo trova comunque nella rete, invece di
perderlo del tutto.

Perché è un moat vero (non solo una funzione furba): il suo valore cresce
con il numero di strutture iscritte — è un effetto rete che un singolo
concorrente con "solo un calendario" non può replicare da solo, per
definizione: servono ALTRE strutture reali sulla stessa piattaforma.

Uso:
    python3 rete_disponibilita.py --demo   # due strutture della stessa città, cerca nella rete
"""
import datetime
import os
import sys

FINESTRA_RICERCA_ORE = 3  # quanto ci si allontana dall'orario richiesto pur di trovare un posto


def cerca_nella_rete(sport, citta, inizio_richiesto, escludi_struttura_id=None, db_path=None):
    # Import qui (non in cima al file) per evitare l'import circolare con
    # prenota.py, che a sua volta userà questo modulo per l'endpoint /rete.
    from prenota import disponibilita
    import prenota as _mod

    path_precedente = _mod.DB
    if db_path:
        _mod.DB = db_path
    try:
        with _mod.db() as conn:
            strutture = conn.execute(
                "SELECT id, nome, citta FROM strutture WHERE citta=?", (citta,)
            ).fetchall()

        risultati = []
        giorno = inizio_richiesto.date().isoformat()
        for s in strutture:
            if escludi_struttura_id and s["id"] == escludi_struttura_id:
                continue
            for voce in disponibilita(s["id"], giorno, sport):
                for slot_iso in voce["slot_liberi"]:
                    slot = datetime.datetime.fromisoformat(slot_iso)
                    distanza_ore = abs((slot - inizio_richiesto).total_seconds()) / 3600
                    if distanza_ore <= FINESTRA_RICERCA_ORE:
                        risultati.append({
                            "struttura": s["nome"],
                            "risorsa": voce["nome"],
                            "inizio": slot_iso,
                            "prezzo_orario": voce["prezzo_orario"],
                            "distanza_ore": round(distanza_ore, 1),
                        })
        risultati.sort(key=lambda r: r["distanza_ore"])
        return risultati
    finally:
        _mod.DB = path_precedente


def demo():
    import tempfile
    from prenota import registra_struttura, crea_risorsa, prenota as _prenota
    import prenota as _mod

    with tempfile.TemporaryDirectory() as tmp:
        _mod.DB = os.path.join(tmp, "rete-demo.db")

        a = registra_struttura({"nome": "Padel Centro", "citta": "Milano", "email": "a@rete.test", "password": "passwordUnoA1", "telefono": "02 1111111"})["struttura"]
        b = registra_struttura({"nome": "Padel Navigli", "citta": "Milano", "email": "b@rete.test", "password": "passwordDueB2", "telefono": "02 2222222"})["struttura"]

        campo_a = crea_risorsa(a["id"], {"nome": "Campo 1", "sport": "padel", "durata_slot_min": 90, "prezzo_orario": 28})
        campo_b = crea_risorsa(b["id"], {"nome": "Campo Centrale", "sport": "padel", "durata_slot_min": 90, "prezzo_orario": 32})

        giorno = "2026-08-10"
        # Riempiamo TUTTI gli slot del campo A per quel giorno: un cliente
        # che lo cerca lì non trova nulla.
        from prenota import disponibilita as _disp
        for slot in _disp(a["id"], giorno, "padel")[0]["slot_liberi"]:
            _prenota(a["id"], {"risorsa_id": campo_a["id"], "nome_cliente": "Cliente Pieno", "telefono_cliente": f"+3931{hash(slot) % 10000000}", "inizio": slot})

        orario_richiesto = datetime.datetime.fromisoformat(f"{giorno}T18:00:00")
        print(f"🔎 Campo A (Padel Centro) pieno il {giorno} — cerco nella rete di Milano per le 18:00...\n")
        suggerimenti = cerca_nella_rete("padel", "Milano", orario_richiesto, escludi_struttura_id=a["id"])
        for s in suggerimenti[:3]:
            print(f"   ✅ {s['struttura']} — {s['risorsa']} alle {s['inizio'][11:16]} ({s['prezzo_orario']}€/h, {s['distanza_ore']}h dall'orario richiesto)")
        if not suggerimenti:
            print("   nessun risultato nella rete")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        print(__doc__)
