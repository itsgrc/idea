#!/usr/bin/env node
/**
 * Adapter telefonia — webhook compatibile Twilio Voice (TwiML).
 *
 * Questo NON è mock: è codice reale, nello stesso formato che Twilio (o
 * qualunque provider VoIP compatibile TwiML: Vonage, Plivo con adapter
 * simile) si aspetta. La parte "mock" del progetto è SOLO il numero di
 * telefono — finché non ne compri uno vero e non lo punti su questo
 * endpoint, questo codice semplicemente non riceve chiamate. Il giorno
 * in cui lo fai, non serve toccare una riga: è già pronto.
 *
 * Flusso di una telefonata reale:
 *   1. Il chiamante compone il numero Twilio
 *   2. Twilio fa una POST su https://tuodominio.it/voice/incoming
 *   3. Rispondiamo con TwiML: <Say> il saluto + <Gather input="speech">
 *   4. Twilio trascrive la voce (STT incluso nel servizio) e fa una
 *      POST su /voice/gather/<session_id> con il testo in SpeechResult
 *   5. Il testo entra in ricevi() ESATTAMENTE come nella demo web/CLI:
 *      la macchina a stati non sa e non le importa se il testo viene
 *      da una tastiera o da una voce vera.
 *   6. Rispondiamo con nuovo TwiML finché la chiamata non è "finita"
 *      (stato terminale) → allora <Hangup/>.
 */
'use strict';
const querystring = require('querystring');
const crypto = require('crypto');

function escapeXml(testo) {
  return String(testo)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

/**
 * Genera il TwiML di risposta. `messaggi` è l'array di frasi restituito
 * da avanza()/ricevi(); `finita` decide se agganciare o aspettare ancora
 * l'input vocale del chiamante.
 */
function generaTwiML(messaggi, { finita, actionUrl, lingua = 'it-IT', voce = 'Polly.Bianca' }) {
  const say = messaggi.map((m) => `<Say voice="${voce}" language="${lingua}">${escapeXml(m)}</Say>`).join('');
  if (finita) {
    return `<?xml version="1.0" encoding="UTF-8"?><Response>${say}<Hangup/></Response>`;
  }
  return (
    `<?xml version="1.0" encoding="UTF-8"?><Response>${say}` +
    `<Gather input="speech" action="${actionUrl}" method="POST" speechTimeout="auto" language="${lingua}">` +
    `</Gather>` +
    // Se il chiamante non dice nulla entro il timeout, Twilio richiama lo
    // stesso URL: ripetiamo la domanda invece di agganciare nel silenzio.
    `<Redirect method="POST">${actionUrl}</Redirect></Response>`
  );
}

/**
 * Valida la firma X-Twilio-Signature — SICUREZZA: senza questo controllo,
 * chiunque scopra l'URL del webhook può inviare richieste false (finte
 * trascrizioni vocali) e far scattare notifiche WhatsApp o eventi
 * calendario a piacere. Algoritmo documentato da Twilio: concatena l'URL
 * completo con chiave+valore di ogni parametro POST in ordine alfabetico,
 * firma con HMAC-SHA1 usando l'Auth Token, confronta in tempo costante.
 *
 * Richiede PUBLIC_URL configurato correttamente (l'URL esatto che hai
 * messo nella console Twilio) — con un URL sbagliato la firma non
 * corrisponderà MAI, anche se la richiesta è genuina: vedi CONFIGURAZIONE.md.
 */
function validaFirmaTwilio({ urlCompleto, params, firmaRicevuta, authToken }) {
  if (!firmaRicevuta || !authToken) return false;
  const stringaDaFirmare = Object.keys(params)
    .sort()
    .reduce((acc, k) => acc + k + params[k], urlCompleto);
  const firmaAttesa = crypto.createHmac('sha1', authToken).update(Buffer.from(stringaDaFirmare, 'utf-8')).digest('base64');
  const bufAttesa = Buffer.from(firmaAttesa);
  const bufRicevuta = Buffer.from(firmaRicevuta);
  if (bufAttesa.length !== bufRicevuta.length) return false;
  return crypto.timingSafeEqual(bufAttesa, bufRicevuta);
}

/** Parsa il corpo x-www-form-urlencoded che Twilio invia (non JSON).
 * Riceve la stringa già letta dal server HTTP (che centralizza la
 * lettura dello stream per tutte le rotte) — non legge `req` da solo,
 * per evitare di consumare due volte lo stesso stream. */
function parseCorpoForm(corpoStringa) {
  return querystring.parse(corpoStringa);
}

/**
 * Handler della chiamata in arrivo — da collegare a POST /voice/incoming
 * nel webhook Twilio (Console Twilio → numero → "A Call Comes In").
 * Ritorna l'XML TwiML pronto da scrivere nella risposta HTTP.
 */
function gestisciChiamataInArrivo(corpoStringa, { nuovaSessione, avanza, sessioni }) {
  const corpo = parseCorpoForm(corpoStringa);
  const sessione = nuovaSessione();
  sessioni.set(sessione.id, sessione);
  sessione.numeroChiamante = corpo.From || 'sconosciuto'; // per le notifiche al titolare
  const messaggi = [];
  avanza(sessione, messaggi);
  const actionUrl = `/voice/gather/${sessione.id}`;
  return generaTwiML(messaggi, { finita: sessione.finita, actionUrl });
}

/**
 * Handler della risposta vocale del chiamante — da collegare a
 * POST /voice/gather/:sessionId (l'URL che generaTwiML mette in `action`).
 * Ritorna l'XML TwiML pronto da scrivere nella risposta HTTP.
 */
function gestisciRispostaVocale(corpoStringa, sessionId, { ricevi, sessioni }) {
  const sessione = sessioni.get(sessionId);
  if (!sessione) return generaTwiML(['Sessione scaduta, richiami per favore.'], { finita: true });
  const corpo = parseCorpoForm(corpoStringa);
  const testo = corpo.SpeechResult || '';
  const messaggi = ricevi(sessione, testo);
  const actionUrl = `/voice/gather/${sessione.id}`;
  return generaTwiML(messaggi, { finita: sessione.finita, actionUrl });
}

module.exports = { generaTwiML, parseCorpoForm, gestisciChiamataInArrivo, gestisciRispostaVocale, escapeXml, validaFirmaTwilio };
