#!/usr/bin/env node
/**
 * Test del caricamento .env (integrazioni/config.js).
 *
 * CONFIGURAZIONE.md dice "copia i valori in .env" e dà per scontato che
 * basti quello per andare live. Prima di caricaDotEnv() nessun codice del
 * progetto leggeva mai quel file: un pilota che lo compilava alla lettera
 * e provava `node server.js` in locale restava comunque in modalità MOCK,
 * senza nessun errore che lo segnalasse. Questo verifica che un .env
 * venga davvero letto — e che l'ambiente reale (Render, Railway, ...)
 * vinca comunque sul file, come dotenv.
 *
 * Uso: node integrazioni/config.test.js
 */
'use strict';
const fs = require('fs');
const path = require('path');
const os = require('os');
const { caricaDotEnv } = require('./config');

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

// File temporaneo isolato: non tocca l'eventuale .env vero del progetto.
const tmpEnv = path.join(os.tmpdir(), `voice-receptionist-test-${process.pid}.env`);
fs.writeFileSync(
  tmpEnv,
  [
    '# commento da ignorare',
    '',
    'TEST_CHIAVE_SEMPLICE=valore',
    'TEST_CHIAVE_QUOTATA="valore tra virgolette"',
    "TEST_CHIAVE_APICI='valore tra apici'",
    'TEST_CHIAVE_CON_SPAZI =   valore con spazi   ',
  ].join('\n')
);

delete process.env.TEST_CHIAVE_SEMPLICE;
delete process.env.TEST_CHIAVE_QUOTATA;
delete process.env.TEST_CHIAVE_APICI;
delete process.env.TEST_CHIAVE_CON_SPAZI;
process.env.TEST_CHIAVE_GIA_IMPOSTATA = 'valore-ambiente-reale';

caricaDotEnv(tmpEnv);

verifica('valore semplice caricato in process.env', process.env.TEST_CHIAVE_SEMPLICE === 'valore');
verifica('valore tra virgolette doppie senza le virgolette', process.env.TEST_CHIAVE_QUOTATA === 'valore tra virgolette');
verifica('valore tra apici singoli senza gli apici', process.env.TEST_CHIAVE_APICI === 'valore tra apici');
verifica('spazi intorno a chiave/valore ignorati', process.env.TEST_CHIAVE_CON_SPAZI === 'valore con spazi');

// Una variabile già impostata (come farebbe l'hosting reale) non deve
// essere sovrascritta dal file — altrimenti un valore MOCK_ nel .env
// rimasto per sbaglio potrebbe silenziosamente rimpiazzare la credenziale
// vera impostata nel pannello di Render/Railway.
fs.writeFileSync(tmpEnv, 'TEST_CHIAVE_GIA_IMPOSTATA=valore-dal-file\n');
caricaDotEnv(tmpEnv);
verifica("una variabile d'ambiente reale vince sempre sul file .env", process.env.TEST_CHIAVE_GIA_IMPOSTATA === 'valore-ambiente-reale');

caricaDotEnv(path.join(os.tmpdir(), 'questo-file-non-esiste.env'));
verifica('.env mancante non genera eccezioni', true);

fs.unlinkSync(tmpEnv);

console.log(`\n${ok} verifiche passate, ${falliti} fallite.`);
console.log(falliti === 0 ? '\n✅ TEST OK (integrazioni/config.js)' : '\n❌ TEST FALLITO (integrazioni/config.js)');
process.exit(falliti === 0 ? 0 : 1);
