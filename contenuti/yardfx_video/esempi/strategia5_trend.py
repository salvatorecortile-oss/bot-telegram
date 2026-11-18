"""Strategia base #5: trend su H1, entrata su M15 — voce Speechify «salvatore», esce dom 22/11/2026 ore 10.
S1 NOTTE      T0   il grafico GRANDE (pannello con trend luminoso) → DIREZIONE · quello PICCOLO (pannello piccolo con rimbalzo) → timbro MOMENTO
S2 QUADERNO   T13  'strategia BASE #5' con 5 candeline · grafico a un'ora · scala che sale con massimi/minimi cerchiati 1-2-3 (SALGONO) · scala che scende (SCENDONO)
S3 TERMINALE  T32  esempio didattico PER COMPRARE: chip 1 ORA SALE · candele 15 MIN che tornano sulla MEDIA 50 e RIPARTONO · STOP sotto il ritracciamento
S4 NOTTE      T61  PER VENDERE con linee luminose: chip 1 ORA SCENDE · il prezzo RISALE sulla media e riparte IN GIÙ · STOP sopra il ritracciamento
S5 TERMINALE  T88  OBIETTIVO in ENTRAMBI I CASI: barre RISCHIO 1 / OBIETTIVO 2 · 2 VOLTE IL RISCHIO
S6 NERO-ROSSO → QUADERNO  T98  TRAPPOLA · CONTRO IL TREND, poi come EVITARLA: ✓ prima guardo l'ora · ✕ se va di lato non opero
S7 NOTTE      T116 se ti è stata UTILE + 4 paletti (TREND) · outro logo + Telegram
Novità rispetto alla #4: numeri cerchiati sui massimi/minimi (libreria 18/11), vendita con linee luminose nel mondo Notte, barre rischio/obiettivo, base musicale minimal."""
import sys, os, math, json, random
sys.path.insert(0, '/home/user/bot-telegram/contenuti/yardfx_video'); import yardfx as Y; import suoni as S
from PIL import Image, ImageDraw, ImageFilter
D = os.path.dirname(os.path.abspath(__file__))
WORDS = json.load(open(os.path.join(D, 'words.json'))); G = Y.make_groups(WORDS)
T = lambda i: WORDS[i][1]
VEND = WORDS[-1][2]
KEYS = {2, 6, 8, 12, 16, 20, 23, 28, 31, 33, 35, 40, 43, 50, 54, 55, 60, 62, 67, 77, 81, 82, 85, 88, 90, 95, 99, 101, 106, 109, 113, 114}
CUTS = [0, T(13), T(32), T(61), T(88), T(98), T(116), VEND + 0.3]
OUT_LEN = 4.2; DUR = CUTS[-1] + OUT_LEN
TRANS = ['blur', 'zoom', 'whip', 'wipe', 'whip_v', 'zoom']
TD = 0.4; TIKTOK = os.environ.get('TIKTOK') == '1'
EV = []
def ev(t, n, g=1.0): EV.append((round(t, 3), n, g))
SP = Y.sprite
def big(b, s, xy, size, col, font=Y.BIG): ImageDraw.Draw(b).text(xy, s, font=Y.F(font, size), fill=col, anchor='mm')

def glow_line(img, pts, col, w, prog, blur=12):
    if prog <= 0: return img
    k = max(2, int(len(pts) * min(1, prog))); m = Image.new('L', (Y.W, Y.H), 0); ImageDraw.Draw(m).line(pts[:k], fill=255, width=w, joint='curve')
    img = Image.composite(Image.new('RGB', (Y.W, Y.H), tuple(int(v * 0.6) for v in col)), img, m.filter(ImageFilter.GaussianBlur(blur)))
    return Image.composite(Image.new('RGB', (Y.W, Y.H), col), img, m)
def candle(d, x, o, c, h, l, w=26, col=None):
    col = col or ((47, 179, 106) if c <= o else (224, 72, 62))
    d.line([(x, h), (x, l)], fill=col, width=4); d.rectangle((x - w / 2, min(o, c), x + w / 2, max(o, c) + 2), fill=col)
def chip(d, s, xy, col, size=44):
    f = Y.F(Y.COND, size); tw = d.textlength(s, font=f); x, y = xy
    d.rounded_rectangle((x - tw / 2 - 26, y - size * .8, x + tw / 2 + 26, y + size * .8), radius=size, fill=tuple(int(v * .22) for v in col), outline=col, width=4)
    d.text((x, y), s, font=f, fill=col, anchor='mm')

# ---------- S1 NOTTE: grafico grande e grafico piccolo ----------
TREND1 = [(150 + i * 26, 960 - i * 11 + 34 * math.sin(i * 0.9)) for i in range(32)]
def s1(t):
    img = Y.night_bg(t); img = Y.light_beams(img, t); img = Y.dust(img, t, 45, 3, Y.GOLD, 40)
    img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('il grafico', 'serif', 92, Y.WHITE), ('GRANDE', 'big', 120, Y.GOLD)], 330), t, -0.4, 0.4, 'float', 1)
    d = ImageDraw.Draw(img); d.rounded_rectangle((110, 470, 970, 1010), radius=26, fill=(14, 20, 40), outline=(60, 74, 120), width=3)
    img = glow_line(img, TREND1, Y.GOLD, 8, (t + 0.3) / 1.6)
    if t > T(6):
        img = SP(img, lambda b: Y.arrow(ImageDraw.Draw(b), 300, 900, 800, 560, Y.ease((t - T(6)) / 0.4), Y.GREEN, 12, 4), t, T(6), enter='none', idle='wobble', amp=0.4)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'DIREZIONE', (Y.W // 2, 1055), 80, Y.ease((t - T(6)) / 0.35)), t, T(6), enter='stamp', idle='breathe', seed=2, dur=0.3)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('quello', 'serif', 76, Y.MUTE), ('PICCOLO', 'big', 96, Y.ICE)], 1210), t, T(7), enter='rise', idle='float', seed=3)
    if t > T(8):
        def small(b):
            d = ImageDraw.Draw(b); d.rounded_rectangle((330, 1250, 750, 1440), radius=20, fill=(14, 20, 40), outline=Y.ICE, width=3)
            for i in range(9):
                if t < T(8) + i * 0.08: break
                x = 370 + i * 42; base = 1390 - i * 9 + (22 if 3 <= i <= 5 else 0)
                candle(d, x, base, base - 26 if i != 4 else base + 10, base - 36, base + 16, 22)
        img = SP(img, small, t, T(8), enter='pop', idle='float', seed=4)
    img = SP(img, lambda b: Y.stamp(b, 'MOMENTO', (860, 1470), 64, Y.GOLD, -6), t, T(12), enter='stamp', idle='wobble', seed=5, dur=0.25, amp=0.4)
    img = Y.camera(img, t, 0, punches=[T(2), T(6), T(8), T(12)], shakes=[T(12)])
    img = Y.color_flash(img, t, [T(6)], Y.GOLD, 0.14, 0.3)
    return Y.color_flash(img, t, [T(12)], Y.ICE, 0.12, 0.25), True
ev(0, 'boom', 0.6); ev(0.05, 'whoosh', 0.6); ev(0.2, 'swoosh_up', 0.4); ev(T(2), 'pop'); ev(T(6), 'stamp', 0.7); ev(T(6) + 0.05, 'swipe', 0.5)
ev(T(7), 'swoosh_up', 0.5); [ev(T(8) + i * 0.08, 'tick', 0.3) for i in range(9)]; ev(T(12), 'stamp'); ev(T(12) + 0.05, 'ding', 0.5)

# ---------- S2 QUADERNO: la direzione su un'ora ----------
UP = [(110, 1180), (170, 1060), (220, 1110), (290, 960), (340, 1020), (410, 860), (460, 920), (520, 760)]
DN = [(570, 760), (630, 880), (680, 830), (750, 980), (800, 930), (870, 1090), (920, 1040), (980, 1180)]
def s2(t):
    img = Y.grid_paper()
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('strategia', 'serif', 96, Y.INK), ('BASE', 'big', 110, Y.INK)], 300), t, CUTS[1], enter='drop', idle='float', seed=6)
    for k in range(5):
        if t > T(15) + k * 0.08:
            img = SP(img, lambda b, k=k: Y.gold_candle(b, 360 + k * 56, 350, 470, 376 + k * 5, 435, 34, 1), t, T(15) + k * 0.08, enter='drop', idle='float', seed=40 + k)
    img = SP(img, lambda b: big(b, '#5', (700, 410), 116, Y.GOLDK), t, T(16), enter='spin', idle='breathe', seed=7)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('grafico a', 'serif', 72, Y.MUTE), ("UN'ORA", 'big', 92, Y.INK)], 620), t, T(18), enter='left', idle='float', seed=8)
    d = ImageDraw.Draw(img)
    if t > T(21): Y.stroke(d, UP, Y.ease((t - T(21)) / 1.4), Y.GREEN_K, 8, seed=21, amp=2)
    if t > T(24):
        for j, (x, y) in enumerate([UP[1], UP[3], UP[5], UP[7]]): Y.number_badge(d, j + 1, (x, y - 50), (t - T(24) - j * 0.15) / 0.3, Y.GREEN_K)
    if t > T(26):
        for j, (x, y) in enumerate([UP[2], UP[4], UP[6]]): Y.circle(d, x, y + 4, 26, 26, Y.ease((t - T(26) - j * 0.15) / 0.3), Y.GREEN_K, 5, 30 + j)
    img = SP(img, lambda b: big(b, 'SALGONO', (310, 1290), 90, Y.GREEN_K), t, T(28), enter='pop', idle='wobble', seed=9, amp=0.5)
    d = ImageDraw.Draw(img)
    if t > T(29): Y.stroke(d, DN, Y.ease((t - T(29)) / 1.0), Y.RED, 8, seed=22, amp=2)
    img = SP(img, lambda b: big(b, 'SCENDONO', (780, 1290), 90, Y.RED), t, T(31), enter='pop', idle='wobble', seed=10, amp=0.5)
    img = Y.camera(img, t, CUTS[1], punches=[T(16), T(20), T(24), T(28), T(31)], shakes=[T(31)], push=0.04)
    img = Y.color_flash(img, t, [T(28)], Y.GREEN, 0.12, 0.22); return Y.color_flash(img, t, [T(31)], Y.RED, 0.12, 0.22), False
ev(CUTS[1], 'swoosh_up', 0.6); ev(CUTS[1] + 0.05, 'pop'); [ev(T(15) + k * 0.08, 'pop_hi', 0.4) for k in range(5)]; ev(T(16), 'ding', 0.6); ev(T(18), 'swipe', 0.5)
ev(T(21), 'riser', 0.3); [ev(T(24) + j * 0.15, 'pop', 0.5) for j in range(4)]; [ev(T(26) + j * 0.15, 'click', 0.5) for j in range(3)]; ev(T(28), 'swoosh_up', 0.6); ev(T(29), 'swipe', 0.5); ev(T(31), 'pop_hi')

# ---------- dati didattici M15: trend su, ritorno sulla media 50, ripartenza ----------
def _data():
    r = random.Random(9); cl = []; ema = []
    for i in range(34):
        e = 3990 + 1.6 * i; off = 11 + 4 * math.sin(i * 1.3)
        if 19 <= i <= 23: off = 11 - 2.4 * (i - 18)
        if i == 24: off = 1.0
        if i >= 25: off = 6 + 5.5 * (i - 24)
        cl.append(e + off + r.uniform(-1.2, 1.2)); ema.append(e)
    cs = []; o = cl[0] - 3
    for i, c in enumerate(cl):
        cs.append({'o': o, 'c': c, 'h': max(o, c) + r.uniform(1, 3), 'l': min(o, c) - r.uniform(1, 3)}); o = c
    cs[24]['l'] = ema[24] - 3; return cs, ema
CS, EMA = _data(); PB = 24; EI = 25; ENTRY = CS[EI]['c']; STOP = CS[PB]['l'] - 2
LO, HI = 3975, 4065
def s3(t):
    img = Y.term_bg(); img = Y.light_sweep(img, t + 1.5, 3.4, 200, 30); img = Y.dust(img, t, 25, 11, Y.ICE, 30)
    img = SP(img, lambda b: Y.hand(ImageDraw.Draw(b), 'esempio didattico', (Y.W // 2, 290), 74, Y.GOLD, Y.ease((t - T(32)) / 0.6)), t, T(32), enter='none', idle='float', seed=11)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'PER COMPRARE', (Y.W // 2, 400), 74, Y.ease((t - T(34)) / 0.35), Y.GREEN), t, T(34), enter='pop', idle='breathe', seed=12)
    img = SP(img, lambda b: chip(ImageDraw.Draw(b), "1 ORA: SALE", (Y.W // 2, 510), Y.GREEN), t, T(39), enter='pop', idle='wobble', seed=13, amp=0.4)
    x0, x1, y0, y1 = 110, 990, 600, 1330
    py = lambda p: y1 - (p - LO) / (HI - LO) * (y1 - y0); step = (x1 - x0) / len(CS); px = lambda i: x0 + (i + .5) * step
    d = ImageDraw.Draw(img); d.rounded_rectangle((x0 - 30, y0 - 40, x1 + 30, y1 + 30), radius=22, fill=Y.CARD, outline=Y.CARD_LINE, width=2)
    if t > T(41): chip(d, '15 MIN', (x0 + 90, y0 + 10), Y.GOLD, 34)
    if t < T(46): k = int(3 + (PB - 3) * Y.ease((t - CUTS[2]) / (T(46) - CUTS[2])))
    elif t < T(52): k = PB + 1
    else: k = int(PB + 1 + (len(CS) - PB - 1) * Y.ease((t - T(52)) / 1.4))
    if t > T(55):
        lay = Image.new('RGBA', (Y.W, Y.H), (0, 0, 0, 0)); ImageDraw.Draw(lay).rectangle((px(EI), py(ENTRY), px(EI) + (x1 - px(EI)) * Y.ease((t - T(55)) / 0.4), py(STOP)), fill=Y.RED + (60,)); img.paste(lay, (0, 0), lay); d = ImageDraw.Draw(img)
    for i, c in enumerate(CS[:k]):
        x = px(i); col = (47, 179, 106) if c['c'] >= c['o'] else (224, 72, 62)
        d.line([(x, py(c['h'])), (x, py(c['l']))], fill=col, width=3); ya, yb = sorted([py(c['o']), py(c['c'])]); d.rectangle((x - step * .32, ya, x + step * .32, max(yb, ya + 3)), fill=col)
    if t > T(48):
        pts = [(px(i), py(EMA[i])) for i in range(max(2, k))]; d.line(pts, fill=Y.ICE, width=5, joint='curve')
        Y.tag_pointer(d, 'MEDIA 50', (px(14), py(EMA[14])), (px(14), py(EMA[14]) + 140), (t - T(48)) / 0.4, Y.ICE, Y.DARK, 36)
    if t > T(46): img = Y.pulse_rings(img, px(PB), py(CS[PB]['l']), t - T(46), Y.GOLD, 1.1, 2, 100, 3); d = ImageDraw.Draw(img)
    if t > T(52): Y.tag_pointer(d, 'RIPARTE', (px(EI) + 10, py(ENTRY)), (px(EI) - 120, py(ENTRY) - 200), (t - T(52)) / 0.4, Y.GREEN, Y.DARK, 38)
    if t > T(55):
        y = py(STOP); a = Y.ease((t - T(55)) / 0.4)
        for xx in range(int(px(EI)), int(px(EI) + (x1 - px(EI)) * a), 22): d.line([(xx, y), (min(xx + 12, x1), y)], fill=Y.RED, width=4)
        if a >= 1: f = Y.F(Y.COND, 38); tw = d.textlength('STOP', font=f); d.rounded_rectangle((x1 - tw - 26, y - 25, x1, y + 25), radius=9, fill=Y.RED); d.text((x1 - 13, y), 'STOP', font=f, fill=Y.DARK, anchor='rm')
    if t > T(58): Y.hand(d, 'sotto il minimo', (px(PB) - 40, py(STOP) + 70), 50, Y.RED, Y.ease((t - T(58)) / 0.5))
    img = Y.camera(img, t, CUTS[2], punches=[T(35), T(40), T(46), T(52), T(55)], shakes=[T(54)], push=0.04)
    img = Y.color_flash(img, t, [T(52)], Y.GREEN, 0.14, 0.26); return Y.color_flash(img, t, [T(55)], Y.RED, 0.12, 0.22), True
ev(CUTS[2], 'swipe'); ev(CUTS[2] + 0.1, 'click'); [ev(CUTS[2] + 0.2 + k * 0.12, 'tick', 0.3) for k in range(14)]; ev(T(34), 'pop_hi'); ev(T(39), 'pop'); ev(T(41), 'click', 0.6)
ev(T(46), 'ding', 0.7); ev(T(48), 'swipe', 0.5); ev(T(52), 'swoosh_up', 0.7); ev(T(52) + 0.1, 'pop_hi', 0.6); ev(T(55), 'alert', 0.6); ev(T(58), 'click', 0.5)

# ---------- S4 NOTTE: vendita con linee luminose ----------
def s4(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 40, 13, Y.RED, 35); img = Y.light_beams(img, t + 1, n=2, strength=14)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('per', 'serif', 88, Y.MUTE), ('VENDERE', 'big', 124, Y.RED)], 320), t, T(61), enter='drop', idle='float', seed=14)
    img = SP(img, lambda b: chip(ImageDraw.Draw(b), "1 ORA: SCENDE", (Y.W // 2, 450), Y.RED), t, T(66), enter='pop', idle='wobble', seed=15, amp=0.4)
    ema = [(120 + i * 27, 640 + i * 16) for i in range(32)]
    price = []
    for i in range(32):
        off = -60 - 15 * math.sin(i * 1.2)
        if 17 <= i <= 21: off = -60 + 14 * (i - 16)
        if i >= 22: off = -10 - 30 * (i - 21)
        price.append((ema[i][0], ema[i][1] - off))
    pa = 18 / 32 * Y.ease((t - CUTS[3]) / 1.2)
    if t > T(73): pa = 18 / 32 + 5 / 32 * Y.ease((t - T(73)) / 0.8)
    if t > T(79): pa = 23 / 32 + 9 / 32 * Y.ease((t - T(79)) / 1.4)
    img = glow_line(img, ema, Y.ICE, 6, min(1, (t - T(75)) / 0.6) if t > T(75) else 0)
    img = glow_line(img, price, Y.GOLD, 8, pa)
    d = ImageDraw.Draw(img)
    if t > T(68): chip(d, '15 MIN', (190, 560), Y.GOLD, 34)
    if t > T(73): Y.tag_pointer(d, 'RISALE', price[21], (price[21][0] - 170, price[21][1] - 190), (t - T(73)) / 0.4, Y.GOLD, Y.DARK, 38)
    if t > T(75): Y.tag_pointer(d, 'MEDIA 50', ema[12], (ema[12][0] + 60, ema[12][1] - 150), (t - T(75)) / 0.4, Y.ICE, Y.DARK, 36)
    if t > T(79):
        img = Y.pulse_rings(img, price[22][0], price[22][1], t - T(79), Y.RED, 1.1, 2, 110, 3); d = ImageDraw.Draw(img)
        Y.arrow(d, price[22][0] + 20, price[22][1] + 20, price[22][0] + 160, price[22][1] + 240, Y.ease((t - T(79)) / 0.4), Y.RED, 9, 7)
    img = SP(img, lambda b: big(b, 'IN GIÙ', (830, 1250), 96, Y.RED), t, T(80), enter='pop', idle='wobble', seed=16, amp=0.5)
    d = ImageDraw.Draw(img)
    if t > T(82):
        ys = min(p[1] for p in price[17:23]) - 40; a = Y.ease((t - T(82)) / 0.4)
        for xx in range(price[16][0], int(price[16][0] + 330 * a), 24): d.line([(xx, ys), (xx + 12, ys)], fill=Y.RED, width=5)
        if a >= 1: d.text((price[16][0] + 345, ys), "STOP", font=Y.F(Y.BIG, 50), fill=Y.RED, anchor='lm')
    if t > T(85): Y.hand(d, 'sopra il massimo', (price[19][0] + 40, min(p[1] for p in price[17:23]) - 110), 50, Y.RED, Y.ease((t - T(85)) / 0.5))
    img = Y.camera(img, t, CUTS[3], punches=[T(62), T(67), T(73), T(79), T(82)], shakes=[T(79)])
    return Y.color_flash(img, t, [T(62), T(79)], Y.RED, 0.14, 0.26), True
ev(CUTS[3], 'whoosh', 0.7); ev(T(61), 'pop'); ev(T(62), 'swipe', 0.5); ev(T(66), 'pop_hi'); ev(T(68), 'click', 0.6); ev(T(73), 'swoosh_up', 0.5); ev(T(75), 'click', 0.6)
ev(T(79), 'boom', 0.5); ev(T(80), 'pop'); ev(T(82), 'alert', 0.6); ev(T(85), 'click', 0.5); [ev(T(78) + k * 0.15, 'tick', 0.3) for k in range(8)]

# ---------- S5 TERMINALE: obiettivo 2 volte il rischio ----------
def s5(t):
    img = Y.term_bg(); img = Y.light_sweep(img, t, 3.2, 200, 35); img = Y.dust(img, t, 30, 7, Y.ICE, 30)
    img = SP(img, lambda b: Y.glow_text(b, 'OBIETTIVO', (Y.W // 2, 360), 140, Y.GREEN, (30, 90, 50)), t, T(88), enter='stamp', idle='breathe', seed=17, dur=0.3)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('in', 'serif', 70, Y.MUTE), ('ENTRAMBI I CASI', 'big', 84, Y.WHITE)], 530), t, T(89), enter='rise', idle='float', seed=18)
    def bars(b):
        d = ImageDraw.Draw(b)
        for i, (lab, v, col, t0, txt) in enumerate([('RISCHIO', 1, Y.RED, T(97), '1'), ('OBIETTIVO', 2, Y.GREEN, T(94), '2')]):
            a = Y.ease((t - t0) / 0.5)
            if a <= 0: continue
            y = 760 + i * 190; d.text((110, y), lab, font=Y.F(Y.COND, 52), fill=Y.WHITE, anchor='lm')
            d.rounded_rectangle((420, y - 40, 420 + 260 * v * a, y + 40), radius=14, fill=col)
            if a >= 1: d.text((420 + 260 * v + 30, y), txt, font=Y.F(Y.BIG, 80), fill=col, anchor='lm')
    img = SP(img, bars, t, T(94), enter='none', idle='float', seed=19, amp=0.3)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'ALMENO 2 VOLTE IL RISCHIO', (Y.W // 2, 1250), 64, Y.ease((t - T(95)) / 0.4)), t, T(95), enter='stamp', idle='breathe', seed=20, dur=0.3)
    img = Y.camera(img, t, CUTS[4], punches=[T(88), T(90), T(94), T(97)], shakes=[T(95)])
    return Y.color_flash(img, t, [T(94)], Y.GREEN, 0.14, 0.28), True
ev(CUTS[4], 'swipe'); ev(T(88), 'stamp', 0.6); ev(T(88) + 0.05, 'ding', 0.6); ev(T(89), 'swoosh_up', 0.5); ev(T(94), 'swoosh_up', 0.6); ev(T(94) + 0.4, 'pop_hi'); ev(T(95), 'coin', 0.7); ev(T(97), 'pop', 0.7)

# ---------- S6: trappola (nero-rosso) e come evitarla (quaderno) ----------
def s6(t):
    if t < T(105):
        img = Y.red_silhouette_bg(t)
        img = SP(img, lambda b: Y.stamp(b, 'TRAPPOLA', (Y.W // 2, 420), 120, Y.RED, -5), t, T(99), enter='stamp', idle='wobble', seed=21, dur=0.3, amp=0.4)
        img = Y.letter_rise(img, 'ENTRARE', (Y.W // 2, 680), 110, Y.WHITE, t, T(100))
        img = Y.letter_rise(img, 'CONTRO IL TREND', (Y.W // 2, 840), 110, Y.RED, t, T(101))
        if t > T(103):
            d = ImageDraw.Draw(img); Y.arrow(d, 300, 1180, 800, 1000, Y.ease((t - T(103)) / 0.4), Y.GREEN, 10, 3); Y.arrow(d, 760, 1100, 380, 1250, Y.ease((t - T(103) - 0.3) / 0.4), Y.RED, 10, 4)
            Y.icon(d, 'croce', 560, 1170, 120, Y.ease((t - T(104)) / 0.3), Y.RED, 12, 9)
        img = Y.camera(img, t, CUTS[5], punches=[T(99), T(101)], shakes=[T(99), T(104)])
        return Y.color_flash(img, t, [T(99), T(104)], Y.RED, 0.15, 0.3), True
    img = Y.grid_paper()
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('come', 'serif', 96, Y.INK), ('EVITARLA', 'big', 124, Y.GREEN_K)], 380), t, T(105), enter='drop', idle='float', seed=22)
    def row(b, y, parts, ok, t0):
        d = ImageDraw.Draw(b); col = Y.GREEN_K if ok else Y.RED
        d.rounded_rectangle((70, y - 95, 1010, y + 95), radius=26, fill=Y.WHITE, outline=col, width=5)
        Y.mixed_title(d, parts, y + 28, cx=600)
        a = Y.ease((t - t0) / 0.35)
        if a > 0: Y.icon(d, 'spunta' if ok else 'croce', 150, y, 90, a, col, 10, 3)
    img = SP(img, lambda b: row(b, 680, [('prima guardo', 'serif', 70, Y.INK), ("L'ORA", 'big', 96, Y.GREEN_K)], True, T(109)), t, T(107), enter='left', idle='float', seed=23, amp=0.5)
    img = SP(img, lambda b: row(b, 960, [('se va', 'serif', 66, Y.INK), ('DI LATO', 'big', 90, Y.RED)], False, T(113)), t, T(110), enter='right', idle='float', seed=24, amp=0.5)
    img = SP(img, lambda b: Y.stamp(b, 'NON OPERO', (Y.W // 2, 1230), 100, Y.RED, -4), t, T(114), enter='stamp', idle='wobble', seed=25, dur=0.3, amp=0.4)
    img = Y.camera(img, t, T(105), punches=[T(106), T(109), T(113), T(114)], shakes=[T(114)], push=0.04)
    img = Y.flash(img, t, [T(105)], 0.18)
    return Y.color_flash(img, t, [T(109)], Y.GREEN, 0.12, 0.22), False
ev(CUTS[5], 'boom', 0.5); ev(T(99), 'stamp'); ev(T(99) + 0.05, 'glitch', 0.5); ev(T(100), 'swoosh_up', 0.4); ev(T(101), 'swoosh_up', 0.5); ev(T(103), 'swipe', 0.5); ev(T(104), 'alert', 0.6)
ev(T(105), 'whoosh', 0.8); ev(T(106), 'pop'); ev(T(107), 'swipe', 0.5); ev(T(109), 'ding'); ev(T(110), 'swipe', 0.5); ev(T(113), 'pop', 0.6); ev(T(114), 'stamp')

# ---------- S7 CTA ----------
CTA_T = [T(121), T(124), T(126), T(129)]
def s7(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 50, 17, Y.GOLD, 55)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('se ti è stata', 'serif', 90, Y.WHITE), ('UTILE', 'big', 110, Y.GOLD)], 420), t, CUTS[6], enter='drop', idle='float', seed=33)
    img = Y.cta_four(img, t, CTA_T, 'TREND', y0=640)
    return Y.camera(img, t, CUTS[6], punches=CTA_T, push=0.03), True
ev(CUTS[6], 'swoosh_up'); ev(T(120), 'pop'); ev(CTA_T[0], 'pop'); ev(CTA_T[1], 'pop_hi'); ev(CTA_T[1] + 0.05, 'bubble', 0.6); ev(CTA_T[2], 'bubble'); ev(T(127), 'pop', 0.5); ev(CTA_T[3], 'swoosh_up'); ev(CTA_T[3] + 0.1, 'coin')

def outro(t):
    s = t - CUTS[7]; img = Y.night_bg(t); img = Y.light_beams(img, t); img = Y.dust(img, t, 50, 19, Y.GOLD, 60)
    img = Y.pulse_rings(img, Y.W // 2, 700, s, Y.GOLD, 1.4, 3, 420)
    img = Y.logo_reveal(img, t, CUTS[7] + 0.05, Y.W // 2, 700, 400)
    img = Y.telegram_cta(img, t, CUTS[7] + 1.2, 1150, line='' if TIKTOK else 'CERCAMI SU TELEGRAM')
    img = Y.camera(img, t, CUTS[7], punches=[CUTS[7] + 0.6, CUTS[7] + 1.75], shakes=[CUTS[7] + 1.75], push=0.05)
    return Y.flash(img, t, [CUTS[7]], 0.18), True
ev(CUTS[7], 'boom', 0.8); ev(CUTS[7] + 0.05, 'whoosh', 0.8); ev(CUTS[7] + 0.6, 'trin', 0.8); ev(CUTS[7] + 0.75, 'swoosh_up', 0.5)
ev(CUTS[7] + 1.2, 'whoosh', 0.9); ev(CUTS[7] + 1.45, 'pop'); ev(CUTS[7] + 1.75, 'stamp', 0.7); ev(CUTS[7] + 1.8, 'coin')
for c in CUTS[1:-1]: ev(c - 0.15, 'whoosh', 0.9)

SC = [s1, s2, s3, s4, s5, s6, s7]
def scene(t):
    for i in range(len(SC)):
        if CUTS[i] <= t < CUTS[i + 1]: return SC[i](t)
    return outro(t)
def frame(t):
    img, dark = scene(t)
    for i, c in enumerate(CUTS[1:-1]):
        if c <= t < c + TD and i < len(TRANS):
            prev, _ = scene(c - 0.01); p = (t - c) / TD
            img = {'whip': lambda: Y.whip(prev, img, p, 1), 'whip_v': lambda: Y.whip_v(prev, img, p, 1), 'blur': lambda: Y.blur_cross(prev, img, p), 'zoom': lambda: Y.zoom_through(prev, img, p), 'wipe': lambda: Y.circle_wipe(prev, img, p)}[TRANS[i]]()
    img = Y.captions_pop(img, t, WORDS, G, KEYS, dark, end=CUTS[6] - 0.05)
    Y.disclaimer(ImageDraw.Draw(img), dark)
    return img
def _f(i): return frame(i / Y.FPS).tobytes()
def enc(out, n0, n1):
    import subprocess
    from multiprocessing import Pool
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{Y.W}x{Y.H}', '-r', str(Y.FPS), '-i', '-',
                          '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', out], stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for b in pool.imap(_f, range(n0, n1), chunksize=4): p.stdin.write(b)
    p.stdin.close(); p.wait()
NAME = 'yardfx_strategia5_trend'
if __name__ == '__main__':
    import subprocess
    m = sys.argv[1]
    if m == 'preview':
        Y.contact_sheet(frame, [float(x) for x in sys.argv[2:]], os.path.join(D, 'preview.png'), w=180)
    elif m == 'main':
        enc(os.path.join(D, 'main.mp4'), 0, int(CUTS[7] * Y.FPS))
    elif m == 'outro':
        enc(os.path.join(D, 'outro_tt.mp4' if TIKTOK else 'outro_ig.mp4'), int(CUTS[7] * Y.FPS), int(DUR * Y.FPS))
    elif m == 'mix':
        S.music_minimal(os.path.join(D, 'base.wav'), DUR)
        a = S.mix(os.path.join(D, 'audio.m4a'), DUR, voce=os.path.join(D, 'voce.mp3'), musica=os.path.join(D, 'base.wav'), eventi=EV, music_db=-16)
        for tag in ['ig', 'tt']:
            lst = os.path.join(D, f'list_{tag}.txt'); open(lst, 'w').write(f"file 'main.mp4'\nfile 'outro_{tag}.mp4'\n")
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-i', a, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'copy', '-shortest', '-movflags', '+faststart',
                            os.path.join(D, f'{NAME}_{"instagram" if tag == "ig" else "tiktok"}.mp4')], check=True)
        print('ok', DUR, len(EV))
