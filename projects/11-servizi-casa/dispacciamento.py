#!/usr/bin/env python3
"""Dispacciamento a cascata — il secondo moat di ProntoCasa (zero dipendenze).

Il problema che nessun elenco di artigiani risolve: un allagamento non
aspetta che tre professionisti rispondano a un preventivo via email.
Questo motore, appena arriva una richiesta, contatta SUBITO il
professionista più affidabile disponibile (vedi affidabilita.py) — non
tutta la lista, uno alla volta — e se non risponde entro la scadenza
(breve per le urgenze, più ampia per il resto) passa automaticamente al
successivo, finché qualcuno accetta o i candidati finiscono.

Perché "urgente" e "normale" condividono lo stesso motore: la differenza
è solo la scadenza per candidato (10 minuti contro 3 ore) — una
semplificazione deliberata rispetto a due flussi separati, più semplice
da mantenere e comunque coerente con l'obiettivo (arrivare a QUALCUNO
disponibile il prima possibile, urgenza o meno).

Uso:
    python3 dispacciamento.py --demo   # simula un dispacciamento a cascata con 3 candidati
"""
import datetime
import os
import sqlite3
import sys

from affidabilita import migliori_candidati
from integrazioni.notifiche import invia_sms_proposta, invia_sms_conferma_cliente

TIMEOUT_MINUTI = {"urgente": 10, "normale": 180}
MAX_CANDIDATI = 5


def _db(db_path=None):
    path = db_path or os.environ.get("PRONTOCASA_DB", "prontocasa.db")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def _prossimo_candidato(richiesta_id, db_path=None):
    # sqlite3 non fa auto-commit: "with conn:" apre e chiude la transazione
    # (commit alla fine del blocco, anche quando si esce con un "return"),
    # "try/finally" fuori si occupa di chiudere comunque la connessione.
    conn = _db(db_path)
    try:
        with conn:
            richiesta = conn.execute("SELECT * FROM richieste WHERE id=?", (richiesta_id,)).fetchone()
            if not richiesta or richiesta["stato"] != "in_attesa":
                return None  # richiesta già assegnata, completata o annullata: niente da fare

            già_contattati = {
                r["professionista_id"]
                for r in conn.execute("SELECT professionista_id FROM proposte WHERE richiesta_id=?", (richiesta_id,)).fetchall()
            }
            if len(già_contattati) >= MAX_CANDIDATI:
                conn.execute("UPDATE richieste SET stato='nessun_professionista' WHERE id=?", (richiesta_id,))
                return None

            candidati = migliori_candidati(richiesta["categoria"], richiesta["citta"], db_path, limite=MAX_CANDIDATI * 2)
            candidati_rimanenti = [c for c in candidati if c["professionista_id"] not in già_contattati]
            if not candidati_rimanenti:
                conn.execute("UPDATE richieste SET stato='nessun_professionista' WHERE id=?", (richiesta_id,))
                return None

            prossimo = candidati_rimanenti[0]
            ordine = len(già_contattati) + 1
            timeout_min = TIMEOUT_MINUTI.get(richiesta["urgenza"], TIMEOUT_MINUTI["normale"])
            scadenza = (datetime.datetime.now() + datetime.timedelta(minutes=timeout_min)).isoformat()
            cur = conn.execute(
                "INSERT INTO proposte (richiesta_id, professionista_id, ordine, stato, scadenza) VALUES (?,?,?,?,?)",
                (richiesta_id, prossimo["professionista_id"], ordine, "in_attesa", scadenza),
            )
            proposta_id = cur.lastrowid
            professionista = conn.execute("SELECT * FROM professionisti WHERE id=?", (prossimo["professionista_id"],)).fetchone()
    finally:
        conn.close()

    try:
        invia_sms_proposta(professionista["telefono"], richiesta)
    except Exception as e:
        print(f"⚠️  SMS al professionista fallito (la proposta resta valida): {e}")
    return proposta_id


def avvia_dispatch(richiesta_id, db_path=None):
    return _prossimo_candidato(richiesta_id, db_path)


def rispondi_proposta(proposta_id, professionista_id, esito, db_path=None):
    conn = _db(db_path)
    try:
        with conn:
            proposta = conn.execute("SELECT * FROM proposte WHERE id=?", (proposta_id,)).fetchone()
            if not proposta:
                raise LookupError("proposta non trovata")
            if proposta["professionista_id"] != professionista_id:
                raise PermissionError("questa proposta non è tua")
            if proposta["stato"] != "in_attesa":
                raise ValueError("questa proposta è già stata chiusa")

            conn.execute(
                "UPDATE proposte SET stato=?, risposta=? WHERE id=?",
                (esito, datetime.datetime.now().isoformat(), proposta_id),
            )

            if esito == "accettata":
                conn.execute(
                    "UPDATE richieste SET stato='assegnata', professionista_assegnato_id=? WHERE id=?",
                    (professionista_id, proposta["richiesta_id"]),
                )
                # Chiude eventuali altre proposte rimaste aperte per la stessa
                # richiesta: nel flusso sequenziale ce n'è al più una alla
                # volta, ma è una garanzia difensiva contro condizioni di gara.
                conn.execute(
                    "UPDATE proposte SET stato='scaduta' WHERE richiesta_id=? AND id != ? AND stato='in_attesa'",
                    (proposta["richiesta_id"], proposta_id),
                )
                richiesta = dict(conn.execute("SELECT * FROM richieste WHERE id=?", (proposta["richiesta_id"],)).fetchone())
                professionista = conn.execute("SELECT * FROM professionisti WHERE id=?", (professionista_id,)).fetchone()
            else:
                richiesta = None
    finally:
        conn.close()

    if esito == "accettata":
        try:
            invia_sms_conferma_cliente(richiesta["cliente_telefono"], professionista)
        except Exception as e:
            print(f"⚠️  SMS al cliente fallito (l'assegnazione resta valida): {e}")
        return richiesta

    # Rifiutata: passa al prossimo candidato e ritorna lo stato aggiornato della richiesta.
    _prossimo_candidato(proposta["richiesta_id"], db_path)
    conn = _db(db_path)
    try:
        return dict(conn.execute("SELECT * FROM richieste WHERE id=?", (proposta["richiesta_id"],)).fetchone())
    finally:
        conn.close()


def controlla_scadute(db_path=None):
    """Da chiamare periodicamente (o opportunisticamente a ogni richiesta
    HTTP, come fa prontocasa.py): sposta al candidato successivo ogni
    proposta rimasta 'in_attesa' oltre la propria scadenza — è il cuore
    della cascata automatica."""
    conn = _db(db_path)
    try:
        with conn:
            scadute = conn.execute(
                "SELECT id, richiesta_id FROM proposte WHERE stato='in_attesa' AND scadenza < ?",
                (datetime.datetime.now().isoformat(),),
            ).fetchall()
            richieste_da_avanzare = []
            for s in scadute:
                conn.execute("UPDATE proposte SET stato='scaduta' WHERE id=?", (s["id"],))
                richieste_da_avanzare.append(s["richiesta_id"])
    finally:
        conn.close()
    for richiesta_id in richieste_da_avanzare:
        _prossimo_candidato(richiesta_id, db_path)


def demo():
    import tempfile
    from prontocasa import registra_professionista, crea_richiesta
    import prontocasa as _mod

    with tempfile.TemporaryDirectory() as tmp:
        _mod.DB = os.path.join(tmp, "dispacciamento-demo.db")

        nomi = ["Primo Idraulico", "Secondo Idraulico", "Terzo Idraulico"]
        professionisti = []
        for i, nome in enumerate(nomi):
            p = registra_professionista({
                "nome": nome, "categoria": "idraulico", "citta": "Napoli",
                "telefono": f"+39333000000{i}", "email": f"idraulico{i}@test.test",
                "password": f"passwordDemo{i}23", "servizi_offerti": "Riparazioni idrauliche",
                "dichiarazione_requisiti": True,
            })["professionista"]
            professionisti.append(p)

        richiesta = crea_richiesta({
            "cliente_nome": "Giulia Bianchi", "cliente_telefono": "+393339991111",
            "categoria": "idraulico", "citta": "Napoli", "descrizione": "tubo rotto, acqua ovunque",
            "urgenza": "urgente",
        })
        print(f"📨 Richiesta #{richiesta['id']} creata, stato: {richiesta['stato']}\n")

        # Il primo candidato non risponde: forziamo la scadenza nel passato
        # per dimostrare la cascata senza aspettare 10 minuti veri.
        with _mod.db() as conn:
            proposta_1 = conn.execute("SELECT * FROM proposte WHERE richiesta_id=?", (richiesta["id"],)).fetchone()
            print(f"👤 Proposta #1 inviata al professionista #{proposta_1['professionista_id']} ({nomi[professionisti.index(next(p for p in professionisti if p['id']==proposta_1['professionista_id']))]})")
            conn.execute("UPDATE proposte SET scadenza=? WHERE id=?", ("2000-01-01T00:00:00", proposta_1["id"]))

        print("⏰ Scadenza forzata nel passato — eseguo controlla_scadute()...")
        controlla_scadute(_mod.DB)

        with _mod.db() as conn:
            proposta_2 = conn.execute(
                "SELECT * FROM proposte WHERE richiesta_id=? AND ordine=2", (richiesta["id"],)
            ).fetchone()
        print(f"👤 Cascata: proposta #2 inviata automaticamente al professionista #{proposta_2['professionista_id']}\n")

        esito = rispondi_proposta(proposta_2["id"], proposta_2["professionista_id"], "accettata", _mod.DB)
        print(f"✅ Il secondo professionista accetta: richiesta ora '{esito['stato']}', assegnata a #{esito['professionista_assegnato_id']}")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        print(__doc__)
