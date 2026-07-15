#!/usr/bin/env python3
"""Motore rischio no-show — il primo moat di Campolibero (zero dipendenze).

Il problema che nessun calendario generico risolve: nei centri sportivi il
no-show (prenoti e non ti presenti) è la perdita economica silenziosa più
grande — uno slot vuoto alle 19 di un martedì non si rivende più. La
soluzione ovvia (deposito obbligatorio sempre) scoraggia i clienti buoni;
quella opposta (mai deposito) regala lo slot ai clienti inaffidabili.

Questo motore decide caso per caso, incrociando due storici REALI:
1. il cliente stesso — ha già saltato prenotazioni in questa struttura?
2. lo slot stesso — quel giorno/quella fascia oraria, in QUESTA struttura,
   ha storicamente un tasso di no-show alto (es. i lunedì mattina presto)?

Nessun concorrente che vende "un calendario" ha né l'interesse né lo
storico per farlo: serve mesi di prenotazioni accumulate PROPRIO in quella
struttura. Più la struttura usa Campolibero, più la stima diventa precisa
— è un vantaggio che si compone nel tempo, non un algoritmo che si copia
in un weekend.

Uso:
    python3 rischio_noshow.py --demo   # storico finto, mostra la valutazione
"""
import datetime
import os
import sqlite3

# Soglie tarate per essere prudenti: meglio un deposito di troppo (piccolo
# attrito) che uno slot perso (perdita piena). Configurabili per struttura
# in futuro; per ora uniche e dichiarate qui.
SOGLIA_RISCHIO_ALTO = 0.4
STORICO_MINIMO_PER_FIDARSI_DEL_CLIENTE = 3  # prenotazioni passate


def _db(db_path=None):
    path = db_path or os.environ.get("CAMPOLIBERO_DB", "campolibero.db")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _storico_cliente(conn, struttura_id, telefono):
    righe = conn.execute(
        """SELECT p.stato FROM prenotazioni p JOIN clienti c ON c.id = p.cliente_id
           WHERE p.struttura_id=? AND c.telefono=? AND p.stato IN ('completata','no_show')""",
        (struttura_id, telefono),
    ).fetchall()
    totale = len(righe)
    no_show = sum(1 for r in righe if r["stato"] == "no_show")
    return totale, no_show


def _storico_slot(conn, struttura_id, risorsa_id, inizio):
    """Tasso di no-show storico per questa risorsa, nello stesso giorno
    della settimana e nella stessa fascia oraria (+/- 1 ora) — non basta
    guardare "quella risorsa in generale": un campo padel può avere un
    lunedì mattina morto e un lunedì sera pienissimo e affidabile."""
    giorno_settimana = inizio.weekday()
    ora = inizio.hour
    righe = conn.execute(
        """SELECT inizio, stato FROM prenotazioni
           WHERE struttura_id=? AND risorsa_id=? AND stato IN ('completata','no_show')""",
        (struttura_id, risorsa_id),
    ).fetchall()
    pertinenti = [
        r for r in righe
        if datetime.datetime.fromisoformat(r["inizio"]).weekday() == giorno_settimana
        and abs(datetime.datetime.fromisoformat(r["inizio"]).hour - ora) <= 1
    ]
    totale = len(pertinenti)
    no_show = sum(1 for r in pertinenti if r["stato"] == "no_show")
    return totale, no_show


def valuta_rischio(struttura_id, telefono_cliente, risorsa_id, inizio, db_path=None):
    conn = _db(db_path)
    try:
        tot_cliente, no_show_cliente = _storico_cliente(conn, struttura_id, telefono_cliente)
        tot_slot, no_show_slot = _storico_slot(conn, struttura_id, risorsa_id, inizio)
    finally:
        conn.close()

    # Cliente con storico pulito e sufficiente: si fida di lui a prescindere
    # dallo slot — è il punto che rende il sistema "intuitivo" invece che
    # punitivo: i clienti affidabili non vedono mai un deposito.
    if tot_cliente >= STORICO_MINIMO_PER_FIDARSI_DEL_CLIENTE and no_show_cliente == 0:
        return {"punteggio": 0.0, "richiede_deposito": False, "motivo": f"cliente affidabile ({tot_cliente} prenotazioni, 0 no-show)"}

    tasso_cliente = (no_show_cliente / tot_cliente) if tot_cliente else None
    tasso_slot = (no_show_slot / tot_slot) if tot_slot else None

    if tasso_cliente is not None and tasso_cliente >= 0.5:
        return {"punteggio": round(tasso_cliente, 2), "richiede_deposito": True,
                "motivo": f"il cliente ha già saltato {no_show_cliente}/{tot_cliente} prenotazioni qui"}

    # Cliente nuovo o senza segnali forti: usa il tasso storico dello slot
    # come proxy, il vero cuore del moat (nessun dato sul singolo cliente
    # nuovo esiste ancora, ma lo slot stesso "parla" dai dati passati).
    if tasso_slot is not None:
        punteggio = tasso_slot if tasso_cliente is None else max(tasso_cliente, tasso_slot) * 0.6
        if punteggio >= SOGLIA_RISCHIO_ALTO:
            return {"punteggio": round(punteggio, 2), "richiede_deposito": True,
                    "motivo": f"questa fascia oraria ha uno storico di no-show del {round(tasso_slot*100)}% in questa struttura"}
        return {"punteggio": round(punteggio, 2), "richiede_deposito": False,
                "motivo": "nessun segnale di rischio sufficiente"}

    return {"punteggio": 0.1, "richiede_deposito": False, "motivo": "nessuno storico ancora disponibile — nessun deposito di default"}


def demo():
    import tempfile
    from prenota import registra_struttura, crea_risorsa, prenota as _prenota, aggiorna_stato_prenotazione
    import prenota as _mod

    with tempfile.TemporaryDirectory() as tmp:
        _mod.DB = os.path.join(tmp, "rischio-demo.db")
        reg = registra_struttura({"nome": "Padel Demo", "citta": "Milano", "email": "demo@rischio.test", "password": "passworddemo1", "telefono": "02 0000000"})
        sid = reg["struttura"]["id"]
        campo = crea_risorsa(sid, {"nome": "Campo 1", "sport": "padel", "durata_slot_min": 90, "prezzo_orario": 30})

        # Costruiamo uno storico: il lunedì mattina alle 8 questa struttura
        # ha 3 no-show su 4 prenotazioni passate — un pattern reale.
        base = datetime.datetime(2026, 6, 1, 8, 0)  # un lunedì
        for settimana in range(4):
            inizio = (base + datetime.timedelta(weeks=settimana)).isoformat()
            p = _prenota(sid, {"risorsa_id": campo["id"], "nome_cliente": f"Cliente {settimana}", "telefono_cliente": f"+3933{settimana}000000", "inizio": inizio})
            esito = "no_show" if settimana < 3 else "completata"
            aggiorna_stato_prenotazione(p["id"], sid, esito)

        # Un cliente nuovo che prova a prenotare LO STESSO slot il lunedì successivo
        prossimo_lunedi = (base + datetime.timedelta(weeks=4)).isoformat()
        rischio_slot_rischioso = valuta_rischio(sid, "+393390000001", campo["id"], datetime.datetime.fromisoformat(prossimo_lunedi), db_path=_mod.DB)
        print("📅 Cliente nuovo, lunedì mattina alle 8 (slot storicamente rischioso):")
        print(f"   {rischio_slot_rischioso}")

        # Lo stesso cliente nuovo, ma per un orario serale senza storico negativo
        sera = (base + datetime.timedelta(weeks=4, hours=12)).isoformat()
        rischio_sera = valuta_rischio(sid, "+393390000002", campo["id"], datetime.datetime.fromisoformat(sera), db_path=_mod.DB)
        print("\n🌆 Cliente nuovo, stesso campo ma orario serale (nessuno storico negativo):")
        print(f"   {rischio_sera}")


if __name__ == "__main__":
    import sys
    if "--demo" in sys.argv:
        demo()
    else:
        print(__doc__)
