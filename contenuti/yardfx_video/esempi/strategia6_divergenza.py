"""Strategia base #6: la divergenza RSI — voce Speechify «salvatore» (accelerata 8%), esce dom 29/11/2026 ore 10.
S1 RAGGI ORO  T0   il PREZZO dice una cosa (linea che scende) · l'RSI un'altra (linea che sale) · CHI HA RAGIONE?
S2 QUADERNO   T12  'strategia BASE #6' + 6 candeline · DIVERGENZA RSI · quadrante RSI 14 da 0 a 100 · quello della numero uno · TIME FRAME M15
S3 NOTTE      T39  DIVERGENZA: il prezzo CONTINUA (sale) · l'RSI NO (scende) · la spinta si sta ESAURENDO
S4 TERMINALE  T51  esempio didattico PER COMPRARE: candele con MINIMO PIÙ BASSO, pannello RSI con MINIMO PIÙ ALTO, CANDELA VERDE CHIUSA, BUY A MERCATO, STOP LOSS
S5 QUADERNO   T84  PER VENDERE a mano: MASSIMO PIÙ ALTO / MASSIMO PIÙ BASSO dell'RSI, CANDELA ROSSA CHIUSA, SELL A MERCATO, STOP LOSS sopra
S6 NOTTE      T115 TAKE PROFIT: barre RISCHIO 1 / TAKE PROFIT 2
S7 NERO-ROSSO → QUADERNO  T122  TRAPPOLA: in un TREND FORTE la divergenza SI RIPETE · come EVITARLA: ✓ candela chiusa ✓ vicino a un supporto (moneta sull'asse)
S8 POSTER     T153 fine della PRIMA SERIE · timbro REGOLA D'ORO · griglia 10x10 con 1 casella = MAI PIÙ DELL'1% DEL CONTO
S9 NOTTE      T166 se ti è stata UTILE + 4 paletti (RSI) · outro
Novità: sfondo a raggi (sunburst_bg), moneta sull'asse per il supporto (level_plank), griglia 10x10 per l'1% (waffle), base 'tensione'."""
import sys, os, math, json, random
sys.path.insert(0, '/home/user/bot-telegram/contenuti/yardfx_video'); import yardfx as Y; import suoni as S
from PIL import Image, ImageDraw, ImageFilter
D = os.path.dirname(os.path.abspath(__file__))
WORDS = json.load(open(os.path.join(D, 'words.json'))); G = Y.make_groups(WORDS)
T = lambda i: WORDS[i][1]
VEND = WORDS[-1][2]
KEYS = {1, 5, 11, 17, 21, 35, 38, 39, 42, 45, 50, 52, 54, 60, 66, 72, 76, 78, 81, 85, 91, 97, 103, 107, 109, 114, 116, 121, 123, 127, 131, 137, 142, 152, 156, 158, 161}
CUTS = [0, T(12), T(39), T(51), T(84), T(115), T(122), T(153), T(166), VEND + 0.3]
OUT_LEN = 4.2; DUR = CUTS[-1] + OUT_LEN
TRANS = ['zoom', 'whip', 'blur', 'wipe', 'whip_v', 'zoom', 'blur', 'whip']
TD = 0.4; TIKTOK = os.environ.get('TIKTOK') == '1'
EV = []
def ev(t, n, g=1.0): EV.append((round(t, 3), n, g))
SP = Y.sprite
def big(b, s, xy, size, col, font=Y.BIG): ImageDraw.Draw(b).text(xy, s, font=Y.F(font, size), fill=col, anchor='mm')
def chip(d, s, xy, col, size=44):
    f = Y.F(Y.COND, size); tw = d.textlength(s, font=f); x, y = xy
    d.rounded_rectangle((x - tw / 2 - 26, y - size * .8, x + tw / 2 + 26, y + size * .8), radius=size, fill=tuple(int(v * .22) for v in col), outline=col, width=4)
    d.text((x, y), s, font=f, fill=col, anchor='mm')
def glow_line(img, pts, col, w, prog, blur=12):
    if prog <= 0: return img
    k = max(2, int(len(pts) * min(1, prog))); m = Image.new('L', (Y.W, Y.H), 0); ImageDraw.Draw(m).line(pts[:k], fill=255, width=w, joint='curve')
    img = Image.composite(Image.new('RGB', (Y.W, Y.H), tuple(int(v * 0.6) for v in col)), img, m.filter(ImageFilter.GaussianBlur(blur)))
    return Image.composite(Image.new('RGB', (Y.W, Y.H), col), img, m)
def candle(d, x, o, c, h, l, w=26, col=None):
    col = col or ((47, 179, 106) if c <= o else (224, 72, 62))
    d.line([(x, h), (x, l)], fill=col, width=4); d.rectangle((x - w / 2, min(o, c), x + w / 2, max(o, c) + 2), fill=col)

# ---------- S1 RAGGI: chi ha ragione? ----------
def s1(t):
    img = Y.sunburst_bg(t); img = Y.dust(img, t, 40, 3, Y.GOLD, 40)
    img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('il', 'serif', 90, Y.WHITE), ('PREZZO', 'big', 130, Y.GOLD)], 360), t, -0.4, 0.4, 'float', 1)
    img = glow_line(img, [(140 + i * 26, 470 + i * 7 + 30 * math.sin(i * 0.9)) for i in range(31)], Y.GOLD, 9, (t + 0.3) / 1.3)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [("l'", 'serif', 90, Y.WHITE), ('RSI', 'big', 130, Y.ICE)], 900), t, T(5), enter='rise', idle='float', seed=2)
    if t > T(5): img = glow_line(img, [(140 + i * 26, 1180 - i * 7 + 25 * math.sin(i * 1.1)) for i in range(31)], Y.ICE, 9, (t - T(5)) / 1.2)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'CHI HA RAGIONE?', (Y.W // 2, 1400), 80, Y.ease((t - T(9)) / 0.35)), t, T(9), enter='stamp', idle='breathe', seed=3, dur=0.3)
    img = Y.camera(img, t, 0, punches=[T(1), T(5), T(11)], shakes=[T(11)])
    return Y.color_flash(img, t, [T(11)], Y.GOLD, 0.14, 0.3), True
ev(0, 'boom', 0.6); ev(0.05, 'whoosh', 0.6); ev(0.2, 'riser', 0.25); ev(T(1), 'pop'); ev(T(5), 'swoosh_up', 0.6); ev(T(5) + 0.1, 'pop_hi', 0.5); ev(T(9), 'stamp', 0.7); ev(T(11), 'boom', 0.5)

# ---------- S2 QUADERNO: cos'è l'RSI ----------
def s2(t):
    img = Y.grid_paper()
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('strategia', 'serif', 92, Y.INK), ('BASE', 'big', 106, Y.INK)], 290), t, CUTS[1], enter='drop', idle='float', seed=6)
    for k in range(6):
        if t > T(14) + k * 0.07:
            img = SP(img, lambda b, k=k: Y.gold_candle(b, 330 + k * 54, 335, 450, 360 + k * 4, 420, 32, 1), t, T(14) + k * 0.07, enter='drop', idle='float', seed=40 + k)
    img = SP(img, lambda b: big(b, '#6', (720, 395), 112, Y.GOLDK), t, T(15), enter='spin', idle='breathe', seed=7)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('la', 'serif', 80, Y.MUTE), ('DIVERGENZA RSI', 'big', 100, Y.RED)], 590), t, T(16), enter='left', idle='float', seed=8)
    if t > T(19):
        val = 30 + 40 * (0.5 + 0.5 * math.sin(t * 1.2))
        img = SP(img, lambda b: Y.dial(b, Y.W // 2, 860, 180, val / 100, Y.ease((t - T(19)) / 0.6), 'RSI 14'), t, T(19), enter='pop', idle='float', seed=9)
    d = ImageDraw.Draw(img)
    if t > T(33):
        d.text((Y.W // 2 - 230, 960), '0', font=Y.F(Y.BIG, 70), fill=Y.INK, anchor='mm');
    if t > T(35): d.text((Y.W // 2 + 230, 960), '100', font=Y.F(Y.BIG, 70), fill=Y.INK, anchor='mm')
    img = SP(img, lambda b: Y.hand(ImageDraw.Draw(b), 'quello della numero uno', (Y.W // 2, 1110), 60, Y.GOLDK, Y.ease((t - T(23)) / 0.6)), t, T(23), enter='none', idle='float', seed=10)
    img = SP(img, lambda b: Y.stamp(b, 'TIME FRAME M15', (Y.W // 2, 1300), 84, Y.RED, -4), t, T(36), enter='stamp', idle='wobble', seed=11, dur=0.3, amp=0.4)
    img = Y.camera(img, t, CUTS[1], punches=[T(15), T(17), T(21), T(38)], shakes=[T(38)], push=0.04)
    return Y.color_flash(img, t, [T(17)], Y.RED, 0.1, 0.2), False
ev(CUTS[1], 'swoosh_up', 0.6); ev(CUTS[1] + 0.05, 'pop'); [ev(T(14) + k * 0.07, 'pop_hi', 0.4) for k in range(6)]; ev(T(15), 'ding', 0.6); ev(T(16), 'swipe', 0.5)
ev(T(19), 'riser', 0.3); [ev(T(19) + 0.1 * k, 'tick', 0.3) for k in range(8)]; ev(T(23), 'click', 0.5); ev(T(33), 'pop', 0.5); ev(T(35), 'pop', 0.5); ev(T(36), 'stamp')

# ---------- S3 NOTTE: cos'è la divergenza ----------
def s3(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 45, 13, Y.GOLD, 45); img = Y.light_beams(img, t + 2, n=2, strength=16)
    img = SP(img, lambda b: Y.glow_text(b, 'DIVERGENZA', (Y.W // 2, 330), 140, Y.GOLD, (130, 90, 20)), t, T(39), enter='stamp', idle='breathe', seed=12, dur=0.3)
    img = glow_line(img, [(140 + i * 26, 760 - i * 9 + 22 * math.sin(i * 1.0)) for i in range(31)], Y.GOLD, 9, (t - T(40)) / 1.0)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('il prezzo', 'serif', 76, Y.WHITE), ('CONTINUA', 'big', 96, Y.GREEN)], 560), t, T(42), enter='rise', idle='float', seed=13)
    if t > T(44): img = glow_line(img, [(140 + i * 26, 980 + i * 8 + 18 * math.sin(i * 1.2)) for i in range(31)], Y.ICE, 9, (t - T(44)) / 0.9)
    img = SP(img, lambda b: Y.stamp(b, "L'RSI NO", (800, 1130), 80, Y.RED, -6), t, T(45), enter='stamp', idle='wobble', seed=14, dur=0.3, amp=0.4)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('la spinta si sta', 'serif', 72, Y.MUTE), ('ESAURENDO', 'big', 96, Y.RED)], 1440), t, T(46), enter='rise', idle='float', seed=15)
    img = Y.camera(img, t, CUTS[2], punches=[T(39), T(42), T(45), T(50)], shakes=[T(45)])
    return Y.color_flash(img, t, [T(45)], Y.RED, 0.14, 0.28), True
ev(CUTS[2], 'whoosh', 0.7); ev(T(39), 'stamp', 0.6); ev(T(40), 'riser', 0.3); ev(T(42), 'pop'); ev(T(44), 'swoosh_up', 0.4); ev(T(45), 'stamp'); ev(T(45) + 0.05, 'glitch', 0.4); ev(T(46), 'swoosh_up', 0.5); ev(T(50), 'pop_hi', 0.6)

# ---------- dati didattici: divergenza rialzista ----------
PR = [4040, 4034, 4027, 4019, 4012, 4006, 4000, 3995, 3991, 3988, 3992, 3999, 4004, 4001, 3995, 3989, 3984, 3980, 3976, 3982, 3991, 4001, 4010, 4018, 4024]
RS = [52, 47, 42, 37, 33, 30, 28, 27, 26, 25, 31, 38, 43, 40, 37, 35, 34, 33, 33, 40, 48, 55, 60, 64, 67]
L1, L2, CI = 9, 18, 19
def s4(t):
    img = Y.term_bg(); img = Y.light_sweep(img, t + 1.5, 3.4, 200, 30); img = Y.dust(img, t, 25, 11, Y.ICE, 30)
    img = SP(img, lambda b: Y.hand(ImageDraw.Draw(b), 'esempio didattico', (Y.W // 2, 270), 70, Y.GOLD, Y.ease((t - T(51)) / 0.6)), t, T(51), enter='none', idle='float', seed=16)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'PER COMPRARE', (Y.W // 2, 380), 70, Y.ease((t - T(53)) / 0.35), Y.GREEN), t, T(53), enter='pop', idle='breathe', seed=17)
    x0, x1, y0, y1 = 110, 990, 480, 960; LO, HI = 3965, 4050; ry0, ry1 = 1040, 1300
    py = lambda p: y1 - (p - LO) / (HI - LO) * (y1 - y0); ry = lambda v: ry1 - v / 100 * (ry1 - ry0)
    step = (x1 - x0) / len(PR); px = lambda i: x0 + (i + .5) * step
    d = ImageDraw.Draw(img); d.rounded_rectangle((x0 - 30, y0 - 30, x1 + 30, ry1 + 30), radius=22, fill=Y.CARD, outline=Y.CARD_LINE, width=2)
    d.line([(x0, ry0 - 30), (x1, ry0 - 30)], fill=Y.CARD_LINE, width=2); d.text((x0 + 4, ry0 - 2), 'RSI 14', font=Y.F(Y.MONO, 24), fill=Y.MUTE, anchor='lm')
    for v in (30, 70): d.line([(x0, ry(v)), (x1, ry(v))], fill=(70, 70, 80), width=2)
    if t < T(72): k = int(4 + (CI - 4) * Y.ease((t - CUTS[3]) / (T(72) - CUTS[3])))
    elif t < T(77): k = CI + 1
    else: k = int(CI + 1 + (len(PR) - CI - 1) * Y.ease((t - T(77)) / 1.3))
    o = PR[0] + 3
    for i in range(k):
        c = PR[i]; h = max(o, c) + 3; l = min(o, c) - 3
        if i in (L1, L2): l = c - 6
        col = (47, 179, 106) if c >= o else (224, 72, 62); x = px(i)
        d.line([(x, py(h)), (x, py(l))], fill=col, width=3); ya, yb = sorted([py(o), py(c)]); d.rectangle((x - step * .32, ya, x + step * .32, max(yb, ya + 3)), fill=col); o = c
    d.line([(px(i), ry(RS[i])) for i in range(k)], fill=Y.ICE, width=5, joint='curve')
    if t > T(58):
        a = Y.ease((t - T(58)) / 0.5); xa, ya_, xb, yb_ = px(L1), py(PR[L1] - 6), px(L2), py(PR[L2] - 6)
        d.line([(xa, ya_), (xa + (xb - xa) * a, ya_ + (yb_ - ya_) * a)], fill=Y.RED, width=6)
        Y.tag_pointer(d, 'MINIMO PIÙ BASSO', (xb, yb_), (xb - 280, yb_ + 80), (t - T(58)) / 0.4, Y.RED, Y.WHITE, 34)
    if t > T(64):
        a = Y.ease((t - T(64)) / 0.5); xa, ya_, xb, yb_ = px(L1), ry(RS[L1]), px(L2), ry(RS[L2])
        d.line([(xa, ya_), (xa + (xb - xa) * a, ya_ + (yb_ - ya_) * a)], fill=Y.GREEN, width=6)
        Y.tag_pointer(d, 'MINIMO PIÙ ALTO', (xb, yb_), (xb - 260, ry1 - 10), (t - T(64)) / 0.4, Y.GREEN, Y.DARK, 34)
    if t > T(72):
        img = Y.pulse_rings(img, px(CI), py(PR[CI]), t - T(72), Y.GREEN, 1.1, 2, 100, 3); d = ImageDraw.Draw(img)
        Y.circle(d, px(CI), py(PR[CI]) + 10, 34, 60, Y.ease((t - T(72)) / 0.4), Y.GREEN, 5, 21)
        Y.tag_pointer(d, 'CANDELA VERDE CHIUSA', (px(CI) + 20, py(PR[CI]) - 30), (px(CI) - 60, y0 + 30), (t - T(72)) / 0.4, Y.GREEN, Y.DARK, 32)
    if t > T(76): chip(d, 'BUY A MERCATO', (Y.W // 2, 1410), Y.GREEN, 48)
    if t > T(79):
        ys = py(PR[L2] - 8); a = Y.ease((t - T(79)) / 0.4)
        for xx in range(int(px(CI)), int(px(CI) + (x1 - px(CI)) * a), 22): d.line([(xx, ys), (min(xx + 12, x1), ys)], fill=Y.RED, width=4)
        if a >= 1: f = Y.F(Y.COND, 34); tw = d.textlength('STOP LOSS', font=f); d.rounded_rectangle((x1 - tw - 24, ys - 23, x1, ys + 23), radius=8, fill=Y.RED); d.text((x1 - 12, ys), 'STOP LOSS', font=f, fill=Y.DARK, anchor='rm')
    img = Y.camera(img, t, CUTS[3], punches=[T(54), T(60), T(66), T(72), T(76), T(81)], shakes=[T(72)], push=0.04)
    img = Y.color_flash(img, t, [T(66), T(72)], Y.GREEN, 0.12, 0.24); return Y.color_flash(img, t, [T(60), T(79)], Y.RED, 0.1, 0.2), True
ev(CUTS[3], 'swipe'); ev(CUTS[3] + 0.1, 'click'); [ev(CUTS[3] + 0.2 + k * 0.12, 'tick', 0.3) for k in range(14)]; ev(T(53), 'pop_hi'); ev(T(58), 'swipe', 0.5); ev(T(60), 'pop', 0.6)
ev(T(64), 'swipe', 0.5); ev(T(66), 'ding', 0.6); ev(T(72), 'ding'); ev(T(76), 'coin', 0.6); ev(T(79), 'alert', 0.6)

# ---------- S5 QUADERNO: la vendita a mano ----------
PXS = [(110, 760), (200, 660), (280, 720), (380, 560), (460, 640), (560, 520), (640, 600)]
RXS = [(110, 1120), (200, 1020), (280, 1080), (380, 1000), (460, 1070), (560, 1050), (640, 1120)]
def s5(t):
    img = Y.grid_paper(); d = ImageDraw.Draw(img)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('per', 'serif', 88, Y.INK), ('VENDERE', 'big', 120, Y.RED)], 300), t, T(84), enter='drop', idle='float', seed=18)
    d = ImageDraw.Draw(img)
    Y.stroke(d, PXS, Y.ease((t - T(86)) / 1.0), Y.INK, 7, seed=31, amp=1.5)
    d.text((90, 470), 'prezzo', font=Y.F(Y.SERIF, 46), fill=Y.MUTE, anchor='lm'); d.text((90, 950), 'RSI', font=Y.F(Y.SERIF, 46), fill=Y.MUTE, anchor='lm') if t > T(92) else None
    if t > T(89): Y.stroke(d, [(380, 540), (560, 500)], Y.ease((t - T(89)) / 0.4), Y.RED, 6, seed=32); Y.hand(d, 'massimo più alto', (470, 450), 50, Y.RED, Y.ease((t - T(89)) / 0.5))
    if t > T(92): Y.stroke(d, RXS, Y.ease((t - T(92)) / 0.8), (40, 110, 190), 7, seed=33, amp=1.5)
    if t > T(95): Y.stroke(d, [(380, 985), (560, 1035)], Y.ease((t - T(95)) / 0.4), Y.RED, 6, seed=34); Y.hand(d, 'massimo più basso', (470, 1170), 50, Y.RED, Y.ease((t - T(95)) / 0.5))
    if t > T(103):
        p = Y.ease((t - T(103)) / 0.6); candle(d, 740, 590, 590 + 180 * p, 560, 610 + 180 * p, 44, Y.RED)
        Y.tag_pointer(d, 'CANDELA ROSSA CHIUSA', (765, 700), (900, 820), (t - T(103)) / 0.4, Y.RED, Y.WHITE, 32)
    if t > T(107): chip(d, 'SELL A MERCATO', (Y.W // 2, 1300), Y.RED, 44)
    if t > T(110):
        Y.stroke(d, [(540, 470), (1000, 470)], Y.ease((t - T(110)) / 0.4), Y.RED, 6, seed=35)
        if t > T(110) + 0.3: d.text((1000, 430), 'STOP LOSS', font=Y.F(Y.BIG, 46), fill=Y.RED, anchor='rm')
    img = Y.camera(img, t, CUTS[4], punches=[T(85), T(91), T(97), T(103), T(107)], shakes=[T(103)], push=0.04)
    return Y.color_flash(img, t, [T(85), T(103)], Y.RED, 0.12, 0.22), False
ev(CUTS[4], 'whoosh', 0.7); ev(T(84), 'swoosh_up', 0.6); ev(T(85), 'pop'); ev(T(86), 'riser', 0.25); ev(T(89), 'swipe', 0.5); ev(T(92), 'riser', 0.25); ev(T(95), 'swipe', 0.5)
ev(T(103), 'boom', 0.5); ev(T(104), 'ding', 0.6); ev(T(107), 'pop'); ev(T(110), 'alert', 0.6)

# ---------- S6 NOTTE: take profit ----------
def s6(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 50, 17, Y.GREEN, 40)
    img = SP(img, lambda b: Y.glow_text(b, 'TAKE PROFIT', (Y.W // 2, 400), 140, Y.GREEN, (30, 90, 50)), t, T(115), enter='stamp', idle='breathe', seed=19, dur=0.3)
    def bars(b):
        d = ImageDraw.Draw(b)
        for i, (lab, v, col, t0, txt) in enumerate([('RISCHIO', 1, Y.RED, T(120), '1'), ('TAKE PROFIT', 2, Y.GREEN, T(118), '2')]):
            a = Y.ease((t - t0) / 0.5)
            if a <= 0: continue
            y = 720 + i * 200; d.text((100, y), lab, font=Y.F(Y.COND, 52), fill=Y.WHITE, anchor='lm')
            d.rounded_rectangle((440, y - 42, 440 + 240 * v * a, y + 42), radius=14, fill=col)
            if a >= 1: d.text((440 + 240 * v + 30, y), txt, font=Y.F(Y.BIG, 84), fill=col, anchor='lm')
    img = SP(img, bars, t, T(117), enter='none', idle='float', seed=20, amp=0.3)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'ALMENO 2 VOLTE IL RISCHIO', (Y.W // 2, 1180), 64, Y.ease((t - T(117)) / 0.4)), t, T(117), enter='stamp', idle='breathe', seed=21, dur=0.3)
    img = Y.camera(img, t, CUTS[5], punches=[T(115), T(118), T(121)], shakes=[T(118)])
    return Y.color_flash(img, t, [T(118)], Y.GREEN, 0.14, 0.28), True
ev(CUTS[5], 'swipe'); ev(T(115), 'stamp', 0.6); ev(T(117), 'pop'); ev(T(118), 'swoosh_up', 0.6); ev(T(118) + 0.4, 'coin', 0.7); ev(T(120), 'pop', 0.6)

# ---------- S7 trappola e come evitarla ----------
def s7(t):
    if t < T(136):
        img = Y.red_silhouette_bg(t)
        img = SP(img, lambda b: Y.stamp(b, 'TRAPPOLA', (Y.W // 2, 360), 120, Y.RED, -5), t, T(123), enter='stamp', idle='wobble', seed=22, dur=0.3, amp=0.4)
        img = Y.letter_rise(img, 'TREND FORTE', (Y.W // 2, 560), 110, Y.WHITE, t, T(126))
        d = ImageDraw.Draw(img)
        if t > T(129):
            pts = [(120 + i * 28, 1150 - i * 18 + 20 * math.sin(i * 1.4)) for i in range(31)]
            d.line(pts[:max(2, int(31 * Y.ease((t - T(129)) / 1.4)))], fill=Y.GOLD, width=8, joint='curve')
            for j, i in enumerate((10, 20, 29)):
                if t > T(131) + j * 0.3: d.text((pts[i][0], pts[i][1] - 70), 'DIV?', font=Y.F(Y.COND, 40), fill=Y.ICE, anchor='mm')
        img = SP(img, lambda b: big(b, 'SI RIPETE', (Y.W // 2, 1320), 110, Y.RED), t, T(131), enter='pop', idle='wobble', seed=23, amp=0.5)
        img = Y.camera(img, t, CUTS[6], punches=[T(123), T(127), T(131)], shakes=[T(123), T(135)])
        return Y.color_flash(img, t, [T(123), T(135)], Y.RED, 0.15, 0.3), True
    img = Y.grid_paper()
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('come', 'serif', 96, Y.INK), ('EVITARLA', 'big', 124, Y.GREEN_K)], 330), t, T(136), enter='drop', idle='float', seed=24)
    def row(b, y, parts, t0):
        d = ImageDraw.Draw(b); d.rounded_rectangle((70, y - 80, 1010, y + 80), radius=26, fill=Y.WHITE, outline=Y.GREEN_K, width=5)
        Y.mixed_title(d, parts, y + 26, cx=600); a = Y.ease((t - t0) / 0.35)
        if a > 0: Y.icon(d, 'spunta', 150, y, 80, a, Y.GREEN_K, 10, 3)
    img = SP(img, lambda b: row(b, 560, [('solo a', 'serif', 66, Y.INK), ('CANDELA CHIUSA', 'big', 84, Y.GREEN_K)], T(142)), t, T(138), enter='left', idle='float', seed=25, amp=0.5)
    img = SP(img, lambda b: row(b, 790, [('vicino a un', 'serif', 60, Y.INK), ('SUPPORTO', 'big', 80, Y.GREEN_K)], T(148)), t, T(144), enter='right', idle='float', seed=26, amp=0.5)
    img = SP(img, lambda b: big(b, 'O A UNA RESISTENZA', (Y.W // 2, 930), 64, Y.RED), t, T(149), enter='pop', idle='float', seed=27)
    if t > T(148): img = Y.level_plank(img, t, None, 'SUPPORTO', y=1180, wdt=520)
    img = Y.camera(img, t, T(136), punches=[T(137), T(142), T(148), T(152)], shakes=[T(142)], push=0.04)
    img = Y.flash(img, t, [T(136)], 0.18)
    return Y.color_flash(img, t, [T(142), T(148)], Y.GREEN, 0.12, 0.22), False
ev(CUTS[6], 'boom', 0.5); ev(T(123), 'stamp'); ev(T(123) + 0.05, 'glitch', 0.5); ev(T(126), 'swoosh_up', 0.5); ev(T(129), 'riser', 0.3); [ev(T(131) + j * 0.3, 'pop', 0.5) for j in range(3)]; ev(T(135), 'alert', 0.5)
ev(T(136), 'whoosh', 0.8); ev(T(137), 'pop'); ev(T(138), 'swipe', 0.5); ev(T(142), 'ding'); ev(T(144), 'swipe', 0.5); ev(T(148), 'click', 0.7); ev(T(148) + 0.05, 'ding', 0.6); ev(T(149), 'pop', 0.6)

# ---------- S8 POSTER: fine della prima serie, regola dell'1% ----------
def s8(t):
    img = Y.poster_bg(t)
    img = Y.word_stack(img, [('fine della', 'small', T(153)), ('PRIMA SERIE', 'big', T(155))], Y.W // 2, 300, t, Y.INK, Y.GOLDK)
    img = SP(img, lambda b: Y.stamp(b, "REGOLA D'ORO", (Y.W // 2, 560), 90, Y.RED, -4), t, T(157), enter='stamp', idle='wobble', seed=28, dur=0.3, amp=0.4)
    d = ImageDraw.Draw(img)
    if t > T(160): Y.waffle(d, 1, (340, 690, 740, 1090), t, T(161), 0.3, Y.RED, (220, 216, 208), 10, None, False)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), "MAI PIÙ DELL'1% DEL CONTO", (Y.W // 2, 1230), 66, Y.ease((t - T(161)) / 0.4), Y.INK, Y.WHITE), t, T(161), enter='stamp', idle='breathe', seed=29, dur=0.3)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('per', 'serif', 66, Y.MUTE), ('OPERAZIONE', 'big', 84, Y.INK)], 1400), t, T(165), enter='rise', idle='float', seed=30)
    img = Y.camera(img, t, CUTS[7], punches=[T(155), T(157), T(161)], shakes=[T(161)], push=0.04)
    return Y.color_flash(img, t, [T(161)], Y.RED, 0.1, 0.2), False
ev(CUTS[7], 'swoosh_up', 0.6); ev(T(155), 'pop'); ev(T(157), 'stamp'); [ev(T(160) + k * 0.03, 'tick', 0.25) for k in range(10)]; ev(T(161), 'stamp', 0.7); ev(T(165), 'pop', 0.6)

# ---------- S7 CTA ----------
CTA_T = [T(171), T(174), T(176), T(179)]
def s9(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 50, 17, Y.GOLD, 55)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('se ti è stata', 'serif', 90, Y.WHITE), ('UTILE', 'big', 110, Y.GOLD)], 420), t, CUTS[8], enter='drop', idle='float', seed=33)
    img = Y.cta_four(img, t, CTA_T, 'RSI', y0=640)
    return Y.camera(img, t, CUTS[8], punches=CTA_T, push=0.03), True
ev(CUTS[8], 'swoosh_up'); ev(T(170), 'pop'); ev(CTA_T[0], 'pop'); ev(CTA_T[1], 'pop_hi'); ev(CTA_T[1] + 0.05, 'bubble', 0.6); ev(CTA_T[2], 'bubble'); ev(T(177), 'pop', 0.5); ev(CTA_T[3], 'swoosh_up'); ev(CTA_T[3] + 0.1, 'coin')

def outro(t):
    s = t - CUTS[9]; img = Y.night_bg(t); img = Y.light_beams(img, t); img = Y.dust(img, t, 50, 19, Y.GOLD, 60)
    img = Y.pulse_rings(img, Y.W // 2, 700, s, Y.GOLD, 1.4, 3, 420)
    img = Y.logo_reveal(img, t, CUTS[9] + 0.05, Y.W // 2, 700, 400)
    img = Y.telegram_cta(img, t, CUTS[9] + 1.2, 1150, line='' if TIKTOK else 'CERCAMI SU TELEGRAM')
    img = Y.camera(img, t, CUTS[9], punches=[CUTS[9] + 0.6, CUTS[9] + 1.75], shakes=[CUTS[9] + 1.75], push=0.05)
    return Y.flash(img, t, [CUTS[9]], 0.18), True
ev(CUTS[9], 'boom', 0.8); ev(CUTS[9] + 0.05, 'whoosh', 0.8); ev(CUTS[9] + 0.6, 'trin', 0.8); ev(CUTS[9] + 0.75, 'swoosh_up', 0.5)
ev(CUTS[9] + 1.2, 'whoosh', 0.9); ev(CUTS[9] + 1.45, 'pop'); ev(CUTS[9] + 1.75, 'stamp', 0.7); ev(CUTS[9] + 1.8, 'coin')
for c in CUTS[1:-1]: ev(c - 0.15, 'whoosh', 0.9)

SC = [s1, s2, s3, s4, s5, s6, s7, s8, s9]
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
    img = Y.captions_pop(img, t, WORDS, G, KEYS, dark, end=CUTS[8] - 0.05)
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
NAME = 'yardfx_strategia6_divergenza'
if __name__ == '__main__':
    import subprocess
    m = sys.argv[1]
    if m == 'preview':
        Y.contact_sheet(frame, [float(x) for x in sys.argv[2:]], os.path.join(D, 'preview.png'), w=180)
    elif m == 'main':
        enc(os.path.join(D, 'main.mp4'), 0, int(CUTS[9] * Y.FPS))
    elif m == 'outro':
        enc(os.path.join(D, 'outro_tt.mp4' if TIKTOK else 'outro_ig.mp4'), int(CUTS[9] * Y.FPS), int(DUR * Y.FPS))
    elif m == 'mix':
        S.music(os.path.join(D, 'base.wav'), DUR, 96, 'tensione')
        a = S.mix(os.path.join(D, 'audio.m4a'), DUR, voce=os.path.join(D, 'voce.mp3'), musica=os.path.join(D, 'base.wav'), eventi=EV, music_db=-16)
        for tag in ['ig', 'tt']:
            lst = os.path.join(D, f'list_{tag}.txt'); open(lst, 'w').write(f"file 'main.mp4'\nfile 'outro_{tag}.mp4'\n")
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-i', a, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'copy', '-shortest', '-movflags', '+faststart',
                            os.path.join(D, f'{NAME}_{"instagram" if tag == "ig" else "tiktok"}.mp4')], check=True)
        print('ok', DUR, len(EV))
