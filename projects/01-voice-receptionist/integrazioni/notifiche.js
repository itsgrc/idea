#!/usr/bin/env node
/**
 * Adapter notifiche — WhatsApp/SMS al titolare via Twilio Messaging API.
 *
 * Finché le credenziali in .env sono "MOCK_..." (default), questo modulo
 * SIMULA l'invio: logga cosa avrebbe mandato, senza fare chiamate di rete
 * né spendere credito. Con credenziali vere, la stessa funzione fa una
 * vera richiesta HTTPS all'API Twilio — zero dipendenze npm, solo il
 * modulo https nativo di Node.
 */
'use strict';
const https = require('https');
const { CONFIG, modalitaSimulata } = require('./config');

function postForm(host, pathname, auth, campi) {
  return new Promise((resolve, reject) => {
    const corpo = new URLSearchParams(campi).toString();
    const req = https.request(
      {
        host,
        path: pathname,
        method: 'POST',
        auth, // 'accountSid:authToken' — Basic Auth richiesta da Twilio
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'Content-Length': Buffer.byteLength(corpo),
        },
      },
      (res) => {
        let data = '';
        res.on('data', (c) => (data += c));
        res.on('end', () => resolve({ status: res.statusCode, body: data }));
      }
    );
    req.on('error', reject);
    req.write(corpo);
    req.end();
  });
}

/**
 * Invia una notifica WhatsApp al titolare. Ritorna { simulato: bool, ... }
 * così chi chiama sa sempre se è successo davvero o solo loggato.
 */
async function inviaWhatsAppTitolare(messaggio) {
  const { twilio, notifiche } = CONFIG;

  if (modalitaSimulata('twilio')) {
    console.log(`📵 [SIMULATO — credenziali mock] WhatsApp al titolare (${notifiche.numeroTitolare}):\n   "${messaggio}"`);
    return { simulato: true, messaggio };
  }

  const risposta = await postForm(
    'api.twilio.com',
    `/2010-04-01/Accounts/${twilio.accountSid}/Messages.json`,
    `${twilio.accountSid}:${twilio.authToken}`,
    {
      From: twilio.numeroWhatsapp,
      To: `whatsapp:${notifiche.numeroTitolare}`,
      Body: messaggio,
    }
  );
  return { simulato: false, status: risposta.status, body: risposta.body };
}

/** Compone il messaggio di notifica a partire da un evento del motore. */
function messaggioPerEvento(evento) {
  const dati = evento.dati || {};
  if (evento.tipo === 'appuntamento_creato') {
    return `📅 Nuovo appuntamento: ${dati.nome || 'cliente'} — preferenza: ${dati.preferenza_orario || 'da confermare'}. Gestito dall'assistente AI.`;
  }
  if (evento.tipo === 'urgenza_notificata') {
    return `🚨 URGENZA segnalata da ${dati.nome || 'chiamante sconosciuto'} — richiamare appena possibile.`;
  }
  if (evento.tipo === 'richiesta_stato_veicolo') {
    return `🔧 Richiesta stato veicolo, targa ${evento.targa || 'n/d'} — verificare e rispondere al cliente.`;
  }
  return `ℹ️ Evento "${evento.tipo}" gestito dall'assistente AI.`;
}

module.exports = { inviaWhatsAppTitolare, messaggioPerEvento };
