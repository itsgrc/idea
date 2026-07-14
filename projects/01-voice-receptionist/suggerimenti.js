#!/usr/bin/env node
/**
 * suggerimenti.js — motore di auto-apprendimento del flusso.
 *
 * Ogni volta che un chiamante dice qualcosa che il flusso non riconosce,
 * server.js logga un evento "fallback" con il testo esatto (vedi emit() in
 * server.js). Questo script raggruppa quelle frasi per parola-chiave
 * ricorrente e propone il nuovo intento da aggiungere — con lo snippet
 * JSON già pronto da incollare nel flusso.
 *
 * Il punto: più chiamate arrivano, più il flusso sa cosa gli manca. Un
 * concorrente che parte da zero non ha questi dati — è un vantaggio che
 * si accumula chiamata dopo chiamata e non si copia con un pitch deck.
 *
 * Uso:
 *   node suggerimenti.js --demo                      genera dati e analizza
 *   node suggerimenti.js eventi.jsonl flows/dentista.json
 */
'use strict';
const fs = require('fs');
const path = require('path');

const STOPWORD = new Set([
  'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'una', 'uno', 'di', 'a', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra',
  'e', 'o', 'ma', 'se', 'che', 'chi', 'cui', 'non', 'ho', 'ha', 'hai', 'sono', 'è', 'avete', 'ho', 'mi', 'si',
  'vorrei', 'posso', 'solo', 'anche', 'ancora', 'allora', 'ok', 'va', 'bene', 'buongiorno', 'grazie', 'per', 'favore',
  'prima', 'poi', 'quindi', 'comunque', 'questo', 'quella', 'questa', 'suo', 'sua', 'mio', 'mia', 'lei', 'lui',
]);

function leggiEventi(logPath) {
  return fs
    .readFileSync(logPath, 'utf8')
    .split('\n')
    .filter(Boolean)
    .map((r) => JSON.parse(r));
}

function tokenizza(testo) {
  return testo
    .toLowerCase()
    .replace(/[.,!?;:()"']/g, ' ')
    .split(/\s+/)
    .filter((w) => w.length >= 4 && !STOPWORD.has(w));
}

function clusterizza(fallbackEvents) {
  const conteggioParola = new Map(); // parola -> Set di indici fallback che la contengono
  const tokensPerEvento = fallbackEvents.map((e) => new Set(tokenizza(e.testo)));

  tokensPerEvento.forEach((tokens, idx) => {
    tokens.forEach((t) => {
      if (!conteggioParola.has(t)) conteggioParola.set(t, new Set());
      conteggioParola.get(t).add(idx);
    });
  });

  const paroleCandidate = [...conteggioParola.entries()]
    .filter(([, idxSet]) => idxSet.size >= 2)
    .sort((a, b) => b[1].size - a[1].size);

  const assegnati = new Set();
  const cluster = [];
  for (const [parola, idxSet] of paroleCandidate) {
    const nuovi = [...idxSet].filter((i) => !assegnati.has(i));
    if (nuovi.length < 2) continue;
    nuovi.forEach((i) => assegnati.add(i));
    cluster.push({
      parola,
      count: nuovi.length,
      esempi: nuovi.map((i) => fallbackEvents[i].testo),
    });
  }

  const isolati = fallbackEvents.filter((_, i) => !assegnati.has(i)).map((e) => e.testo);
  return { cluster, isolati };
}

function stampaSuggerimenti({ cluster, isolati }, nomeFlow) {
  console.log(`\n${'═'.repeat(64)}`);
  console.log(`🧠 MOTORE DI APPRENDIMENTO — suggerimenti per "${nomeFlow}"`);
  console.log('═'.repeat(64));

  if (cluster.length === 0) {
    console.log('Nessun pattern ricorrente nei fallback: il flusso copre bene le richieste ricevute finora.\n');
    return;
  }

  cluster.forEach((c, i) => {
    const nomeIntento = c.parola.replace(/[^a-z0-9]/gi, '_');
    console.log(`\n${i + 1}. Suggerimento: aggiungi l'intento "${c.parola}" (comparso ${c.count} volte)`);
    console.log('   Frasi che il flusso non ha capito:');
    c.esempi.slice(0, 4).forEach((e) => console.log(`     - "${e}"`));
    console.log('   Snippet da incollare in stati.intento.intenti:');
    console.log(`     "${nomeIntento}": { "parole": ["${c.parola}"], "vai_a": "info_${nomeIntento}" }`);
    console.log(`   (ricorda di creare anche lo stato "info_${nomeIntento}" con la risposta giusta)`);
  });

  if (isolati.length) {
    console.log(`\n📎 Altri ${isolati.length} casi isolati (nessun pattern ricorrente, monitorare):`);
    isolati.slice(0, 5).forEach((e) => console.log(`   - "${e}"`));
  }

  console.log(`\n${'═'.repeat(64)}`);
  console.log('Ogni suggerimento applicato oggi evita quel fallback a TUTTE le chiamate future.');
  console.log('Questo è il ciclo che rende il flusso più intelligente ogni settimana, senza riscrivere nulla da zero.\n');
}

function main() {
  let logPath, flowPath;
  if (process.argv.includes('--demo')) {
    const { genera, LOG_PATH } = require('./simulatore.js');
    if (!fs.existsSync(LOG_PATH)) genera(25);
    logPath = LOG_PATH;
    flowPath = path.join(__dirname, 'flows', 'dentista.json');
  } else {
    logPath = process.argv[2];
    flowPath = process.argv[3];
    if (!logPath) {
      console.error('Uso: node suggerimenti.js <eventi.jsonl> [flusso.json]   oppure   node suggerimenti.js --demo');
      process.exit(1);
    }
  }
  const eventi = leggiEventi(logPath);
  const fallbackEvents = eventi.filter((e) => e.tipo === 'fallback');
  const nomeFlow = flowPath ? JSON.parse(fs.readFileSync(flowPath, 'utf8')).nome : 'flusso';
  stampaSuggerimenti(clusterizza(fallbackEvents), nomeFlow);
}

module.exports = { clusterizza, tokenizza };
if (require.main === module) main();
