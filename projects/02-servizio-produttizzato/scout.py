#!/usr/bin/env python3
"""TrovaBandi — motore di matching bandi ↔ azienda (v0, zero dipendenze).

Il cuore del servizio RADAR: dato il profilo di un'azienda cliente e il
database dei bandi monitorati, produce il report mensile con i soli bandi
per cui l'azienda è idonea, ognuno con la sua scheda di una pagina.

In v0 il database bandi è un JSON curato a mano (bandi.json): è così che
si parte davvero — 30 minuti a settimana di curation umana battono
qualsiasi scraper mal fatto. Lo scraping delle fonti si aggiunge in v1
quando i clienti pagano.

Uso:
    python3 scout.py --demo                 # report per il cliente di esempio
    python3 scout.py profilo_cliente.json   # report per un cliente reale
"""
import json
import sys
import datetime

BANDI_DB = "bandi.json"

CLIENTE_DEMO = {
    "azienda": "Meccanica Rossi Srl",
    "regione": "Lombardia",
    "settori": ["manifattura", "meccanica"],
    "dipendenti": 18,
    "fatturato": 2_400_000,
    "interessi": ["macchinari", "digitale", "export", "formazione"],
    "referente": "Sig. Rossi",
}


def carica_bandi():
    try:
        with open(BANDI_DB) as f:
            return json.load(f)
    except FileNotFoundError:
        sys.exit(f"Database bandi non trovato: {BANDI_DB}")


def dimensione_ok(bando, cliente):
    d = cliente["dipendenti"]
    return bando["dipendenti_min"] <= d <= bando["dipendenti_max"]


def match(bando, cliente):
    """Ritorna (idoneo, motivi, punteggio_priorità)."""
    motivi, punti = [], 0

    # Territorio: nazionale o della regione del cliente
    if bando["territorio"] not in ("nazionale", cliente["regione"]):
        return False, [f"territorio {bando['territorio']}"], 0
    motivi.append(f"territorio: {bando['territorio']} ✓")

    # Settore
    if bando["settori"] != ["tutti"] and not set(bando["settori"]) & set(cliente["settori"]):
        return False, ["settore non ammesso"], 0
    motivi.append("settore ammesso ✓")

    # Dimensione
    if not dimensione_ok(bando, cliente):
        return False, [f"richiede {bando['dipendenti_min']}–{bando['dipendenti_max']} dipendenti"], 0
    motivi.append(f"dimensione ok ({cliente['dipendenti']} dip.) ✓")

    # Priorità: interesse dichiarato del cliente + scadenza vicina + intensità aiuto
    if bando["tema"] in cliente["interessi"]:
        punti += 3
        motivi.append(f"tema '{bando['tema']}' tra gli interessi dichiarati ★")
    giorni = (datetime.date.fromisoformat(bando["scadenza"]) - datetime.date.today()).days
    if giorni < 0:
        return False, ["scaduto"], 0
    if giorni <= 45:
        punti += 2
        motivi.append(f"scadenza vicina ({giorni} giorni) ⏰")
    if bando.get("tipo_calcolo") == "fondo_perduto":
        punti += bando["intensita_pct"] // 25  # più fondo perduto = più priorità
    else:
        punti += 1  # contributo su interessi/altro: valido ma non paragonabile a un fondo perduto

    return True, motivi, punti


def scheda(bando, cliente, motivi):
    giorni = (datetime.date.fromisoformat(bando["scadenza"]) - datetime.date.today()).days
    massimale = f"{bando['massimale_eur']:,} €" if bando.get("massimale_eur") else "variabile (vedi note)"
    modalita = bando.get("modalita_scadenza", "scadenza fissa")
    return f"""
### {bando['titolo']}

| | |
|---|---|
| **Ente** | {bando['ente']} |
| **Tema** | {bando['tema']} |
| **Contributo** | {bando['tipo']} fino al **{bando['intensita_pct']}%**, max **{massimale}** |
| **Modalità** | {modalita} — {"scade tra " + str(giorni) + " giorni" if giorni <= 60 else bando['scadenza']} |
| **Fonte** | {bando['fonte']} (verificato il {bando.get('data_verifica', 'n/d')}) |

**Perché {cliente['azienda']} è idonea:** {" · ".join(motivi)}

**Prossimo passo:** rispondere a questa email con "mi interessa" — prepariamo noi la domanda ({bando['note_operative']}).
"""


def report(cliente):
    bandi = carica_bandi()
    idonei = []
    scartati = 0
    for b in bandi:
        ok, motivi, punti = match(b, cliente)
        if ok:
            idonei.append((punti, b, motivi))
        else:
            scartati += 1
    idonei.sort(key=lambda x: -x[0])

    oggi = datetime.date.today().strftime("%d/%m/%Y")
    righe = [
        f"# 📋 Report bandi — {cliente['azienda']}",
        f"",
        f"*Preparato il {oggi} · profilo: {cliente['regione']}, {', '.join(cliente['settori'])}, {cliente['dipendenti']} dipendenti*",
        f"",
        f"**{len(idonei)} bandi idonei** trovati su {len(bandi)} monitorati ({scartati} esclusi perché non pertinenti — non ti facciamo perdere tempo).",
    ]
    for i, (punti, b, motivi) in enumerate(idonei, 1):
        priorita = "🔥 ALTA" if punti >= 5 else ("⭐ media" if punti >= 3 else "· ordinaria")
        righe.append(f"\n---\n\n## {i}. Priorità {priorita}")
        righe.append(scheda(b, cliente, motivi))
    righe.append("\n---\n*Report generato dal sistema RADAR e verificato dal consulente prima dell'invio. Le informazioni provengono dalle fonti ufficiali citate; l'idoneità definitiva è confermata in fase di preparazione della domanda.*")
    return "\n".join(righe)


def main():
    if "--demo" in sys.argv:
        cliente = CLIENTE_DEMO
    elif len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            cliente = json.load(f)
    else:
        sys.exit("Uso: python3 scout.py --demo | profilo_cliente.json")

    testo = report(cliente)
    print(testo)
    nome = f"report-{cliente['azienda'].split()[0].lower()}-{datetime.date.today().isoformat()}.md"
    with open(nome, "w") as f:
        f.write(testo + "\n")
    print(f"\n💾 Salvato: {nome}", file=sys.stderr)


if __name__ == "__main__":
    main()
