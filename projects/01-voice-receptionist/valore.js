#!/usr/bin/env node
/**
 * valore.js — il Report ROI: il documento che chiude la vendita al giorno 30
 * del pilota gratuito (vedi GO-TO-MARKET.md). Legge il log eventi del motore
 * (eventi.jsonl) e traduce ogni evento nel suo valore economico, configurato
 * dal titolare in fase di onboarding (valori/<flusso>.json).
 *
 * Il punto: un log di chiamate non vende nulla. "23 chiamate gestite" non
 * convince nessuno. "2.400 € di valore recuperato, il servizio ne costa 300"
 * sì — ed è un numero che nessun competitor generalista (Twilio+GPT a mano)
 * calcola automaticamente per il cliente.
 *
 * Uso:
 *   node valore.js --demo                               genera dati e mostra il report
 *   node valore.js eventi.jsonl valori/dentista.json     sui dati reali
 */
'use strict';
const fs = require('fs');
const path = require('path');

function leggiEventi(logPath) {
  if (!fs.existsSync(logPath)) return [];
  return fs
    .readFileSync(logPath, 'utf8')
    .split('\n')
    .filter(Boolean)
    .map((r) => JSON.parse(r));
}

function leggiValori(valoriPath) {
  const v = JSON.parse(fs.readFileSync(valoriPath, 'utf8'));
  delete v._nota;
  return v;
}

function calcolaReport(eventi, valori) {
  const conteggi = {};
  for (const e of eventi) conteggi[e.tipo] = (conteggi[e.tipo] || 0) + 1;

  const chiamateIniziate = conteggi.chiamata_iniziata || 0;
  const chiamateConcluse = conteggi.chiamata_conclusa || 0;
  const fallback = conteggi.fallback || 0;
  const turniTotali = eventi.filter((e) => ['fallback', 'appuntamento_creato', 'urgenza_notificata', 'richiesta_stato_veicolo'].includes(e.tipo)).length + fallback;

  const righeValore = [];
  let totale = 0;
  for (const [tipo, valoreUnitario] of Object.entries(valori)) {
    const n = conteggi[tipo] || 0;
    const subtotale = n * valoreUnitario;
    totale += subtotale;
    if (n > 0) righeValore.push({ tipo, n, valoreUnitario, subtotale });
  }

  const tassoComprensione = turniTotali > 0 ? 1 - fallback / turniTotali : 1;

  return { chiamateIniziate, chiamateConcluse, fallback, righeValore, totale, tassoComprensione };
}

const ETICHETTE = {
  appuntamento_creato: 'Appuntamenti fissati',
  urgenza_notificata: 'Urgenze gestite',
  richiesta_stato_veicolo: 'Richieste stato veicolo',
};

function stampaReport(r, { periodo = 'periodo analizzato', costoMensile = 300 } = {}) {
  console.log(`\n${'═'.repeat(64)}`);
  console.log(`📊 REPORT ROI — ${periodo}`);
  console.log('═'.repeat(64));
  console.log(`Chiamate gestite dall'assistente: ${r.chiamateIniziate}  (concluse: ${r.chiamateConcluse})`);
  console.log(`Tasso di comprensione: ${(r.tassoComprensione * 100).toFixed(0)}%  (${r.fallback} richieste non riconosciute)`);
  console.log('-'.repeat(64));
  for (const riga of r.righeValore) {
    const etichetta = (ETICHETTE[riga.tipo] || riga.tipo).padEnd(28);
    console.log(`${etichetta} ${String(riga.n).padStart(4)} × ${String(riga.valoreUnitario).padStart(4)} € = ${riga.subtotale.toLocaleString('it-IT')} €`);
  }
  console.log('-'.repeat(64));
  console.log(`💶 VALORE RECUPERATO TOTALE: ${r.totale.toLocaleString('it-IT')} €`);
  console.log(`💳 Costo del servizio: ${costoMensile} €`);
  const roi = costoMensile > 0 ? r.totale / costoMensile : 0;
  console.log(`📈 Ritorno: ${roi.toFixed(1)}× — per ogni euro pagato, ${roi.toFixed(1)} € recuperati`);
  console.log('═'.repeat(64));
  console.log('Questo è il numero da mostrare al cliente il giorno 30 del pilota.');
  console.log('Non "quante chiamate", ma "quanti soldi altrimenti persi".\n');
}

function main() {
  let logPath, valoriPath;
  if (process.argv.includes('--demo')) {
    const { genera, LOG_PATH } = require('./simulatore.js');
    if (!fs.existsSync(LOG_PATH)) genera(25);
    logPath = LOG_PATH;
    valoriPath = path.join(__dirname, 'valori', 'dentista.json');
  } else {
    logPath = process.argv[2];
    valoriPath = process.argv[3];
    if (!logPath || !valoriPath) {
      console.error('Uso: node valore.js <eventi.jsonl> <valori/flusso.json>  oppure  node valore.js --demo');
      process.exit(1);
    }
  }
  const eventi = leggiEventi(logPath);
  const valori = leggiValori(valoriPath);
  const report = calcolaReport(eventi, valori);
  stampaReport(report);
}

module.exports = { leggiEventi, leggiValori, calcolaReport };
if (require.main === module) main();
