"""
Registro di verifica: salva ogni previsione automatica e, quando sono passate
le candele previste, la confronta con il prezzo vero.

Database: data/kronos.db (solo di Kronos, non tocca gli altri bot).
"""
import sqlite3
from contextlib import closing
from datetime import datetime, timezone

import pandas as pd

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS forecasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    last_candle_time TEXT NOT NULL,
    last_close REAL NOT NULL,
    pred_len INTEGER NOT NULL,
    samples INTEGER NOT NULL,
    upside_probability REAL NOT NULL,
    volatility_up_probability REAL NOT NULL,
    mean_final_close REAL NOT NULL,
    p10_final_close REAL NOT NULL,
    p90_final_close REAL NOT NULL,
    bias TEXT NOT NULL,
    model TEXT,
    status TEXT NOT NULL DEFAULT 'in_attesa',
    actual_close REAL,
    actual_high REAL,
    actual_low REAL,
    evaluated_at TEXT,
    UNIQUE (symbol, timeframe, last_candle_time, pred_len, samples)
);
"""


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class Journal:
    def __init__(self, db_path=None):
        self.db_path = str(db_path or config.DB_PATH)
        with closing(self._conn()) as c, c:
            c.executescript(SCHEMA)

    def _conn(self):
        c = sqlite3.connect(self.db_path, timeout=30)
        c.row_factory = sqlite3.Row
        return c

    def save(self, r):
        """Salva una previsione. Ritorna False se era gia' salvata."""
        with closing(self._conn()) as c, c:
            cur = c.execute(
                """INSERT OR IGNORE INTO forecasts (created_at, symbol, timeframe, last_candle_time,
                   last_close, pred_len, samples, upside_probability, volatility_up_probability,
                   mean_final_close, p10_final_close, p90_final_close, bias, model)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (_now(), r["symbol"], r["timeframe"], r["last_candle_time"], r["last_close"],
                 r["pred_len"], r["samples"], r["upside_probability"],
                 r["volatility_up_probability"], r["mean_final_close"], r["p10_final_close"],
                 r["p90_final_close"], r["bias"], r.get("model")),
            )
            return cur.rowcount == 1

    def pending(self):
        with closing(self._conn()) as c:
            return [dict(x) for x in c.execute(
                "SELECT * FROM forecasts WHERE status='in_attesa' ORDER BY last_candle_time")]

    def evaluate(self, symbol, timeframe, history):
        """
        Confronta le previsioni in attesa con le candele vere in `history`.
        Conta le candele (non l'orologio), cosi' i weekend non falsano il conto.
        Ritorna quante previsioni sono state verificate.
        """
        if history is None or history.empty:
            return 0
        times = pd.to_datetime(history["timestamps"])
        first = times.iloc[0]
        done = 0
        with closing(self._conn()) as c, c:
            rows = c.execute(
                "SELECT * FROM forecasts WHERE status='in_attesa' AND symbol=? AND timeframe=?",
                (symbol, timeframe)).fetchall()
            for row in rows:
                start = pd.Timestamp(row["last_candle_time"])
                if start < first:
                    # troppo vecchia: le candele non sono piu' disponibili
                    c.execute("UPDATE forecasts SET status='scaduta', evaluated_at=? WHERE id=?",
                              (_now(), row["id"]))
                    continue
                after = history[times > start]
                if len(after) < row["pred_len"]:
                    continue  # non ancora passate tutte le candele previste
                window = after.iloc[:row["pred_len"]]
                c.execute(
                    """UPDATE forecasts SET status='verificata', actual_close=?, actual_high=?,
                       actual_low=?, evaluated_at=? WHERE id=?""",
                    (float(window["close"].iloc[-1]), float(window["high"].max()),
                     float(window["low"].min()), _now(), row["id"]))
                done += 1
        return done

    def stats(self, symbol=None, timeframe=None, days=None):
        q = "SELECT * FROM forecasts WHERE 1=1"
        args = []
        if symbol:
            q += " AND symbol=?"
            args.append(symbol)
        if timeframe:
            q += " AND timeframe=?"
            args.append(timeframe)
        if days:
            q += " AND created_at >= datetime('now', ?)"
            args.append(f"-{int(days)} days")
        with closing(self._conn()) as c:
            rows = [dict(x) for x in c.execute(q, args)]
        return compute_stats(rows)


def compute_stats(rows):
    ver = [r for r in rows if r["status"] == "verificata"]
    out = {
        "totale": len(rows),
        "verificate": len(ver),
        "in_attesa": sum(r["status"] == "in_attesa" for r in rows),
        "scadute": sum(r["status"] == "scaduta" for r in rows),
    }
    if not ver:
        return out

    def went_up(r):
        return r["actual_close"] > r["last_close"]

    for bias in ("RIALZO", "RIBASSO"):
        sel = [r for r in ver if r["bias"] == bias]
        ok = [r for r in sel if went_up(r) == (bias == "RIALZO")]
        out[bias] = {"segnali": len(sel), "corretti": len(ok),
                     "percentuale": round(100 * len(ok) / len(sel), 1) if sel else None}
    out["NEUTRO"] = {"segnali": sum(r["bias"] == "NEUTRO" for r in ver)}

    # direzione della maggioranza degli scenari (tutte le previsioni)
    maj = [r for r in ver if r["upside_probability"] != 0.5]
    maj_ok = [r for r in maj if went_up(r) == (r["upside_probability"] > 0.5)]
    out["direzione_maggioranza_pct"] = round(100 * len(maj_ok) / len(maj), 1) if maj else None
    # quante volte il prezzo vero e' finito dentro il range 10-90% (ideale ~80%)
    inside = [r for r in ver if r["p10_final_close"] <= r["actual_close"] <= r["p90_final_close"]]
    out["dentro_range_pct"] = round(100 * len(inside) / len(ver), 1)
    # errore medio in dollari tra prezzo medio previsto e prezzo vero
    out["errore_medio"] = round(sum(abs(r["actual_close"] - r["mean_final_close"]) for r in ver) / len(ver), 2)
    # Brier: 0 = perfetto, 0.25 = come tirare una moneta
    out["brier"] = round(sum((r["upside_probability"] - (1.0 if went_up(r) else 0.0)) ** 2
                             for r in ver) / len(ver), 4)
    return out


def format_stats(s, title="Registro Kronos"):
    lines = [f"📊 {title}",
             f"Previsioni: {s['totale']} (verificate {s['verificate']}, "
             f"in attesa {s['in_attesa']}, scadute {s['scadute']})"]
    if not s["verificate"]:
        lines.append("Nessuna previsione ancora verificata: aspetta che passino le candele previste.")
        return "\n".join(lines)
    for b, icon in (("RIALZO", "🟢"), ("RIBASSO", "🔴")):
        d = s[b]
        pct = f"{d['percentuale']}%" if d["percentuale"] is not None else "-"
        lines.append(f"{icon} {b}: {d['corretti']}/{d['segnali']} corretti ({pct})")
    lines.append(f"⚪ NEUTRO (nessun segnale): {s['NEUTRO']['segnali']}")
    lines.append(f"Direzione della maggioranza degli scenari: {s['direzione_maggioranza_pct']}% corretta "
                 "(50% = come tirare una moneta)")
    lines.append(f"Prezzo vero dentro il range 10-90%: {s['dentro_range_pct']}% (ideale circa 80%)")
    lines.append(f"Errore medio sul prezzo: {s['errore_medio']} $")
    lines.append(f"Brier: {s['brier']} (più basso è meglio; 0.25 = moneta)")
    if s["verificate"] < 100:
        lines.append(f"⚠️ Solo {s['verificate']} verifiche: servono almeno 100-200 per fidarsi dei numeri.")
    return "\n".join(lines)
