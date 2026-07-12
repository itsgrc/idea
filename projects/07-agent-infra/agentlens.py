#!/usr/bin/env python3
"""AgentLens — scatola nera per agenti AI (v0, zero dipendenze, un file).

Registra ogni step di un agente (chiamate LLM, tool, decisioni, errori) su
JSONL e produce il report che risponde a: perché ha fatto così? quanto è
costato? dove rallenta? In Europa questi log sono anche un obbligo di legge
per i sistemi ad alto rischio (EU AI Act, Art. 12).

Uso come libreria:
    from agentlens import Trace
    with Trace("nome-agente", file="tracce.jsonl") as t:
        with t.step("llm", model="claude-x", prompt_version="v3") as s:
            ...
            s.done(tokens_in=1200, tokens_out=300, cost_eur=0.011)

Uso come CLI:
    python3 agentlens.py report tracce.jsonl
"""
import json
import sys
import time
import uuid
from collections import defaultdict


class _Step:
    def __init__(self, trace, kind, **meta):
        self.trace = trace
        self.kind = kind
        self.meta = meta
        self.extra = {}
        self.error = None

    def done(self, **extra):
        self.extra.update(extra)

    def __enter__(self):
        self.t0 = time.time()
        return self

    def __exit__(self, exc_type, exc, tb):
        record = {
            "trace_id": self.trace.trace_id,
            "agent": self.trace.agent,
            "ts": self.t0,
            "kind": self.kind,
            "duration_ms": round((time.time() - self.t0) * 1000, 1),
            **self.meta,
            **self.extra,
        }
        if exc:
            record["error"] = f"{exc_type.__name__}: {exc}"
        self.trace._write(record)
        return False  # non inghiottire le eccezioni


class Trace:
    """Una traccia = una esecuzione dell'agente (es. una telefonata gestita)."""

    def __init__(self, agent, file="tracce.jsonl", **meta):
        self.agent = agent
        self.file = file
        self.trace_id = str(uuid.uuid4())[:8]
        self.meta = meta

    def _write(self, record):
        with open(self.file, "a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def step(self, kind, **meta):
        return _Step(self, kind, **meta)

    def event(self, kind, **data):
        self._write({"trace_id": self.trace_id, "agent": self.agent, "ts": time.time(), "kind": kind, "duration_ms": 0, **data})

    def __enter__(self):
        self.t0 = time.time()
        self.event("trace_start", **self.meta)
        return self

    def __exit__(self, exc_type, exc, tb):
        self.event("trace_end", total_ms=round((time.time() - self.t0) * 1000, 1), ok=exc is None)
        return False


# ------------------------------------------------------------------ report
def _percentile(valori, p):
    if not valori:
        return 0
    valori = sorted(valori)
    idx = min(len(valori) - 1, int(len(valori) * p / 100))
    return valori[idx]


def report(path):
    records = [json.loads(r) for r in open(path) if r.strip()]
    if not records:
        print("Nessuna traccia trovata.")
        return

    tracce = defaultdict(list)
    for r in records:
        tracce[r["trace_id"]].append(r)

    per_kind = defaultdict(lambda: {"n": 0, "ms": [], "err": 0, "cost": 0.0})
    esiti_ok = 0
    for tid, rs in tracce.items():
        for r in rs:
            k = per_kind[r["kind"]]
            k["n"] += 1
            k["ms"].append(r.get("duration_ms", 0))
            k["err"] += 1 if "error" in r else 0
            k["cost"] += r.get("cost_eur", 0)
            if r["kind"] == "trace_end" and r.get("ok"):
                esiti_ok += 1

    costo_tot = sum(k["cost"] for k in per_kind.values())
    print(f"\n🔍 AgentLens — report su {path}")
    print(f"{'═' * 66}")
    print(f"Esecuzioni: {len(tracce)}   riuscite: {esiti_ok}/{len(tracce)}   costo totale: {costo_tot:.4f} €")
    print(f"Costo medio per esecuzione: {costo_tot / max(len(tracce), 1):.4f} €")
    print(f"\n{'step':<16}{'n':>5}{'p50 ms':>10}{'p95 ms':>10}{'errori':>8}{'costo €':>10}")
    print("─" * 66)
    for kind, k in sorted(per_kind.items(), key=lambda kv: -sum(kv[1]['ms'])):
        if kind in ("trace_start",):
            continue
        print(f"{kind:<16}{k['n']:>5}{_percentile(k['ms'], 50):>10.0f}{_percentile(k['ms'], 95):>10.0f}{k['err']:>8}{k['cost']:>10.4f}")
    print(f"{'═' * 66}")
    print("💡 Ogni riga con errori > 0 è un ticket di supporto evitato se lo vedi prima tu.\n")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "report":
        report(sys.argv[2])
    else:
        print(__doc__)
