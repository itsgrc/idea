#!/usr/bin/env python3
"""Gestionale officina — spina dorsale MVP (zero dipendenze).

API REST minimale su http.server + sqlite3. Copre il flusso quotidiano:
cliente → veicolo → intervento con stati (accettato → in_lavorazione →
pronto → consegnato), preventivo e importo finale.

Uso:
    python3 app.py --selftest   # crea db temporaneo, esegue il flusso, verifica
    python3 app.py              # API su :8000 (db: officina.db)

Endpoints:
    POST /clienti        {nome, telefono}
    POST /veicoli        {cliente_id, targa, modello}
    POST /interventi     {veicolo_id, descrizione, preventivo}
    PATCH /interventi/<id>  {stato} | {importo_finale}
    GET  /interventi?stato=pronto
    GET  /riepilogo      # il numero che il titolare guarda la sera
"""
import json
import os
import re
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

DB = os.environ.get("OFFICINA_DB", "officina.db")
STATI = ["accettato", "in_lavorazione", "pronto", "consegnato"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS clienti (
    id INTEGER PRIMARY KEY, nome TEXT NOT NULL, telefono TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS veicoli (
    id INTEGER PRIMARY KEY, cliente_id INTEGER NOT NULL REFERENCES clienti(id),
    targa TEXT NOT NULL UNIQUE, modello TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS interventi (
    id INTEGER PRIMARY KEY, veicolo_id INTEGER NOT NULL REFERENCES veicoli(id),
    descrizione TEXT NOT NULL, stato TEXT NOT NULL DEFAULT 'accettato',
    preventivo REAL, importo_finale REAL,
    creato TEXT DEFAULT CURRENT_TIMESTAMP, aggiornato TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def crea(tabella, campi, dati):
    mancanti = [c for c in campi if c not in dati]
    if mancanti:
        raise ValueError(f"campi mancanti: {', '.join(mancanti)}")
    with db() as conn:
        cur = conn.execute(
            f"INSERT INTO {tabella} ({','.join(campi)}) VALUES ({','.join('?' * len(campi))})",
            [dati[c] for c in campi],
        )
        riga = conn.execute(f"SELECT * FROM {tabella} WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(riga)


def aggiorna_intervento(iid, dati):
    consentiti = {}
    if "stato" in dati:
        if dati["stato"] not in STATI:
            raise ValueError(f"stato non valido, usa uno di: {STATI}")
        consentiti["stato"] = dati["stato"]
    if "importo_finale" in dati:
        consentiti["importo_finale"] = float(dati["importo_finale"])
    if not consentiti:
        raise ValueError("niente da aggiornare (stato o importo_finale)")
    with db() as conn:
        set_sql = ", ".join(f"{k}=?" for k in consentiti) + ", aggiornato=CURRENT_TIMESTAMP"
        conn.execute(f"UPDATE interventi SET {set_sql} WHERE id=?", [*consentiti.values(), iid])
        riga = conn.execute("SELECT * FROM interventi WHERE id=?", (iid,)).fetchone()
        if not riga:
            raise LookupError("intervento non trovato")
        # Gancio v1: quando lo stato diventa "pronto" qui parte l'SMS al cliente.
        return dict(riga)


def lista_interventi(stato=None):
    q = """SELECT i.*, v.targa, v.modello, c.nome AS cliente, c.telefono
           FROM interventi i JOIN veicoli v ON v.id=i.veicolo_id
           JOIN clienti c ON c.id=v.cliente_id"""
    args = []
    if stato:
        q += " WHERE i.stato=?"
        args.append(stato)
    with db() as conn:
        return [dict(r) for r in conn.execute(q + " ORDER BY i.creato", args)]


def riepilogo():
    with db() as conn:
        per_stato = {s: conn.execute("SELECT COUNT(*) FROM interventi WHERE stato=?", (s,)).fetchone()[0] for s in STATI}
        incassato = conn.execute("SELECT COALESCE(SUM(importo_finale),0) FROM interventi WHERE stato='consegnato'").fetchone()[0]
        in_corso = conn.execute("SELECT COALESCE(SUM(preventivo),0) FROM interventi WHERE stato!='consegnato'").fetchone()[0]
    return {"per_stato": per_stato, "incassato": incassato, "valore_in_officina": in_corso}


class Handler(BaseHTTPRequestHandler):
    def _json(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body, ensure_ascii=False).encode())

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_POST(self):
        try:
            if self.path == "/clienti":
                return self._json(201, crea("clienti", ["nome", "telefono"], self._body()))
            if self.path == "/veicoli":
                return self._json(201, crea("veicoli", ["cliente_id", "targa", "modello"], self._body()))
            if self.path == "/interventi":
                return self._json(201, crea("interventi", ["veicolo_id", "descrizione", "preventivo"], self._body()))
            self._json(404, {"errore": "endpoint sconosciuto"})
        except Exception as e:
            self._json(400, {"errore": str(e)})

    def do_PATCH(self):
        m = re.match(r"^/interventi/(\d+)$", self.path)
        if not m:
            return self._json(404, {"errore": "endpoint sconosciuto"})
        try:
            self._json(200, aggiorna_intervento(int(m.group(1)), self._body()))
        except LookupError as e:
            self._json(404, {"errore": str(e)})
        except Exception as e:
            self._json(400, {"errore": str(e)})

    def do_GET(self):
        if self.path.startswith("/interventi"):
            stato = None
            if "stato=" in self.path:
                stato = self.path.split("stato=")[1].split("&")[0]
            return self._json(200, lista_interventi(stato))
        if self.path == "/riepilogo":
            return self._json(200, riepilogo())
        self._json(404, {"errore": "endpoint sconosciuto"})

    def log_message(self, fmt, *args):
        print(f"  {self.command} {self.path}")


def selftest():
    global DB
    DB = "officina_test.db"
    if os.path.exists(DB):
        os.remove(DB)
    c = crea("clienti", ["nome", "telefono"], {"nome": "Luca Bianchi", "telefono": "333 1234567"})
    v = crea("veicoli", ["cliente_id", "targa", "modello"], {"cliente_id": c["id"], "targa": "AB123CD", "modello": "Panda 1.2"})
    i = crea("interventi", ["veicolo_id", "descrizione", "preventivo"], {"veicolo_id": v["id"], "descrizione": "Tagliando + pastiglie", "preventivo": 280})
    for stato in ["in_lavorazione", "pronto"]:
        aggiorna_intervento(i["id"], {"stato": stato})
    aggiorna_intervento(i["id"], {"stato": "consegnato", "importo_finale": 295})
    r = riepilogo()
    pronti = lista_interventi("consegnato")
    assert r["incassato"] == 295, r
    assert pronti[0]["cliente"] == "Luca Bianchi", pronti
    print("Flusso: accettazione → lavorazione → pronto → consegna ✅")
    print(f"Riepilogo serale: {json.dumps(r, ensure_ascii=False)}")
    os.remove(DB)
    print("✅ SELFTEST OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    else:
        print(f"🔧 Gestionale officina su :8000 (db: {DB})")
        HTTPServer(("", 8000), Handler).serve_forever()
