"""
Previsioni automatiche: controlla ogni 30 secondi se e' chiusa una nuova
candela; se si', fa la previsione, la salva nel registro e verifica quelle
passate. Gira in sottofondo dentro "python main.py".
"""
import logging
import threading

import config

log = logging.getLogger("kronos.auto")


class AutoRunner:
    def __init__(self, forecaster, journal, symbol=None, timeframe=None):
        self.forecaster = forecaster
        self.journal = journal
        self.symbol = symbol or config.DEFAULT_SYMBOL
        self.timeframe = timeframe or config.DEFAULT_TIMEFRAME
        self._stop = threading.Event()
        self._thread = None

    def step(self):
        """Un giro: previsione (se c'e' una candela nuova) + verifica. Ritorna la previsione."""
        r = self.forecaster.forecast(self.symbol, self.timeframe)
        # salva anche se la previsione era gia' stata calcolata per un altro bot
        # (il registro ignora i doppioni)
        if self.journal.save(r):
            log.info("Nuova previsione %s %s: %s (rialzo %.0f%%) salvata nel registro",
                     r["symbol"], r["timeframe"], r["bias"], r["upside_probability"] * 100)
        if self.journal.pending():
            history = self.forecaster.get_history(self.symbol, self.timeframe, config.EVAL_LOOKBACK)
            n = self.journal.evaluate(r["symbol"], r["timeframe"], history)
            if n:
                log.info("Verificate %d previsioni passate", n)
        return r

    def _loop(self):
        log.info("Previsioni automatiche attive: %s %s (controllo ogni %ss)",
                 self.symbol, self.timeframe, config.AUTO_CHECK_SECONDS)
        while not self._stop.is_set():
            try:
                self.step()
            except Exception as e:  # MT5 chiuso, mercato chiuso, ecc.: riprova al giro dopo
                log.warning("Previsione automatica non riuscita: %s", e)
            self._stop.wait(config.AUTO_CHECK_SECONDS)

    def start(self):
        self._thread = threading.Thread(target=self._loop, name="kronos-auto", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
