"""
Servizio previsioni Kronos.

    python main.py            -> avvia il servizio locale (per gli altri bot)
    python main.py --once     -> fa una sola previsione e la stampa

Il servizio risponde solo sul tuo PC:
    http://127.0.0.1:8765/health
    http://127.0.0.1:8765/forecast?symbol=XAUUSD&timeframe=M15
    http://127.0.0.1:8765/forecast?symbol=XAUUSD&timeframe=M15&format=text
    http://127.0.0.1:8765/stats     -> risultati del registro di verifica

Con KRONOS_AUTO=true fa anche una previsione a ogni candela chiusa e la
salva nel registro (data/kronos.db), poi la confronta con il prezzo vero.

NON apre ordini: restituisce solo la previsione.
"""
import argparse
import json
import logging
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import config
from auto import AutoRunner
from forecast import Forecaster, format_text
from journal import Journal, format_stats
from mt5_data import MT5Candles

log = logging.getLogger("kronos")


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler(config.LOG_FILE, encoding="utf-8")],
    )


def make_handler(forecaster, journal=None):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, body, content_type="application/json; charset=utf-8"):
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _json(self, status, obj):
            self._send(status, json.dumps(obj, ensure_ascii=False))

        def do_GET(self):
            url = urlparse(self.path)
            q = {k: v[-1] for k, v in parse_qs(url.query).items()}
            if url.path == "/health":
                return self._json(200, {"ok": True})
            if url.path == "/stats":
                if journal is None:
                    return self._json(404, {"ok": False, "error": "registro non attivo"})
                days = q.get("giorni")
                s = journal.stats(days=int(days) if days and days.isdigit() else None)
                if q.get("format") == "json":
                    return self._json(200, dict(s, ok=True))
                return self._send(200, format_stats(s), "text/plain; charset=utf-8")
            if url.path != "/forecast":
                return self._json(404, {"ok": False, "error": "usa /forecast, /stats o /health"})
            try:
                r = forecaster.forecast(
                    symbol=q.get("symbol"),
                    timeframe=q.get("timeframe"),
                    pred_len=q.get("pred_len"),
                    samples=q.get("samples"),
                    force=q.get("force") == "1",
                )
            except ValueError as e:
                return self._json(400, {"ok": False, "error": str(e)})
            except Exception as e:  # MT5 chiuso, modello non caricato, ecc.
                log.exception("Errore previsione")
                return self._json(503, {"ok": False, "error": str(e)})
            if q.get("format") == "text":
                return self._send(200, format_text(r), "text/plain; charset=utf-8")
            return self._json(200, dict(r, ok=True))

        def log_message(self, fmt, *args):
            log.info("%s %s", self.address_string(), fmt % args)

    return Handler


def main(argv=None):
    p = argparse.ArgumentParser(description="Servizio previsioni Kronos")
    p.add_argument("--once", action="store_true", help="una sola previsione e poi esce")
    p.add_argument("--symbol", default=config.DEFAULT_SYMBOL)
    p.add_argument("--timeframe", default=config.DEFAULT_TIMEFRAME)
    args = p.parse_args(argv)

    setup_logging()
    forecaster = Forecaster(MT5Candles())

    if args.once:
        r = forecaster.forecast(args.symbol, args.timeframe)
        print(format_text(r))
        return

    # Carico subito il modello, cosi' la prima richiesta non aspetta
    _ = forecaster.predictor
    journal = Journal()
    runner = None
    if config.AUTO_ENABLED:
        runner = AutoRunner(forecaster, journal)
        runner.start()
    server = ThreadingHTTPServer((config.HOST, config.PORT), make_handler(forecaster, journal))
    log.info("Servizio Kronos attivo su http://%s:%s  (CTRL+C per fermare)", config.HOST, config.PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Fermato")
    finally:
        if runner:
            runner.stop()
        server.server_close()
        forecaster.candles.shutdown()


if __name__ == "__main__":
    main()
