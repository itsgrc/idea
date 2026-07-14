#!/usr/bin/env python3
"""Monitor — verifica automatica che le fonti dei bandi siano ancora raggiungibili.

Confine onesto di questo strumento: NON legge il contenuto della pagina per
capire se la scadenza è cambiata (ogni portale — MIMIT, Unioncamere, CCIAA —
ha una struttura diversa; un parser per ciascuno sarebbe fragile e darebbe
un falso senso di sicurezza). Fa invece la cosa che SI può automatizzare in
modo affidabile: verificare che l'URL risponda ancora (non sia stato
rimosso o spostato — il segnale più comune di un bando concluso e
archiviato). Il controllo del CONTENUTO (scadenza, importi) resta un
controllo umano — è quello che verifica_freschezza.py mette in agenda.

Pensato per girare su un cron settimanale (vedi CONFIGURAZIONE.md).

NOTA — nell'ambiente di sviluppo in cui questo progetto è stato scritto, il
proxy di rete del sandbox blocca le connessioni dirette a domini esterni
arbitrari (policy del sandbox, non un limite di questo codice): lo script
qui riporterà "PROBLEMA — 403/Forbidden" per OGNI url anche se il bando
è online e valido. Su un hosting reale (server proprio, Render, Railway,
un cron su qualunque VPS) le richieste HTTPS standard funzionano senza
questa restrizione.

Uso:
    python3 monitor.py
"""
import json
import sys
import urllib.request
import urllib.error


def controlla_url(url, timeout=8):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0 (compatibile; MonitorBandi/1.0)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, None
    except urllib.error.HTTPError as e:
        # Alcuni portali rifiutano HEAD (405): riprova con GET prima di arrenderti.
        if e.code == 405:
            try:
                req2 = urllib.request.Request(url, method="GET", headers={"User-Agent": "Mozilla/5.0 (compatibile; MonitorBandi/1.0)"})
                with urllib.request.urlopen(req2, timeout=timeout) as r:
                    return r.status, None
            except Exception as e2:
                return None, str(e2)
        return e.code, str(e)
    except Exception as e:
        return None, str(e)


def main():
    with open("bandi.json") as f:
        bandi = json.load(f)

    print(f"\n{'═' * 66}")
    print(f"🌐 MONITOR RAGGIUNGIBILITÀ FONTI — {len(bandi)} bandi")
    print(f"{'═' * 66}\n")

    problemi = 0
    for b in bandi:
        url = b.get("fonte", "")
        if not url.startswith("http"):
            print(f"⚪ {b['titolo']}: nessun URL da verificare (fonte non http)")
            continue
        status, errore = controlla_url(url)
        if status and 200 <= status < 400:
            print(f"✅ {b['titolo']}: raggiungibile ({status})")
        else:
            problemi += 1
            print(f"🔴 {b['titolo']}: PROBLEMA — {errore or f'status {status}'}")
            print(f"   {url}")
            print(f"   → il bando potrebbe essere stato archiviato/rimosso: verificare manualmente e aggiornare bandi.json")

    print(f"\n{'═' * 66}")
    if problemi:
        print(f"⚠️  {problemi} fonte/i da verificare manualmente prima del prossimo invio.")
        sys.exit(1)
    print("✅ Tutte le fonti sono raggiungibili.")
    sys.exit(0)


if __name__ == "__main__":
    main()
