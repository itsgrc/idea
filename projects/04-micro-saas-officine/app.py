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


WEB_HTML = """<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ponte — Lavagna officina</title><style>
:root{--bg:#F4F4F2;--card:#fff;--ink:#1B1D1F;--muted:#5C6166;--line:#DCDDDA;--y:#F5B301;--dark:#232629}
@media(prefers-color-scheme:dark){:root{--bg:#151719;--card:#1E2124;--ink:#EAEBEC;--muted:#9CA1A7;--line:#33373B}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,sans-serif;line-height:1.5}
header{background:var(--dark);color:#F2F3F4;padding:14px 18px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px}
header b{text-transform:uppercase;letter-spacing:.04em}header b i{color:var(--y);font-style:normal}
#riep{font-family:ui-monospace,Menlo,monospace;font-size:12.5px;color:#C9CCCF}
main{max-width:760px;margin:0 auto;padding:16px}
form{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px;display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:16px}
form h3{grid-column:1/-1;margin:0 0 2px;font-size:13px;text-transform:uppercase;letter-spacing:.06em}
input{padding:10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);font-size:15px}
input.full{grid-column:1/-1}
button{grid-column:1/-1;background:var(--y);border:0;border-radius:8px;padding:12px;font-weight:800;font-size:15px;text-transform:uppercase;cursor:pointer;color:#1B1D1F}
.job{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;margin-bottom:10px;display:grid;grid-template-columns:auto 1fr auto;gap:10px;align-items:center}
.plate{font-family:ui-monospace,Menlo,monospace;background:var(--ink);color:var(--bg);border-radius:4px;padding:3px 8px;font-weight:700;font-size:13px}
.job .d{font-size:14px}.job .d small{display:block;color:var(--muted);font-size:12.5px}
.job select{padding:8px;border-radius:8px;border:1px solid var(--line);background:var(--bg);color:var(--ink);font-weight:700;font-size:13px}
.s-accettato{border-left:5px solid #8A8F94}.s-in_lavorazione{border-left:5px solid var(--y)}
.s-pronto{border-left:5px solid #3E7A4E}.s-consegnato{opacity:.55;border-left:5px solid #3E7A4E}
</style></head><body>
<header><b>🔧 <i>PONTE</i> — lavagna officina</b><span id="riep"></span></header>
<main>
<form id="nuovo"><h3>➕ Nuova accettazione (30 secondi)</h3>
<input id="nome" placeholder="Cliente" required><input id="tel" placeholder="Telefono" required>
<input id="targa" placeholder="Targa" required><input id="modello" placeholder="Modello" required>
<input id="descr" class="full" placeholder="Lavoro da fare" required>
<input id="prev" class="full" placeholder="Preventivo €" type="number" step="1" required>
<button>Accetta veicolo</button></form>
<div id="lista"></div>
</main>
<script>
const STATI=["accettato","in_lavorazione","pronto","consegnato"];
async function carica(){
  const jobs=await (await fetch('/interventi')).json();
  const r=await (await fetch('/riepilogo')).json();
  document.getElementById('riep').textContent=
    `in officina: ${jobs.filter(j=>j.stato!=='consegnato').length} · valore: ${r.valore_in_officina}€ · incassato: ${r.incassato}€`;
  const el=document.getElementById('lista');el.innerHTML='';
  jobs.sort((a,b)=>STATI.indexOf(a.stato)-STATI.indexOf(b.stato));
  for(const j of jobs){
    const d=document.createElement('div');d.className='job s-'+j.stato;
    d.innerHTML=`<span class="plate">${j.targa}</span>
      <span class="d">${j.modello} — ${j.descrizione}<small>${j.cliente} · ${j.telefono} · prev. ${j.preventivo}€</small></span>`;
    const sel=document.createElement('select');
    for(const s of STATI){const o=document.createElement('option');o.value=s;o.textContent=s.replace('_',' ');if(s===j.stato)o.selected=true;sel.appendChild(o)}
    sel.onchange=async()=>{await fetch('/interventi/'+j.id,{method:'PATCH',body:JSON.stringify({stato:sel.value})});carica()};
    d.appendChild(sel);el.appendChild(d);
  }
}
document.getElementById('nuovo').addEventListener('submit',async e=>{
  e.preventDefault();const g=id=>document.getElementById(id).value;
  const c=await (await fetch('/clienti',{method:'POST',body:JSON.stringify({nome:g('nome'),telefono:g('tel')})})).json();
  const v=await (await fetch('/veicoli',{method:'POST',body:JSON.stringify({cliente_id:c.id,targa:g('targa'),modello:g('modello')})})).json();
  await fetch('/interventi',{method:'POST',body:JSON.stringify({veicolo_id:v.id,descrizione:g('descr'),preventivo:+g('prev')})});
  e.target.reset();carica();
});
carica();
</script></body></html>"""


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
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(WEB_HTML.encode())
            return
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
