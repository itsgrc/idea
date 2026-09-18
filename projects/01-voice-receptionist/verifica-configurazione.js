#!/usr/bin/env node
/**
 * Verifica configurazione — la checklist "sono pronto per un pilota vero?"
 * in un comando solo, pensata per l'onboarding < 2 ore di GO-TO-MARKET.md.
 * Non serve saper leggere codice: dice cosa è già vero, cosa è ancora
 * simulato, e segnala gli errori di configurazione più comuni PRIMA che
 * li scopra la prima chiamata reale di un cliente pilota (in particolare
 * PUBLIC_URL sbagliato: la firma Twilio non corrisponde mai, vedi
 * CONFIGURAZIONE.md e integrazioni/telefonia.js).
 *
 * Uso: node verifica-configurazione.js
 */
'use strict';
const fs = require('fs');
const path = require('path');
const { CONFIG, isMock, modalitaSimulata } = require('./integrazioni/config');

let problemiBloccanti = 0;
function riga(ok, testo) {
  console.log(`${ok ? '✅' : '🟡'} ${testo}`);
  if (!ok) problemiBloccanti++;
}

console.log(`\n${'═'.repeat(64)}`);
console.log('🔍 VERIFICA CONFIGURAZIONE — pronto per un pilota reale?');
console.log('═'.repeat(64) + '\n');

const envEsiste = fs.existsSync(path.join(__dirname, '.env'));
riga(envEsiste, envEsiste ? '.env presente' : '.env non trovato — copia .env.example in .env (vedi CONFIGURAZIONE.md passo 2)');

const twilioReale = !modalitaSimulata('twilio');
riga(
  twilioReale,
  twilioReale
    ? 'Twilio: credenziali reali — un numero puntato qui riceve chiamate vere'
    : 'Twilio: ancora MOCK — nessuna chiamata reale in arrivo (la demo web/CLI funziona comunque, vedi README "Prova subito")'
);

const url = CONFIG.server.publicUrl;
if (isMock(url)) {
  riga(false, 'PUBLIC_URL ancora MOCK — obbligatorio prima di puntare un numero Twilio reale (CONFIGURAZIONE.md passo 2)');
} else {
  const problemiUrl = [];
  if (!/^https:\/\//.test(url)) problemiUrl.push('non inizia con https://');
  if (url.endsWith('/')) problemiUrl.push('finisce con uno slash: deve essere identico, carattere per carattere, al webhook scritto nella console Twilio');
  if (problemiUrl.length) {
    riga(false, `PUBLIC_URL="${url}" — ${problemiUrl.join('; ')}. Con un URL sbagliato la firma Twilio non validerà MAI: ogni chiamata reale verrebbe rifiutata con 403`);
  } else {
    riga(true, `PUBLIC_URL="${url}" — formato corretto`);
  }
}

const notificheReali = !isMock(CONFIG.twilio.numeroWhatsapp) && !isMock(CONFIG.notifiche.numeroTitolare);
riga(
  notificheReali,
  notificheReali
    ? 'Notifiche WhatsApp al titolare: configurate'
    : 'Notifiche WhatsApp al titolare: ancora MOCK — il titolare non riceverà nulla su WhatsApp (opzionale ma consigliato, CONFIGURAZIONE.md passo 3)'
);

const calendarioReale = !modalitaSimulata('calendario');
riga(
  calendarioReale,
  calendarioReale
    ? 'Google Calendar: configurato'
    : 'Google Calendar: ancora MOCK — nessun evento creato davvero (opzionale, CONFIGURAZIONE.md passo 4)'
);

const integrazioniAttive = process.env.INTEGRAZIONI_ATTIVE === '1';
if (!integrazioniAttive && (notificheReali || calendarioReale)) {
  riga(false, 'INTEGRAZIONI_ATTIVE non è "1": hai credenziali reali ma restano spente. Imposta INTEGRAZIONI_ATTIVE=1 in .env');
} else if (integrazioniAttive) {
  riga(true, 'INTEGRAZIONI_ATTIVE=1 — le azioni chiamano davvero le integrazioni configurate sopra');
}

const flowPath = process.env.FLOW || path.join(__dirname, 'flows', 'dentista.json');
try {
  const flow = JSON.parse(fs.readFileSync(flowPath, 'utf8'));
  riga(true, `Flusso attivo: "${flow.nome}" (${flowPath})`);
  const valoriPath = path.join(__dirname, 'valori', path.basename(flowPath));
  riga(fs.existsSync(valoriPath), fs.existsSync(valoriPath) ? `Valori ROI: ${valoriPath}` : `Valori ROI mancanti (${valoriPath}) — valore.js non troverà i prezzi di questo flusso`);
} catch (err) {
  riga(false, `Flusso non leggibile (${flowPath}): ${err.message}`);
}

console.log(`\n${'═'.repeat(64)}`);
if (twilioReale && problemiBloccanti === 0) {
  console.log('✅ Pronto a ricevere chiamate reali. Fai comunque un test end-to-end da un telefono vero prima del cliente pilota.');
} else if (twilioReale) {
  console.log('🟡 Twilio è configurato ma c\'è ancora qualcosa da sistemare qui sopra prima di fidarsi di una chiamata reale.');
} else {
  console.log('🟡 Ancora in modalità demo: la chat web/CLI funziona, il telefono no. Segui CONFIGURAZIONE.md per andare live.');
}
console.log('═'.repeat(64) + '\n');
