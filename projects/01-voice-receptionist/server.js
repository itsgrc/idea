#!/usr/bin/env node
/**
 * Voice AI Receptionist — motore conversazionale MVP (zero dipendenze).
 *
 * La logica di business vive nel flusso JSON (flows/*.json): stati, intenti,
 * azioni. Questo file è solo il motore che la esegue. In produzione la stessa
 * macchina a stati riceve testo da STT (telefonata) invece che da tastiera,
 * e l'intent matching a parole chiave viene sostituito/affiancato da un LLM
 * (vedi LLMAdapter più sotto).
 *
 * Uso:
 *   node server.js --demo    conversazione interattiva nel terminale
 *   node server.js --test    conversazione scriptata (exit code 0 = ok)
 *   node server.js           API HTTP su :3000
 */
'use strict';

const http = require('http');
const fs = require('fs');
const path = require('path');
const readline = require('readline');
const crypto = require('crypto');

const FLOW_PATH = process.env.FLOW || path.join(__dirname, 'flows', 'dentista.json');
const flow = JSON.parse(fs.readFileSync(FLOW_PATH, 'utf8'));

/* ------------------------------------------------------------------ *
 * LLMAdapter — punto di innesto per il modello linguistico.
 * In MVP: matching a parole chiave. In produzione: sostituire classify()
 * con una chiamata all'API Claude che riceve la frase dell'utente e la
 * lista di intenti possibili, e restituisce l'intento più probabile.
 * ------------------------------------------------------------------ */
const LLMAdapter = {
  classify(testo, intenti) {
    const t = testo.toLowerCase();
    let migliore = null;
    let punteggio = 0;
    for (const [nome, def] of Object.entries(intenti)) {
      const colpi = def.parole.filter((p) => t.includes(p)).length;
      if (colpi > punteggio) {
        punteggio = colpi;
        migliore = nome;
      }
    }
    return migliore;
  },
};

/* ------------------------------------------------------------------ *
 * Azioni — side effect verso il mondo reale. In MVP loggano soltanto;
 * in produzione: API calendario, SMS, WhatsApp del titolare.
 * ------------------------------------------------------------------ */
const Azioni = {
  crea_appuntamento(sessione) {
    sessione.eventi.push({ tipo: 'appuntamento_creato', dati: { ...sessione.dati } });
  },
  notifica_urgente_titolare(sessione) {
    sessione.eventi.push({ tipo: 'urgenza_notificata', numero: sessione.id });
  },
};

/* ------------------------------------------------------------------ *
 * Macchina a stati
 * ------------------------------------------------------------------ */
const sessioni = new Map();

function interpola(msg, sessione) {
  return msg.replace(/\{(\w+)\}/g, (_, k) => sessione.dati[k] ?? flow[k] ?? `{${k}}`);
}

function nuovaSessione() {
  const id = crypto.randomUUID();
  const sessione = { id, stato: 'saluto', dati: {}, eventi: [], attesa_input: null, finita: false };
  sessioni.set(id, sessione);
  return sessione;
}

// Esegue gli stati "parlanti" finché non serve input dell'utente o la chiamata finisce.
function avanza(sessione, risposte) {
  while (!sessione.finita) {
    const stato = flow.stati[sessione.stato];
    if (!stato) throw new Error(`Stato sconosciuto: ${sessione.stato}`);

    if (stato.messaggio) risposte.push(interpola(stato.messaggio, sessione));
    if (stato.azione && Azioni[stato.azione]) Azioni[stato.azione](sessione);
    if (stato.terminale) {
      sessione.finita = true;
      return;
    }
    if (stato.salva_in || stato.intenti) {
      // Serve l'input dell'utente prima di proseguire.
      sessione.attesa_input = { salva_in: stato.salva_in, intenti: stato.intenti, fallback: stato.fallback, vai_a: stato.vai_a };
      return;
    }
    sessione.stato = stato.vai_a;
  }
}

function ricevi(sessione, testo) {
  const risposte = [];
  const attesa = sessione.attesa_input;

  if (!attesa) {
    avanza(sessione, risposte);
    return risposte;
  }

  if (attesa.salva_in) sessione.dati[attesa.salva_in] = testo.trim();

  if (attesa.intenti) {
    const intento = LLMAdapter.classify(testo, attesa.intenti);
    if (!intento) {
      risposte.push(attesa.fallback || 'Non ho capito, può ripetere?');
      return risposte; // resta in attesa sullo stesso stato
    }
    sessione.stato = attesa.intenti[intento].vai_a;
  } else {
    sessione.stato = attesa.vai_a;
  }

  sessione.attesa_input = null;
  avanza(sessione, risposte);
  return risposte;
}

/* ------------------------------------------------------------------ *
 * Modalità demo interattiva
 * ------------------------------------------------------------------ */
function demo() {
  const sessione = nuovaSessione();
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  const saluti = [];
  avanza(sessione, saluti);
  console.log('📞 *squillo* — chiamata in arrivo (scrivi come se stessi parlando al telefono, Ctrl+C per riagganciare)\n');
  saluti.forEach((r) => console.log(`🤖 ${r}`));

  const chiedi = () =>
    rl.question('👤 ', (testo) => {
      ricevi(sessione, testo).forEach((r) => console.log(`🤖 ${r}`));
      if (sessione.finita) {
        console.log('\n📋 Eventi generati:', JSON.stringify(sessione.eventi, null, 2));
        rl.close();
        return;
      }
      chiedi();
    });
  chiedi();
}

/* ------------------------------------------------------------------ *
 * Modalità test: conversazione scriptata, verifica il flusso completo.
 * ------------------------------------------------------------------ */
function test() {
  const sessione = nuovaSessione();
  const out = [];
  avanza(sessione, out);
  const battute = ['Vorrei prenotare una pulizia dei denti', 'Mario Rossi', 'meglio il pomeriggio', 'no grazie'];
  for (const b of battute) {
    out.push(`> ${b}`);
    ricevi(sessione, b).forEach((r) => out.push(r));
    if (sessione.finita) break;
  }
  console.log(out.join('\n'));
  const ok = sessione.eventi.some((e) => e.tipo === 'appuntamento_creato') && sessione.dati.nome === 'Mario Rossi';
  console.log(ok ? '\n✅ TEST OK: appuntamento creato per Mario Rossi' : '\n❌ TEST FALLITO');
  process.exit(ok ? 0 : 1);
}

/* ------------------------------------------------------------------ *
 * API HTTP — la stessa interfaccia che userà il webhook telefonico.
 *   POST /call/start                 → { session_id, messages }
 *   POST /call/:id/message {text}    → { messages, done, events }
 * ------------------------------------------------------------------ */
function api() {
  const server = http.createServer((req, res) => {
    const rispondi = (code, body) => {
      res.writeHead(code, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(body));
    };
    let corpo = '';
    req.on('data', (c) => (corpo += c));
    req.on('end', () => {
      try {
        if (req.method === 'POST' && req.url === '/call/start') {
          const sessione = nuovaSessione();
          const messages = [];
          avanza(sessione, messages);
          return rispondi(200, { session_id: sessione.id, messages });
        }
        const m = req.url.match(/^\/call\/([\w-]+)\/message$/);
        if (req.method === 'POST' && m) {
          const sessione = sessioni.get(m[1]);
          if (!sessione) return rispondi(404, { error: 'sessione non trovata' });
          const { text } = JSON.parse(corpo || '{}');
          const messages = ricevi(sessione, String(text || ''));
          return rispondi(200, { messages, done: sessione.finita, events: sessione.eventi });
        }
        if (req.url === '/health') return rispondi(200, { ok: true, flow: flow.nome });
        rispondi(404, { error: 'not found' });
      } catch (err) {
        rispondi(500, { error: err.message });
      }
    });
  });
  server.listen(3000, () => console.log(`🎙️  Voice receptionist API su :3000 — flusso: "${flow.nome}"`));
}

if (process.argv.includes('--demo')) demo();
else if (process.argv.includes('--test')) test();
else api();
