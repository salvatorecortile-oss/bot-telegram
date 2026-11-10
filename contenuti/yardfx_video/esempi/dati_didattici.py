"""candele DIDATTICHE (inventate per l'esempio, dichiarato a voce e a schermo) e RSI 14 calcolato davvero su quelle candele"""
import random
def rsi(closes, n=14):
    out = [None] * len(closes); g = l = 0.0
    for i in range(1, len(closes)):
        ch = closes[i] - closes[i - 1]; up, dn = max(ch, 0), max(-ch, 0)
        if i <= n: g += up / n; l += dn / n
        else: g = (g * (n - 1) + up) / n; l = (l * (n - 1) + dn) / n
        if i >= n: out[i] = 100 if l == 0 else 100 - 100 / (1 + g / l)
    return out
def candles(path_closes, seed, wick=2.2):
    r = random.Random(seed); cs = []; prev = path_closes[0]
    for c in path_closes[1:]:
        o = prev; h = max(o, c) + r.uniform(0.3, wick); lo = min(o, c) - r.uniform(0.3, wick)
        cs.append({'o': o, 'h': h, 'l': lo, 'c': c, 'g': c >= o}); prev = c
    return cs
def rule_example(seed=4):
    """laterale -> discesa forte (RSI < 30) -> base -> risalita (RSI torna sopra 30) -> rally fino all'obiettivo"""
    r = random.Random(seed); p = 4060.0; path = [p]
    for i in range(22): p += r.uniform(-2.2, 2.4); path.append(p)        # laterale
    for i in range(12): p -= r.uniform(1.8, 4.8); path.append(p)         # discesa
    for i in range(6): p += r.uniform(-1.6, 1.4); path.append(p)         # base
    for i in range(30): p += r.uniform(-0.6, 2.9); path.append(p)        # risalita
    cs = candles(path, seed); cl = [c['c'] for c in cs]; rs = rsi(cl)
    below = [i for i, v in enumerate(rs) if v is not None and v < 30]
    if not below: return None
    ci = next((i for i in range(below[0], len(rs)) if rs[i] is not None and rs[i] > 30 and rs[i - 1] <= 30), None)
    if ci is None: return None
    entry = cs[ci]['c']; stop = min(c['l'] for c in cs[max(0, ci - 10):ci + 1]) - 1.5; tp = entry + 2 * (entry - stop)
    hit = next((i for i in range(ci + 1, len(cs)) if cs[i]['h'] >= tp), None)
    if hit is None: return None
    return dict(cs=cs[:hit + 3], rsi=rs[:hit + 3], ci=ci, entry=entry, stop=stop, tp=tp, hit=hit, mn=min(v for v in rs if v is not None))
def trend_example(seed=3):
    r = random.Random(seed); p = 4000.0; path = [p]
    for i in range(16): p += r.uniform(-1.5, 1.6); path.append(p)
    for i in range(44): p += r.uniform(0.2, 3.4); path.append(p)
    cs = candles(path, seed); return dict(cs=cs, rsi=rsi([c['c'] for c in cs]))
if __name__ == '__main__':
    for s in range(1, 60):
        e = rule_example(s)
        if e and e['mn'] < 25 and 15 < e['ci'] < 50: print('seed', s, 'ci', e['ci'], 'hit', e['hit'], 'n', len(e['cs']), round(e['mn'], 1), round(e['entry'], 1), round(e['stop'], 1), round(e['tp'], 1)); break
    t = trend_example(); print('trend rsi>70 frazione', sum(1 for v in t['rsi'][20:] if v and v > 70) / len(t['rsi'][20:]))
