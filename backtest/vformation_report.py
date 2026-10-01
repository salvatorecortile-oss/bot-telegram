"""Statistiche dei trade del backtest V-Formation (tutto in R = multipli del rischio)."""
from __future__ import annotations

import numpy as np
import pandas as pd

BE_EPS = 0.05   # |R| sotto questa soglia = break-even


def summarize(trades: pd.DataFrame, risk_pct: float = 1.0, risk_a_mult: float = 0.5) -> dict:
    if trades is None or trades.empty:
        return {"setup": 0}
    t = trades.sort_values("exit_time")
    r = t["R"].to_numpy(float)
    wins, losses = r[r > BE_EPS], r[r < -BE_EPS]
    gross_win, gross_loss = wins.sum(), -losses.sum()

    cum = np.cumsum(r)
    dd_r = (np.maximum.accumulate(np.concatenate(([0.0], cum)))[1:] - cum).max()

    streak = best = 0
    for x in r:
        streak = streak + 1 if x < -BE_EPS else 0
        best = max(best, streak)

    # equity con rischio % per trade (rango A a rischio ridotto), composto
    mult = np.where(t["rango"].to_numpy() == "S", 1.0, risk_a_mult)
    eq = np.cumprod(1 + r * risk_pct / 100 * mult)
    peak = np.maximum.accumulate(np.concatenate(([1.0], eq)))[1:]
    dd_pct = ((peak - eq) / peak).max() * 100

    months = max((t["exit_time"].max() - t["entry_time"].min()).days / 30.44, 1e-9)
    return {
        "setup": len(r),
        "win %": round(len(wins) / len(r) * 100, 1),
        "BE %": round((len(r) - len(wins) - len(losses)) / len(r) * 100, 1),
        "loss %": round(len(losses) / len(r) * 100, 1),
        "R medio": round(r.mean(), 3),
        "R totale": round(r.sum(), 1),
        "profit factor": round(gross_win / gross_loss, 2) if gross_loss > 0 else float("inf"),
        "win medio R": round(wins.mean(), 2) if len(wins) else 0.0,
        "loss medio R": round(losses.mean(), 2) if len(losses) else 0.0,
        "max DD R": round(dd_r, 1),
        "max perdite consecutive": best,
        "rendimento %": round((eq[-1] - 1) * 100, 1),
        "max DD %": round(dd_pct, 1),
        "setup/mese": round(len(r) / months, 1),
    }


def breakdown(trades: pd.DataFrame, by: str, **kw) -> pd.DataFrame:
    if trades is None or trades.empty:
        return pd.DataFrame()
    t = trades.copy()
    if by == "anno":
        t["anno"] = pd.to_datetime(t["entry_time"]).dt.year
    elif by == "ora":
        t["ora"] = pd.to_datetime(t["entry_time"]).dt.hour
    rows = {k: summarize(g, **kw) for k, g in t.groupby(by)}
    cols = ["setup", "win %", "R medio", "R totale", "profit factor", "max DD R"]
    return pd.DataFrame(rows).T[cols]
