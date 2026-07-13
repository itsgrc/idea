#!/usr/bin/env python3
"""AgentLens — dashboard HTML delle tracce (anteprima del prodotto cloud).

Trasforma un file JSONL di tracce in una dashboard HTML autonoma: KPI,
tabella per step, waterfall di ogni esecuzione. È l'anteprima statica di
ciò che il piano Team offre hosted — e un ottimo strumento di vendita:
si genera dal vivo davanti al cliente con le SUE tracce.

Uso:
    python3 demo.py                       # genera tracce.jsonl
    python3 dashboard.py tracce.jsonl     # → dashboard.html
"""
import html
import json
import sys
from collections import defaultdict

COLORI = {"llm": "#A78BFA", "stt": "#7EE787", "tool": "#E3B341", "fallback": "#F47067"}


def percentile(v, p):
    if not v:
        return 0
    v = sorted(v)
    return v[min(len(v) - 1, int(len(v) * p / 100))]


def carica(path):
    tracce = defaultdict(list)
    for riga in open(path):
        if riga.strip():
            r = json.loads(riga)
            tracce[r["trace_id"]].append(r)
    return tracce


def genera(path):
    tracce = carica(path)
    per_kind = defaultdict(lambda: {"n": 0, "ms": [], "err": 0, "cost": 0.0})
    ok = 0
    for rs in tracce.values():
        for r in rs:
            k = per_kind[r["kind"]]
            k["n"] += 1
            k["ms"].append(r.get("duration_ms", 0))
            k["err"] += 1 if "error" in r else 0
            k["cost"] += r.get("cost_eur", 0)
            if r["kind"] == "trace_end" and r.get("ok"):
                ok += 1
    costo_tot = sum(k["cost"] for k in per_kind.values())
    errori_tot = sum(k["err"] for k in per_kind.values())

    kpi = f"""
    <div class="kpis">
      <div class="kpi"><b>{len(tracce)}</b><span>esecuzioni</span></div>
      <div class="kpi"><b>{ok}/{len(tracce)}</b><span>riuscite</span></div>
      <div class="kpi"><b>{costo_tot:.4f} €</b><span>costo totale</span></div>
      <div class="kpi"><b>{(costo_tot / max(len(tracce), 1)):.4f} €</b><span>costo / esecuzione</span></div>
      <div class="kpi {'warn' if errori_tot else ''}"><b>{errori_tot}</b><span>errori</span></div>
    </div>"""

    righe = ""
    for kind, k in sorted(per_kind.items(), key=lambda kv: -sum(kv[1]["ms"])):
        if kind in ("trace_start", "trace_end"):
            continue
        colore = COLORI.get(kind, "#7D8A9C")
        righe += f"""<tr><td><i style="background:{colore}"></i>{html.escape(kind)}</td>
        <td class="n">{k['n']}</td><td class="n">{percentile(k['ms'],50):.0f}</td>
        <td class="n">{percentile(k['ms'],95):.0f}</td>
        <td class="n {'err' if k['err'] else ''}">{k['err']}</td><td class="n">{k['cost']:.4f}</td></tr>"""

    waterfalls = ""
    for tid, rs in list(tracce.items()):
        steps = [r for r in rs if r["kind"] not in ("trace_start", "trace_end")]
        fine = next((r for r in rs if r["kind"] == "trace_end"), {})
        tot = max(sum(s.get("duration_ms", 0) for s in steps), 1)
        barre = ""
        for s in steps:
            w = max(s.get("duration_ms", 0) / tot * 100, 1.2)
            colore = COLORI.get(s["kind"], "#7D8A9C")
            err = "outline:2px solid #F47067;" if "error" in s else ""
            titolo = html.escape(f"{s['kind']} · {s.get('duration_ms',0):.0f} ms" + (f" · ERRORE: {s['error']}" if "error" in s else ""))
            barre += f'<i style="width:{w:.1f}%;background:{colore};{err}" title="{titolo}"></i>'
        stato = "✅" if fine.get("ok") else "❌"
        waterfalls += f"""<div class="tr"><span class="tid">{stato} {html.escape(tid)}</span>
        <div class="wf">{barre}</div><span class="tms">{fine.get('total_ms','—')} ms</span></div>"""

    legenda = " ".join(f'<span><i style="background:{c}"></i>{k}</span>' for k, c in COLORI.items())

    return f"""<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AgentLens — dashboard</title><style>
:root{{--bg:#0B0E14;--panel:#12161F;--ink:#C7D2E0;--bright:#EDF2F8;--muted:#7D8A9C;--line:#232B3A;--green:#7EE787;--red:#F47067}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:ui-monospace,Menlo,Consolas,monospace;font-size:14px;line-height:1.6}}
.wrap{{max-width:900px;margin:0 auto;padding:28px 20px}}
h1{{font-family:system-ui,sans-serif;font-size:22px;color:var(--bright);margin:0 0 4px}}
.sub{{color:var(--muted);font-size:12.5px;margin:0 0 22px}}
.kpis{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-bottom:24px}}
.kpi{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}}
.kpi b{{display:block;font-size:20px;color:var(--green)}}.kpi.warn b{{color:var(--red)}}
.kpi span{{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.08em}}
table{{border-collapse:collapse;width:100%;background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden;margin-bottom:26px}}
th,td{{padding:9px 12px;border-bottom:1px solid var(--line);text-align:left}}
th{{font-size:10.5px;text-transform:uppercase;letter-spacing:.1em;color:var(--muted)}}
td.n{{text-align:right;font-variant-numeric:tabular-nums}}td.err{{color:var(--red);font-weight:700}}
td i{{display:inline-block;width:9px;height:9px;border-radius:2px;margin-right:8px}}
h2{{font-family:system-ui,sans-serif;font-size:15px;color:var(--bright);margin:0 0 4px}}
.leg{{font-size:11.5px;color:var(--muted);margin:0 0 14px}}.leg i{{display:inline-block;width:9px;height:9px;border-radius:2px;margin:0 5px 0 12px}}
.tr{{display:grid;grid-template-columns:150px 1fr 70px;gap:12px;align-items:center;margin-bottom:8px}}
.tid{{font-size:12px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.wf{{display:flex;gap:2px;height:18px;background:var(--panel);border:1px solid var(--line);border-radius:5px;padding:2px}}
.wf i{{border-radius:3px;min-width:3px}}
.tms{{font-size:11.5px;color:var(--muted);text-align:right;font-variant-numeric:tabular-nums}}
footer{{color:var(--muted);font-size:11px;margin-top:26px;border-top:1px solid var(--line);padding-top:12px}}
</style></head><body><div class="wrap">
<h1>🔍 AgentLens</h1><p class="sub">dashboard generata da <code>{html.escape(path)}</code> — anteprima statica del piano Team</p>
{kpi}
<table><tr><th>step</th><th style="text-align:right">n</th><th style="text-align:right">p50 ms</th><th style="text-align:right">p95 ms</th><th style="text-align:right">errori</th><th style="text-align:right">costo €</th></tr>{righe}</table>
<h2>Esecuzioni (waterfall)</h2><p class="leg">passa il mouse sulle barre per il dettaglio ·{legenda}</p>
{waterfalls}
<footer>AgentLens — tracer open source (MIT). I dati restano sul tuo disco: questa pagina è un singolo file HTML senza richieste esterne.</footer>
</div></body></html>"""


def main():
    if len(sys.argv) < 2:
        sys.exit("Uso: python3 dashboard.py tracce.jsonl [output.html]")
    out = sys.argv[2] if len(sys.argv) > 2 else "dashboard.html"
    with open(out, "w") as f:
        f.write(genera(sys.argv[1]))
    print(f"✅ Dashboard generata: {out}")


if __name__ == "__main__":
    main()
