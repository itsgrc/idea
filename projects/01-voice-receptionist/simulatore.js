#!/usr/bin/env node
/**
 * Simulatore di chiamate — genera un log eventi realistico per far vedere
 * (senza aspettare 30 giorni di pilota reale) cosa producono valore.js e
 * suggerimenti.js. Guida l'engine reale (server.js) attraverso conversazioni
 * scriptate, incluse alcune domande che il flusso NON sa gestire — servono
 * a dimostrare il motore di auto-apprendimento.
 *
 * Casuale ma deterministico (mulberry32 con seme fisso): la demo produce
 * sempre lo stesso output, riproducibile per screenshot e verifiche.
 *
 * Uso:
 *   node simulatore.js                    # 25 chiamate sul flusso dentista
 *   node simulatore.js --n 50             # 50 chiamate
 *   FLOW=flows/officina.json node simulatore.js
 */
'use strict';
const fs = require('fs');
const path = require('path');

const LOG_PATH = path.join(__dirname, 'eventi-demo.jsonl');

function mulberry32(seme) {
  return function () {
    seme = (seme + 0x6d2b79f5) | 0;
    let t = Math.imul(seme ^ (seme >>> 15), seme | 1);
    t = (t + Math.imul(t ^ (t >>> 7), t | 61)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const rng = mulberry32(42);

const NOMI = ['Mario Rossi', 'Laura Bianchi', 'Giuseppe Verdi', 'Anna Ferrari', 'Paolo Colombo', 'Chiara Ricci', 'Marco Esposito', 'Sara Romano'];
const nomeCasuale = () => NOMI[Math.floor(rng() * NOMI.length)];
const TARGHE = ['AB123CD Panda blu', 'FG456HL Golf grigia', 'XY789ZK 500 bianca', 'LM234NP Clio rossa'];
const targaCasuale = () => TARGHE[Math.floor(rng() * TARGHE.length)];

// I copioni (battute che finge di dire il chiamante) vivono dentro il flusso
// stesso (flow.simulazione.copioni), non qui: ogni settore ha il proprio
// vocabolario e i propri intenti, e un copione scritto contro le parole
// chiave di un flusso genera conversazioni fuori sequenza (o solo fallback)
// su un altro — stessa filosofia "il flusso comanda, non il codice" usata
// per gli stati e per gli script di `--test`. {{nome}} e {{targa}} nelle
// battute vengono sostituiti con un valore casuale (ma deterministico).
function generaBattute(copione) {
  return copione.battute.map((b) => (b === '{{nome}}' ? nomeCasuale() : b === '{{targa}}' ? targaCasuale() : b));
}

function scegliCopione(copioni) {
  const totale = copioni.reduce((s, c) => s + c.peso, 0);
  let r = rng() * totale;
  for (const c of copioni) {
    if (r < c.peso) return c;
    r -= c.peso;
  }
  return copioni[0];
}

function genera(n) {
  if (fs.existsSync(LOG_PATH)) fs.unlinkSync(LOG_PATH);
  process.env.EVENTI_LOG = LOG_PATH;
  // require DOPO aver settato EVENTI_LOG: il motore legge l'env var al load.
  const { nuovaSessione, ricevi, avanza, flow } = require('./server.js');

  const copioni = flow.simulazione && flow.simulazione.copioni;
  if (!copioni || !copioni.length) {
    throw new Error(`Il flusso "${flow.nome}" non definisce copioni di simulazione (campo "simulazione.copioni" mancante nel suo file flows/*.json).`);
  }

  for (let i = 0; i < n; i++) {
    const sessione = nuovaSessione();
    avanza(sessione, []); // come fanno demo()/test()/api(): pronuncia il saluto e arriva al primo stato in attesa, PRIMA di inviare la prima battuta.
    const battute = generaBattute(scegliCopione(copioni));
    for (const b of battute) {
      if (sessione.finita) break;
      ricevi(sessione, b);
    }
  }
  console.log(`✅ Simulate ${n} chiamate sul flusso "${flow.nome}" → ${path.basename(LOG_PATH)}`);
  return LOG_PATH;
}

if (require.main === module) {
  const idx = process.argv.indexOf('--n');
  const n = idx > -1 ? parseInt(process.argv[idx + 1], 10) : 25;
  genera(n);
}

module.exports = { genera, LOG_PATH };
