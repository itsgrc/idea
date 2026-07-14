#!/usr/bin/env python3
"""Campagna — mail-merge che trasforma un CSV di prospect in outreach pronto.

Il collo di bottiglia del servizio non è trovare i bandi: è scrivere email
personalizzate una per una. Questo script prende un CSV di prospect (i TUOI
contatti reali — qui trovi solo un esempio con aziende fittizie) e per
ciascuno:
  1. lo fa passare nel motore di matching di scout.py sul database REALE
  2. calcola il contributo potenziale del bando migliore
  3. genera l'email personalizzata pronta da incollare in un client di posta

Non invia nulla: produce testo. L'invio resta una scelta e un'azione umana —
questo script elimina solo il lavoro meccanico di scrivere 10 email quasi
identiche.

Uso:
    python3 campagna.py --demo                          # usa prospects_esempio.csv
    python3 campagna.py prospects_reali.csv              # sui tuoi contatti veri
"""
import csv
import sys
import datetime

from scout import carica_bandi, match


def leggi_prospects(path):
    prospects = []
    with open(path, newline="", encoding="utf-8") as f:
        for riga in csv.DictReader(f):
            prospects.append({
                "azienda": riga["azienda"],
                "referente": riga["referente"],
                "email": riga.get("email", "").strip(),
                "settori": [s.strip() for s in riga["settore"].split(";")],
                "regione": riga["regione"],
                "dipendenti": int(riga["dipendenti"]),
                "interessi": [s.strip() for s in riga["interessi"].split(";")],
                "investimento_previsto": int(riga["investimento_previsto"]),
            })
    return prospects


def migliore_bando(prospect, bandi):
    candidati = []
    for b in bandi:
        cliente_compat = {**prospect, "regione": prospect["regione"]}
        ok, motivi, punti = match(b, cliente_compat)
        if ok:
            candidati.append((punti, b, motivi))
    candidati.sort(key=lambda x: -x[0])
    return candidati[0] if candidati else None


def calcola_contributo(prospect, bando):
    """Ritorna un numero solo per i bandi a fondo perduto veri. Per i contributi
    su interessi (es. Sabatini) un calcolo automatico "% dell'investimento"
    sarebbe FALSO — il beneficio reale dipende dal piano di ammortamento
    bancario, non è una percentuale sull'investimento. Meglio non quantificare
    che quantificare male: un numero sbagliato in un'email brucia la fiducia
    del prospect molto più in fretta di quanto un cliente vero perdoni."""
    if bando.get("tipo_calcolo") != "fondo_perduto":
        return None
    grezzo = prospect["investimento_previsto"] * bando["intensita_pct"] / 100
    if bando.get("massimale_eur"):
        return min(grezzo, bando["massimale_eur"])
    return grezzo


def genera_email(prospect, bando, motivi, contributo):
    oggetto = f"{contributo:,.0f} € potenziali per {prospect['azienda']}" if contributo is not None else f"Un'agevolazione per {prospect['azienda']}: {bando['titolo']}"
    if contributo is not None:
        # "Stimato", non "spettante": l'importo dipende da graduatoria,
        # ammissibilità della spesa e fondi residui dell'ente — mai
        # presentarlo come un numero certo, nemmeno quando la % è chiara.
        corpo_economico = (
            f"Si tratta di {bando['tipo']} fino al {bando['intensita_pct']}% — sul suo\n"
            f"investimento previsto di {prospect['investimento_previsto']:,} € parliamo di\n"
            f"circa **{contributo:,.0f} € stimati** di contributo a fondo perduto\n"
            f"(l'importo definitivo dipende da graduatoria, ammissibilità della spesa\n"
            f"e fondi residui dell'ente: nessun contributo è garantito prima dell'esito)."
        )
    else:
        nota = bando.get("nota_calcolo", "l'importo non è calcolabile come percentuale semplice dell'investimento indicato: verificare i dettagli con il bando ufficiale.")
        corpo_economico = f"Si tratta di {bando['tipo']}: {nota}"
    email = prospect.get("email") or "(email non fornita)"
    return f"""
{'=' * 66}
A: {prospect['referente']} <{email}> — {prospect['azienda']}
Oggetto: {oggetto}
{'-' * 66}
Buongiorno {prospect['referente']},

in {prospect['regione']} è aperto in questo momento un bando per cui
{prospect['azienda']} risulta idonea: **{bando['titolo']}** ({bando['ente']}).

{corpo_economico}

Perché siete idonei: {" · ".join(motivi)}.

Fonte ufficiale (verificata il {bando.get('data_verifica', 'n/d')}): {bando['fonte']}

Le mando gratis la scheda completa con i prossimi passi? Mi basta un "sì".

Cordiali saluti
{'=' * 66}
""".strip()


def main():
    path = "prospects_esempio.csv" if "--demo" in sys.argv else (sys.argv[1] if len(sys.argv) > 1 else None)
    if not path:
        sys.exit("Uso: python3 campagna.py --demo | prospects.csv")

    prospects = leggi_prospects(path)
    bandi = carica_bandi()

    email_generate, senza_match = [], []
    for p in prospects:
        risultato = migliore_bando(p, bandi)
        if risultato:
            _punti, bando, motivi = risultato
            contributo = calcola_contributo(p, bando)
            email_generate.append(genera_email(p, bando, motivi, contributo))
        else:
            senza_match.append(p["azienda"])

    print(f"\n📧 Campagna generata: {len(email_generate)} email pronte su {len(prospects)} prospect\n")
    for e in email_generate:
        print(e)
        print()

    if senza_match:
        print(f"⚠️  Nessun bando idoneo trovato per: {', '.join(senza_match)} — non li contattare a vuoto, aspetta nuovi bandi.")

    nome_file = f"campagna-{datetime.date.today().isoformat()}.md"
    with open(nome_file, "w", encoding="utf-8") as f:
        f.write(f"# Campagna outreach — {datetime.date.today().strftime('%d/%m/%Y')}\n\n")
        f.write("\n\n".join(email_generate))
    print(f"\n💾 Salvato: {nome_file} — {len(email_generate)} email pronte da copiare e inviare.")


if __name__ == "__main__":
    main()
