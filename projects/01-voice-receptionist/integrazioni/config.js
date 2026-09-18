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
const fs = require('fs');
const path = require('path');

/* ------------------------------------------------------------------ *
 * Caricamento .env — CONFIGURAZIONE.md dice "copia i valori in .env" e
 * dà per scontato che basti quello. Senza questo, nulla legge mai il
 * file: process.env[...] resta sempre MOCK_ anche con .env compilato
 * correttamente, in silenzio (nessun errore, nessun avviso) — un pilota
 * seguirebbe la guida alla lettera e si ritroverebbe comunque in
 * modalità simulata su un test locale. Niente pacchetto dotenv: due
 * variabili d'ambiente valgono più di una dipendenza in più (principio
 * "zero dipendenze finché possibile" del portfolio). Le variabili già
 * impostate dall'ambiente reale (Render, Railway, ...) vincono sempre
 * sul file, come fa dotenv.
 * ------------------------------------------------------------------ */
function caricaDotEnv(percorso) {
  if (!fs.existsSync(percorso)) return;
  for (const riga of fs.readFileSync(percorso, 'utf8').split('\n')) {
    const r = riga.trim();
    if (!r || r.startsWith('#')) continue;
    const eq = r.indexOf('=');
    if (eq === -1) continue;
    const chiave = r.slice(0, eq).trim();
    let valore = r.slice(eq + 1).trim();
    if ((valore.startsWith('"') && valore.endsWith('"')) || (valore.startsWith("'") && valore.endsWith("'"))) {
      valore = valore.slice(1, -1);
    }
    if (process.env[chiave] === undefined) process.env[chiave] = valore;
  }
}
caricaDotEnv(path.join(__dirname, '..', '.env'));

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

module.exports = { CONFIG, isMock, modalitaSimulata, caricaDotEnv };
