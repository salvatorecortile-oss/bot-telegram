"""
Backtest della strategia V-Formation su dati MT5 (o CSV).

Esempi (dalla cartella del bot, sul PC con MetaTrader 5):

    python backtest/run_vformation.py --symbols EURUSD GBPUSD USDCHF EURGBP --timeframe M5 --from 2021-01-01
    python backtest/run_vformation.py --symbols EURUSD --compare --split 2024-01-01
    python backtest/run_vformation.py --symbols EURUSD --set bias_mode=ema htf=1D min_rank=S
    python backtest/run_vformation.py --csv mio_file.csv --compare

Lo script SCARICA SOLO DATI: non invia ordini e non modifica il conto.
"""
from __future__ import annotations

import argparse
import dataclasses
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from data_mt5 import load_csv, load_mt5, pip_size  # noqa: E402
from vformation_engine import DIAG_NAMES, Params, run_backtest  # noqa: E402
from vformation_report import breakdown, summarize  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parent / "results"

# Varianti da confrontare con --compare (ognuna cambia pochi parametri rispetto alla base)
SCENARIOS: dict[str, dict] = {
    "base": {},
    "config_tradingview": dict(tp1_mode="rr", tp1_rr=1.0, tp2_mode="rr", tp2_rr=2.0,
                               bias_mode="ema", htf="1D", max_right_bars=23),
    "bias_off": dict(bias_mode="off"),
    "bias_ema_D1": dict(bias_mode="ema", htf="1D"),
    "bias_struttura_H4": dict(bias_mode="struct", htf="4h"),
    "solo_rango_S": dict(min_rank="S"),
    "sweep_asia_o_giorno_prec": dict(sweep_mode="asia_pd"),
    "entry_0.618": dict(entry_fib=0.618),
    "tp_1R_2R": dict(tp1_mode="rr", tp1_rr=1.0, tp2_mode="rr", tp2_rr=2.0),
    "tutto_a_2R": dict(tp1_mode="rr", tp1_rr=2.0, tp1_pct=100.0),
    "senza_sessione": dict(use_session=False),
}


def parse_overrides(items: list[str]) -> dict:
    fields = {f.name: f for f in dataclasses.fields(Params)}
    out = {}
    for item in items or []:
        key, _, raw = item.partition("=")
        key = key.strip()
        if key not in fields:
            raise SystemExit(f"Parametro sconosciuto: {key}\nDisponibili: {', '.join(fields)}")
        default = fields[key].default
        if raw.lower() in ("none", "null"):
            val = None
        elif isinstance(default, bool):
            val = raw.lower() in ("1", "true", "si", "sì", "yes", "on")
        elif isinstance(default, int):
            val = int(raw)
        elif isinstance(default, float) or default is None:
            val = float(raw)
        else:
            val = raw
        out[key] = val
    return out


def main() -> None:
    # console di Windows: evita errori con i caratteri speciali dell'output
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    ap = argparse.ArgumentParser(description="Backtest V-Formation su dati MT5")
    ap.add_argument("--symbols", nargs="+", default=["EURUSD"], help="simboli MT5 (con eventuale suffisso del broker)")
    ap.add_argument("--timeframe", default="M5", help="M1, M5, M15, M30, H1, H4")
    ap.add_argument("--from", dest="date_from", default="2021-01-01")
    ap.add_argument("--to", dest="date_to", default=date.today().isoformat())
    ap.add_argument("--csv", nargs="+", help="usa questi CSV invece di MT5 (un file per simbolo)")
    ap.add_argument("--server-tz", default="Europe/Athens",
                    help="fuso orario del server del broker (la maggior parte dei broker forex usa GMT+2/+3 = Europe/Athens)")
    ap.add_argument("--set", nargs="*", default=[], metavar="CHIAVE=VALORE", help="modifica i parametri di base")
    ap.add_argument("--compare", action="store_true", help="confronta le varianti predefinite")
    ap.add_argument("--split", help="data che separa in-sample e out-of-sample, es. 2024-01-01")
    ap.add_argument("--refresh", action="store_true", help="riscarica i dati da MT5 ignorando la cache")
    args = ap.parse_args()

    base = Params(**parse_overrides(args.set))

    # ── dati ──
    datasets = []
    if args.csv:
        for path in args.csv:
            df, point, digits = load_csv(path)
            datasets.append((Path(path).stem, df, point, digits))
    else:
        for sym in args.symbols:
            print(f"▶ {sym} {args.timeframe}")
            df, point, digits = load_mt5(sym, args.timeframe, args.date_from, args.date_to, args.refresh)
            datasets.append((sym, df, point, digits))

    scenarios = SCENARIOS if args.compare else {"base": {}}
    out_dir = RESULTS_DIR / datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    summaries, diags, all_trades = {}, {}, {}
    for name, overrides in scenarios.items():
        p = dataclasses.replace(base, **overrides)
        frames, diag_tot = [], [0] * len(DIAG_NAMES)
        for sym, df, point, digits in datasets:
            trades, diag = run_backtest(df, p, point, pip_size(point, digits), args.server_tz, sym)
            frames.append(trades)
            diag_tot = [a + b for a, b in zip(diag_tot, diag)]
        trades = pd.concat([f for f in frames if not f.empty], ignore_index=True) if any(not f.empty for f in frames) else pd.DataFrame()
        all_trades[name] = trades
        diags[name] = diag_tot
        kw = dict(risk_pct=p.risk_pct, risk_a_mult=p.risk_a_mult)
        summaries[name] = summarize(trades, **kw)
        if args.split and not trades.empty:
            cut = pd.Timestamp(args.split)
            ins, oos = trades[trades["entry_time"] < cut], trades[trades["entry_time"] >= cut]
            s_in, s_out = summarize(ins, **kw), summarize(oos, **kw)
            summaries[name].update({
                "IS setup": s_in.get("setup", 0), "IS R medio": s_in.get("R medio", 0),
                "OOS setup": s_out.get("setup", 0), "OOS R medio": s_out.get("R medio", 0),
                "OOS profit factor": s_out.get("profit factor", 0),
            })
        if not trades.empty:
            trades.to_csv(out_dir / f"trade_{name}.csv", index=False)
        print(f"  ✓ {name}: {summaries[name].get('setup', 0)} setup")

    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)

    print("\n" + "═" * 100)
    print(f"RISULTATI  ({', '.join(d[0] for d in datasets)} · {args.timeframe} · rischio {base.risk_pct}% per setup)")
    print("═" * 100)
    summary_df = pd.DataFrame(summaries).T
    print(summary_df.to_string())
    summary_df.to_csv(out_dir / "riepilogo_scenari.csv")

    diag_df = pd.DataFrame(diags, index=DIAG_NAMES)
    print("\nDIAGNOSTICA")
    print(diag_df.to_string())
    diag_df.to_csv(out_dir / "diagnostica.csv")

    first = next(iter(scenarios))
    trades = all_trades[first]
    if not trades.empty:
        kw = dict(risk_pct=base.risk_pct, risk_a_mult=base.risk_a_mult)
        for by in ("simbolo", "anno", "lato", "rango"):
            print(f"\nDettaglio '{first}' per {by}")
            print(breakdown(trades, by, **kw).to_string())

    print(f"\nFile salvati in: {out_dir}")


if __name__ == "__main__":
    main()
