#!/usr/bin/env python3
"""Generatore del calendario editoriale 90 giorni (build in public).

Rotazione dei 4 pilastri su 3 post/settimana (lun-mer-ven) + newsletter il
sabato. Ogni slot ha pilastro, format e call-to-action già assegnati: la
decisione è già presa, resta solo da scrivere.

Uso:
    python3 calendario.py                # stampa il calendario
    python3 calendario.py > CALENDARIO.md
"""
import datetime
import itertools

PILASTRI = {
    "📈 Numeri veri": {
        "format": "Screenshot/tabella + 5 righe di contesto",
        "cta": "Iscriviti alla newsletter per il report completo",
        "spunti": [
            "Dashboard settimanale del portfolio: demo fatte, piloti, incassi",
            "Quanto costa DAVVERO far partire il progetto X (scontrini alla mano)",
            "Funnel reale: da N contatti a N clienti, tutti i numeri in mezzo",
        ],
    },
    "🔧 Come si fa": {
        "format": "Tutorial passo-passo (carosello o thread)",
        "cta": "Il codice è open source: link alla repo",
        "spunti": [
            "Come ho costruito un receptionist AI a zero dipendenze",
            "Il questionario che classifica un'azienda sotto l'AI Act in 10 minuti",
            "Lo script di vendita porta-a-porta, parola per parola",
        ],
    },
    "💡 Analisi": {
        "format": "Post lungo con una tabella o un grafico",
        "cta": "Cosa ne pensi? Rispondo a tutti i commenti",
        "spunti": [
            "La classifica delle 9 idee di business (dal README della repo)",
            "Perché l'Italia è il mercato PERFETTO per la silver economy",
            "EU AI Act: la multa arriva ad agosto e nessuno è pronto",
        ],
    },
    "❌ Errori": {
        "format": "Storia in prima persona, onesta, con la lezione alla fine",
        "cta": "Seguimi per non ripetere i miei errori",
        "spunti": [
            "Il pilota che NON si è convertito e cosa mi ha insegnato",
            "Ho buttato una settimana su una feature che nessuno voleva",
            "La chiamata a freddo andata malissimo (trascrizione inclusa)",
        ],
    },
}

GIORNI_POST = [0, 2, 4]  # lun, mer, ven
GIORNO_NEWSLETTER = 5    # sab


def genera(inizio=None, settimane=13):
    inizio = inizio or datetime.date.today()
    # allinea al lunedì successivo
    inizio += datetime.timedelta(days=(7 - inizio.weekday()) % 7)
    rotazione = itertools.cycle(PILASTRI.items())
    contatori = {nome: 0 for nome in PILASTRI}

    print("# 📅 Calendario Editoriale — 90 giorni build in public\n")
    print(f"Inizio: lunedì {inizio.strftime('%d/%m/%Y')} — 3 post/settimana + newsletter il sabato\n")

    for settimana in range(settimane):
        lunedi = inizio + datetime.timedelta(weeks=settimana)
        print(f"## Settimana {settimana + 1} ({lunedi.strftime('%d/%m')})\n")
        print("| Giorno | Pilastro | Format | Spunto | CTA |")
        print("|---|---|---|---|---|")
        for g in GIORNI_POST:
            data = lunedi + datetime.timedelta(days=g)
            nome, p = next(rotazione)
            spunto = p["spunti"][contatori[nome] % len(p["spunti"])]
            contatori[nome] += 1
            print(f"| {data.strftime('%a %d/%m')} | {nome} | {p['format']} | {spunto} | {p['cta']} |")
        sabato = lunedi + datetime.timedelta(days=GIORNO_NEWSLETTER)
        print(f"| {sabato.strftime('%a %d/%m')} | 💌 Newsletter | Riepilogo settimana + il dietro le quinte | I 3 post della settimana + un extra solo per iscritti | Inoltra a un amico |")
        print()

    print("---\n**Regola:** se un giorno salti il post, NON recuperare: riprendi dal successivo. Il ritmo sostenibile batte la perfezione.")


if __name__ == "__main__":
    genera()
