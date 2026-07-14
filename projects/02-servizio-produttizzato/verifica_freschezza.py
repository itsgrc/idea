#!/usr/bin/env python3
"""Verifica Freschezza — il vero prodotto di un servizio RADAR abbonamento.

Chiunque può copiare una lista di bandi UNA volta. Il valore di un abbonamento
mensile sta nel tenerla viva: bandi che scadono, importi che cambiano, sportelli
che si aprono. Questo script forza la disciplina — segnala quali voci del
database sono scadute, in scadenza, o non riverificate da troppo tempo — così
il RADAR non diventa mai la lista morta che vendono i concorrenti.

Regola della casa: nessuna voce resta in bandi.json più di 30 giorni senza
essere riverificata sulla fonte ufficiale (data_verifica aggiornata a mano
dopo il controllo). Chi salta questa disciplina vende informazioni vecchie
a pagamento — è il modo più veloce di perdere un cliente.

Uso:
    python3 verifica_freschezza.py                 # controlla bandi.json
    python3 verifica_freschezza.py --max-giorni 14  # soglia più severa
"""
import json
import sys
import datetime

SOGLIA_RIVERIFICA_GIORNI_DEFAULT = 30
SOGLIA_SCADENZA_IMMINENTE_GIORNI = 20


def carica(path="bandi.json"):
    with open(path) as f:
        return json.load(f)


def analizza(bandi, soglia_riverifica):
    oggi = datetime.date.today()
    scaduti, in_scadenza, da_riverificare, ok = [], [], [], []

    for b in bandi:
        scadenza = datetime.date.fromisoformat(b["scadenza"])
        giorni_a_scadenza = (scadenza - oggi).days
        data_verifica = b.get("data_verifica")
        giorni_da_verifica = (oggi - datetime.date.fromisoformat(data_verifica)).days if data_verifica else 9999

        voce = {"titolo": b["titolo"], "giorni_a_scadenza": giorni_a_scadenza, "giorni_da_verifica": giorni_da_verifica, "fonte": b.get("fonte", "n/d")}

        if giorni_a_scadenza < 0 and b.get("modalita_scadenza") not in ("a sportello", "avvisi periodici"):
            scaduti.append(voce)
        elif giorni_a_scadenza <= SOGLIA_SCADENZA_IMMINENTE_GIORNI and b.get("modalita_scadenza") not in ("a sportello", "avvisi periodici"):
            in_scadenza.append(voce)

        if giorni_da_verifica > soglia_riverifica:
            da_riverificare.append(voce)
        elif voce not in scaduti and voce not in in_scadenza:
            ok.append(voce)

    return scaduti, in_scadenza, da_riverificare, ok


def stampa(scaduti, in_scadenza, da_riverificare, ok, soglia):
    oggi = datetime.date.today().strftime("%d/%m/%Y")
    print(f"\n{'═' * 66}")
    print(f"🔍 VERIFICA FRESCHEZZA DATABASE BANDI — {oggi}")
    print(f"{'═' * 66}")
    print(f"Soglia di riverifica: {soglia} giorni · Preavviso scadenza: {SOGLIA_SCADENZA_IMMINENTE_GIORNI} giorni\n")

    if scaduti:
        print(f"🔴 SCADUTI — rimuovere o aggiornare SUBITO ({len(scaduti)}):")
        for v in scaduti:
            print(f"   · {v['titolo']}  (scaduto da {-v['giorni_a_scadenza']} giorni)")
        print()

    if in_scadenza:
        print(f"🟠 IN SCADENZA — avvisare i clienti con questo interesse ({len(in_scadenza)}):")
        for v in in_scadenza:
            print(f"   · {v['titolo']}  (scade tra {v['giorni_a_scadenza']} giorni)")
        print()

    if da_riverificare:
        print(f"🟡 DA RIVERIFICARE sulla fonte ufficiale — dati potenzialmente stantii ({len(da_riverificare)}):")
        for v in da_riverificare:
            print(f"   · {v['titolo']}  (verificato {v['giorni_da_verifica']} giorni fa)")
            print(f"     → {v['fonte']}")
        print()

    if ok:
        print(f"✅ Freschi e in regola ({len(ok)}):")
        for v in ok:
            print(f"   · {v['titolo']}")
        print()

    print(f"{'═' * 66}")
    if scaduti or da_riverificare:
        print("⚠️  AZIONE RICHIESTA prima di inviare il prossimo report ai clienti.")
        print("    Un database con voci scadute o stantie è peggio di nessun database:")
        print("    un cliente che scopre un bando scaduto nel TUO report non si fida più.")
        sys.exit(1)
    else:
        print("✅ Database in ordine. Prossima verifica consigliata tra 7 giorni.")
        sys.exit(0)


def main():
    soglia = SOGLIA_RIVERIFICA_GIORNI_DEFAULT
    if "--max-giorni" in sys.argv:
        soglia = int(sys.argv[sys.argv.index("--max-giorni") + 1])
    bandi = carica()
    stampa(*analizza(bandi, soglia), soglia)


if __name__ == "__main__":
    main()
