#!/usr/bin/env python3
"""Richiami automatici — il moat di Ponte (zero dipendenze).

Ogni gestionale da tavolo (Excel, quaderno) tiene la storia degli
interventi ma nessuno la rilegge mai per predire il PROSSIMO intervento.
Questo script sì: per ogni veicolo, guarda la storia dei "tipo" di
intervento già eseguiti (tagliando, cambio_gomme, revisione, ...), stima
l'intervallo tipico tra un intervento e il successivo dello stesso tipo,
e segnala i veicoli che sono in ritardo o in scadenza — un elenco di
richiamo pronto da lavorare, generato dai DATI REALI di quell'officina
specifica, non da una regola fissa uguale per tutti.

Perché è difficile da replicare: un concorrente che vende "un gestionale"
generico non ha né l'interesse né lo storico per farlo — richiede mesi di
dati accumulati PROPRIO in quell'officina. Più l'officina usa Ponte, più
questa lista diventa precisa: il vantaggio si compone nel tempo.

Uso:
    python3 richiami.py --demo         # popola dati finti e mostra i richiami
    python3 richiami.py --officina 1   # richiami reali per quell'officina (officina.db)
"""
import datetime
import json
import os
import sys

from app import db, crea, aggiorna_intervento, registra_officina

# Intervalli di riferimento (in giorni) per tipo di intervento, usati SOLO
# come prior iniziale quando non c'è ancora storico sufficiente (< 2
# interventi dello stesso tipo per quel veicolo): sono medie di mercato
# indicative, non un dato certificato — vanno dichiarate come tali.
INTERVALLI_DI_RIFERIMENTO_GIORNI = {
    "tagliando": 365,
    "cambio_gomme": 180,
    "revisione": 730,
    "generico": None,  # nessuna periodicità nota: non generare richiami per "generico"
}

SOGLIA_SCADENZA_GIORNI = 30  # entro quanti giorni dalla stima si segnala "in scadenza"


def _oggi():
    return datetime.date.today()


def _parse_data(s):
    return datetime.datetime.strptime(s.split(" ")[0], "%Y-%m-%d").date()


def storia_per_veicolo(officina_id):
    """Ritorna {veicolo_id: {"targa":..., "telefono":..., "interventi": [(tipo, data), ...]}}
    ordinati cronologicamente, solo interventi 'consegnato' (l'unico stato
    per cui sappiamo con certezza che il lavoro è stato davvero fatto)."""
    with db() as conn:
        righe = conn.execute(
            """SELECT v.id AS veicolo_id, v.targa, v.modello, c.telefono, c.nome AS cliente,
                      i.tipo, i.aggiornato
               FROM interventi i JOIN veicoli v ON v.id=i.veicolo_id
               JOIN clienti c ON c.id=v.cliente_id
               WHERE i.officina_id=? AND i.stato='consegnato'
               ORDER BY v.id, i.aggiornato""",
            (officina_id,),
        ).fetchall()
    veicoli = {}
    for r in righe:
        v = veicoli.setdefault(r["veicolo_id"], {
            "targa": r["targa"], "modello": r["modello"], "telefono": r["telefono"],
            "cliente": r["cliente"], "interventi": [],
        })
        v["interventi"].append((r["tipo"], _parse_data(r["aggiornato"])))
    return veicoli


def stima_prossima_scadenza(interventi_tipo, tipo):
    """interventi_tipo: lista di date (ordinata) per un singolo tipo su un
    singolo veicolo. Ritorna (prossima_data_stimata, intervallo_usato,
    fonte) oppure None se non c'è abbastanza informazione per stimare."""
    if tipo not in INTERVALLI_DI_RIFERIMENTO_GIORNI or INTERVALLI_DI_RIFERIMENTO_GIORNI[tipo] is None:
        return None
    if not interventi_tipo:
        return None
    ultima = interventi_tipo[-1]
    if len(interventi_tipo) >= 2:
        # Storico reale di QUESTO veicolo, in QUESTA officina: la stima più
        # forte, quella che nessun concorrente senza questi dati può fare.
        intervalli = [(interventi_tipo[i] - interventi_tipo[i - 1]).days for i in range(1, len(interventi_tipo))]
        media = sum(intervalli) / len(intervalli)
        return ultima + datetime.timedelta(days=media), round(media), "storico_veicolo"
    # Solo un intervento passato: usa il riferimento di mercato, dichiarato come tale.
    riferimento = INTERVALLI_DI_RIFERIMENTO_GIORNI[tipo]
    return ultima + datetime.timedelta(days=riferimento), riferimento, "riferimento_di_mercato"


def genera_richiami(officina_id):
    veicoli = storia_per_veicolo(officina_id)
    richiami = []
    oggi = _oggi()
    for veicolo_id, info in veicoli.items():
        per_tipo = {}
        for tipo, data in info["interventi"]:
            per_tipo.setdefault(tipo, []).append(data)
        for tipo, date_ in per_tipo.items():
            stima = stima_prossima_scadenza(sorted(date_), tipo)
            if not stima:
                continue
            prossima, intervallo_giorni, fonte = stima
            giorni_alla_scadenza = (prossima - oggi).days
            if giorni_alla_scadenza <= SOGLIA_SCADENZA_GIORNI:
                richiami.append({
                    "veicolo_id": veicolo_id,
                    "targa": info["targa"],
                    "modello": info["modello"],
                    "cliente": info["cliente"],
                    "telefono": info["telefono"],
                    "tipo": tipo,
                    "ultimo_intervento": max(date_).isoformat(),
                    "prossima_scadenza_stimata": prossima.isoformat(),
                    "giorni_alla_scadenza": giorni_alla_scadenza,
                    "stato": "scaduto" if giorni_alla_scadenza < 0 else "in_scadenza",
                    "intervallo_usato_giorni": intervallo_giorni,
                    "fonte_stima": fonte,
                })
    richiami.sort(key=lambda r: r["giorni_alla_scadenza"])
    return richiami


def demo():
    import app as _app_module
    _app_module.DB = "richiami_demo.db"
    if os.path.exists(_app_module.DB):
        os.remove(_app_module.DB)

    reg = registra_officina({"nome": "Officina Demo", "email": "demo@richiami.test", "password": "passworddemo1", "telefono": "051 0000000"})
    officina_id = reg["officina"]["id"]

    oggi = _oggi()

    def crea_veicolo(cliente_nome, telefono, targa, modello):
        c = crea("clienti", ["nome", "telefono"], {"nome": cliente_nome, "telefono": telefono}, officina_id)
        return crea("veicoli", ["cliente_id", "targa", "modello"], {"cliente_id": c["id"], "targa": targa, "modello": modello}, officina_id)["id"]

    def intervento_nel_passato(veicolo_id, tipo, giorni_fa_chiuso):
        i = crea("interventi", ["veicolo_id", "descrizione", "preventivo", "tipo"],
                  {"veicolo_id": veicolo_id, "descrizione": tipo, "preventivo": 200, "tipo": tipo}, officina_id)
        aggiorna_intervento(i["id"], {"stato": "consegnato", "importo_finale": 200}, officina_id)
        # Forza aggiornato alla data desiderata (il selftest reale usa CURRENT_TIMESTAMP,
        # qui serve simulare mesi di storia in pochi secondi).
        data_chiusura = (oggi - datetime.timedelta(days=giorni_fa_chiuso)).isoformat() + " 10:00:00"
        with db() as conn:
            conn.execute("UPDATE interventi SET aggiornato=? WHERE id=?", (data_chiusura, i["id"]))

    # Veicolo 1: due tagliandi passati sullo STESSO veicolo, con intervallo reale
    # di ~205 giorni -> prossimo stimato dallo storico, già scaduto
    v1 = crea_veicolo("Luca Bianchi", "+393331111111", "AB123CD", "Panda 1.2")
    intervento_nel_passato(v1, "tagliando", 410)
    intervento_nel_passato(v1, "tagliando", 205)

    # Veicolo 2: un solo cambio gomme 6 mesi fa -> in scadenza (riferimento di mercato)
    v2 = crea_veicolo("Anna Verdi", "+393332222222", "EF456GH", "Yaris")
    intervento_nel_passato(v2, "cambio_gomme", 175)

    # Veicolo 3: tagliando recente, nessun richiamo atteso
    v3 = crea_veicolo("Marco Neri", "+393333333333", "IJ789KL", "500X")
    intervento_nel_passato(v3, "tagliando", 20)

    richiami = genera_richiami(officina_id)
    print(f"📋 {len(richiami)} veicoli da richiamare (officina demo):\n")
    for r in richiami:
        icona = "🔴" if r["stato"] == "scaduto" else "🟡"
        print(f"{icona} {r['targa']} ({r['modello']}) — {r['cliente']} {r['telefono']}")
        print(f"   {r['tipo']}: ultimo {r['ultimo_intervento']}, stimato scadere il {r['prossima_scadenza_stimata']} "
              f"({r['giorni_alla_scadenza']} giorni) — fonte: {r['fonte_stima']}")
    os.remove(_app_module.DB)


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    elif "--officina" in sys.argv:
        idx = sys.argv.index("--officina")
        officina_id = int(sys.argv[idx + 1])
        for r in genera_richiami(officina_id):
            print(json.dumps(r, ensure_ascii=False))
    else:
        print(__doc__)
