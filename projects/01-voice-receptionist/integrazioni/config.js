#!/usr/bin/env node
/**
 * Config centralizzata delle integrazioni esterne — legge le variabili
 * d'ambiente definite in .env.example. Finché sono valorizzate con
 * "MOCK_..." (il default), tutti gli adapter lavorano in modalità
 * simulata: loggano cosa avrebbero fatto, senza chiamare alcuna API
 * reale né spendere credito. Il giorno in cui inserisci le credenziali
 * vere, lo stesso codice invia SMS, WhatsApp, crea eventi calendario —
 * zero righe da riscrivere.
 *
 * Come andare live: vedi CONFIGURAZIONE.md nella cartella del progetto.
 */
'use strict';

function leggi(nome, fallbackMock) {
  return process.env[nome] || fallbackMock;
}

const CONFIG = {
  twilio: {
    accountSid: leggi('TWILIO_ACCOUNT_SID', 'MOCK_ACCOUNT_SID'),
    authToken: leggi('TWILIO_AUTH_TOKEN', 'MOCK_AUTH_TOKEN'),
    numeroTelefono: leggi('TWILIO_PHONE_NUMBER', 'MOCK_+390000000000'),
    numeroWhatsapp: leggi('TWILIO_WHATSAPP_FROM', 'MOCK_whatsapp:+390000000000'),
  },
  notifiche: {
    numeroTitolare: leggi('NOTIFICHE_NUMERO_TITOLARE', 'MOCK_+393331234567'),
  },
  server: {
    // URL pubblico su cui Twilio raggiunge questo server (es. https://tuoapp.onrender.com).
    // Serve a validare la firma X-Twilio-Signature: senza l'URL esatto usato da
    // Twilio per firmare la richiesta, non si può verificare che sia autentica.
    publicUrl: leggi('PUBLIC_URL', 'MOCK_https://tuoapp.esempio.it'),
  },
  calendario: {
    googleClientId: leggi('GOOGLE_CALENDAR_CLIENT_ID', 'MOCK_CLIENT_ID'),
    googleClientSecret: leggi('GOOGLE_CALENDAR_CLIENT_SECRET', 'MOCK_CLIENT_SECRET'),
    googleRefreshToken: leggi('GOOGLE_CALENDAR_REFRESH_TOKEN', 'MOCK_REFRESH_TOKEN'),
    calendarId: leggi('GOOGLE_CALENDAR_ID', 'MOCK_calendario@studio.it'),
  },
};

function isMock(valore) {
  return typeof valore === 'string' && valore.startsWith('MOCK_');
}

// true finché ANCHE UNA SOLA credenziale Twilio è ancora mock — è la
// leva che decide se gli adapter chiamano l'API vera o simulano.
function modalitaSimulata(sezione) {
  return Object.values(CONFIG[sezione]).some(isMock);
}

module.exports = { CONFIG, isMock, modalitaSimulata };
