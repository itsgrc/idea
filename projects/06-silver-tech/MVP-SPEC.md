# 📋 Specifica MVP — FiloDiretto

## Il flusso della chiamata (2 minuti, sempre uguale, sempre gentile)

```
1. APERTURA     «Buongiorno signora Maria, sono Filo! Come sta stamattina?»
                (stessa voce ogni giorno: la familiarità è la feature)
2. BENESSERE    ascolto attivo → classificazione: ok / debole / forte
3. ROUTINE      «Ha preso la pastiglia della pressione?» (personalizzato)
4. AGGANCIO     «Ieri mi raccontava del nipotino — è poi venuto a trovarla?»
                (memoria delle conversazioni = la magia che fa affezionare)
5. CHIUSURA     «Le auguro una bella giornata, ci sentiamo domani alle 10!»
```

**Regola d'oro:** l'AI non finge mai di essere umana. «Sono Filo, l'assistente della sua famiglia» — gli anziani apprezzano l'onestà e ci si affezionano lo stesso (è anche un obbligo: EU AI Act, Art. 50).

## Regole di escalation (vedi anche checkin_simulator.py)

| Evento | Azione | Tempo |
|---|---|---|
| Nessuna risposta | Riprova | +30 min |
| Nessuna risposta ×2 | 🚨 SMS + chiamata al familiare di riferimento | immediato |
| Segnale forte (caduta, dolore, confusione) | 🚨 chiamata al familiare + trascrizione | immediato |
| 3 segnali deboli in 7 giorni | ⚠️ avviso "pattern" al familiare | serale |
| Parola d'emergenza («aiuto») | 🚨 protocollo emergenza (familiare, poi 112 se configurato) | immediato |

## Dashboard famiglia (web, mobile-first)

- 🟢/🟡/🔴 stato di oggi, visibile in 2 secondi dallo smartphone
- Storico chiamate con sintesi (non trascrizione integrale: privacy del genitore)
- Report settimanale via WhatsApp/email il sabato mattina
- Pulsante «chiamata extra adesso» (feature più richiesta nei test USA di prodotti simili)

## Privacy & GDPR (vantaggio competitivo, non burocrazia)

- Consenso esplicito dell'anziano registrato alla prima chiamata
- Audio cancellato dopo la classificazione (si conservano solo le sintesi) — default
- Dati sanitari: minimizzazione — si registra «ha preso le medicine: sì/no», non diagnosi
- Il servizio è trattato secondo il GDPR; la telefonia riusa lo stack del progetto #01 (Twilio, fornitore extra-UE) con le garanzie previste dal GDPR (Clausole Contrattuali Standard) — non promettere «i dati non lasciano l'Europa» finché l'infrastruttura reale non lo garantisce davvero: è lo stesso errore già trovato e corretto nei progetti #01 e #04.
- Classificazione AI Act: da verificare con il progetto #03 (probabile rischio trasparenza, non alto rischio, finché non si fanno valutazioni sanitarie)

## Cosa NON fa l'MVP (e va detto chiaramente ai clienti)

- ❌ Non è un dispositivo medico, non fa diagnosi
- ❌ Non sostituisce il 112 né la badante
- ❌ Non registra video, non ha sensori, non "sorveglia"

## Stack tecnico

Motore conversazionale: **riuso del progetto #01** (stessa macchina a stati, flusso `filodiretto.json`). Telefonia: stesso provider voce del #01. Dashboard: web app minima. Costo marginale per famiglia: ~2–4 €/mese (chiamate + AI) su 29 € di prezzo → margine lordo ~90%.
