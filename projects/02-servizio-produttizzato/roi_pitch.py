#!/usr/bin/env python3
"""Generatore di pitch personalizzato con ROI calcolato.

Inserisci i numeri del prospect, ottieni l'email di vendita pronta da inviare
con il SUO ritorno sull'investimento già calcolato. Il principio: non vendere
il servizio, vendere il numero.

Uso:
    python3 roi_pitch.py --esempio          # demo con dati di esempio
    python3 roi_pitch.py                    # modalità interattiva
"""
import sys

ESEMPIO = {
    "azienda": "Meccanica Rossi Srl",
    "nome": "Sig. Rossi",
    "settore": "meccanica di precisione",
    "regione": "Lombardia",
    "investimento_previsto": 120_000,   # € che l'azienda vuole comunque spendere (macchinari, digitale...)
    "percentuale_fondo_perduto": 40,    # % tipica coperta dai bandi del settore/regione
    "pacchetto": "CACCIA",
    "prezzo_mensile": 390,
    "success_fee_pct": 5,
}


def chiedi(etichetta, default=None, tipo=str):
    suffisso = f" [{default}]" if default is not None else ""
    valore = input(f"{etichetta}{suffisso}: ").strip()
    if not valore and default is not None:
        return default
    return tipo(valore)


def genera(d):
    contributo = d["investimento_previsto"] * d["percentuale_fondo_perduto"] / 100
    costo_anno = d["prezzo_mensile"] * 12
    fee = contributo * d["success_fee_pct"] / 100
    costo_totale = costo_anno + fee
    roi = (contributo - costo_totale) / costo_totale

    return f"""
{'=' * 62}
📊 ROI PER {d['azienda'].upper()}
{'=' * 62}
Investimento che farebbe comunque:      {d['investimento_previsto']:>12,.0f} €
Contributo a fondo perduto potenziale:  {contributo:>12,.0f} €  ({d['percentuale_fondo_perduto']}%)
Costo servizio anno 1 (fisso + fee):    {costo_totale:>12,.0f} €
ROI per il cliente:                     {roi:>12.1f}x
{'=' * 62}

✉️  EMAIL PRONTA DA INVIARE
{'-' * 62}
Oggetto: {contributo:,.0f} € di fondo perduto per {d['azienda']}

Buongiorno {d['nome']},

lei ha in programma un investimento di circa {d['investimento_previsto']:,.0f} €
({d['settore']}). In {d['regione']} i bandi attivi coprono in media il
{d['percentuale_fondo_perduto']}% di investimenti come il suo: parliamo di
{contributo:,.0f} € che potrebbe non spendere di tasca sua.

Il nostro servizio {d['pacchetto']} le costa {d['prezzo_mensile']} €/mese più il
{d['success_fee_pct']}% SOLO se il contributo viene erogato. Fatti due conti:
per ogni euro che ci paga, gliene tornano in tasca {roi + 1:,.1f}.

Le va una chiamata di 15 minuti questa settimana per vedere i bandi
concreti per cui {d['azienda']} è già idonea?

Cordiali saluti
{'-' * 62}
"""


def main():
    if "--esempio" in sys.argv:
        print(genera(ESEMPIO))
        return
    print("Inserisci i dati del prospect (invio = valore di esempio)\n")
    d = {
        "azienda": chiedi("Nome azienda", ESEMPIO["azienda"]),
        "nome": chiedi("Nome del titolare", ESEMPIO["nome"]),
        "settore": chiedi("Settore", ESEMPIO["settore"]),
        "regione": chiedi("Regione", ESEMPIO["regione"]),
        "investimento_previsto": chiedi("Investimento previsto (€)", ESEMPIO["investimento_previsto"], int),
        "percentuale_fondo_perduto": chiedi("% fondo perduto tipica", ESEMPIO["percentuale_fondo_perduto"], int),
        "pacchetto": chiedi("Pacchetto proposto", ESEMPIO["pacchetto"]),
        "prezzo_mensile": chiedi("Prezzo mensile (€)", ESEMPIO["prezzo_mensile"], int),
        "success_fee_pct": chiedi("Success fee %", ESEMPIO["success_fee_pct"], int),
    }
    print(genera(d))


if __name__ == "__main__":
    main()
