# ⚖️ Checklist legale — prima di mettere online una homepage

> Le 10 homepage in questo repo sono **pagine dimostrative** già scritte con criteri prudenziali (vedi sotto) e ora portano tutte un **banner "sito in costruzione"** ben visibile in cima alla pagina. Prima di pubblicarle su un dominio reale e raccogliere contatti veri, completa questa checklist.
>
> **Questo documento non è consulenza legale e non certifica la conformità a nessuna norma.** È un punto di partenza strutturato, scritto da un'AI, non da un avvocato. Le leggi cambiano, variano per giurisdizione e per i dettagli specifici di ogni attività: nessun documento generato automaticamente può sostituire il parere di un professionista abilitato. **Nessuna pagina va usata con clienti veri, e nessun backend va esposto su un dominio pubblico con dati reali, prima che un avvocato l'abbia rivista.**

## ✅ Già incorporato in tutte le 10 pagine

- **Banner "sito in costruzione"** ben visibile in cima a ogni homepage (e alla pagina pubblica `assessment.html` del progetto 03): dichiara che è una pagina dimostrativa, non ancora attiva al pubblico, con prezzi/nomi provvisori.
- **Nessuna testimonianza o recensione inventata** (pratica ingannevole ex Codice del Consumo — vietata e sanzionabile): le pagine non ne contengono affatto.
- **Nessuna promessa di guadagno o di risultato**: garanzie solo su ciò che è controllabile (es. rimborso se non troviamo bandi idonei), mai sull'esito.
- **Esempi marcati come esempi**: conversazioni, tabelle e numeri illustrativi sono etichettati come tali.
- **Prezzi «indicativi di lancio, IVA esclusa/inclusa»**: nessuna offerta al pubblico vincolante prima del go-live.
- **Trasparenza AI (Reg. UE 2024/1689, art. 50)**: ogni servizio che usa AI per interagire con le persone lo dichiara, anche nelle demo — vedi la sezione dedicata sotto.
- **Zero cookie / zero tracciamento** su tutte le homepage: pagine statiche, nessun banner cookie necessario finché resta così.
- **Disclaimer specifici per settore**: «non è consulenza legale» (Conforme), «non è un dispositivo medico, chiamare il 112» (FiloDiretto), «strumento di supporto, firma sempre professionale» (Perizia), «non è offerta al pubblico né sollecitazione» (Continuità), «stima statistica, nessun risultato garantito» (Campolibero).
- **Nomi dichiarati provvisori**: ogni footer segnala che il nome è in verifica di registrabilità.

## ⚠️ Attenzione: non è più vero che "nessun form raccoglie dati"

Le versioni precedenti di questa pagina dicevano che i moduli sono segnaposto e nessun dato viene raccolto. **Non è più così per diversi progetti**: nel corso dello sviluppo sono stati costruiti backend reali, testati, dietro credenziali ancora mock. Se il backend viene collegato a credenziali vere e messo su un hosting pubblico, quei form iniziano a raccogliere DAVVERO dati personali — anche se la homepage sopra dice ancora "in costruzione".

| Progetto | Cosa raccoglie oggi, se attivato | Protezioni già incorporate nel codice |
|---|---|---|
| 03 Conforme (`lead_capture.py`) | Email + classificazione di rischio AI Act del prospect | Autenticazione API a chiave (mock = accesso negato), rate limit, validazione email server-side |
| 04 Ponte (`app.py`) | Dati di clienti/veicoli di ogni officina registrata | Login vero (PBKDF2), isolamento multi-tenant testato, rate limit login |
| 05 Cantiere Aperto (`iscrizioni.py`) | Email degli iscritti alla newsletter | Doppio opt-in GDPR, cancellazione automatica delle iscrizioni mai confermate, disiscrizione = cancellazione immediata |
| 06 FiloDiretto (`dashboard.py`) | **Dati particolari (salute, art. 9 GDPR)**: segnali di malessere, farmaci | Consenso obbligatorio che blocca tecnicamente l'accesso finché non raccolto, token dedicato, cancellazione automatica oltre 90 giorni |
| 10 Campolibero (`prenota.py`) | Dati di clienti che prenotano (nome, telefono) + eventuali depositi via Stripe | Login vero, isolamento multi-tenant, webhook di pagamento con firma verificata |

**Prima di collegare uno qualunque di questi a credenziali reali su un hosting pubblico**: serve l'informativa privacy corrispondente (punto 3 sotto), non basta che il codice sia tecnicamente sicuro.

## 🤖 EU AI Act (Reg. UE 2024/1689) — stato per progetto

Aggiornato al pacchetto **Digital Omnibus** (Consiglio UE, 29/06/2026): gli obblighi per i sistemi **alto rischio** sono stati rinviati (Allegato III: dic. 2027; Allegato I: ago. 2028); gli obblighi di **trasparenza (art. 50)** restano invariati e scadono **ad agosto 2026**; le pratiche vietate (art. 5) sono già in vigore dal febbraio 2025.

| Progetto | Usa un sistema AI che interagisce con persone? | Obbligo principale | Stato |
|---|---|---|---|
| 01 Rispondo | Sì (voce sintetica che risponde al telefono) | Art. 50(1): dichiarare che si sta parlando con un'AI | ✅ Dichiarato nel flusso conversazionale e nella homepage |
| 03 Conforme | No (è lo strumento che classifica i sistemi AI DI ALTRI) | — | Il prodotto stesso aiuta i clienti a rispettare l'AI Act |
| 04 Ponte | No — il motore anti-scadenza (`richiami.py`) è statistica sullo storico, non AI/ML | — | Correttamente non descritto come "AI" nella homepage |
| 06 FiloDiretto | Sì (voce sintetica) | Art. 50(1) | ✅ Dichiarato («sono Filo, l'assistente della sua famiglia») |
| 09 Perizia | Sì — genera bozze di documenti (testo) | Art. 50(2): dichiarare che il contenuto è generato da AI | ✅ Rafforzato: la bozza è sempre dichiarata come generata da AI e mai spacciata per validata finché un professionista non firma |
| 10 Campolibero | No — il motore anti no-show è statistica sullo storico, non AI/ML | — | Correttamente non descritto come "AI" nella homepage |
| 02, 05, 07, 08 | Non usano AI che interagisce direttamente con persone su queste pagine | — | Nessun obbligo di trasparenza art. 50 identificato per l'homepage attuale |

**Prima di andare in produzione con QUALUNQUE progetto che usa AI**: la classificazione di rischio va rifatta formalmente con gli strumenti del progetto 03 (`classifica.py`), non desunta da questa tabella — questa tabella è un punto di partenza, non una classificazione ufficiale.

## 📋 Da fare PRIMA del go-live di ciascuna pagina

### 1. Nome e marchio
- [ ] Ricerca di anteriorità su **UIBM** (marchi italiani) ed **EUIPO** (marchi UE) per il nome scelto
- [ ] Verifica che il dominio .it/.com sia libero e non confondibile con marchi altrui
- [ ] Ricerca Google + registro imprese: nessuna azienda omonima nello stesso settore
- ⚠️ In particolare: nomi generici usati qui (Rispondo, Conforme, Ponte, Perizia, Campolibero…) potrebbero avere omonimi — la verifica è OBBLIGATORIA prima dell'uso commerciale

### 2. Soggetto giuridico e identità
- [ ] P.IVA attiva e footer aggiornato con: denominazione, sede, P.IVA/REA, contatti (obbligo ex art. 35 DPR 633/72 e D.Lgs. 70/2003 per i servizi online)
- [ ] PEC e domicilio digitale registrati

### 3. Privacy e cookie (quando si attivano i backend reali — vedi tabella sopra)
- [ ] Informativa privacy completa (artt. 13-14 GDPR) linkata dal footer, PRIMA di collegare qualunque backend a credenziali reali
- [ ] Registro dei trattamenti; DPA con i fornitori (hosting, email/SMS, pagamenti, AI provider)
- [ ] Se si aggiungono cookie non tecnici o analytics: cookie banner conforme alle Linee guida del Garante
- [ ] Doppio opt-in per la newsletter — **già implementato tecnicamente** in Cantiere Aperto (`iscrizioni.py`), verificare solo che l'informativa collegata sia pronta
- [ ] FiloDiretto tratta dati di categorie particolari (salute): **DPIA obbligatoria** prima di qualunque raccolta reale, anche se il consenso tecnico è già bloccante nel codice
- [ ] Ponte e Campolibero: i clienti finali (chi prenota) sono terzi rispetto al gestore della struttura — chiarire chi è titolare e chi è responsabile del trattamento (art. 28 GDPR), serve un DPA con ogni struttura cliente

### 4. Pagamenti (nuovo — riguarda Campolibero)
- [ ] Se si accettano depositi reali via Stripe: verificare gli obblighi PSD2/SCA (Strong Customer Authentication) applicabili
- [ ] Chiarire nei termini di servizio la natura del deposito (caparra confirmatoria vs acconto: trattamento fiscale e di recesso diversi)
- [ ] Verificare se serve una licenza o una semplice integrazione con un PSP autorizzato (Stripe lo è, ma il flusso contrattuale con l'utente finale va scritto)

### 5. Condizioni di vendita (quando si accettano ordini/abbonamenti)
- [ ] Termini e condizioni del servizio redatti da un legale
- [ ] Diritto di recesso 14 giorni per i consumatori (FiloDiretto, Cantiere Aperto, Campolibero se B2C) ex Codice del Consumo
- [ ] Politica di rimborso coerente con quanto promesso in pagina (es. garanzia 90 giorni TrovaBandi)

### 6. Specifici per settore
- [ ] **Conforme / Perizia**: definire il perimetro con l'ordine professionale competente (attività riservate ad avvocati/medici) e formalizzare le partnership con professionisti abilitati
- [ ] **TrovaBandi**: verificare eventuali requisiti per attività di assistenza su fondi pubblici; mai promettere esiti
- [ ] **FiloDiretto**: confermare con un legale che il servizio resta fuori dal perimetro del dispositivo medico (Reg. UE 2017/745) mantenendo le funzioni attuali
- [ ] **Continuità**: le operazioni M&A vanno perfezionate con professionisti abilitati; niente raccolta di capitali dal pubblico senza le autorizzazioni del caso; qualunque sistema AI introdotto nelle aziende acquisite va classificato secondo l'AI Act prima dell'uso
- [ ] **Rispondo / FiloDiretto**: registrazione delle chiamate solo con informativa e base giuridica; verificare gli obblighi del Codice Comunicazioni Elettroniche col provider di telefonia
- [ ] **Campolibero**: chiarire con ogni struttura cliente chi raccoglie il consenso dei propri clienti finali per l'invio SMS (di norma implicito nell'accettazione della prenotazione, ma va scritto nell'informativa della struttura)

### 7. Accessibilità
- [ ] Le pagine sono già costruite con buone pratiche (contrasto, focus visibile, riduzione animazioni); per clienti PA o grandi imprese, verificare i requisiti dell'European Accessibility Act (in vigore da giugno 2025)

## 🔁 Regola di manutenzione

Ogni modifica a prezzi, promesse o funzioni nelle pagine → ripassare i punti 3 e 5. Ogni nuovo canale di raccolta dati o nuovo backend collegato a credenziali reali → informativa aggiornata e, se servono dati particolari, DPIA PRIMA dell'attivazione — non dopo.
