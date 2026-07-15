#!/usr/bin/env python3
"""Pattern Tracker — il moat di FiloDiretto (zero dipendenze).

checkin_simulator.py mostra COME funzionerebbe l'escalation con dati
casuali — utile per progettare e vendere il servizio prima di avere un
cliente vero. Questo script fa la stessa analisi ma sui dati REALI: legge
il log eventi (`eventi.jsonl`) prodotto da `server.js` del progetto 01
quando gira con `FLOW=flows/filodiretto.json`, e ne ricava lo stato di
oggi e il report settimanale — gli stessi identici, ma non inventati.

Perché è un moat: chiunque può simulare un report. Nessun concorrente ha
il motore conversazionale (progetto 01), il webhook telefonico reale, E
lo storico giorno-dopo-giorno di UNA famiglia specifica da cui riconoscere
un pattern — serve tempo reale accumulato con quella famiglia, non si
compra né si copia.

Uso:
    python3 pattern_tracker.py --demo          # con eventi.jsonl di esempio generati al volo
    python3 pattern_tracker.py                 # sui dati reali (EVENTI_LOG, default eventi.jsonl)
"""
import datetime
import json
import os
import sys

EVENTI_LOG = os.environ.get("EVENTI_LOG", os.path.join(os.path.dirname(os.path.abspath(__file__)), "eventi.jsonl"))

# Quanti "segnali deboli" in quanti giorni fanno scattare l'avviso di
# pattern — stessa regola dichiarata in MVP-SPEC.md, non inventata qui.
SOGLIA_SEGNALI_DEBOLI = 3
FINESTRA_PATTERN_GIORNI = 7


def leggi_eventi(path=None):
    path = path or EVENTI_LOG
    if not os.path.exists(path):
        return []
    eventi = []
    with open(path, encoding="utf-8") as f:
        for riga in f:
            riga = riga.strip()
            if riga:
                eventi.append(json.loads(riga))
    return eventi


def _giorno(evento):
    return datetime.datetime.fromtimestamp(evento["ts"] / 1000).date()


def registra_no_risposta(path=None):
    """Chiamato dal webhook di stato chiamata (chiamata_uscente.py) quando
    Twilio segnala che l'assistito non ha risposto: è l'unico evento che
    NON nasce dentro server.js (che gestisce solo chiamate risposte), ma
    deve finire nello stesso log per essere visto dallo stesso motore di
    analisi — un log unico, non due sistemi paralleli da tenere allineati."""
    path = path or EVENTI_LOG
    record = {"ts": int(datetime.datetime.now().timestamp() * 1000), "flow": "FiloDiretto — chiamata quotidiana", "tipo": "no_risposta"}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def eventi_per_giorno(eventi):
    per_giorno = {}
    for e in eventi:
        if "ts" not in e:
            continue
        per_giorno.setdefault(_giorno(e), []).append(e)
    return per_giorno


def classifica_giorno(eventi_del_giorno):
    """Un solo giorno può avere più eventi (chiamata + eventuale
    riprogrammazione): vince sempre il segnale più grave visto quel giorno."""
    tipi = {e["tipo"] for e in eventi_del_giorno}
    n_no_risposta = sum(1 for e in eventi_del_giorno if e["tipo"] == "no_risposta")
    if "allerta_famiglia_immediata" in tipi:
        return "rosso", "segnale forte — famiglia già avvisata durante la chiamata"
    if n_no_risposta >= 2:
        return "rosso", "nessuna risposta a due tentativi — famiglia da avvisare"
    if "registra_segnale_debole" in tipi:
        return "giallo", "segnale debole — da tenere d'occhio"
    if n_no_risposta == 1:
        return "giallo", "un tentativo senza risposta (in attesa del richiamo)"
    if "registra_esito_ok" in tipi or "chiamata_conclusa" in tipi:
        return "verde", "tutto bene"
    return "grigio", "nessuna chiamata registrata"


def stato_di_oggi(eventi=None):
    eventi = eventi if eventi is not None else leggi_eventi()
    oggi = datetime.date.today()
    di_oggi = [e for e in eventi if "ts" in e and _giorno(e) == oggi]
    if not di_oggi:
        return {"data": oggi.isoformat(), "stato": "grigio", "motivo": "nessuna chiamata ancora oggi"}
    stato, motivo = classifica_giorno(di_oggi)
    return {"data": oggi.isoformat(), "stato": stato, "motivo": motivo}


def rileva_pattern(eventi=None, oggi=None):
    """La regola dell'MVP-SPEC: 3 segnali deboli in 7 giorni → avviso
    "pattern" alla famiglia, anche se nessun singolo giorno era abbastanza
    grave da scatenare un'allerta immediata da solo."""
    eventi = eventi if eventi is not None else leggi_eventi()
    oggi = oggi or datetime.date.today()
    soglia = oggi - datetime.timedelta(days=FINESTRA_PATTERN_GIORNI)
    giorni_con_segnale_debole = {
        _giorno(e) for e in eventi
        if "ts" in e and e["tipo"] == "registra_segnale_debole" and soglia <= _giorno(e) <= oggi
    }
    if len(giorni_con_segnale_debole) >= SOGLIA_SEGNALI_DEBOLI:
        return {
            "pattern_rilevato": True,
            "giorni_con_segnale": sorted(g.isoformat() for g in giorni_con_segnale_debole),
            "messaggio": f"{len(giorni_con_segnale_debole)} segnali deboli negli ultimi {FINESTRA_PATTERN_GIORNI} giorni: vale la pena una chiamata in più.",
        }
    return {"pattern_rilevato": False}


def report_settimanale(eventi=None, oggi=None):
    eventi = eventi if eventi is not None else leggi_eventi()
    oggi = oggi or datetime.date.today()
    per_giorno = eventi_per_giorno(eventi)
    giorni_settimana = [oggi - datetime.timedelta(days=i) for i in range(6, -1, -1)]
    righe = []
    ok = 0
    for g in giorni_settimana:
        stato, motivo = classifica_giorno(per_giorno.get(g, []))
        if stato == "verde":
            ok += 1
        righe.append({"data": g.isoformat(), "stato": stato, "motivo": motivo})
    pattern = rileva_pattern(eventi, oggi)
    return {
        "settimana_dal": giorni_settimana[0].isoformat(),
        "settimana_al": giorni_settimana[-1].isoformat(),
        "giorni_ok": ok,
        "giorni_totali": len(giorni_settimana),
        "dettaglio": righe,
        "pattern": pattern,
    }


def stampa_report(r):
    print(f"💌 REPORT SETTIMANALE — dal {r['settimana_dal']} al {r['settimana_al']}")
    print(f"   Ha risposto bene {r['giorni_ok']}/{r['giorni_totali']} giorni.")
    for g in r["dettaglio"]:
        icona = {"verde": "🟢", "giallo": "🟡", "rosso": "🔴", "grigio": "⚪"}[g["stato"]]
        print(f"   {icona} {g['data']} — {g['motivo']}")
    if r["pattern"]["pattern_rilevato"]:
        print(f"   ⚠️ {r['pattern']['messaggio']}")


def demo():
    """Genera uno storico REALE (non a caso come checkin_simulator.py):
    usa davvero server.js con FLOW=filodiretto.json per 7 chiamate, così
    questo script analizza dati prodotti dal motore vero — poi ritocca
    solo i timestamp per farli ricadere nei 7 giorni scorsi, senza dover
    aspettare una settimana reale per mostrare il rilevamento pattern."""
    import subprocess
    import tempfile

    p1 = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "01-voice-receptionist")
    flow_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "flows", "filodiretto.json")
    oggi = datetime.date.today()
    # 3 giornate con segnale debole nella finestra di 7 giorni: deve far
    # scattare il rilevamento pattern, esattamente come da MVP-SPEC.md.
    battute = [
        "sono un po' stanca oggi",
        "tutto bene grazie",
        "ho dormito male e sono un po' giù",
        "tutto bene",
        "un po' sola oggi, mio figlio non chiama",
        "bene bene",
        "sto bene, grazie di aver chiamato",
    ]
    with tempfile.TemporaryDirectory() as tmp:
        log_path = os.path.join(tmp, "eventi-demo-filodiretto.jsonl")
        for delta, battuta in enumerate(battute):
            script = f"""
const {{ nuovaSessione, ricevi, avanza }} = require('{p1}/server.js');
const s = nuovaSessione();
avanza(s, []);
ricevi(s, {json.dumps(battuta)});
ricevi(s, 'si, appena finiamo');
ricevi(s, 'tutto tranquillo qui');
"""
            env = dict(os.environ, FLOW=flow_path, EVENTI_LOG=log_path)
            subprocess.run(["node", "-e", script], cwd=p1, env=env, capture_output=True, text=True, timeout=15)

        eventi = leggi_eventi(log_path)
        # Ogni chiamata genera 4 eventi (chiamata_iniziata, l'azione del
        # flusso, chiamata_conclusa, e talvolta un evento di transizione):
        # li raggruppiamo per sessione (session_id) per assegnare l'intero
        # gruppo allo stesso giorno simulato, in ordine cronologico.
        sessioni_ordinate = []
        for e in eventi:
            sid = e.get("session_id")
            if sid not in sessioni_ordinate:
                sessioni_ordinate.append(sid)
        giorno_per_sessione = {
            sid: oggi - datetime.timedelta(days=len(sessioni_ordinate) - 1 - i)
            for i, sid in enumerate(sessioni_ordinate)
        }
        for e in eventi:
            giorno_target = giorno_per_sessione[e.get("session_id")]
            e["ts"] = int(datetime.datetime.combine(giorno_target, datetime.time(10, 0)).timestamp() * 1000)

    stampa_report(report_settimanale(eventi, oggi))
    print()
    print("Stato di oggi:", json.dumps(stato_di_oggi([e for e in eventi if _giorno(e) == oggi]), ensure_ascii=False))


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        stampa_report(report_settimanale())
        print()
        print("Stato di oggi:", json.dumps(stato_di_oggi(), ensure_ascii=False))
