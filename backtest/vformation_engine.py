"""
Motore di backtest della strategia V-Formation.

Replica la logica di tradingview/v_formation/v_formation_strategy.pine:
impulso -> ritraccio -> V-Formation, entry limite sul ritraccio della gamba
destra, stop oltre la V, TP1 parziale + TP2, filtri di bias, sessione e sweep.

Differenze rispetto al backtester di TradingView (volute, per essere più realistici):
- i prezzi delle barre sono BID (come in MT5); i long entrano e gli short
  escono all'ASK = BID + spread (spread storico della barra o fisso);
- dentro la barra il percorso è O->H->L->C oppure O->L->H->C, come fa
  TradingView: si sceglie l'estremo più vicino all'apertura;
- se sono pendenti sia un long che uno short e uno viene eseguito,
  l'altro non può più entrare (niente inversioni di posizione);
- i risultati sono in R (multipli del rischio iniziale), indipendenti dal lotto.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time as dtime

import numpy as np
import pandas as pd

# ─────────────────────────────── PARAMETRI ────────────────────────────────────


@dataclass
class Params:
    # Swing e V-Formation
    piv_len: int = 3
    atr_len: int = 14
    imp_min_atr: float = 2.0
    ret_min: float = 0.5
    ret_max: float = 0.886
    need_break_c: bool = True
    v_tol_atr: float = 0.1
    min_rank: str = "A"              # "A" oppure "S"
    max_right_bars: int = 20
    # Entry e uscite
    entry_fib: float = 0.5
    pending_max: int = 30
    sl_buf_atr: float = 0.1
    tp1_mode: str = "right_high"     # right_high | impulse_high | rr
    tp1_rr: float = 1.0
    tp1_pct: float = 50.0
    tp2_mode: str = "impulse_high"   # impulse_high | rr
    tp2_rr: float = 2.0
    be_after_tp1: bool = True
    min_rr: float = 1.0
    # Filtri di contesto
    bias_mode: str = "struct"        # struct | ema | off
    htf: str = "1h"                  # frequenza pandas: 15min, 30min, 1h, 4h, 1D
    htf_piv: int = 3
    htf_ema_len: int = 50
    use_session: bool = True
    session: str = "09:00-17:00"
    local_tz: str = "Europe/Rome"
    close_eos: bool = False
    sweep_mode: str = "off"          # off | asia_pd | pd | asia
    asia_session: str = "01:00-08:00"
    max_trades_day: int = 2
    # Rischio (solo per la simulazione dell'equity)
    risk_pct: float = 1.0
    risk_a_mult: float = 0.5
    # Costi
    spread_pips: float | None = None  # None = spread storico della barra (MT5)
    slippage_pips: float = 0.0        # applicato a stop loss e break-even


DIAG_NAMES = [
    "V trovate",
    "Ordini piazzati",
    "Ordini eseguiti",
    "Scartate: prezzo oltre la V",
    "Scartate: gamba destra corta",
    "Scartate: sessione/limiti",
    "Scartate: bias contrario",
    "Scartate: R:R basso",
    "Ordini scaduti",
    "Ordini annullati da filtro",
]
D_FOUND, D_PLACED, D_FILLED, D_BROKEN, D_NORANK, D_CONTEXT, D_BIAS, D_RR, D_TIMEOUT, D_FILTER = range(10)

# ─────────────────────────────── INDICATORI ───────────────────────────────────


def atr_rma(h: np.ndarray, l: np.ndarray, c: np.ndarray, n: int) -> np.ndarray:
    """ATR di Wilder (come ta.atr di TradingView)."""
    prev_c = np.concatenate(([c[0]], c[:-1]))
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev_c), np.abs(l - prev_c)))
    tr[0] = h[0] - l[0]
    out = np.full(len(tr), np.nan)
    if len(tr) < n:
        return out
    out[n - 1] = tr[:n].mean()
    alpha = 1.0 / n
    for i in range(n, len(tr)):
        out[i] = out[i - 1] + alpha * (tr[i] - out[i - 1])
    return out


def pivots(h: np.ndarray, l: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
    """
    Pivot high/low con n barre a sinistra e n a destra.
    Ritorna due array booleani indicizzati sulla barra del pivot (non su
    quella di conferma, che è n barre dopo).
    """
    size = len(h)
    is_ph = np.zeros(size, dtype=bool)
    is_pl = np.zeros(size, dtype=bool)
    if size < 2 * n + 1:
        return is_ph, is_pl
    win = 2 * n + 1
    hw = np.lib.stride_tricks.sliding_window_view(h, win)
    lw = np.lib.stride_tricks.sliding_window_view(l, win)
    center_h = hw[:, n]
    center_l = lw[:, n]
    # strettamente più alto delle barre a sinistra, non superato a destra
    ph = (center_h > hw[:, :n].max(axis=1)) & (center_h >= hw[:, n + 1:].max(axis=1))
    pl = (center_l < lw[:, :n].min(axis=1)) & (center_l <= lw[:, n + 1:].min(axis=1))
    is_ph[n:size - n] = ph
    is_pl[n:size - n] = pl
    return is_ph, is_pl


def _parse_session(s: str) -> tuple[int, int]:
    a, b = s.split("-")
    ta, tb = dtime.fromisoformat(a), dtime.fromisoformat(b)
    return ta.hour * 60 + ta.minute, tb.hour * 60 + tb.minute


def session_mask(local_minutes: np.ndarray, session: str) -> np.ndarray:
    start, end = _parse_session(session)
    if start <= end:
        return (local_minutes >= start) & (local_minutes < end)
    return (local_minutes >= start) | (local_minutes < end)


def htf_bias(times: pd.Series, o, h, l, c, p: Params) -> np.ndarray:
    """Bias del timeframe superiore, preso dall'ultima candela HTF già chiusa."""
    if p.bias_mode == "off":
        return np.zeros(len(times), dtype=int)
    df = pd.DataFrame({"open": o, "high": h, "low": l, "close": c}, index=pd.DatetimeIndex(times))
    htf = df.resample(p.htf, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    ).dropna()
    hh, hl, hc = htf["high"].to_numpy(), htf["low"].to_numpy(), htf["close"].to_numpy()
    bias = np.zeros(len(htf), dtype=int)
    if p.bias_mode == "struct":
        n = p.htf_piv
        is_ph, is_pl = pivots(hh, hl, n)
        last_h = last_l = np.nan
        b = 0
        for i in range(len(htf)):
            j = i - n                      # pivot confermato su questa candela
            if j >= 0 and is_ph[j]:
                last_h = hh[j]
            if j >= 0 and is_pl[j]:
                last_l = hl[j]
            if not np.isnan(last_h) and hc[i] > last_h:
                b = 1
            elif not np.isnan(last_l) and hc[i] < last_l:
                b = -1
            bias[i] = b
    elif p.bias_mode == "ema":
        ema = pd.Series(hc).ewm(span=p.htf_ema_len, adjust=False).mean().to_numpy()
        bias = np.sign(hc - ema).astype(int)
    else:
        raise ValueError(f"bias_mode sconosciuto: {p.bias_mode}")
    # valore della candela HTF precedente (chiusa) per ogni barra del TF operativo
    shifted = pd.Series(bias, index=htf.index).shift(1)
    buckets = pd.DatetimeIndex(times).floor(p.htf) if not p.htf.upper().endswith("D") else pd.DatetimeIndex(times).floor("D")
    return shifted.reindex(buckets).fillna(0).astype(int).to_numpy()


def prev_day_levels(times: pd.Series, h, l) -> tuple[np.ndarray, np.ndarray]:
    """Massimo/minimo del giorno precedente (giorni del server del broker, come D1 di MT5)."""
    df = pd.DataFrame({"high": h, "low": l}, index=pd.DatetimeIndex(times))
    d = df.resample("1D").agg({"high": "max", "low": "min"}).dropna().shift(1)
    days = pd.DatetimeIndex(times).floor("D")
    return d["high"].reindex(days).to_numpy(), d["low"].reindex(days).to_numpy()


# ─────────────────────────────── STRUTTURE ────────────────────────────────────


class Setup:
    """Setup di una direzione. I prezzi sono in "spazio direzionale" (prezzo × dir)."""

    __slots__ = ("dir", "state", "a", "b", "c", "d", "e", "f", "e_bar", "placed_bar",
                 "sl", "rank", "entry", "tp1", "tp2", "filled_bar", "found_time")

    def __init__(self, direction: int):
        self.dir = direction
        self.state = 0      # 0 nessuno, 1 V in formazione, 2 ordine limite, 3 in posizione
        self.rank = 0
        self.filled_bar = -1


@dataclass
class Position:
    dir: int
    rank: int
    entry_price: float
    sl: float
    tp1: float
    tp2: float
    risk: float
    entry_bar: int
    setup_info: dict
    frac: float = 1.0
    tp1_done: bool = False
    be_done: bool = False
    r: float = 0.0
    exits: list = field(default_factory=list)


# ─────────────────────────────── BACKTEST ─────────────────────────────────────


def run_backtest(df: pd.DataFrame, p: Params, point: float, pip: float,
                 server_tz: str = "Europe/Athens", symbol: str = "") -> tuple[pd.DataFrame, list[int]]:
    """
    df: colonne time (ora del server MT5, naive), open, high, low, close e,
    opzionale, spread (in point). Ritorna (trade, contatori di diagnostica).
    """
    times = pd.to_datetime(df["time"]).reset_index(drop=True)
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    n_bars = len(df)

    if p.spread_pips is not None:
        spread = np.full(n_bars, p.spread_pips * pip)
    elif "spread" in df.columns:
        spread = df["spread"].to_numpy(float) * point
    else:
        spread = np.zeros(n_bars)
    slip = p.slippage_pips * pip

    n = p.piv_len
    atr = atr_rma(h, l, c, p.atr_len)
    is_ph, is_pl = pivots(h, l, n)

    # estremi delle n barre dopo il pivot (inizio della gamba destra)
    hh_after = pd.Series(h).rolling(n, min_periods=1).max().to_numpy()
    ll_after = pd.Series(l).rolling(n, min_periods=1).min().to_numpy()

    local = (pd.DatetimeIndex(times)
             .tz_localize(server_tz, ambiguous=np.zeros(n_bars, dtype=bool), nonexistent="shift_forward")
             .tz_convert(p.local_tz))
    local_min = (local.hour * 60 + local.minute).to_numpy()
    local_day = (local.year * 10000 + local.month * 100 + local.day).to_numpy()
    in_sess_raw = session_mask(local_min, p.session)
    in_sess = in_sess_raw if p.use_session else np.ones(n_bars, dtype=bool)
    in_asia = session_mask(local_min, p.asia_session)

    bias = htf_bias(times, o, h, l, c, p)
    pdh, pdl = prev_day_levels(times, h, l)

    use_asia_sw = p.sweep_mode in ("asia_pd", "asia")
    use_pd_sw = p.sweep_mode in ("asia_pd", "pd")
    swept_low = np.zeros(n_bars, dtype=bool)
    swept_high = np.zeros(n_bars, dtype=bool)

    zz_p: list[float] = []
    zz_b: list[int] = []
    zz_t: list[int] = []

    diag = [0] * len(DIAG_NAMES)
    trades: list[dict] = []
    L, S = Setup(1), Setup(-1)
    pos: Position | None = None
    trades_today = 0
    asia_run_hi = asia_run_lo = asia_hi = asia_lo = np.nan
    min_rank = 2 if p.min_rank == "S" else 1
    t_now = [-1]

    # ── helper ──────────────────────────────────────────────────────────────
    def add_swing(t: int, price: float, bar: int) -> bool:
        if zz_t and zz_t[-1] == t:
            if (t == 1 and price > zz_p[-1]) or (t == -1 and price < zz_p[-1]):
                zz_p[-1] = price
                zz_b[-1] = bar
                return True
            return False
        zz_p.append(price)
        zz_b.append(bar)
        zz_t.append(t)
        if len(zz_t) > 50:
            del zz_p[0], zz_b[0], zz_t[0]
        return True

    def pattern(direction: int, atr_now: float):
        if len(zz_t) < 5 or zz_t[-1] != -direction or np.isnan(atr_now):
            return None
        pa, pb, pc, pd_, pe = (direction * x for x in zz_p[-5:])
        imp = pb - pa
        if imp <= 0:
            return None
        ret = (pb - pe) / imp
        ok = (imp >= p.imp_min_atr * atr_now and pb > pd_ and pe > pa
              and p.ret_min <= ret <= p.ret_max and (not p.need_break_c or pe < pc))
        return (pa, pb, pc, pd_, pe, zz_b[-1]) if ok else None

    def arm(s: Setup, pat, f_init: float, t: int):
        s.a, s.b, s.c, s.d, s.e, s.e_bar = pat
        s.f = f_init
        s.sl = s.e - p.sl_buf_atr * atr[t]
        s.rank = 0
        s.placed_bar = -1
        s.found_time = times[t]
        s.state = 1

    def close_part(frac: float, price: float, reason: str, t: int):
        nonlocal pos
        r = frac * pos.dir * (price - pos.entry_price) / pos.risk
        pos.r += r
        pos.frac -= frac
        pos.exits.append((reason, round(frac, 4), price, str(times[t])))
        if pos.frac <= 1e-9:
            info = pos.setup_info
            trades.append({
                "simbolo": symbol,
                "lato": "long" if pos.dir == 1 else "short",
                "rango": "S" if pos.rank == 2 else "A",
                "v_trovata": info["found_time"],
                "entry_time": times[pos.entry_bar],
                "exit_time": times[t],
                "entry": pos.entry_price,
                "sl": info["sl"],
                "tp1": pos.tp1,
                "tp2": pos.tp2,
                "R": round(pos.r, 4),
                "uscite": " | ".join(f"{e[0]} {e[1]:.0%} @{e[2]:.5f}" for e in pos.exits),
                "durata_barre": t - pos.entry_bar,
            })
            pos = None

    def open_pos(s: Setup, price: float, t: int):
        nonlocal pos
        d = s.dir
        sl, tp1, tp2 = d * s.sl, d * s.tp1, d * s.tp2
        risk = d * (price - sl)
        if risk <= 0:            # entry peggiore dello stop (gap enorme): si ignora
            s.state = 0
            return
        pos = Position(dir=d, rank=s.rank, entry_price=price, sl=sl, tp1=tp1, tp2=tp2,
                       risk=risk, entry_bar=t,
                       setup_info={"found_time": s.found_time, "sl": sl})
        s.filled_bar = t

    def triggers(sp: float):
        """Livelli attivi in prezzo BID: (tipo, setup, direzione di attraversamento, livello)."""
        out = []
        if pos is None:
            # niente nuovi ingressi se in questa barra un ordine è già stato eseguito
            if L.filled_bar == t_now[0] or S.filled_bar == t_now[0]:
                return out
            for s in (L, S):
                if s.state == 2:
                    if s.dir == 1:
                        out.append(("fill", s, -1, s.entry - sp))          # ask <= entry
                    else:
                        out.append(("fill", s, 1, -s.entry))               # bid >= entry
        elif pos.dir == 1:
            out.append(("sl", None, -1, pos.sl))
            if not pos.tp1_done:
                out.append(("tp1", None, 1, pos.tp1))
            out.append(("tp2", None, 1, pos.tp2))
        else:
            out.append(("sl", None, 1, pos.sl - sp))                       # ask >= sl
            if not pos.tp1_done:
                out.append(("tp1", None, -1, pos.tp1 - sp))                # ask <= tp
            out.append(("tp2", None, -1, pos.tp2 - sp))
        return out

    def apply(kind: str, s: Setup | None, bid: float, sp: float, t: int):
        if kind == "fill":
            open_pos(s, bid + sp if s.dir == 1 else bid, t)
            return
        long_ = pos.dir == 1
        exit_px = bid if long_ else bid + sp
        if kind == "sl":
            exit_px = exit_px - slip if long_ else exit_px + slip
            close_part(pos.frac, exit_px, "BE" if pos.be_done else "SL", t)
        elif kind == "tp1":
            pos.tp1_done = True
            close_part(min(pos.frac, p.tp1_pct / 100.0), exit_px, "TP1", t)
        else:
            close_part(pos.frac, exit_px, "TP2", t)

    def execute_bar(t: int):
        t_now[0] = t
        sp = spread[t]
        bo, bh, bl, bc = o[t], h[t], l[t], c[t]
        # 1) livelli già superati all'apertura (gap): esecuzione al prezzo di apertura
        for _ in range(4):
            hit = next(((k, s) for k, s, dr, lv in triggers(sp)
                        if (dr == -1 and bo <= lv) or (dr == 1 and bo >= lv)), None)
            if hit is None:
                break
            apply(hit[0], hit[1], bo, sp, t)
        # 2) percorso intrabar
        path = [bo, bh, bl, bc] if (bh - bo) < (bo - bl) else [bo, bl, bh, bc]
        for a, b in zip(path[:-1], path[1:]):
            cur = a
            for _ in range(6):
                cands = [(lv, k, s) for k, s, dr, lv in triggers(sp)
                         if (b > cur and dr == 1 and cur <= lv <= b)
                         or (b < cur and dr == -1 and b <= lv <= cur)]
                if not cands:
                    break
                lv, k, s = min(cands, key=lambda x: x[0]) if b > cur else max(cands, key=lambda x: x[0])
                apply(k, s, lv, sp, t)
                cur = lv

    def cancel(s: Setup, reason: int):
        diag[reason] += 1
        s.state = 0

    def step(s: Setup, hi_d: float, lo_d: float, ctx_ok: bool, bias_ok: bool, t: int):
        if s.state not in (1, 2):
            return
        if hi_d > s.f:
            s.f = hi_d
        tol = p.v_tol_atr * atr[t]
        s.rank = 2 if s.f > s.d + tol else (1 if s.f >= s.d - tol else 0)
        leg = s.f - s.e
        s.entry = s.f - p.entry_fib * leg
        risk = s.entry - s.sl
        if p.tp1_mode == "right_high":
            s.tp1 = s.f
        elif p.tp1_mode == "impulse_high":
            s.tp1 = max(s.b, s.f)
        else:
            s.tp1 = s.entry + p.tp1_rr * risk
        tp2_liq = s.b if s.b > s.f + tol else s.entry + p.tp2_rr * risk
        s.tp2 = max(tp2_liq if p.tp2_mode == "impulse_high" else s.entry + p.tp2_rr * risk, s.tp1)
        final_tp = s.tp1 if p.tp1_pct >= 100 else s.tp2
        rr = (final_tp - s.entry) / risk if risk > 0 else 0.0
        rank_ok = s.rank >= min_rank
        rr_ok = risk > 0 and s.tp1 > s.entry and rr >= p.min_rr
        can_place = ctx_ok and bias_ok and rank_ok and rr_ok
        broken = lo_d < s.e
        age = t - s.e_bar
        expired = s.state == 1 and ((s.rank == 0 and age > p.max_right_bars) or age > p.max_right_bars + p.pending_max)
        timeout = s.state == 2 and t - s.placed_bar > p.pending_max
        filtered = s.state == 2 and not can_place
        if broken or expired or timeout or filtered:
            reason = (D_BROKEN if broken else D_TIMEOUT if timeout else D_FILTER if filtered
                      else D_NORANK if not rank_ok else D_CONTEXT if not ctx_ok
                      else D_BIAS if not bias_ok else D_RR)
            cancel(s, reason)
            return
        if s.state == 1 and can_place:
            s.state = 2
            s.placed_bar = t
            diag[D_PLACED] += 1

    # ── loop principale ─────────────────────────────────────────────────────
    for t in range(n_bars):
        if t > 0 and local_day[t] != local_day[t - 1]:
            trades_today = 0

        # sessione asiatica (come nello script Pine)
        prev_asia = in_asia[t - 1] if t > 0 else False
        if in_asia[t] and not prev_asia:
            asia_run_hi, asia_run_lo = h[t], l[t]
        elif in_asia[t]:
            asia_run_hi, asia_run_lo = max(asia_run_hi, h[t]), min(asia_run_lo, l[t])
        if not in_asia[t] and prev_asia:
            asia_hi, asia_lo = asia_run_hi, asia_run_lo
        swept_low[t] = ((use_asia_sw and not np.isnan(asia_lo) and l[t] < asia_lo)
                        or (use_pd_sw and not np.isnan(pdl[t]) and l[t] < pdl[t]))
        swept_high[t] = ((use_asia_sw and not np.isnan(asia_hi) and h[t] > asia_hi)
                         or (use_pd_sw and not np.isnan(pdh[t]) and h[t] > pdh[t]))

        # 1) esecuzione degli ordini durante la barra
        execute_bar(t)

        # 2) alla chiusura: fill, break-even
        for s in (L, S):
            if s.state == 2 and s.filled_bar == t:
                diag[D_FILLED] += 1
                trades_today += 1
                s.state = 3 if (pos is not None and pos.dir == s.dir) else 0
            elif s.state == 3:
                if pos is None or pos.dir != s.dir:
                    s.state = 0
                elif p.be_after_tp1 and pos.tp1_done and not pos.be_done:
                    pos.sl = pos.entry_price
                    pos.be_done = True

        # 3) nuovi swing e nuove V
        new_high = new_low = False
        j = t - n
        if j >= 0 and is_ph[j]:
            new_high = add_swing(1, h[j], j)
        if j >= 0 and is_pl[j]:
            new_low = add_swing(-1, l[j], j)
        if new_low and L.state != 3:
            pat = pattern(1, atr[t])
            if pat and (p.sweep_mode == "off" or swept_low[j]):
                arm(L, pat, hh_after[t], t)
                diag[D_FOUND] += 1
        if new_high and S.state != 3:
            pat = pattern(-1, atr[t])
            if pat and (p.sweep_mode == "off" or swept_high[j]):
                arm(S, pat, -ll_after[t], t)
                diag[D_FOUND] += 1

        # 4) avanzamento dei setup
        flat = pos is None
        base_ok = bool(in_sess[t]) and flat and trades_today < p.max_trades_day
        b = bias[t]
        step(L, h[t], l[t], base_ok, p.bias_mode == "off" or b == 1, t)
        step(S, -l[t], -h[t], base_ok, p.bias_mode == "off" or b == -1, t)

        # 5) chiusura a fine sessione
        if p.close_eos and pos is not None and t > 0 and in_sess_raw[t - 1] and not in_sess_raw[t]:
            exit_px = c[t] if pos.dir == 1 else c[t] + spread[t]
            close_part(pos.frac, exit_px, "Fine sessione", t)

    if pos is not None:
        exit_px = c[-1] if pos.dir == 1 else c[-1] + spread[-1]
        close_part(pos.frac, exit_px, "Fine dati", n_bars - 1)

    return pd.DataFrame(trades), diag
