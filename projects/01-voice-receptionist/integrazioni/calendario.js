#!/usr/bin/env node
/**
 * Adapter calendario — crea l'evento su Google Calendar quando il motore
 * conferma un appuntamento. Stessa filosofia degli altri adapter: con
 * credenziali mock simula (logga), con credenziali vere fa la chiamata
 * reale via HTTPS nativo, zero dipendenze npm.
 *
 * Per andare live serve un progetto Google Cloud con Calendar API attiva
 * e un refresh token OAuth2 (vedi CONFIGURAZIONE.md per i passaggi).
 */
'use strict';
const https = require('https');
const { CONFIG, modalitaSimulata } = require('./config');

function postJson(host, pathname, headers, corpoOggetto) {
  return new Promise((resolve, reject) => {
    const corpo = JSON.stringify(corpoOggetto);
    const req = https.request(
      { host, path: pathname, method: 'POST', headers: { ...headers, 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(corpo) } },
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

async function ottieniAccessToken() {
  const { googleClientId, googleClientSecret, googleRefreshToken } = CONFIG.calendario;
  const risposta = await postJson('oauth2.googleapis.com', '/token', {}, {
    client_id: googleClientId,
    client_secret: googleClientSecret,
    refresh_token: googleRefreshToken,
    grant_type: 'refresh_token',
  });
  return JSON.parse(risposta.body).access_token;
}

/**
 * Crea l'evento calendario per un appuntamento. `dettagli` arriva dai
 * dati raccolti dal flusso (nome cliente, preferenza orario, ecc.) —
 * in produzione un vero slot orario si sceglie con la disponibilità
 * reale dell'agenda: qui usiamo la preferenza come titolo/nota, pronto
 * per essere raffinato quando l'agenda vera è collegata.
 */
async function creaEventoAppuntamento(dettagli) {
  if (modalitaSimulata('calendario')) {
    console.log(`🗓️  [SIMULATO — credenziali mock] Evento calendario: ${dettagli.nome || 'cliente'} — ${dettagli.preferenza_orario || dettagli.targa || 'da definire'}`);
    return { simulato: true, dettagli };
  }

  const accessToken = await ottieniAccessToken();
  const inizio = new Date(Date.now() + 24 * 3600 * 1000); // placeholder: domani stessa ora — da raffinare con l'agenda reale
  const fine = new Date(inizio.getTime() + 30 * 60 * 1000);
  const risposta = await postJson(
    'www.googleapis.com',
    `/calendar/v3/calendars/${encodeURIComponent(CONFIG.calendario.calendarId)}/events`,
    { Authorization: `Bearer ${accessToken}` },
    {
      summary: `Appuntamento — ${dettagli.nome || 'cliente'}`,
      description: `Creato dall'assistente AI. Preferenza: ${dettagli.preferenza_orario || 'n/d'}.`,
      start: { dateTime: inizio.toISOString() },
      end: { dateTime: fine.toISOString() },
    }
  );
  return { simulato: false, status: risposta.status, body: risposta.body };
}

module.exports = { creaEventoAppuntamento, ottieniAccessToken };
