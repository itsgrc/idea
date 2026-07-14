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

// Ogni copione è verificato a mano contro le parole chiave di flows/dentista.json,
// per non innescare corrispondenze accidentali (es. "visita" dentro una frase sul
// parcheggio farebbe matchare "appuntamento" invece di generare il fallback voluto).
const COPIONI = [
  { peso: 50, battute: () => ['Vorrei prenotare una pulizia dei denti', nomeCasuale(), 'meglio il pomeriggio'] },
  { peso: 20, battute: () => ['Ho un forte dolore a un dente', nomeCasuale()] },
  { peso: 15, battute: () => ['Avete un parcheggio per i pazienti?', 'Sì, vorrei comunque prenotare una visita', nomeCasuale(), 'la mattina se possibile'] },
  { peso: 15, battute: () => ['Posso pagare con il bancomat?', 'Va bene, allora vorrei fissare un appuntamento', nomeCasuale(), 'il pomeriggio'] },
];

function scegliCopione() {
  const totale = COPIONI.reduce((s, c) => s + c.peso, 0);
  let r = rng() * totale;
  for (const c of COPIONI) {
    if (r < c.peso) return c;
    r -= c.peso;
  }
  return COPIONI[0];
}

function genera(n) {
  if (fs.existsSync(LOG_PATH)) fs.unlinkSync(LOG_PATH);
  process.env.EVENTI_LOG = LOG_PATH;
  // require DOPO aver settato EVENTI_LOG: il motore legge l'env var al load.
  const { nuovaSessione, ricevi, avanza, flow } = require('./server.js');

  for (let i = 0; i < n; i++) {
    const sessione = nuovaSessione();
    avanza(sessione, []); // come fanno demo()/test()/api(): pronuncia il saluto e arriva al primo stato in attesa, PRIMA di inviare la prima battuta.
    const battute = scegliCopione().battute();
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
