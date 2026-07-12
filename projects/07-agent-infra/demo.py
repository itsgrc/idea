#!/usr/bin/env python3
"""Demo: un finto agente (receptionist telefonico) strumentato con AgentLens.

Esegue 5 "telefonate" simulate e stampa il report. Fa vedere in 10 secondi
cosa compra il cliente: visibilità totale su cosa fa l'agente e quanto costa.

Uso: python3 demo.py
"""
import os
import random
import time

from agentlens import Trace, report

TRACCE = "tracce.jsonl"
rng = random.Random(42)

if os.path.exists(TRACCE):
    os.remove(TRACCE)

print("📞 Simulo 5 telefonate gestite dall'agente receptionist...\n")

for chiamata in range(5):
    with Trace("receptionist-dentista", file=TRACCE, cliente="Studio Demo") as t:
        # Trascrizione vocale
        with t.step("stt", provider="voce-eu") as s:
            time.sleep(rng.uniform(0.01, 0.04))
            s.done(secondi_audio=rng.randint(20, 90))

        # 2-4 turni di conversazione con l'LLM
        for turno in range(rng.randint(2, 4)):
            with t.step("llm", model="claude", prompt_version="v3") as s:
                time.sleep(rng.uniform(0.02, 0.08))
                s.done(tokens_in=rng.randint(400, 1500), tokens_out=rng.randint(50, 300),
                       cost_eur=round(rng.uniform(0.002, 0.015), 4))

        # Chiamata al tool calendario (nell'ultima chiamata simuliamo un errore)
        try:
            with t.step("tool", name="calendario.crea_appuntamento") as s:
                time.sleep(rng.uniform(0.01, 0.05))
                if chiamata == 4:
                    raise TimeoutError("API calendario non risponde")
                s.done(esito="appuntamento_creato")
        except TimeoutError:
            t.event("fallback", azione="presa nota manuale, notifica al titolare")

print("Fatto. Ecco il report che vede il cliente:\n")
report(TRACCE)
print("Le tracce grezze sono in tracce.jsonl — una riga JSON per ogni step,")
print("pronte per la dashboard hosted (il prodotto a pagamento).")
