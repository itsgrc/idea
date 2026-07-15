#!/usr/bin/env python3
"""Dashboard famiglia + webhook stato chiamata + consenso GDPR (zero dipendenze).

Tre cose in un solo piccolo server (http.server, libreria standard):

1. GET  /                       la pagina che il figlio guarda la sera (stato di
                                 oggi 🟢/🟡/🔴 + report settimanale), letti da
                                 pattern_tracker.py sui dati REALI
2. POST /voice/stato-chiamata   webhook Twilio: riceve l'esito della chiamata
                                 uscente (risposta / non risposta) e lo registra
                                 nello stesso log che alimenta il punto 1
3. POST /consenso                registra il consenso esplicito dell'assistito
                                 raccolto alla prima chiamata (obbligatorio prima
                                 di considerare il servizio "attivo" — non è solo
                                 un modulo da spuntare, il servizio si rifiuta di
                                 mostrare dati finché il consenso non è registrato)

Dati sanitari (anche minimizzati: "ha preso le medicine sì/no", segnali di
malessere) sono dati particolari ex art. 9 GDPR: /stato e /report-settimanale
richiedono un token d'accesso dedicato a QUESTA famiglia (non una password
tradizionale — per un utente non tecnico un link privato da salvare nei
preferiti è più realistico di un login, ed è lo stesso modello di un link
calendario privato). Con il token ancora al valore mock, l'accesso è sempre
negato, come per LEAD_API_KEY/NEWSLETTER_API_KEY negli altri progetti.

Uso:
    python3 dashboard.py             # serve su :8030
    python3 dashboard.py --demo      # genera dati con pattern_tracker.demo() e mostra il flusso
"""
import base64
import hashlib
import hmac
import json
import os
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

from pattern_tracker import stato_di_oggi, report_settimanale, registra_no_risposta, leggi_eventi, pulisci_eventi_vecchi

CONSENSO_PATH = os.environ.get("CONSENSO_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "consenso.json"))
PORTA = int(os.environ.get("FILODIRETTO_DASHBOARD_PORT", "8030"))

# Un solo token per l'intero deployment (un assistito = un'installazione):
# copre sia l'operatore che registra il consenso in onboarding sia la
# famiglia che consulta lo stato — proporzionato al modello di questo
# prodotto (una famiglia per installazione), non una scelta valida per un
# SaaS multi-tenant come il progetto 04, che infatti usa login vero.
FAMIGLIA_ACCESS_TOKEN = os.environ.get("FILODIRETTO_ACCESS_TOKEN", "MOCK_cambia_questo_token_prima_di_andare_live")

TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "MOCK_AUTH_TOKEN")
PUBLIC_URL = os.environ.get("FILODIRETTO_PUBLIC_URL", "MOCK_https://tuoapp.esempio.it")

# Esiti di chiamata Twilio che contano come "non ha risposto" ai fini
# dell'escalation (MVP-SPEC.md): non solo "no-answer" in senso stretto.
ESITI_NON_RISPOSTA = {"no-answer", "busy", "failed", "canceled"}


def valida_firma_twilio(url_completo, params, firma_ricevuta, auth_token):
    """Porting Python dell'identica validazione già in uso nel progetto 01
    (integrazioni/telefonia.js, validaFirmaTwilio): HMAC-SHA1 dell'URL
    completo concatenato ai parametri ordinati, confronto a tempo costante."""
    if not firma_ricevuta or not auth_token:
        return False
    stringa = url_completo + "".join(f"{k}{params[k]}" for k in sorted(params))
    attesa = base64.b64encode(hmac.new(auth_token.encode("utf-8"), stringa.encode("utf-8"), hashlib.sha1).digest()).decode()
    return hmac.compare_digest(attesa, firma_ricevuta)


def token_autorizzato(token_fornito):
    if FAMIGLIA_ACCESS_TOKEN.startswith("MOCK_"):
        return False
    return hmac.compare_digest(str(token_fornito or ""), FAMIGLIA_ACCESS_TOKEN)


def leggi_consenso():
    if not os.path.exists(CONSENSO_PATH):
        return None
    with open(CONSENSO_PATH, encoding="utf-8") as f:
        return json.load(f)


def registra_consenso(dati):
    for campo in ("nome_assistito", "chi_raccoglie", "data_raccolta"):
        if not dati.get(campo):
            raise ValueError(f"campo mancante: {campo}")
    with open(CONSENSO_PATH, "w", encoding="utf-8") as f:
        json.dump(dati, f, ensure_ascii=False, indent=2)
    return dati


DASHBOARD_HTML = """<!doctype html><html lang="it"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FiloDiretto — come sta oggi</title><style>
:root{--bg:#FAFAF8;--card:#fff;--ink:#232323;--muted:#6B6B66;--line:#E4E3DD;--verde:#3E7A4E;--giallo:#B8860B;--rosso:#B3261E;--grigio:#8A8F94}
@media(prefers-color-scheme:dark){:root{--bg:#171715;--card:#212220;--ink:#EDEDEA;--muted:#A3A39C;--line:#37372F}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:system-ui,sans-serif;line-height:1.5}
main{max-width:480px;margin:0 auto;padding:24px 18px}
h1{font-size:20px;margin:0 0 4px}
.sub{color:var(--muted);font-size:14px;margin:0 0 20px}
.stato{border-radius:14px;padding:24px;text-align:center;margin-bottom:20px;border:1px solid var(--line);background:var(--card)}
.stato .pallino{width:56px;height:56px;border-radius:50%;margin:0 auto 12px}
.stato .motivo{font-size:15px;color:var(--muted)}
.verde{background:var(--verde)}.giallo{background:var(--giallo)}.rosso{background:var(--rosso)}.grigio{background:var(--grigio)}
.report{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
.giorno{display:flex;align-items:center;gap:10px;padding:6px 0;font-size:14px;border-bottom:1px solid var(--line)}
.giorno:last-child{border-bottom:0}
.giorno .p{width:14px;height:14px;border-radius:50%;flex:none}
.pattern{margin-top:14px;background:#F5B30122;border:1px solid #F5B301;border-radius:8px;padding:10px;font-size:13.5px}
.errore{color:var(--rosso);text-align:center;padding:40px 16px}
</style></head><body>
<main id="app"><p>Caricamento…</p></main>
<script>
const COLORI = {verde:'var(--verde)', giallo:'var(--giallo)', rosso:'var(--rosso)', grigio:'var(--grigio)'};
const token = new URLSearchParams(location.search).get('token') || '';
async function carica(){
  const app = document.getElementById('app');
  const [rStato, rReport] = await Promise.all([
    fetch('/stato?token=' + encodeURIComponent(token)),
    fetch('/report-settimanale?token=' + encodeURIComponent(token)),
  ]);
  if (!rStato.ok || !rReport.ok) {
    app.innerHTML = '<div class="errore">Link non valido o scaduto. Chiedi il link corretto a chi ha attivato il servizio.</div>';
    return;
  }
  const stato = await rStato.json();
  const report = await rReport.json();
  app.innerHTML = `
    <h1>FiloDiretto</h1>
    <p class="sub">Come sta oggi, ${new Date(stato.data).toLocaleDateString('it-IT', {weekday:'long', day:'numeric', month:'long'})}</p>
    <div class="stato"><div class="pallino ${stato.stato}"></div><div class="motivo">${stato.motivo}</div></div>
    <div class="report">
      <b>Ultimi 7 giorni</b> — ${report.giorni_ok}/${report.giorni_totali} giorni sereni
      ${report.dettaglio.map(g => `<div class="giorno"><span class="p ${g.stato}"></span>${g.data} — ${g.motivo}</div>`).join('')}
      ${report.pattern.pattern_rilevato ? `<div class="pattern">⚠️ ${report.pattern.messaggio}</div>` : ''}
    </div>
    <button id="extra" style="width:100%;margin-top:14px;padding:12px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--ink);font-size:14px;cursor:pointer">📞 Richiedi una chiamata extra adesso</button>
    <p id="extra-esito" class="sub" style="text-align:center"></p>
  `;
  document.getElementById('extra').addEventListener('click', async () => {
    const esito = document.getElementById('extra-esito');
    esito.textContent = 'Invio richiesta…';
    const res = await fetch('/richiedi-chiamata-extra', { method: 'POST', headers: { 'X-Access-Token': token } });
    esito.textContent = res.ok ? 'Richiesta inviata — verrà gestita a breve.' : 'Richiesta non riuscita, riprova.';
  });
}
carica();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _json(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body, ensure_ascii=False).encode())

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode())
            return
        if parsed.path in ("/stato", "/report-settimanale"):
            token = (qs.get("token") or [""])[0]
            if not token_autorizzato(token):
                return self._json(401, {"errore": "token non valido — vedi CONFIGURAZIONE.md"})
            if leggi_consenso() is None:
                return self._json(403, {"errore": "servizio non attivo: consenso non ancora raccolto (vedi POST /consenso)"})
            pulisci_eventi_vecchi()
            if parsed.path == "/stato":
                return self._json(200, stato_di_oggi())
            return self._json(200, report_settimanale())
        self._json(404, {"errore": "endpoint sconosciuto"})

    def do_POST(self):
        if self.path == "/consenso":
            token = self.headers.get("X-Access-Token", "")
            if not token_autorizzato(token):
                return self._json(401, {"errore": "token non valido — vedi CONFIGURAZIONE.md"})
            try:
                return self._json(201, registra_consenso(self._body()))
            except ValueError as e:
                return self._json(400, {"errore": str(e)})

        if self.path == "/voice/stato-chiamata":
            # Webhook Twilio: NON usa il token famiglia (Twilio non lo
            # conosce), usa la firma X-Twilio-Signature, come in telefonia.js.
            n = int(self.headers.get("Content-Length") or 0)
            corpo = self.rfile.read(n).decode("utf-8")
            params = dict(urllib.parse.parse_qsl(corpo))
            url_completo = PUBLIC_URL.rstrip("/") + "/voice/stato-chiamata"
            firma = self.headers.get("X-Twilio-Signature", "")
            solo_mock = TWILIO_AUTH_TOKEN.startswith("MOCK_") or PUBLIC_URL.startswith("MOCK_")
            if not solo_mock and not valida_firma_twilio(url_completo, params, firma, TWILIO_AUTH_TOKEN):
                return self._json(403, {"errore": "firma Twilio non valida"})
            call_status = params.get("CallStatus", "")
            if call_status in ESITI_NON_RISPOSTA:
                registra_no_risposta()
            return self._json(200, {"registrato": call_status})

        if self.path == "/richiedi-chiamata-extra":
            token = self.headers.get("X-Access-Token", "")
            if not token_autorizzato(token):
                return self._json(401, {"errore": "token non valido"})
            # v1: nessuna chiamata immediata automatica — solo una richiesta
            # tracciata per revisione manuale. Dichiarato onestamente, non
            # promesso come "automatico" finché non lo è davvero.
            print("📞 Richiesta di chiamata extra ricevuta — da gestire manualmente in v1")
            return self._json(202, {"richiesto": True, "nota": "richiesta registrata, gestione manuale in questa versione"})

        self._json(404, {"errore": "endpoint sconosciuto"})

    def log_message(self, fmt, *args):
        print(f"  {self.command} {self.path}")


def demo():
    import pattern_tracker
    pattern_tracker.demo()


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
    else:
        print(f"👵 FiloDiretto — dashboard famiglia su :{PORTA}")
        HTTPServer(("", PORTA), Handler).serve_forever()
