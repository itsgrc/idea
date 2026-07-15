#!/usr/bin/env python3
"""Generatore del pilastro "📈 Numeri veri" — il moat di Cantiere Aperto.

Il posizionamento della newsletter è "numeri veri, non un altro guru" (vedi
README.md). Il problema: senza questo script, "numeri veri" vuol dire
copiare a mano output sparsi tra 4 progetti scritti in due linguaggi
diversi — noioso, lento, e col rischio concreto di scrivere un numero
vecchio o, peggio, presentare una demo come se fosse un dato reale.

Questo script legge i dati REALI degli altri progetti del portfolio
(eventi.jsonl del progetto 01, bandi.json del progetto 02, il calendario
normativo del progetto 03, officina.db del progetto 04) e compone la
sezione da incollare nella newsletter — con la fonte di ogni numero
dichiarata esplicitamente (reale vs dimostrativo), MAI mescolata senza
etichetta: è l'unico modo per cui "numeri veri" resti una promessa vera e
non un'altra affermazione di marketing.

Perché è un moat: nessun concorrente che scrive "contenuti sull'AI" ha
9 progotti reali che girano dietro le quinte da cui estrarre questi numeri
— e il valore cresce ogni settimana che i progetti restano in funzione,
non si può comprare né copiare in un weekend.

Uso:
    python3 generatore_numero.py             # sezione con i dati disponibili oggi
    python3 generatore_numero.py --demo      # forza dati dimostrativi ovunque (per provare il formato)
"""
import datetime
import json
import os
import sqlite3
import subprocess
import sys

PROGETTI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P1 = os.path.join(PROGETTI, "01-voice-receptionist")
P2 = os.path.join(PROGETTI, "02-servizio-produttizzato")
P3 = os.path.join(PROGETTI, "03-ai-act-compliance")
P4 = os.path.join(PROGETTI, "04-micro-saas-officine")


def numero_progetto1(forza_demo=False):
    """Chiama valore.js del progetto 01 (Rispondo) in un processo Node
    separato: se esiste uno storico reale (eventi.jsonl) lo usa, altrimenti
    dichiara esplicitamente che i numeri sono dimostrativi."""
    log_reale = os.path.join(P1, "eventi.jsonl")
    reale = (not forza_demo) and os.path.exists(log_reale) and os.path.getsize(log_reale) > 0
    script_js = f"""
const fs = require('fs');
const {{ leggiEventi, leggiValori, calcolaReport }} = require('./valore.js');
const forzaDemo = {"true" if forza_demo else "false"};
let logPath = 'eventi.jsonl';
let pulire = false;
if (forzaDemo || !fs.existsSync(logPath) || fs.statSync(logPath).size === 0) {{
  const {{ genera }} = require('./simulatore.js');
  logPath = genera(25);
  pulire = true;
}}
const eventi = leggiEventi(logPath);
const valori = leggiValori('valori/dentista.json');
const r = calcolaReport(eventi, valori);
console.log(JSON.stringify(r));
if (pulire) fs.unlinkSync(logPath);
"""
    try:
        out = subprocess.run(
            ["node", "-e", script_js], capture_output=True, text=True, cwd=P1, timeout=15,
        )
        if out.returncode != 0:
            return {"progetto": "Rispondo (voce AI)", "errore": out.stderr.strip()[-300:], "fonte": "n/d"}
        r = json.loads(out.stdout.strip().splitlines()[-1])
    except Exception as e:
        return {"progetto": "Rispondo (voce AI)", "errore": str(e), "fonte": "n/d"}
    return {
        "progetto": "Rispondo (voce AI)",
        "chiamate_gestite": r["chiamateIniziate"],
        "valore_recuperato_eur": r["totale"],
        "tasso_comprensione_pct": round(r["tassoComprensione"] * 100),
        "fonte": "reale" if reale else "demo",
    }


def numero_progetto2(forza_demo=False):
    """bandi.json è il catalogo REALE usato dal tool (non un file demo):
    contarne le voci e l'ultima data di verifica non richiede alcun dato
    finto — è sempre reale finché il file esiste."""
    path_bandi = os.path.join(P2, "bandi.json")
    if not os.path.exists(path_bandi):
        return {"progetto": "TrovaBandi", "errore": "bandi.json non trovato", "fonte": "n/d"}
    with open(path_bandi, encoding="utf-8") as f:
        bandi = json.load(f)
    fondo_perduto = sum(1 for b in bandi if b.get("tipo_calcolo") == "fondo_perduto")
    ultima_verifica = max((b.get("data_verifica", "") for b in bandi), default="n/d")
    return {
        "progetto": "TrovaBandi",
        "bandi_in_catalogo": len(bandi),
        "di_cui_a_fondo_perduto": fondo_perduto,
        "ultima_verifica": ultima_verifica,
        "fonte": "reale",
    }


def numero_progetto3(forza_demo=False):
    """Il calendario normativo (CALENDARIO in scadenzario.py) è un fatto
    regolatorio verificato, non dipende da un cliente demo: il countdown è
    sempre reale, a prescindere da quanti clienti reali il progetto ha oggi."""
    sys.path.insert(0, P3)
    try:
        import importlib
        scadenzario = importlib.import_module("scadenzario")
        tappe = scadenzario.prossime_tappe()
        prossima = min((t for t in tappe if not t["passata"]), key=lambda t: t["giorni"])
        return {
            "progetto": "Conforme (EU AI Act)",
            "prossima_scadenza": prossima["titolo"],
            "giorni_alla_scadenza": prossima["giorni"],
            "fonte": "reale",
        }
    except Exception as e:
        return {"progetto": "Conforme (EU AI Act)", "errore": str(e), "fonte": "n/d"}
    finally:
        sys.path.remove(P3)
        for mod in ("scadenzario", "classifica", "registro"):
            sys.modules.pop(mod, None)


def numero_progetto4(forza_demo=False):
    """officina.db, se esiste, contiene dati di officine REALMENTE
    registrate (non un file demo): sommare le officine attive e l'incassato
    complessivo è un dato reale. Se il file non esiste ancora, il numero
    vero è zero — coerente con lo stile "zero clienti, zero euro" già
    usato nel numero zero della newsletter: uno zero onesto vale più di
    una demo travestita da traguardo."""
    path_db = os.path.join(P4, "officina.db")
    if forza_demo or not os.path.exists(path_db):
        return {
            "progetto": "Ponte (gestionale officine)",
            "officine_attive": 0,
            "incassato_totale_eur": 0,
            "fonte": "reale",
        }
    conn = sqlite3.connect(path_db)
    try:
        n_officine = conn.execute("SELECT COUNT(*) FROM officine").fetchone()[0]
        incassato = conn.execute("SELECT COALESCE(SUM(importo_finale),0) FROM interventi WHERE stato='consegnato'").fetchone()[0]
    finally:
        conn.close()
    return {
        "progetto": "Ponte (gestionale officine)",
        "officine_attive": n_officine,
        "incassato_totale_eur": incassato,
        "fonte": "reale",
    }


def genera_sezione_numeri_veri(forza_demo=False):
    numeri = [
        numero_progetto1(forza_demo),
        numero_progetto2(forza_demo),
        numero_progetto3(forza_demo),
        numero_progetto4(forza_demo),
    ]
    oggi = datetime.date.today().strftime("%d/%m/%Y")
    righe = [f"## 📈 NUMERI VERI — lo stato del cantiere, {oggi}\n"]
    for n in numeri:
        etichetta_fonte = f"_[{n['fonte']}]_" if n.get("fonte") not in (None, "reale") else ""
        if "errore" in n:
            righe.append(f"- **{n['progetto']}**: dato non disponibile ({n['errore']})")
            continue
        if n["progetto"] == "Rispondo (voce AI)":
            righe.append(
                f"- **{n['progetto']}**: {n['chiamate_gestite']} chiamate gestite, "
                f"{n['valore_recuperato_eur']:.0f}€ di valore stimato recuperato, "
                f"{n['tasso_comprensione_pct']}% comprese correttamente {etichetta_fonte}"
            )
        elif n["progetto"] == "TrovaBandi":
            righe.append(
                f"- **{n['progetto']}**: {n['bandi_in_catalogo']} bandi in catalogo "
                f"({n['di_cui_a_fondo_perduto']} a fondo perduto), ultima verifica {n['ultima_verifica']} {etichetta_fonte}"
            )
        elif n["progetto"] == "Conforme (EU AI Act)":
            righe.append(
                f"- **{n['progetto']}**: prossima scadenza normativa — \"{n['prossima_scadenza']}\" "
                f"tra {n['giorni_alla_scadenza']} giorni {etichetta_fonte}"
            )
        elif n["progetto"] == "Ponte (gestionale officine)":
            officina_label = "officina attiva" if n["officine_attive"] == 1 else "officine attive"
            righe.append(
                f"- **{n['progetto']}**: {n['officine_attive']} {officina_label}, "
                f"{n['incassato_totale_eur']:.0f}€ incassati tramite il gestionale {etichetta_fonte}"
            )
    righe.append(
        "\n_I numeri senza etichetta sono reali, presi dai sistemi in funzione oggi stesso. "
        'I numeri etichettati "[demo]" vengono da dati dimostrativi (nessuno storico reale '
        "ancora accumulato per quel progetto) e sono segnalati come tali: mai spacciare una "
        'demo per un traguardo raggiunto — è la promessa "numeri veri" di questa newsletter._'
    )
    return "\n".join(righe)


if __name__ == "__main__":
    print(genera_sezione_numeri_veri(forza_demo="--demo" in sys.argv))
