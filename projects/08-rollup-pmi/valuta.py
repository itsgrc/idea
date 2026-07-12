#!/usr/bin/env python3
"""Calcolatore di acquisizione PMI — struttura, sostenibilità, ROI.

Dato il conto economico dell'azienda target, calcola: prezzo ai multipli di
mercato, struttura dell'operazione (equity/debito/earn-out), sostenibilità
della rata sul flusso di cassa, ROI cash-on-cash e l'effetto dell'AI-fication
sui margini. Il numero finale è quello che decide: si fa o non si fa.

Uso:
    python3 valuta.py --esempio    # caso tipo: studio amministrazione condomini
    python3 valuta.py              # interattivo
"""
import sys

ESEMPIO = {
    "nome": "Studio Amministrazioni Alfa (60 condomini)",
    "fatturato": 320_000,
    "ebitda": 55_000,          # margine 17% — tipico studio analogico
    "multiplo": 3.0,           # 2-4x EBITDA per micro-aziende senza compratori
    "pct_equity": 25,          # % prezzo pagata cash
    "pct_debito": 50,          # % prezzo a debito bancario
    "pct_earnout": 25,         # % prezzo differita al venditore (2 anni)
    "tasso_debito": 6.5,       # % annuo
    "anni_debito": 5,
    "uplift_ai_punti": 12,     # punti di margine EBITDA guadagnati con l'AI in 18 mesi
}


def rata_annua(capitale, tasso_pct, anni):
    if capitale == 0:
        return 0
    i = tasso_pct / 100
    return capitale * i / (1 - (1 + i) ** -anni)


def analizza(d):
    prezzo = d["ebitda"] * d["multiplo"]
    equity = prezzo * d["pct_equity"] / 100
    debito = prezzo * d["pct_debito"] / 100
    earnout = prezzo * d["pct_earnout"] / 100
    rata = rata_annua(debito, d["tasso_debito"], d["anni_debito"])
    earnout_annuo = earnout / 2  # pagato in 2 anni

    ebitda_post_ai = d["fatturato"] * (d["ebitda"] / d["fatturato"] + d["uplift_ai_punti"] / 100)

    # DSCR = capacità dell'azienda di ripagare il debito con la propria cassa
    dscr_pre = d["ebitda"] / (rata + earnout_annuo) if (rata + earnout_annuo) else float("inf")
    dscr_post = ebitda_post_ai / (rata + earnout_annuo) if (rata + earnout_annuo) else float("inf")

    cassa_libera_post = ebitda_post_ai - rata - earnout_annuo
    roi_cash = cassa_libera_post / equity if equity else float("inf")

    valore_rivendita = ebitda_post_ai * (d["multiplo"] + 1)  # margini migliori = multiplo migliore

    print(f"""
{'═' * 64}
🏢 ANALISI ACQUISIZIONE — {d['nome']}
{'═' * 64}
Fatturato: {d['fatturato']:>12,.0f} €     EBITDA: {d['ebitda']:,.0f} € ({d['ebitda']/d['fatturato']:.0%})

PREZZO ({d['multiplo']}× EBITDA):          {prezzo:>12,.0f} €
  di cui equity (cash tuo):     {equity:>12,.0f} €  ({d['pct_equity']}%)
  di cui debito bancario:       {debito:>12,.0f} €  ({d['pct_debito']}%, {d['tasso_debito']}%, {d['anni_debito']} anni)
  di cui earn-out al venditore: {earnout:>12,.0f} €  ({d['pct_earnout']}%, in 2 anni)

SERVIZIO DEL DEBITO
  Rata bancaria annua:          {rata:>12,.0f} €
  Earn-out annuo (primi 2 aa):  {earnout_annuo:>12,.0f} €
  DSCR pre-AI:                  {dscr_pre:>12.2f}   {'✅ sostenibile' if dscr_pre >= 1.2 else '🚨 TROPPO STRETTO — rinegozia prezzo o struttura'}

EFFETTO AI-FICATION (+{d['uplift_ai_punti']} punti margine in 18 mesi)
  EBITDA post-AI:               {ebitda_post_ai:>12,.0f} €  ({ebitda_post_ai/d['fatturato']:.0%})
  DSCR post-AI:                 {dscr_post:>12.2f}
  Cassa libera annua (post):    {cassa_libera_post:>12,.0f} €

RITORNI
  ROI cash-on-cash:             {roi_cash:>12.0%} annuo sull'equity investita
  Payback dell'equity:          {equity / cassa_libera_post if cassa_libera_post > 0 else float('inf'):>12.1f} anni
  Valore rivendita stimato:     {valore_rivendita:>12,.0f} €  ({(d['multiplo']+1)}× su EBITDA migliorato)
{'═' * 64}
VERDETTO: {'🟢 SI FA — i numeri reggono anche senza uplift AI' if dscr_pre >= 1.2 else ('🟡 SOLO se confidi nell_uplift AI — margine di errore basso' if dscr_post >= 1.3 else '🔴 NON SI FA a questo prezzo')}
{'═' * 64}
Regola: mai comprare contando sull'AI per pagare i debiti. L'AI è
l'upside, il DSCR pre-AI ≥ 1.2 è il requisito.
""")


def chiedi(etichetta, default, tipo=float):
    v = input(f"{etichetta} [{default}]: ").strip()
    return tipo(v) if v else default


def main():
    if "--esempio" in sys.argv:
        analizza(ESEMPIO)
        return
    d = dict(ESEMPIO)
    d["nome"] = input(f"Nome azienda target [{ESEMPIO['nome']}]: ").strip() or ESEMPIO["nome"]
    for campo in ["fatturato", "ebitda", "multiplo", "pct_equity", "pct_debito", "pct_earnout", "tasso_debito", "anni_debito", "uplift_ai_punti"]:
        d[campo] = chiedi(campo.replace("_", " "), ESEMPIO[campo])
    analizza(d)


if __name__ == "__main__":
    main()
