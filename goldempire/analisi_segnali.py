"""
Analisi completa dei segnali della Sala: quali SIGNAL guadagnano e quali perdono.

Mette insieme DUE fonti:
  1) LA SALA: tutti i messaggi del canale sorgente da una data (default 15/10/2026).
     Ogni segnale viene ricostruito dall'inizio alla fine (ingresso, SL/TP, BE,
     stop spostati, chiusure, inversioni 5/6) con i prezzi M1 di MT5: cosi'
     contano anche i segnali che il bot NON ha aperto.
  2) IL BOT: le operazioni vere chiuse nel database (data/goldempire.db), con
     il profitto reale in $ preso da MT5.

Avvio (dalla cartella del bot, con MT5 aperto; il bot puo' restare acceso):
    py analisi_segnali.py                  dal 15/10/2026
    py analisi_segnali.py 2026-11-01       da un'altra data
    py analisi_segnali.py offline          rifa' l'analisi coi dati gia' scaricati

Scrive in data/:
    analisi_segnali.txt     il riepilogo (lo stesso che vedi a schermo)
    analisi_sala.csv        ogni segnale della sala, con esito e se il bot l'ha aperto
    analisi_segnali.csv     ogni operazione vera del bot
    sala_messaggi.json      i messaggi scaricati (per rifare l'analisi senza Telegram)
    sala_prezzi_m1.csv      i prezzi M1 scaricati da MT5

Non apre, non chiude e non modifica nulla: legge soltanto.
"""
import asyncio
import bisect
import csv
import json
import shutil
import sqlite3
import sys
import tempfile
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from config import (
    API_HASH, API_ID, BASE_DIR, DATA_DIR, DB_PATH, FREE_CLOSE_COOLDOWN_MINUTES, MT5_PATH, MT5_SYMBOL,
    PENDING_EXPIRY_MINUTES, PIP_SIZE, REVERSAL_SIGNALS, SESSION_NAME, SOURCE_CHAT,
)
from signal_parser import parse_signal

DEFAULT_SINCE = "2026-10-15"
CLOSED_STATUSES = (
    "CLOSED_TP", "CLOSED_SL", "CLOSED_BE", "CLOSED_MANUAL", "CLOSED_EXTERNAL", "CLOSED_STOP_PROFIT",
)
MIN_TRADES = 8          # sotto questo numero il giudizio e' "pochi dati"
USD_PER_PIP = 0.10      # 1 pip (0,10 $ di prezzo) a 0,01 lotti = 0,10 $

MESSAGES_FILE = DATA_DIR / "sala_messaggi.json"
PRICES_FILE = DATA_DIR / "sala_prezzi_m1.csv"


# ============================================================
# DATI: database del bot
# ============================================================
def load_trades(db_path, since=None):
    if not Path(db_path).exists():
        return []
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    placeholders = ",".join("?" for _ in CLOSED_STATUSES)
    query = f"SELECT * FROM signals WHERE status IN ({placeholders}) AND pips IS NOT NULL"
    params = list(CLOSED_STATUSES)
    if since:
        query += " AND closed_at >= ?"
        params.append(since.isoformat())
    rows = [dict(r) for r in conn.execute(query + " ORDER BY closed_at", params)]
    conn.close()
    return rows


def load_all_signals(db_path):
    """{source_message_id: riga} di TUTTI i segnali visti dal bot (anche non aperti)."""
    if not Path(db_path).exists():
        return {}
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = {int(r["source_message_id"]): dict(r) for r in conn.execute("SELECT * FROM signals")}
    conn.close()
    return rows


# ============================================================
# DATI: Telegram (messaggi della Sala) e MT5 (prezzi M1)
# ============================================================
async def _download_messages(since):
    from telethon import TelegramClient
    # Copia della sessione: il bot acceso tiene bloccato il file originale.
    original = BASE_DIR / f"{SESSION_NAME}.session"
    tmp = Path(tempfile.mkdtemp()) / "analisi.session"
    shutil.copy(original, tmp)
    client = TelegramClient(str(tmp.with_suffix("")), API_ID, API_HASH)
    out = []
    try:
        await client.connect()
        if not await client.is_user_authorized():
            raise RuntimeError("sessione Telegram non autorizzata")
        async for m in client.iter_messages(SOURCE_CHAT, offset_date=since, reverse=True):
            text = m.raw_text or ""
            if not text.strip():
                continue
            out.append({"id": m.id, "date": m.date.astimezone(timezone.utc).isoformat(),
                        "reply_to": m.reply_to_msg_id, "text": text})
    finally:
        await client.disconnect()
        shutil.rmtree(tmp.parent, ignore_errors=True)
    return out


def get_messages(since, offline=False):
    if not offline:
        try:
            messages = asyncio.run(_download_messages(since))
            MESSAGES_FILE.write_text(json.dumps(messages, ensure_ascii=False), encoding="utf-8")
            print(f"Scaricati {len(messages)} messaggi della sala.")
        except Exception as exc:  # noqa: BLE001
            print(f"⚠️ Telegram non disponibile ({exc}): uso i messaggi gia' salvati, se ci sono.")
    if not MESSAGES_FILE.exists():
        return []
    messages = json.loads(MESSAGES_FILE.read_text(encoding="utf-8"))
    return [m for m in messages if datetime.fromisoformat(m["date"]) >= since]


def _download_prices(since):
    import MetaTrader5 as mt5
    if not mt5.initialize(path=MT5_PATH):
        raise RuntimeError(f"MT5 non si collega: {mt5.last_error()}")
    try:
        mt5.symbol_select(MT5_SYMBOL, True)
        tick = mt5.symbol_info_tick(MT5_SYMBOL)
        # Fuso orario del server MT5 (le candele sono in ora server).
        offset = round((int(tick.time) - time.time()) / 900) * 900 if tick else 0
        start = since - timedelta(hours=6)
        rates = mt5.copy_rates_range(MT5_SYMBOL, mt5.TIMEFRAME_M1, start + timedelta(seconds=offset),
                                     datetime.now(timezone.utc) + timedelta(seconds=offset + 3600))
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"nessuna candela M1 ({mt5.last_error()})")
        return [(int(r["time"]) - offset, float(r["open"]), float(r["high"]), float(r["low"]), float(r["close"]))
                for r in rates]
    finally:
        mt5.shutdown()


def get_prices(since, offline=False):
    if not offline:
        try:
            bars = _download_prices(since)
            with open(PRICES_FILE, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["time_utc", "open", "high", "low", "close"])
                w.writerows(bars)
            print(f"Scaricate {len(bars)} candele M1 da MT5.")
            return bars
        except Exception as exc:  # noqa: BLE001
            print(f"⚠️ Prezzi MT5 non disponibili ({exc}): uso quelli gia' salvati, se ci sono.")
    if not PRICES_FILE.exists():
        return []
    with open(PRICES_FILE, newline="") as f:
        reader = csv.reader(f)
        next(reader, None)
        return [(int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4])) for r in reader]


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


# ============================================================
# RICOSTRUZIONE DEI SEGNALI DELLA SALA
# ============================================================
class Prices:
    def __init__(self, bars):
        self.bars = sorted(bars)
        self.times = [b[0] for b in self.bars]

    def __bool__(self):
        return bool(self.bars)

    def between(self, start, end):
        """Candele che INIZIANO dopo start e finiscono entro end (secondi UTC)."""
        i = bisect.bisect_right(self.times, start)
        j = bisect.bisect_right(self.times, end - 60)
        return self.bars[i:j]

    def at(self, ts):
        """Prezzo al momento ts (apertura della candela di quel minuto)."""
        i = bisect.bisect_right(self.times, ts) - 1
        if i < 0:
            return None
        bar = self.bars[i]
        return bar[1] if ts - bar[0] < 60 else bar[4]


def family(signal_no):
    return "?" if signal_no is None else str(int(float(signal_no)))


def _label(signal_no):
    if signal_no is None:
        return "?"
    return str(signal_no) if isinstance(signal_no, float) else str(int(signal_no))


def simulate(messages, bars, now=None):
    """
    Ricostruisce le operazioni della sala. Restituisce una lista di dict con
    esito (pips), motivo di chiusura e stato (CHIUSA / APERTA / NON ESEGUITA / ANNULLATA).
    """
    prices = Prices(bars)
    now = now or time.time()
    trades = {}
    order = []
    last_free_close = None

    def close(t, price, ts, reason, pips=None):
        if pips is None and price is not None:
            sign = 1 if t["direction"] == "BUY" else -1
            pips = (price - t["entry"]) * sign / PIP_SIZE
        t.update(status="CHIUSA", exit=price, exit_ts=ts, reason=reason, pips=pips)

    def advance(t, until):
        """Controlla con le candele se SL/TP (o l'ingresso del pendente) vengono toccati."""
        if not prices:
            return
        for (ts, o, h, l, c) in prices.between(t["checked"], until):
            if t["status"] == "PENDENTE":
                if PENDING_EXPIRY_MINUTES and ts > t["open_ts"] + PENDING_EXPIRY_MINUTES * 60:
                    t.update(status="NON ESEGUITA", reason="scaduto")
                    break
                buy = t["direction"] == "BUY"
                limit = t["order_type"] == "LIMIT"
                touched = (l <= t["entry"]) if buy == limit else (h >= t["entry"])
                if not touched:
                    continue
                t["status"] = "APERTA"
            if t["status"] != "APERTA":
                break
            buy = t["direction"] == "BUY"
            sl_hit = t["sl"] and ((l <= t["sl"]) if buy else (h >= t["sl"]))
            tp_hit = t["tp"] and ((h >= t["tp"]) if buy else (l <= t["tp"]))
            if sl_hit:  # stessa candela con SL e TP: si conta lo SL (prudente)
                reason = "BE" if t["be"] and abs(t["sl"] - t["entry"]) < 0.5 else "SL"
                close(t, t["sl"], ts, reason)
                break
            if tp_hit:
                close(t, t["tp"], ts, "TP")
                break
        t["checked"] = max(t["checked"], until)

    def open_trades():
        return [t for t in (trades[i] for i in order) if t["status"] in ("APERTA", "PENDENTE")]

    def target_for(msg, signal):
        reply = msg.get("reply_to")
        if reply and reply in trades:
            return trades[reply]
        if signal.get("signal_no") is not None:
            same = [t for t in open_trades() if t["signal_no"] == signal["signal_no"]]
            if same:
                return same[-1]
        return None

    for msg in sorted(messages, key=lambda m: (m["date"], m["id"])):
        ts = datetime.fromisoformat(msg["date"]).timestamp()
        for t in open_trades():
            advance(t, ts)
        try:
            signal = parse_signal(msg["text"])
        except Exception:  # noqa: BLE001
            signal = None
        if not signal:
            continue
        action = signal["action"]

        if action == "OPEN":
            fam = family(signal["signal_no"])
            if signal["signal_no"] is not None and int(fam) in REVERSAL_SIGNALS:
                # Inversione 5/6: chiude le opposte dello stesso SIGNAL al nuovo ingresso.
                for t in open_trades():
                    if t["signal_no"] == signal["signal_no"] and t["direction"] != signal["direction"]:
                        if t["status"] == "PENDENTE":
                            t.update(status="ANNULLATA", reason="inversione")
                        else:
                            close(t, prices.at(ts) or signal["entry"], ts, "INVERSIONE")
            market = signal.get("order_type", "MARKET") == "MARKET"
            trades[msg["id"]] = {
                "id": msg["id"], "date": msg["date"], "open_ts": ts, "checked": ts,
                "signal_no": signal["signal_no"], "family": fam, "label": _label(signal["signal_no"]),
                "direction": signal["direction"], "order_type": signal.get("order_type", "MARKET"),
                "entry": float(signal["entry"]), "sl": float(signal["sl"]),
                "tp": float(signal["tp"]) if signal.get("tp") else None, "first_sl": float(signal["sl"]),
                "status": "APERTA" if market or not prices else "PENDENTE",
                "be": False, "exit": None, "exit_ts": None, "reason": None, "pips": None,
            }
            order.append(msg["id"])
            continue

        if action in ("BLOCK_SIGNAL",):
            continue

        if action == "FREE_CLOSE":
            reply = msg.get("reply_to")
            t = trades.get(reply) if reply else None
            if t is None:
                if signal.get("reply_only"):
                    continue
                if last_free_close is not None and ts - last_free_close < FREE_CLOSE_COOLDOWN_MINUTES * 60:
                    continue
                candidates = [x for x in open_trades() if x["status"] == "APERTA"]
                if signal.get("signal_no") is not None:
                    candidates = [x for x in candidates if x["signal_no"] == signal["signal_no"]]
                if not candidates:
                    continue
                t = candidates[-1]
            last_free_close = ts
            if t["status"] == "PENDENTE":
                t.update(status="ANNULLATA", reason="annullato")
            elif t["status"] == "APERTA":
                close(t, prices.at(ts), ts, "CHIUSA A PAROLE")
            continue

        t = target_for(msg, signal)
        if t is None or t["status"] not in ("APERTA", "PENDENTE"):
            continue
        if action == "CANCEL":
            if t["status"] == "PENDENTE":
                t.update(status="ANNULLATA", reason="annullato")
            else:
                close(t, prices.at(ts), ts, "ANNULLATO DALLA SALA")
        elif t["status"] == "PENDENTE":
            continue
        elif action == "BREAKEVEN":
            new_sl = signal.get("new_sl") or t["entry"]
            t["sl"], t["be"] = float(new_sl), True
        elif action == "MOVE_SL":
            new_sl = signal.get("new_sl")
            if new_sl and abs(float(new_sl) - t["entry"]) < t["entry"] * 0.2:
                t["sl"] = float(new_sl)
        elif action in ("TP_HIT", "SL_HIT", "CLOSE"):
            reason = {"TP_HIT": "TP", "SL_HIT": "SL", "CLOSE": "CHIUSA DALLA SALA"}[action]
            exit_price = signal.get("exit_price")
            if exit_price is None:
                exit_price = t["tp"] if action == "TP_HIT" and t["tp"] else \
                    t["sl"] if action == "SL_HIT" else prices.at(ts)
            close(t, exit_price, ts, reason, pips=signal.get("pips"))

    for i in order:
        t = trades[i]
        if t["status"] in ("APERTA", "PENDENTE"):
            advance(t, now)
        if t["status"] == "APERTA" and prices:
            last = prices.bars[-1][4]
            sign = 1 if t["direction"] == "BUY" else -1
            t["pips"] = (last - t["entry"]) * sign / PIP_SIZE
            t["reason"] = "ANCORA APERTA"
        elif t["status"] == "PENDENTE":
            t.update(status="NON ESEGUITA", reason="mai eseguito")
    return [trades[i] for i in order]


# ============================================================
# STATISTICHE
# ============================================================
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
        "avg": sum(values) / len(values) if values else 0.0,
        "avg_win": sum(wins) / len(wins) if wins else 0.0,
        "avg_loss": sum(losses) / len(losses) if losses else 0.0,
        "pf": (sum(wins) / gross_loss) if gross_loss else float("inf") if wins else 0.0,
        "worst": min(values) if values else 0.0,
        "streak": worst_streak,
        "drawdown": drawdown,
    }


def verdict(s):
    if s["n"] < MIN_TRADES:
        return "POCHI DATI" + (" (finora perde)" if s["net"] < 0 else "")
    if s["net"] < 0 or s["pf"] < 1.0:
        return "BLOCCARE"
    if s["pf"] < 1.3:
        return "DEBOLE"
    return "TENERE"


def _fmt_pf(pf):
    return "inf" if pf == float("inf") else f"{pf:.2f}"


def trade_usd(row, profits):
    ticket = row.get("position_ticket")
    if ticket and int(ticket) in profits:
        return profits[int(ticket)]
    # Stima dai pips: 1 pip = PIP_SIZE $ di prezzo, 1 lotto = 100 once.
    return float(row["pips"]) * PIP_SIZE * float(row.get("volume") or 0.01) * 100


def _table(groups, title):
    """groups: {chiave: [valori $ in ordine di tempo]}"""
    lines = [title]
    header = (f"{'SIGNAL':<22}{'Op.':>5}{'Vinte':>7}{'Netto $':>10}{'Media $':>9}{'Media +':>9}{'Media -':>9}"
              f"{'PF':>7}{'Peggiore':>10}{'Perse fila':>11}{'DD max $':>10}  Giudizio")
    lines.append(header)
    lines.append("-" * (len(header) + 12))
    for key, values in sorted(groups.items(), key=lambda kv: stats(kv[1])["net"], reverse=True):
        s = stats(values)
        lines.append(f"{key:<22}{s['n']:>5}{s['win_rate']:>6.0f}%{s['net']:>10.2f}{s['avg']:>9.2f}"
                     f"{s['avg_win']:>9.2f}{s['avg_loss']:>9.2f}{_fmt_pf(s['pf']):>7}{s['worst']:>10.2f}"
                     f"{s['streak']:>11}{s['drawdown']:>10.2f}  {verdict(s)}")
    allv = [v for vals in groups.values() for v in vals]
    if allv:
        s = stats(allv)
        lines.append(f"{'TOTALE':<22}{s['n']:>5}{s['win_rate']:>6.0f}%{s['net']:>10.2f}{s['avg']:>9.2f}"
                     f"{'':>18}{_fmt_pf(s['pf']):>7}{s['worst']:>10.2f}{s['streak']:>11}{s['drawdown']:>10.2f}")
    return lines


def _session(ts):
    """Fascia oraria italiana di apertura."""
    hour = (datetime.fromtimestamp(ts, timezone.utc) + timedelta(hours=1)).hour
    if hour < 9:
        return "notte/Asia (0-9)"
    if hour < 14:
        return "Londra (9-14)"
    if hour < 18:
        return "New York (14-18)"
    return "sera (18-24)"


def _what_if(values_by_key, ordered_values):
    """Per ogni segnale: netto e DD se lo escludi."""
    total = stats([v for _, v in ordered_values])
    lines = []
    for key in sorted(values_by_key):
        kept = [v for k, v in ordered_values if k != key]
        s = stats(kept)
        lines.append(f"  senza {key:<6}: netto {s['net']:+9.2f} $ ({s['net'] - total['net']:+8.2f})   "
                     f"DD max {s['drawdown']:8.2f} $")
    return lines


def report(sala, bot_trades, profits, bot_signals, since):
    out = []
    out.append("=" * 100)
    out.append(f"ANALISI SEGNALI GOLD EMPIRE dal {since.date().isoformat()} "
               f"- generata il {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    out.append("Importi in $ per 0,01 lotti (sala: 1 pip = 0,10 $). Netto = somma dei risultati.")
    out.append("=" * 100)

    # ---------- SALA ----------
    closed = [t for t in sala if t["status"] == "CHIUSA" and t["pips"] is not None]
    still_open = [t for t in sala if t["status"] == "APERTA"]
    not_filled = [t for t in sala if t["status"] in ("NON ESEGUITA", "ANNULLATA")]
    no_price = [t for t in sala if t["status"] == "CHIUSA" and t["pips"] is None]
    out.append(f"\n### 1) LA SALA: {len(sala)} segnali di apertura letti "
               f"({len(closed)} chiusi, {len(still_open)} ancora aperti, {len(not_filled)} pendenti mai eseguiti "
               f"o annullati, {len(no_price)} chiusi senza prezzo)")
    if sala:
        by_fam, by_label, by_dir, by_sess, by_month = (defaultdict(list) for _ in range(5))
        seq_fam, seq_label = [], []
        for t in sorted(closed, key=lambda x: x["exit_ts"] or x["open_ts"]):
            usd = t["pips"] * USD_PER_PIP
            by_fam["SIGNAL " + t["family"]].append(usd)
            by_label[t["label"]].append(usd)
            by_dir[f"{t['label']} {t['direction']}"].append(usd)
            by_sess[f"{t['family']} {_session(t['open_ts'])}"].append(usd)
            by_month[f"{t['family']} {t['date'][:7]}"].append(usd)
            seq_fam.append(("SIGNAL " + t["family"], usd))
            seq_label.append((t["label"], usd))
        out += [""] + _table(by_fam, "Per famiglia (tutti i 5.x insieme):")
        out += [""] + _table(by_label, "Per singolo segnale (5.1, 5.2 ... separati):")
        out += [""] + _table(by_dir, "Per segnale e direzione:")
        out += [""] + _table(by_month, "Per famiglia e mese (per vedere se sta peggiorando):")
        out += [""] + _table(by_sess, "Per famiglia e orario di apertura (ora italiana):")
        reasons = defaultdict(list)
        for t in closed:
            reasons[t["reason"]].append(t["pips"] * USD_PER_PIP)
        out += [""] + _table(reasons, "Come si chiudono (tutti i segnali):")
        out.append("\nCosa succede se escludi un segnale (sala, singoli segnali):")
        out += _what_if(by_label, seq_label)
        if still_open:
            out.append("\nAncora aperti nella sala (risultato al prezzo attuale, non contati sopra):")
            for t in still_open:
                out.append(f"  {t['date'][:16]} SIGNAL {t['label']} {t['direction']} @ {t['entry']:.2f} "
                           f"-> {t['pips'] * USD_PER_PIP:+.2f} $")

    # ---------- BOT ----------
    out.append(f"\n### 2) IL BOT (operazioni vere, profitto {'reale MT5' if profits else 'stimato dai pips'}): "
               f"{len(bot_trades)} chiuse")
    if bot_trades:
        fam, lab = defaultdict(list), defaultdict(list)
        for row in bot_trades:
            usd = trade_usd(row, profits)
            fam["SIGNAL " + family(row["signal_no"])].append(usd)
            lab[_label(row["signal_no"])].append(usd)
        out += [""] + _table(fam, "Per famiglia:")
        out += [""] + _table(lab, "Per singolo segnale:")

    # ---------- CONFRONTO ----------
    if sala:
        out.append("\n### 3) CONFRONTO SALA / BOT")
        opened_ids = {sid for sid, r in bot_signals.items() if r.get("position_ticket")}
        missed = [t for t in closed if t["id"] not in opened_ids]
        taken = [t for t in closed if t["id"] in opened_ids]
        s_taken = stats([t["pips"] * USD_PER_PIP for t in taken])
        s_missed = stats([t["pips"] * USD_PER_PIP for t in missed])
        out.append(f"Segnali della sala APERTI dal bot: {s_taken['n']}  (nella sala hanno fatto "
                   f"{s_taken['net']:+.2f} $)")
        out.append(f"Segnali della sala NON aperti dal bot: {s_missed['n']}  (nella sala hanno fatto "
                   f"{s_missed['net']:+.2f} $)")
        reasons = defaultdict(list)
        for t in missed:
            row = bot_signals.get(t["id"])
            reasons[row["status"] if row else "NON VISTO DAL BOT"].append(t["pips"] * USD_PER_PIP)
        for k, v in sorted(reasons.items(), key=lambda kv: -len(kv[1])):
            out.append(f"   - {k:<24} {len(v):>3} segnali, nella sala {sum(v):+9.2f} $")

    # ---------- CONSIGLIO ----------
    out.append("\n### 4) GIUDIZIO FINALE (sala, singoli segnali)")
    if sala and closed:
        by_label = defaultdict(list)
        for t in sorted(closed, key=lambda x: x["exit_ts"] or x["open_ts"]):
            by_label[t["label"]].append(t["pips"] * USD_PER_PIP)
        keep, weak, block, few = [], [], [], []
        for k, v in by_label.items():
            verdict_text = verdict(stats(v))
            (block if verdict_text == "BLOCCARE" else weak if verdict_text == "DEBOLE"
             else keep if verdict_text == "TENERE" else few).append(k)
        out.append("  TENERE:     " + (", ".join(sorted(keep)) or "-"))
        out.append("  DEBOLI:     " + (", ".join(sorted(weak)) or "-"))
        out.append("  BLOCCARE:   " + (", ".join(sorted(block)) or "-"))
        out.append("  POCHI DATI: " + (", ".join(sorted(few)) or "-"))
        out.append("Nota: EXCLUDED_SIGNALS blocca una FAMIGLIA intera (es. 5 = tutti i 5.x).")
    out.append(f"\nLegenda: PF = profitti / perdite (sopra 1,3 buono, sotto 1 perde). DD = calo massimo. "
               f"POCHI DATI = meno di {MIN_TRADES} operazioni: risultato non affidabile.")
    return "\n".join(out)


def write_sala_csv(sala, bot_signals, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["data_utc", "messaggio", "signal", "famiglia", "direzione", "tipo", "ingresso", "sl_iniziale",
                    "tp", "stato", "chiusura", "uscita", "pips", "dollari_001", "bot"])
        for t in sala:
            row = bot_signals.get(t["id"])
            bot = "APERTA" if row and row.get("position_ticket") else (row["status"] if row else "non visto")
            num = (lambda x: "" if x is None else f"{x:.2f}".replace(".", ","))
            w.writerow([t["date"][:16].replace("T", " "), t["id"], t["label"], t["family"], t["direction"],
                        t["order_type"], num(t["entry"]), num(t["first_sl"]), num(t["tp"]), t["status"],
                        t["reason"] or "", num(t["exit"]), num(t["pips"]),
                        num(None if t["pips"] is None else t["pips"] * USD_PER_PIP), bot])


def write_bot_csv(trades, profits, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["chiusa", "signal", "famiglia", "direzione", "ingresso", "chiusura", "esito", "pips", "dollari"])
        for row in trades:
            w.writerow([row["closed_at"][:16].replace("T", " "), row["signal_no"], family(row["signal_no"]),
                        row["direction"], row["open_price"], row["close_price"], row["status"].replace("CLOSED_", ""),
                        f"{float(row['pips']):.1f}".replace(".", ","),
                        f"{trade_usd(row, profits):.2f}".replace(".", ",")])


def main():
    args = [a.lower() for a in sys.argv[1:]]
    offline = "offline" in args
    dates = [a for a in args if a != "offline"]
    since = datetime.fromisoformat(dates[0] if dates else DEFAULT_SINCE).replace(tzinfo=timezone.utc)

    messages = get_messages(since, offline)
    bars = get_prices(since, offline)
    if messages and not bars:
        print("⚠️ Senza prezzi M1 i segnali chiusi solo da SL/TP non annunciati non si possono ricostruire bene.")
    sala = simulate(messages, bars)
    bot_trades = load_trades(DB_PATH, since)
    profits = real_profits([r["position_ticket"] for r in bot_trades if r.get("position_ticket")])
    bot_signals = load_all_signals(DB_PATH)

    text = report(sala, bot_trades, profits, bot_signals, since)
    print(text)
    (DATA_DIR / "analisi_segnali.txt").write_text(text, encoding="utf-8")
    if sala:
        write_sala_csv(sala, bot_signals, DATA_DIR / "analisi_sala.csv")
    if bot_trades:
        write_bot_csv(bot_trades, profits, DATA_DIR / "analisi_segnali.csv")
    print(f"\nFile salvati nella cartella {DATA_DIR}: analisi_segnali.txt, analisi_sala.csv, analisi_segnali.csv, "
          "sala_messaggi.json, sala_prezzi_m1.csv")


if __name__ == "__main__":
    main()
