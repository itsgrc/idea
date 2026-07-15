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
 * Integrazioni esterne (WhatsApp, calendario) — vedi integrazioni/.
 * Disattivate di default (INTEGRAZIONI_ATTIVE=1 per accenderle): così
 * test, demo e simulatore restano puliti e veloci senza doverle
 * disabilitare a mano. In produzione si accendono con una variabile
 * d'ambiente, zero modifiche al codice. Con credenziali ancora mock,
 * "attive" significa comunque solo simulare (loggare), mai spendere
 * credito o chiamare API vere per sbaglio.
 * ------------------------------------------------------------------ */
const INTEGRAZIONI_ATTIVE = process.env.INTEGRAZIONI_ATTIVE === '1';
const { inviaWhatsAppTitolare, messaggioPerEvento } = require('./integrazioni/notifiche');
const { creaEventoAppuntamento } = require('./integrazioni/calendario');
const { gestisciChiamataInArrivo, gestisciRispostaVocale, parseCorpoForm, validaFirmaTwilio } = require('./integrazioni/telefonia');
const { CONFIG, modalitaSimulata } = require('./integrazioni/config');

function notificaSeAttivo(evento) {
  if (!INTEGRAZIONI_ATTIVE) return;
  inviaWhatsAppTitolare(messaggioPerEvento(evento)).catch((err) => console.error('⚠️  notifica fallita:', err.message));
}
function creaEventoCalendarioSeAttivo(dettagli) {
  if (!INTEGRAZIONI_ATTIVE) return;
  creaEventoAppuntamento(dettagli).catch((err) => console.error('⚠️  evento calendario fallito:', err.message));
}

/* ------------------------------------------------------------------ *
 * Log eventi — ogni chiamata, appuntamento, urgenza e fallback finisce
 * su un file JSONL. È la materia prima di valore.js (report ROI) e
 * suggerimenti.js (motore di auto-apprendimento): il motore da solo
 * logga, gli strumenti a valle trasformano i log in soldi e in
 * miglioramenti del flusso. Disattivato in --test per non sporcare
 * l'output delle verifiche automatiche.
 * ------------------------------------------------------------------ */
const EVENTI_LOG = process.env.EVENTI_LOG || (process.argv.includes('--test') ? null : 'eventi.jsonl');
function logEvento(record) {
  if (!EVENTI_LOG) return;
  fs.appendFileSync(EVENTI_LOG, JSON.stringify(record) + '\n');
}
function emit(sessione, evento) {
  const record = { ts: Date.now(), flow: flow.nome, session_id: sessione.id, ...evento };
  sessione.eventi.push(record);
  logEvento(record);
  return record;
}

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
    const evento = emit(sessione, { tipo: 'appuntamento_creato', dati: { ...sessione.dati }, numero_chiamante: sessione.numeroChiamante });
    notificaSeAttivo(evento);
    creaEventoCalendarioSeAttivo(sessione.dati);
  },
  notifica_urgente_titolare(sessione) {
    const evento = emit(sessione, { tipo: 'urgenza_notificata', dati: { ...sessione.dati }, numero_chiamante: sessione.numeroChiamante });
    notificaSeAttivo(evento);
  },
  verifica_stato_veicolo(sessione) {
    const evento = emit(sessione, { tipo: 'richiesta_stato_veicolo', targa: sessione.dati.targa, numero_chiamante: sessione.numeroChiamante });
    notificaSeAttivo(evento);
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
  const sessione = { id, stato: 'saluto', dati: {}, eventi: [], attesa_input: null, finita: false, creata: Date.now() };
  sessioni.set(id, sessione);
  emit(sessione, { tipo: 'chiamata_iniziata' });
  return sessione;
}

// Pulizia periodica: senza questo, ogni chiamata (conclusa o abbandonata
// a metà) resterebbe per sempre in memoria — un memory leak su un server
// che gira per settimane. Rimuove le sessioni concluse e quelle rimaste
// "a metà" (es. il chiamante ha riagganciato senza completare) da oltre
// SESSIONE_MAX_ETA_MS.
const SESSIONE_MAX_ETA_MS = 30 * 60 * 1000; // 30 minuti
function pulisciSessioni() {
  const ora = Date.now();
  for (const [id, sessione] of sessioni) {
    if (sessione.finita || ora - sessione.creata > SESSIONE_MAX_ETA_MS) sessioni.delete(id);
  }
  // Stessa disciplina anche per la mappa del rate limiter: senza pulizia
  // sarebbe lei stessa un memory leak, l'esatto problema che dovrebbe prevenire.
  for (const [ip, richieste] of richiestePerIp) {
    const recenti = richieste.filter((t) => ora - t < RATE_LIMIT_FINESTRA_MS);
    if (recenti.length === 0) richiestePerIp.delete(ip);
    else richiestePerIp.set(ip, recenti);
  }
}

// Esegue gli stati "parlanti" finché non serve input dell'utente o la chiamata finisce.
function avanza(sessione, risposte) {
  while (!sessione.finita) {
    const stato = flow.stati[sessione.stato];
    if (!stato) throw new Error(`Stato sconosciuto: ${sessione.stato}`);

    if (stato.messaggio) risposte.push(interpola(stato.messaggio, sessione));
    if (stato.azione) {
      // Azioni note = side effect dedicato; azioni solo dichiarate nel flusso
      // diventano comunque eventi tracciati (il flusso comanda, non il codice).
      if (Azioni[stato.azione]) Azioni[stato.azione](sessione);
      else emit(sessione, { tipo: stato.azione, dati: { ...sessione.dati } });
    }
    if (stato.terminale) {
      emit(sessione, { tipo: 'chiamata_conclusa', stato_finale: sessione.stato });
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
      emit(sessione, { tipo: 'fallback', stato: sessione.stato, testo: testo.trim() });
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
 * Demo web — chat nel browser su GET /, per far provare la demo ai
 * clienti senza terminale. Usa la stessa API del webhook telefonico.
 * ------------------------------------------------------------------ */
const WEB_HTML = `<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Demo — ${flow.nome}</title><style>
:root{--bg:#F7F9FB;--card:#fff;--ink:#12263A;--muted:#5A6B7C;--acc:#E4572E;--soft:#FDEEE8;--line:#DCE4EC}
@media(prefers-color-scheme:dark){:root{--bg:#0D1B29;--card:#132436;--ink:#E8EEF4;--muted:#93A6B8;--acc:#FF7A50;--soft:#27201E;--line:#24384C}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,sans-serif;display:flex;flex-direction:column;min-height:100vh}
header{padding:16px 20px;border-bottom:1px solid var(--line)}header b{font-size:15px}header span{display:block;font-size:12px;color:var(--muted)}
#chat{flex:1;max-width:640px;width:100%;margin:0 auto;padding:20px;display:flex;flex-direction:column;gap:8px}
.m{max-width:82%;padding:10px 14px;border-radius:14px;font-size:15px;line-height:1.5}
.ai{background:var(--soft);border-bottom-left-radius:4px;align-self:flex-start}
.me{background:var(--card);border:1px solid var(--line);border-bottom-right-radius:4px;align-self:flex-end}
form{display:flex;gap:8px;max-width:640px;width:100%;margin:0 auto;padding:0 20px 20px}
input{flex:1;padding:12px 14px;border:1px solid var(--line);border-radius:10px;background:var(--card);color:var(--ink);font-size:15px}
button{background:var(--acc);color:#fff;border:0;border-radius:10px;padding:12px 20px;font-weight:700;font-size:15px;cursor:pointer}
#done{display:none;text-align:center;color:var(--muted);font-size:13px;padding:0 0 16px}
</style></head><body>
<header><b>📞 Demo chiamata — ${flow.nome}</b><span>Scrivi come se stessi parlando al telefono. In produzione questa conversazione è vocale.</span></header>
<div id="chat"></div>
<p id="done">✅ Chiamata conclusa — ricarica la pagina per simularne un'altra.</p>
<form id="f"><input id="t" autocomplete="off" placeholder="La tua risposta…" autofocus><button>Invia</button></form>
<script>
const chat=document.getElementById('chat'),f=document.getElementById('f'),t=document.getElementById('t');
let sid=null;
function add(txt,cls){const d=document.createElement('div');d.className='m '+cls;d.textContent=txt;chat.appendChild(d);d.scrollIntoView({block:'end'})}
async function start(){const r=await fetch('/call/start',{method:'POST'});const j=await r.json();sid=j.session_id;j.messages.forEach(m=>add(m,'ai'))}
f.addEventListener('submit',async e=>{e.preventDefault();const v=t.value.trim();if(!v||!sid)return;add(v,'me');t.value='';
const r=await fetch('/call/'+sid+'/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:v})});
const j=await r.json();j.messages.forEach(m=>add(m,'ai'));
if(j.done){document.getElementById('done').style.display='block';f.style.display='none'}});
start();
</script></body></html>`;

/* ------------------------------------------------------------------ *
 * API HTTP — la stessa interfaccia che userà il webhook telefonico.
 *   GET  /                           → demo web (chat)
 *   POST /call/start                 → { session_id, messages }
 *   POST /call/:id/message {text}    → { messages, done, events }
 *   POST /voice/incoming             → webhook Twilio (TwiML), chiamata reale
 *   POST /voice/gather/:sessionId    → webhook Twilio (TwiML), risposta vocale
 * ------------------------------------------------------------------ */
// Anti-spam su /call/start (il widget demo pubblico della homepage, senza
// autenticazione per design): senza un limite, chiunque potrebbe creare
// migliaia di sessioni al minuto, saturando memoria prima che la pulizia
// periodica intervenga.
const RATE_LIMIT_MAX = parseInt(process.env.RATE_LIMIT_MAX || '20', 10);
const RATE_LIMIT_FINESTRA_MS = 60 * 60 * 1000; // per ora, per IP
const richiestePerIp = new Map();
function rateLimitSuperato(ip) {
  const ora = Date.now();
  const richieste = (richiestePerIp.get(ip) || []).filter((t) => ora - t < RATE_LIMIT_FINESTRA_MS);
  richieste.push(ora);
  richiestePerIp.set(ip, richieste);
  return richieste.length > RATE_LIMIT_MAX;
}

function api() {
  const server = http.createServer((req, res) => {
    const rispondi = (code, body) => {
      res.writeHead(code, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(body));
    };
    const rispondiXml = (xml) => {
      res.writeHead(200, { 'Content-Type': 'text/xml; charset=utf-8' });
      res.end(xml);
    };
    let corpo = '';
    req.on('data', (c) => (corpo += c));
    req.on('end', () => {
      try {
        if (req.method === 'POST' && req.url === '/call/start') {
          if (rateLimitSuperato(req.socket.remoteAddress)) return rispondi(429, { error: 'troppe richieste, riprova più tardi' });
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
        if (req.method === 'POST' && (req.url === '/voice/incoming' || /^\/voice\/gather\//.test(req.url))) {
          // SICUREZZA: verifica che la richiesta arrivi davvero da Twilio,
          // non da chiunque abbia scoperto l'URL del webhook (vedi
          // integrazioni/telefonia.js per i dettagli dell'algoritmo).
          // Saltata se le credenziali sono ancora mock: non c'è nulla di
          // reale da validare, e la demo via curl resta testabile.
          if (!modalitaSimulata('twilio')) {
            const urlCompleto = CONFIG.server.publicUrl.replace(/\/$/, '') + req.url;
            const valida = validaFirmaTwilio({
              urlCompleto,
              params: parseCorpoForm(corpo),
              firmaRicevuta: req.headers['x-twilio-signature'],
              authToken: CONFIG.twilio.authToken,
            });
            if (!valida) {
              res.writeHead(403, { 'Content-Type': 'text/plain' });
              return res.end('Firma non valida');
            }
          }
        }
        if (req.method === 'POST' && req.url === '/voice/incoming') {
          return rispondiXml(gestisciChiamataInArrivo(corpo, { nuovaSessione, avanza, sessioni }));
        }
        const g = req.url.match(/^\/voice\/gather\/([\w-]+)$/);
        if (req.method === 'POST' && g) {
          return rispondiXml(gestisciRispostaVocale(corpo, g[1], { ricevi, sessioni }));
        }
        if (req.url === '/health') return rispondi(200, { ok: true, flow: flow.nome });
        if (req.method === 'GET' && req.url === '/') {
          res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
          return res.end(WEB_HTML);
        }
        rispondi(404, { error: 'not found' });
      } catch (err) {
        rispondi(500, { error: err.message });
      }
    });
  });
  // .unref(): il timer di pulizia non deve mai impedire al processo di
  // terminare (rilevante per --test e per chi importa server.js da altri
  // script, dove questa funzione non gira comunque).
  setInterval(pulisciSessioni, 5 * 60 * 1000).unref();
  server.listen(3000, () => console.log(`🎙️  Voice receptionist API su :3000 — flusso: "${flow.nome}"`));
}

module.exports = { nuovaSessione, ricevi, avanza, flow, EVENTI_LOG };

if (require.main === module) {
  if (process.argv.includes('--demo')) demo();
  else if (process.argv.includes('--test')) test();
  else api();
}
