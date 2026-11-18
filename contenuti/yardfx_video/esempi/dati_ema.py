import random
def ema(v, n):
    k = 2 / (n + 1); out = [v[0]]
    for x in v[1:]: out.append(out[-1] + k * (x - out[-1]))
    return out
def build(seed=3):
    r = random.Random(seed); closes = []; p = 3700.0
    for i in range(300):
        if i < 262: d = 0.35
        elif i < 278: d = -2.6
        else: d = 2.4
        p += d + r.gauss(0, 2.2); closes.append(p)
    e9, e21, e200 = ema(closes, 9), ema(closes, 21), ema(closes, 200)
    cs = []; o = closes[0]
    for i, c in enumerate(closes):
        h = max(o, c) + abs(r.gauss(0, 1.8)) + 0.5; l = min(o, c) - abs(r.gauss(0, 1.8)) - 0.5
        cs.append({'o': o, 'h': h, 'l': l, 'c': c, 'g': c >= o}); o = c
    S0 = 250; cs, e9, e21, e200 = cs[S0:], e9[S0:], e21[S0:], e200[S0:]
    xi = next(i for i in range(25, len(cs)) if e9[i - 1] < e21[i - 1] and e9[i] >= e21[i])
    entry = cs[xi]['c']; stop = min(c['l'] for c in cs[xi - 8:xi + 1]) - 1.0; tp = entry + 2 * (entry - stop)
    hit = next((i for i in range(xi + 1, len(cs)) if cs[i]['h'] >= tp), None)
    return cs, e9, e21, e200, xi, entry, stop, tp, hit
if __name__ == '__main__':
    for s in range(1, 10):
        cs, e9, e21, e200, xi, en, st, tp, hit = build(s)
        print(s, len(cs), xi, round(en), round(st), round(tp), hit, round(min(e200)), round(min(c['l'] for c in cs)), round(max(c['h'] for c in cs)), all(cs[i]['c'] > e200[i] for i in range(xi - 3, xi + 1)))
