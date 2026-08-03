#!/usr/bin/env python3
"""Motore di affidabilità — il primo moat di ProntoCasa (zero dipendenze).

Ogni marketplace di servizi per la casa ha le stelline. Il problema: le
stelline si comprano, si gonfiano, e un professionista nuovo parte da
zero recensioni indipendentemente da quanto sia bravo. Questo motore non
chiede mai un giudizio soggettivo al cliente: calcola un punteggio dai
FATTI già registrati dalla piattaforma — chi risponde davvero quando
viene contattato, chi accetta i lavori che gli vengono proposti, chi li
porta a termine invece di sparire a metà.

Tre segnali, tutti oggettivi:
1. tasso di risposta — risponde entro la scadenza o lascia scadere?
2. tasso di accettazione — tra chi risponde, quanti accettano?
3. tasso di completamento — tra chi accetta, quanti il cliente conferma
   completati (e non annullati a metà)?

Perché è un moat: nessun concorrente che vende "un elenco di artigiani"
ha questi dati — servono mesi di richieste reali passate sulla stessa
piattaforma. Un professionista non può comprare un punteggio alto, può
solo guadagnarselo rispondendo, accettando e finendo i lavori.

Uso:
    python3 affidabilita.py --demo   # storico finto, mostra il calcolo
"""
import os
import sqlite3

# Un professionista nuovo, senza storico, NON deve partire penalizzato
# (sarebbe ingiusto e scoraggerebbe le nuove iscrizioni) né avvantaggiato
# a caso: 0.5 è il punto neutro, esattamente a metà tra "pessimo" e
# "ottimo" — stessa logica del rischio no-show nel progetto 10, che non
# penalizza un cliente nuovo senza motivo.
PUNTEGGIO_NEUTRO_SENZA_STORICO = 0.5

PESO_RISPOSTA = 0.4
PESO_ACCETTAZIONE = 0.3
PESO_COMPLETAMENTO = 0.3


def _db(db_path=None):
    path = db_path or os.environ.get("PRONTOCASA_DB", "prontocasa.db")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def calcola_affidabilita(professionista_id, db_path=None):
    conn = _db(db_path)
    try:
        proposte = conn.execute(
            "SELECT * FROM proposte WHERE professionista_id=? AND stato != 'in_attesa'",
            (professionista_id,),
        ).fetchall()
        if not proposte:
            return {
                "punteggio": PUNTEGGIO_NEUTRO_SENZA_STORICO,
                "n_proposte": 0,
                "motivo": "nessuno storico ancora — punteggio neutro di partenza",
            }

        n_totale = len(proposte)
        n_risposte = sum(1 for p in proposte if p["stato"] in ("accettata", "rifiutata"))
        n_accettate = sum(1 for p in proposte if p["stato"] == "accettata")
        tasso_risposta = n_risposte / n_totale
        tasso_accettazione = (n_accettate / n_risposte) if n_risposte else 0.0

        richieste_accettate = [p["richiesta_id"] for p in proposte if p["stato"] == "accettata"]
        n_completate = 0
        if richieste_accettate:
            segnaposto = ",".join("?" * len(richieste_accettate))
            n_completate = conn.execute(
                f"SELECT COUNT(*) FROM richieste WHERE id IN ({segnaposto}) AND stato='completata'",
                richieste_accettate,
            ).fetchone()[0]
        tasso_completamento = (n_completate / len(richieste_accettate)) if richieste_accettate else 0.0

        punteggio = (
            PESO_RISPOSTA * tasso_risposta
            + PESO_ACCETTAZIONE * tasso_accettazione
            + PESO_COMPLETAMENTO * tasso_completamento
        )
        return {
            "punteggio": round(punteggio, 2),
            "n_proposte": n_totale,
            "tasso_risposta": round(tasso_risposta, 2),
            "tasso_accettazione": round(tasso_accettazione, 2),
            "tasso_completamento": round(tasso_completamento, 2),
        }
    finally:
        conn.close()


def migliori_candidati(categoria, citta, db_path=None, limite=5):
    """Professionisti disponibili in quella categoria/città, ordinati dal
    più affidabile: è la classifica usata dal dispacciamento (vedi
    dispacciamento.py) per decidere chi contattare per primo."""
    conn = _db(db_path)
    try:
        righe = conn.execute(
            "SELECT id FROM professionisti WHERE categoria=? AND citta=? AND disponibile=1",
            (categoria, citta),
        ).fetchall()
    finally:
        conn.close()
    candidati = [
        {"professionista_id": r["id"], **calcola_affidabilita(r["id"], db_path)}
        for r in righe
    ]
    candidati.sort(key=lambda c: c["punteggio"], reverse=True)
    return candidati[:limite]


def demo():
    import tempfile
    from prontocasa import registra_professionista, db as _db_pc
    import prontocasa as _mod

    with tempfile.TemporaryDirectory() as tmp:
        _mod.DB = os.path.join(tmp, "affidabilita-demo.db")

        bravo = registra_professionista({
            "nome": "Mario Idraulico", "categoria": "idraulico", "citta": "Torino",
            "telefono": "+393331110001", "email": "mario@idraulico.test", "password": "passwordMario1",
            "servizi_offerti": "Riparazioni urgenti, sostituzione sanitari", "tariffa_base": 30, "tariffa_oraria": 25,
            "dichiarazione_requisiti": True,
        })["professionista"]
        scarso = registra_professionista({
            "nome": "Luigi Idraulico", "categoria": "idraulico", "citta": "Torino",
            "telefono": "+393331110002", "email": "luigi@idraulico.test", "password": "passwordLuigi1",
            "servizi_offerti": "Riparazioni generiche", "tariffa_base": 25, "tariffa_oraria": 20,
            "dichiarazione_requisiti": True,
        })["professionista"]

        # Storico simulato direttamente sulle tabelle (bypassa il dispacciamento
        # reale solo per costruire velocemente uno storico di esempio).
        import secrets
        with _mod.db() as conn:
            for i in range(6):
                conn.execute(
                    "INSERT INTO richieste (codice, cliente_nome, cliente_telefono, categoria, citta, descrizione, stato) VALUES (?,?,?,?,?,?,?)",
                    (secrets.token_urlsafe(8), f"Cliente {i}", f"+393339990{i:02d}", "idraulico", "Torino", "perdita rubinetto", "completata"),
                )
            richieste_ids = [r["id"] for r in conn.execute("SELECT id FROM richieste").fetchall()]
            # Mario: risponde sempre, accetta sempre, completa sempre (5/5)
            for rid in richieste_ids[:5]:
                conn.execute(
                    "INSERT INTO proposte (richiesta_id, professionista_id, ordine, stato, scadenza) VALUES (?,?,?,?,datetime('now'))",
                    (rid, bravo["id"], 1, "accettata"),
                )
            # Luigi: risponde a 3 su 6, ne accetta 1, non la completa mai
            for i, rid in enumerate(richieste_ids):
                stato = "accettata" if i == 0 else ("rifiutata" if i < 3 else "scaduta")
                conn.execute(
                    "INSERT INTO proposte (richiesta_id, professionista_id, ordine, stato, scadenza) VALUES (?,?,?,?,datetime('now'))",
                    (rid, scarso["id"], 2, stato, ),
                )
            conn.execute("UPDATE richieste SET stato='in_attesa' WHERE id=?", (richieste_ids[0],))

        print("📊 Mario (risponde e completa sempre):", calcola_affidabilita(bravo["id"], _mod.DB))
        print("📊 Luigi (spesso non risponde, non completa):", calcola_affidabilita(scarso["id"], _mod.DB))
        print("\n🏆 Classifica per idraulico a Torino:")
        for c in migliori_candidati("idraulico", "Torino", _mod.DB):
            print(f"   professionista #{c['professionista_id']}: punteggio {c['punteggio']}")


if __name__ == "__main__":
    import sys
    if "--demo" in sys.argv:
        demo()
    else:
        print(__doc__)
