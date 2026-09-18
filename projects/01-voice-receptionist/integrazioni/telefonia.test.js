#!/usr/bin/env node
/**
 * Test del webhook telefonico (integrazioni/telefonia.js) — zero dipendenze,
 * solo assert nativo. Il README dichiara questo codice "testato (incluse
 * richieste HTTP che simulano firme Twilio valide e contraffatte)": prima di
 * questo file quella verifica non esisteva come script rieseguibile, solo
 * come prova manuale fatta una tantum. Copre la parte più critica per la
 * sicurezza del progetto — senza una firma valida, un estraneo che scopre
 * l'URL del webhook potrebbe far scattare notifiche/eventi calendario falsi.
 *
 * Uso: node integrazioni/telefonia.test.js
 */
'use strict';
const assert = require('assert');
const crypto = require('crypto');
const { generaTwiML, gestisciChiamataInArrivo, gestisciRispostaVocale, validaFirmaTwilio } = require('./telefonia');

// Evita che require('../server') scriva su eventi.jsonl durante il test
// (stessa leva che usa `node server.js --test`, vedi server.js).
process.argv.push('--test');
const { nuovaSessione, ricevi, avanza } = require('../server');

let ok = 0;
let falliti = 0;
function verifica(descrizione, condizione) {
  if (condizione) {
    ok++;
  } else {
    falliti++;
    console.error(`❌ ${descrizione}`);
  }
}

/* ------------------------------------------------------------------ *
 * 1. Firma X-Twilio-Signature
 * ------------------------------------------------------------------ */
function firma({ urlCompleto, params, authToken }) {
  const stringaDaFirmare = Object.keys(params)
    .sort()
    .reduce((acc, k) => acc + k + params[k], urlCompleto);
  return crypto.createHmac('sha1', authToken).update(Buffer.from(stringaDaFirmare, 'utf-8')).digest('base64');
}

const url = 'https://tuoapp.onrender.com/voice/incoming';
const params = { From: '+390212345678', CallSid: 'CA123' };
const authToken = 'auth_token_di_prova';
const firmaGiusta = firma({ urlCompleto: url, params, authToken });

verifica('firma valida → accettata', validaFirmaTwilio({ urlCompleto: url, params, firmaRicevuta: firmaGiusta, authToken }) === true);
verifica('firma contraffatta → rifiutata', validaFirmaTwilio({ urlCompleto: url, params, firmaRicevuta: 'ZmlybWFmaW50YQ==', authToken }) === false);
verifica(
  'firma di lunghezza diversa dalla attesa → rifiutata (senza eccezioni)',
  validaFirmaTwilio({ urlCompleto: url, params, firmaRicevuta: 'corta', authToken }) === false
);
verifica(
  'parametro alterato dopo la firma → rifiutata',
  validaFirmaTwilio({ urlCompleto: url, params: { ...params, CallSid: 'CA999-alterato' }, firmaRicevuta: firmaGiusta, authToken }) === false
);
verifica(
  'URL diverso da quello firmato (es. PUBLIC_URL sbagliato) → rifiutata',
  validaFirmaTwilio({ urlCompleto: url + '/altro', params, firmaRicevuta: firmaGiusta, authToken }) === false
);
verifica('firma mancante → rifiutata', validaFirmaTwilio({ urlCompleto: url, params, firmaRicevuta: '', authToken }) === false);
verifica('authToken mancante → rifiutata', validaFirmaTwilio({ urlCompleto: url, params, firmaRicevuta: firmaGiusta, authToken: '' }) === false);

/* ------------------------------------------------------------------ *
 * 2. Escaping XML — il testo dettato dal chiamante finisce nei dati di
 *    sessione e poi in {placeholder} dei messaggi del flusso: se non
 *    fosse escapato correttamente, un chiamante potrebbe rompere (o
 *    iniettare markup in) il TwiML restituito a Twilio.
 * ------------------------------------------------------------------ */
const sessioniXml = new Map();
gestisciChiamataInArrivo('From=%2B390212345678', { nuovaSessione, avanza, sessioni: sessioniXml });
let [sidXml] = sessioniXml.keys();
gestisciRispostaVocale('SpeechResult=' + encodeURIComponent('Vorrei prenotare una pulizia dei denti'), sidXml, { ricevi, sessioni: sessioniXml });
const nomeOstile = 'Mario <Hangup/> & "Rossi" <b>test</b>';
const twimlConNomeOstile = gestisciRispostaVocale('SpeechResult=' + encodeURIComponent(nomeOstile), sidXml, { ricevi, sessioni: sessioniXml });

verifica('nome dettato con markup non finisce in chiaro nel TwiML', !twimlConNomeOstile.includes('<Hangup/> &'));
verifica('markup del chiamante viene escapato (&lt;b&gt;)', twimlConNomeOstile.includes('&lt;b&gt;'));
verifica('il TwiML resta XML valido (nessun tag "test" spurio)', !/<test>/.test(twimlConNomeOstile));

/* ------------------------------------------------------------------ *
 * 3. Chiamata end-to-end simulata attraverso i due handler del webhook
 *    (esattamente il percorso che segue una telefonata Twilio vera).
 * ------------------------------------------------------------------ */
const sessioniE2E = new Map();
const twimlSaluto = gestisciChiamataInArrivo('From=%2B393331234567&CallSid=CA-e2e', { nuovaSessione, avanza, sessioni: sessioniE2E });
verifica('la chiamata in arrivo risponde con <Gather> (aspetta la voce)', twimlSaluto.includes('<Gather'));
verifica('la chiamata in arrivo saluta con il nome dello studio', twimlSaluto.includes('Studio Dentistico Demo'));

const [sidE2E] = sessioniE2E.keys();
gestisciRispostaVocale('SpeechResult=' + encodeURIComponent('Vorrei prenotare una pulizia'), sidE2E, { ricevi, sessioni: sessioniE2E });
gestisciRispostaVocale('SpeechResult=' + encodeURIComponent('Mario Rossi'), sidE2E, { ricevi, sessioni: sessioniE2E });
const twimlFinale = gestisciRispostaVocale('SpeechResult=' + encodeURIComponent('pomeriggio'), sidE2E, { ricevi, sessioni: sessioniE2E });

verifica('la chiamata si conclude con <Hangup/>', twimlFinale.includes('<Hangup/>'));
verifica('la chiamata NON aspetta altra voce dopo l\'hangup (niente <Gather>)', !twimlFinale.includes('<Gather'));

const sidInesistente = gestisciRispostaVocale('SpeechResult=ciao', 'sessione-mai-esistita', { ricevi, sessioni: sessioniE2E });
verifica('una sessione scaduta/inesistente non fa crashare il webhook', sidInesistente.includes('richiami per favore'));

console.log(`\n${ok} verifiche passate, ${falliti} fallite.`);
console.log(falliti === 0 ? '\n✅ TEST OK (integrazioni/telefonia.js)' : '\n❌ TEST FALLITO (integrazioni/telefonia.js)');
process.exit(falliti === 0 ? 0 : 1);
