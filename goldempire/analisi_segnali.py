"""
Analisi dei segnali della Sala: quali SIGNAL guadagnano e quali perdono.

Legge le operazioni chiuse dal database del bot (data/goldempire.db) e, se
MetaTrader 5 e' aperto, prende il profitto REALE in $ di ogni posizione.

Avvio (dalla cartella del bot):
    py analisi_segnali.py              tutte le operazioni
    py analisi_segnali.py 30           solo gli ultimi 30 giorni

Scrive anche il dettaglio in data/analisi_segnali.csv (si apre con Excel).
Non apre, non chiude e non modifica nulla: legge soltanto.
"""
import csv
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from config import DATA_DIR, DB_PATH, MT5_PATH, PIP_SIZE

CLOSED_STATUSES = (
    "CLOSED_TP", "CLOSED_SL", "CLOSED_BE", "CLOSED_MANUAL", "CLOSED_EXTERNAL", "CLOSED_STOP_PROFIT",
)
MIN_TRADES = 8  # sotto questo numero il giudizio e' "pochi dati"


def load_trades(db_path, days=None):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in CLOSED_STATUSES)
    query = (f"SELECT * FROM signals WHERE status IN ({placeholders}) AND pips IS NOT NULL")
    params = list(CLOSED_STATUSES)
    if days:
        query += " AND closed_at >= ?"
        params.append((datetime.now(timezone.utc) - timedelta(days=days)).isoformat())
    rows = [dict(r) for r in conn.execute(query + " ORDER BY closed_at", params)]
    conn.close()
    return rows


def real_profits(tickets):
    """{ticket: profitto netto $} da MT5 (profitto + commissioni + swap). {} se MT5 non c'e'."""
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return {}
    if not mt5.initialize(path=MT5_PATH):
        return {}
    out = {}
    try:
        for ticket in tickets:
            deals = mt5.history_deals_get(position=int(ticket)) or []
            if deals:
                out[int(ticket)] = sum(float(d.profit) + float(d.commission) + float(d.swap) for d in deals)
    finally:
        mt5.shutdown()
    return out


def trade_usd(row, profits):
    ticket = row.get("position_ticket")
    if ticket and int(ticket) in profits:
        return profits[int(ticket)]
    # Stima dai pips: 1 pip = PIP_SIZE $ di prezzo, 1 lotto = 100 once.
    return float(row["pips"]) * PIP_SIZE * float(row.get("volume") or 0.01) * 100


def family(row):
    n = row.get("signal_no")
    return "?" if n is None else str(int(float(n)))


def stats(values):
    wins = [v for v in values if v > 0]
    losses = [v for v in values if v < 0]
    streak = worst_streak = 0
    for v in values:
        streak = streak + 1 if v < 0 else 0
        worst_streak = max(worst_streak, streak)
    equity = peak = drawdown = 0.0
    for v in values:
        equity += v
        peak = max(peak, equity)
        drawdown = min(drawdown, equity - peak)
    gross_loss = -sum(losses)
    return {
        "n": len(values),
        "win_rate": 100.0 * len(wins) / len(values) if values else 0.0,
        "net": sum(values),
        "avg_win": sum(wins) / len(wins) if wins else 0.0,
        "avg_loss": sum(losses) / len(losses) if losses else 0.0,
        "pf": (sum(wins) / gross_loss) if gross_loss else float("inf") if wins else 0.0,
        "worst": min(values) if values else 0.0,
        "streak": worst_streak,
        "drawdown": drawdown,
    }


def verdict(s):
    if s["n"] < MIN_TRADES:
        return "POCHI DATI"
    if s["net"] < 0 or s["pf"] < 1.0:
        return "BLOCCARE"
    if s["pf"] < 1.3:
        return "DEBOLE"
    return "TENERE"


def _fmt_pf(pf):
    return "inf" if pf == float("inf") else f"{pf:.2f}"


def analyze(trades, profits):
    by_family = defaultdict(list)
    by_family_dir = defaultdict(list)
    for row in trades:
        usd = trade_usd(row, profits)
        by_family[family(row)].append(usd)
        by_family_dir[(family(row), row["direction"])].append(usd)
    return by_family, by_family_dir


def report(trades, profits, days=None):
    lines = []
    period = f"ultimi {days} giorni" if days else "tutto lo storico"
    source = "profitto reale da MT5" if profits else "stima dai pips (MT5 non collegato)"
    lines.append(f"ANALISI SEGNALI GOLD EMPIRE - {period} - {len(trades)} operazioni chiuse ({source})")
    if not trades:
        lines.append("Nessuna operazione chiusa nel periodo.")
        return "\n".join(lines)
    first, last = trades[0]["closed_at"][:10], trades[-1]["closed_at"][:10]
    lines.append(f"Dal {first} al {last}\n")

    by_family, by_family_dir = analyze(trades, profits)
    header = f"{'SIGNAL':<8}{'Op.':>5}{'Vinte':>8}{'Netto $':>11}{'Media +':>10}{'Media -':>10}" \
             f"{'PF':>7}{'Peggiore':>10}{'Perse fila':>12}{'DD max $':>10}   Giudizio"
    lines.append(header)
    lines.append("-" * len(header) + "-" * 12)
    ordered = sorted(by_family.items(), key=lambda kv: stats(kv[1])["net"], reverse=True)
    for fam, values in ordered:
        s = stats(values)
        lines.append(f"{fam:<8}{s['n']:>5}{s['win_rate']:>7.0f}%{s['net']:>11.2f}{s['avg_win']:>10.2f}"
                     f"{s['avg_loss']:>10.2f}{_fmt_pf(s['pf']):>7}{s['worst']:>10.2f}{s['streak']:>12}"
                     f"{s['drawdown']:>10.2f}   {verdict(s)}")
    total = stats([v for vals in by_family.values() for v in vals])
    lines.append(f"{'TOTALE':<8}{total['n']:>5}{total['win_rate']:>7.0f}%{total['net']:>11.2f}"
                 f"{'':>20}{_fmt_pf(total['pf']):>7}{total['worst']:>10.2f}{total['streak']:>12}"
                 f"{total['drawdown']:>10.2f}")

    lines.append("\nPer direzione:")
    for fam, _ in ordered:
        parts = []
        for direction in ("BUY", "SELL"):
            vals = by_family_dir.get((fam, direction))
            if vals:
                s = stats(vals)
                parts.append(f"{direction} {s['n']} op. {s['win_rate']:.0f}% vinte, {s['net']:+.2f} $")
        lines.append(f"  SIGNAL {fam}: " + " | ".join(parts))

    to_block = [fam for fam, vals in ordered if verdict(stats(vals)) == "BLOCCARE"]
    lines.append("")
    if to_block:
        kept = [v for fam, vals in by_family.items() if fam not in to_block for v in vals]
        k = stats(kept)
        lines.append(f"Senza i SIGNAL {', '.join(to_block)}: {k['net']:+.2f} $ invece di {total['net']:+.2f} $, "
                     f"DD max {k['drawdown']:.2f} $ invece di {total['drawdown']:.2f} $.")
        lines.append("Per bloccarli, nel .env del conto principale: EXCLUDED_SIGNALS="
                     + ",".join(f for f in to_block if f != "?"))
    else:
        lines.append("Nessun segnale con abbastanza operazioni da bloccare.")
    lines.append("\nLegenda: PF = profitti / perdite (sopra 1,3 buono, sotto 1 perde). "
                 f"POCHI DATI = meno di {MIN_TRADES} operazioni.")
    return "\n".join(lines)


def write_csv(trades, profits, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["chiusa", "signal", "famiglia", "direzione", "ingresso", "chiusura", "esito", "pips", "dollari"])
        for row in trades:
            w.writerow([row["closed_at"][:16].replace("T", " "), row["signal_no"], family(row), row["direction"],
                        row["open_price"], row["close_price"], row["status"].replace("CLOSED_", ""),
                        f"{float(row['pips']):.1f}".replace(".", ","),
                        f"{trade_usd(row, profits):.2f}".replace(".", ",")])


def main():
    days = int(sys.argv[1]) if len(sys.argv) > 1 else None
    trades = load_trades(DB_PATH, days)
    profits = real_profits([r["position_ticket"] for r in trades if r.get("position_ticket")])
    print(report(trades, profits, days))
    if trades:
        path = DATA_DIR / "analisi_segnali.csv"
        write_csv(trades, profits, path)
        print(f"\nDettaglio operazione per operazione: {path}")


if __name__ == "__main__":
    main()
