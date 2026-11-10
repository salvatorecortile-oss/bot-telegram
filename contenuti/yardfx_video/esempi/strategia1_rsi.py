"""Strategia base #1: RSI 14 su M15 — voce Enea di Salvatore, video animato con musica ed effetti.
Regola voce = schermo: ogni scritta compare quando la voce la dice.
S1 NOTTE   0      STRATEGIA BASE #1 · RSI (onde, faretto)
S2 QUADERNO T14   quadrante RSI 0→100, 14 candele che si accendono
S3 TERMINALE T33  pannello RSI: zona 30 IPERVENDUTO / 70 IPERCOMPRATO
S4 TERMINALE T52  LA REGOLA · ESEMPIO DIDATTICO · XAUUSD M15: discesa, RSI sotto 30 e risale, ENTRY / STOP LOSS / OBIETTIVO 2× RISCHIO
S5 QUADERNO T85   TRAPPOLA: trend forte, RSI sopra 70 per ore, NON VENDERE CONTRO IL TREND
S6 NOTTE   T104   SE TI È STATA UTILE + 4 paletti (seguimi, mi piace, commenta STRATEGIA, condividi)
"""
import sys, os, math, json
sys.path.insert(0, '/home/user/bot-telegram/contenuti/yardfx_video'); import yardfx as Y; import suoni as S
from PIL import Image, ImageDraw
import dati_didattici as dati
D = os.path.dirname(os.path.abspath(__file__))
WORDS = json.load(open(os.path.join(D, 'words_aligned.json'))); G = Y.make_groups(WORDS)
T = lambda i: WORDS[i][1]
VEND = WORDS[-1][2]; DUR = VEND + 4.3
KEYS = {4, 14, 21, 23, 31, 34, 38, 46, 48, 54, 58, 62, 67, 74, 75, 82, 87, 96, 101}
CUTS = [0, T(14), T(33), T(52), T(85), T(104), VEND + 0.3]
TRANS = ['zoom', 'whip_v', 'blur', 'wipe', 'whip', 'flash']
TD = 0.4
EX = dati.rule_example(1); TR = dati.trend_example()
EV = []
def ev(t, name, g=1.0): EV.append((round(t, 3), name, g))
SP = Y.sprite

def big_word(b, s, xy, size, col, font=Y.BIG):
    ImageDraw.Draw(b).text(xy, s, font=Y.F(font, size), fill=col, anchor='mm')

# ---------------- S1 ----------------
def s1(t):
    img = Y.night_bg(t); img = Y.light_beams(img, t); img = Y.dust(img, t, 45, 3, Y.GOLD, 40)
    img = Y.spotlight(img, Y.W // 2 + 50 * math.sin(t * 1.2), 100, 760, 520, 60)
    d = ImageDraw.Draw(img)
    img = Y.blur_in(img, lambda b: big_word(b, 'STRATEGIA BASE', (Y.W // 2, 520), 130, Y.WHITE), t, -0.4, 0.45, 'float', 1)
    img = SP(img, lambda b: Y.glow_text(b, '#1', (Y.W // 2, 690), 190, Y.GOLD, (130, 90, 20)), t, T(2), enter='spin', idle='breathe', seed=2)
    if t > T(4): img = Y.pulse_rings(img, Y.W // 2, 960, t - T(4), Y.GOLD, 1.3, 3, 520)
    img = SP(img, lambda b: Y.glow_text(b, 'RSI', (Y.W // 2, 960), 300, Y.WHITE, (90, 110, 170)), t, T(4), enter='stamp', idle='float', seed=3, dur=0.35)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('ogni', 'serif', 90, Y.MUTE), ('TRADER', 'big', 100, Y.GOLD)], 1230), t, T(10), enter='rise', idle='float', seed=4)
    img = Y.camera(img, t, 0, punches=[T(2), T(4), T(11)], shakes=[T(4)])
    img = Y.color_flash(img, t, [T(4)], Y.GOLD, 0.16, 0.4)
    return img, True
ev(0, 'boom', 0.7); ev(0.05, 'whoosh', 0.6); ev(T(2), 'swoosh_up'); ev(T(2) + 0.1, 'pop_hi'); ev(T(4), 'boom'); ev(T(4), 'stamp', 0.7); ev(T(10), 'pop')

# ---------------- S2 ----------------
def gauge(b, cx, cy, r, v, ink):
    d = ImageDraw.Draw(b); n = 20; on = int(n * v / 100 + 0.001)
    for i in range(n):
        a0 = 150 + i * 240 / n + 1.5; a1 = 150 + (i + 1) * 240 / n - 1.5
        c = (Y.GREEN if i < 6 else Y.RED if i >= 14 else Y.GOLD) if i < on else (210, 206, 196)
        d.arc((cx - r, cy - r, cx + r, cy + r), a0, a1, fill=c, width=int(r * 0.2))
    d.text((cx, cy + 10), str(int(v)), font=Y.F(Y.BIG, int(r * 0.75)), fill=ink, anchor='mm')
    for val, a in [(0, 150), (100, 390)]:
        x = cx + (r + 50) * math.cos(math.radians(a)); y = cy + (r + 50) * math.sin(math.radians(a))
        d.text((x, y), str(val), font=Y.F(Y.MONO, 40), fill=Y.MUTE, anchor='mm')
def s2(t):
    s = t - CUTS[1]; img = Y.grid_paper(); d = ImageDraw.Draw(img)
    img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [("l'RSI è un", 'serif', 92, Y.INK), ('INDICATORE', 'big', 100, Y.INK)], 330), t, CUTS[1], 0.4, 'float', 5, 0.6)
    v = 0 if t < T(21) else 100 * Y.ease((t - T(21)) / (T(23) + 0.4 - T(21)))
    v += 0 if t < T(23) + 0.5 else -8 * (0.5 + 0.5 * math.sin((t - T(23)) * 2.5))
    img = SP(img, lambda b: gauge(b, Y.W // 2, 700, 230, v, Y.INK), t, T(17), enter='pop', idle='float', seed=6, anchor=(Y.W // 2, 700))
    if t > T(24): img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('la', 'serif', 80, Y.INK), ('FORZA', 'big', 96, Y.GOLDK), ('del prezzo', 'serif', 80, Y.INK)], 1060), t, T(26), enter='left', idle='float', seed=7)
    if t > T(31) - 0.1:
        d = ImageDraw.Draw(img); k = min(14, int((t - T(31) + 0.1) / 0.06) + 1)
        for i in range(k):
            x = 120 + i * 60; up = i % 3 != 1; hh = 50 + (i * 37 % 40); y = 1260 + 8 * math.sin(t * 3 + i)
            col = Y.GREEN if up else Y.RED; d.line([(x, y - hh / 2 - 18), (x, y + hh / 2 + 18)], fill=Y.INK, width=3); d.rectangle((x - 18, y - hh / 2, x + 18, y + hh / 2), fill=col)
        img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), '14 CANDELE', (Y.W // 2, 1410), 80, 1), t, T(31) + 0.2, enter='stamp', idle='breathe', seed=8, dur=0.3)
    img = Y.camera(img, t, CUTS[1], punches=[T(21), T(23), T(31)], shakes=[T(23) + 0.4])
    return img, False
ev(CUTS[1], 'whoosh', 0.6); ev(T(17), 'pop'); [ev(T(21) + k * 0.06, 'tick', 0.6) for k in range(16)]; ev(T(23) + 0.4, 'ding'); ev(T(26), 'swipe', 0.6)
[ev(T(31) - 0.1 + k * 0.06, 'click', 0.5) for k in range(14)]; ev(T(31) + 0.2, 'stamp', 0.8)

# ---------------- S3 ----------------
def rsi_panel(b, t, box, line, z30=1.0, z70=1.0, label30=0, label70=0, glow_i=None):
    x0, y0, x1, y1 = box; d = ImageDraw.Draw(b)
    d.rounded_rectangle((x0 - 20, y0 - 30, x1 + 20, y1 + 30), radius=22, fill=Y.CARD, outline=Y.CARD_LINE, width=2)
    py = lambda v: y1 - v / 100 * (y1 - y0)
    lay = Image.new('RGBA', b.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    if z30 > 0: ld.rectangle((x0, py(30), x0 + (x1 - x0) * Y.ease(z30), y1), fill=Y.GREEN + (55,))
    if z70 > 0: ld.rectangle((x0, y0, x0 + (x1 - x0) * Y.ease(z70), py(70)), fill=Y.RED + (55,))
    b.paste(lay, (0, 0), lay); d = ImageDraw.Draw(b)
    for v, c in [(30, Y.GREEN), (70, Y.RED)]:
        for xx in range(int(x0), int(x1), 24): d.line([(xx, py(v)), (xx + 12, py(v))], fill=c, width=3)
        d.text((x0 - 34, py(v)), str(v), font=Y.F(Y.MONO, 30), fill=c, anchor='rm')
    if len(line) > 1:
        pts = [(x0 + (x1 - x0) * i / (len(line) - 1 if len(line) > 1 else 1), py(v)) for i, v in enumerate(line)]
        d.line(pts, fill=Y.GOLD, width=6, joint='curve'); ex, ey = pts[-1]; d.ellipse((ex - 11, ey - 11, ex + 11, ey + 11), fill=Y.WHITE)
    if label30: Y.key_box(d, 'IPERVENDUTO', (x0 + 250, py(15)), 54, label30, Y.GREEN)
    if label70: Y.key_box(d, 'IPERCOMPRATO', (x1 - 280, py(85)), 54, label70, Y.RED)
    d.text((x0, y0 - 60), 'RSI (14)', font=Y.F(Y.MONO, 34), fill=Y.MUTE, anchor='lm')
    return b
def osc(t, n=80):
    return [50 + 38 * math.sin(i * 0.19 + t * 0.9) * (0.7 + 0.3 * math.sin(i * 0.05)) + 6 * math.sin(i * 0.9) for i in range(n)]
def s3(t):
    s = t - CUTS[2]; img = Y.term_bg(); img = Y.light_sweep(img, t, 3.2, 200, 35); img = Y.dust(img, t, 30, 7, Y.ICE, 30)
    d = ImageDraw.Draw(img)
    n = int(20 + 60 * Y.ease(s / 6)); line = osc(t)[:n]
    z30 = (t - T(33)) / 0.5; z70 = (t - T(45)) / 0.5
    img = SP(img, lambda b: rsi_panel(b, t, (150, 560, 980, 1300), line, z30, z70, (t - T(38)) / 0.4 if t > T(38) else 0, (t - T(48)) / 0.4 if t > T(48) else 0), t, CUTS[2], enter='rise', idle='float', seed=9, amp=0.3)
    if t > T(33): img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('sotto', 'serif', 90, Y.WHITE), ('30', 'big', 110, Y.GREEN)], 360), t, T(33), enter='left', idle='float', seed=10, exit_t=T(45) - 0.3)
    if t > T(45): img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('sopra', 'serif', 90, Y.WHITE), ('70', 'big', 110, Y.RED)], 360), t, T(45), enter='right', idle='float', seed=11)
    if T(40) < t < T(45): img = SP(img, lambda b: Y.arrow(ImageDraw.Draw(b), 860, 1080, 900, 1260, Y.ease((t - T(40)) / 0.4), Y.GREEN, 8, 5), t, T(40), enter='none', idle='wobble')
    if t > T(50): img = SP(img, lambda b: Y.arrow(ImageDraw.Draw(b), 300, 760, 260, 600, Y.ease((t - T(50)) / 0.4), Y.RED, 8, 6), t, T(50), enter='none', idle='wobble')
    img = Y.camera(img, t, CUTS[2], punches=[T(34), T(38), T(46), T(48)], shakes=[T(38), T(48)])
    img = Y.color_flash(img, t, [T(38)], Y.GREEN, 0.15, 0.3); img = Y.color_flash(img, t, [T(48)], Y.RED, 0.15, 0.3)
    return img, True
ev(CUTS[2], 'swipe'); ev(CUTS[2] + 0.1, 'swoosh_up'); ev(T(33), 'swipe', 0.6); ev(T(34), 'pop'); ev(T(38), 'stamp', 0.7); ev(T(38), 'pop_hi'); ev(T(40), 'whoosh', 0.4)
ev(T(45), 'swipe', 0.6); ev(T(46), 'pop'); ev(T(48), 'stamp', 0.7); ev(T(48), 'pop_hi'); ev(T(50), 'swoosh_up', 0.5)

# ---------------- S4 ----------------
CS, RS, CI = EX['cs'], EX['rsi'], EX['ci']
LO = min(c['l'] for c in CS) - 4; HI = max(EX['tp'], max(c['h'] for c in CS)) + 4
def reveal(t):
    a = 14
    if t < T(64): return int(a + (CI - 8 - a) * Y.ease((t - CUTS[3]) / (T(64) - CUTS[3])))
    if t < T(71) + 0.3: return int(CI - 8 + 8 * Y.ease((t - T(64)) / (T(71) + 0.3 - T(64)))) + 1
    if t < T(80): return CI + 1
    return int(CI + 1 + (len(CS) - CI - 1) * Y.ease((t - T(80)) / (T(84) + 0.8 - T(80))))
def chart4(b, t):
    k = max(2, reveal(t)); x0, x1, y0, y1 = 110, 990, 520, 1080
    d = ImageDraw.Draw(b); d.rounded_rectangle((x0 - 30, y0 - 50, x1 + 30, y1 + 30), radius=22, fill=Y.CARD, outline=Y.CARD_LINE, width=2)
    d.text((x0, y0 - 22), 'GRAFICO A 15 MINUTI', font=Y.F(Y.MONO, 30), fill=Y.MUTE, anchor='lm')
    py = lambda p: y1 - (p - LO) / (HI - LO) * (y1 - y0); step = (x1 - x0) / len(CS)
    xe = x0 + (CI + 0.5) * step
    zones = []
    if t > T(75): zones.append((EX['stop'] - 3, EX['stop'], 'STOP LOSS', Y.RED, (t - T(75)) / 0.4))
    if t > T(80): zones.append((EX['tp'], EX['tp'] + 3, 'OBIETTIVO', Y.GREEN, (t - T(80)) / 0.4))
    lay = Image.new('RGBA', b.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    if t > T(75): ld.rectangle((xe, py(EX['entry']), xe + (x1 - xe) * Y.ease((t - T(75)) / 0.4), py(EX['stop'])), fill=Y.RED + (50,))
    if t > T(80): ld.rectangle((xe, py(EX['tp']), xe + (x1 - xe) * Y.ease((t - T(80)) / 0.4), py(EX['entry'])), fill=Y.GREEN + (45,))
    b.paste(lay, (0, 0), lay); d = ImageDraw.Draw(b)
    for i, c in enumerate(CS[:k]):
        x = x0 + (i + 0.5) * step; col = (47, 179, 106) if c['g'] else (224, 72, 62)
        d.line([(x, py(c['h'])), (x, py(c['l']))], fill=col, width=3); ya, yb = sorted([py(c['o']), py(c['c'])]); d.rectangle((x - step * .32, ya, x + step * .32, max(yb, ya + 3)), fill=col)
    def hline(p, col, lab, a):
        if a <= 0: return
        y = py(p); xe2 = xe + (x1 - xe) * Y.ease(a)
        for xx in range(int(xe), int(xe2), 22): d.line([(xx, y), (min(xx + 12, xe2), y)], fill=col, width=4)
        if a >= 1:
            f = Y.F(Y.COND, 38); tw = d.textlength(lab, font=f); d.rounded_rectangle((x1 - tw - 26, y - 25, x1, y + 25), radius=9, fill=col); d.text((x1 - 13, y), lab, font=f, fill=Y.DARK, anchor='rm')
    if t > T(72): hline(EX['entry'], Y.GOLD, 'ACQUISTO', (t - T(74)) / 0.4)
    if t > T(75): hline(EX['stop'], Y.RED, 'STOP LOSS', (t - T(75)) / 0.4)
    if t > T(80): hline(EX['tp'], Y.GREEN, 'OBIETTIVO', (t - T(80)) / 0.4)
    # RSI sotto il grafico
    rx0, rx1, ry0, ry1 = x0, x1, 1170, 1380; rpy = lambda v: ry1 - v / 100 * (ry1 - ry0)
    d.rounded_rectangle((rx0 - 30, ry0 - 40, rx1 + 30, ry1 + 20), radius=18, fill=Y.CARD, outline=Y.CARD_LINE, width=2)
    d.text((rx0, ry0 - 18), 'RSI (14)', font=Y.F(Y.MONO, 26), fill=Y.MUTE, anchor='lm')
    for v, c in [(30, Y.GREEN), (70, Y.RED)]:
        for xx in range(rx0, rx1, 22): d.line([(xx, rpy(v)), (xx + 11, rpy(v))], fill=c, width=3)
        d.text((rx0 - 10, rpy(v)), str(v), font=Y.F(Y.MONO, 24), fill=c, anchor='rm')
    pts = [(x0 + (i + 0.5) * step, rpy(v)) for i, v in enumerate(RS[:k]) if v is not None]
    if len(pts) > 1: d.line(pts, fill=Y.GOLD, width=5, joint='curve')
    return b, py, step, x0, rpy
def s4(t):
    s = t - CUTS[3]; img = Y.term_bg(); img = Y.light_sweep(img, t + 1.5, 3.4, 200, 30); img = Y.dust(img, t, 25, 11, Y.ICE, 30)
    d = ImageDraw.Draw(img)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('ecco', 'serif', 86, Y.MUTE), ('LA REGOLA', 'big', 104, Y.WHITE)], 330), t, CUTS[3], enter='drop', idle='float', seed=12)
    if t > T(57): img = SP(img, lambda b: Y.hand(ImageDraw.Draw(b), 'esempio didattico', (Y.W // 2, 410), 62, Y.GOLD, Y.ease((t - T(57)) / 0.6)), t, T(57), enter='none', idle='float', seed=13)
    holder = {}
    def draw(b):
        r = chart4(b, t); holder['g'] = r
    img = SP(img, draw, t, CUTS[3] + 0.1, enter='rise', idle='float', seed=14, amp=0.25)
    if 'g' not in holder: return Y.camera(img, t, CUTS[3]), True
    _, py, step, x0, rpy = holder['g']
    xe = x0 + (CI + 0.5) * step
    if t > T(66): img = Y.pulse_rings(img, xe, rpy(RS[CI]), t - T(66), Y.GREEN, 1.0, 2, 110, 3)
    if t > T(71): img = SP(img, lambda b: Y.circle(ImageDraw.Draw(b), xe, rpy(RS[CI]), 70, 45, Y.ease((t - T(71)) / 0.4), Y.GREEN, 6, 7), t, T(71), enter='none', idle='wobble', amp=0.5)
    if t > T(72): img = SP(img, lambda b: Y.arrow(ImageDraw.Draw(b), xe - 120, py(EX['entry']) + 170, xe - 10, py(EX['entry']) + 15, Y.ease((t - T(72)) / 0.35), Y.WHITE, 7, 8), t, T(72), enter='none', idle='wobble', amp=0.4)
    if t > T(82): img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'IL DOPPIO DEL RISCHIO', (Y.W // 2, 1470), 64, 1), t, T(82), enter='stamp', idle='breathe', seed=15, dur=0.3)
    img = Y.camera(img, t, CUTS[3], punches=[T(54), T(62), T(71), T(74), T(80), T(82)], shakes=[T(82)], push=0.04)
    img = Y.color_flash(img, t, [T(74)], Y.GOLD, 0.15, 0.3); img = Y.color_flash(img, t, [T(82)], Y.GREEN, 0.15, 0.3)
    return img, True
ev(CUTS[3], 'whoosh', 0.7); ev(CUTS[3] + 0.1, 'swoosh_up'); ev(T(54), 'pop'); ev(T(57), 'click'); ev(T(62), 'tick'); ev(T(66), 'riser', 0.5)
ev(T(71), 'ding'); ev(T(72), 'swipe', 0.6); ev(T(74), 'coin'); ev(T(75), 'alert', 0.7); ev(T(80), 'pop_hi'); ev(T(82), 'stamp', 0.8); ev(T(82) + 0.05, 'trin', 0.7)
[ev(T(80) + k * 0.12, 'tick', 0.35) for k in range(8)]

# ---------------- S5 ----------------
TCS, TRS = TR['cs'], TR['rsi']
def trend_draw(b, t, s):
    d = ImageDraw.Draw(b); k = max(3, int(len(TCS) * Y.ease(s / 3.5))); x0, x1, y0, y1 = 140, 960, 520, 950
    lo = min(c['l'] for c in TCS); hi = max(c['h'] for c in TCS); py = lambda p: y1 - (p - lo) / (hi - lo) * (y1 - y0); step = (x1 - x0) / len(TCS)
    for i, c in enumerate(TCS[:k]):
        x = x0 + (i + 0.5) * step; col = Y.GREEN_K if c['g'] else Y.RED
        d.line([(x, py(c['h'])), (x, py(c['l']))], fill=Y.INK, width=2); ya, yb = sorted([py(c['o']), py(c['c'])]); d.rectangle((x - step * .3, ya, x + step * .3, max(yb, ya + 3)), fill=col)
    rx0, rx1, ry0, ry1 = x0, x1, 1010, 1200; rpy = lambda v: ry1 - v / 100 * (ry1 - ry0)
    d.rectangle((rx0, ry0, rx1, ry1), outline=(150, 145, 135), width=2)
    for v in (30, 70):
        for xx in range(rx0, rx1, 20): d.line([(xx, rpy(v)), (xx + 10, rpy(v))], fill=Y.RED if v == 70 else Y.GREEN_K, width=3)
    pts = [(x0 + (i + 0.5) * step, rpy(v)) for i, v in enumerate(TRS[:k]) if v is not None]
    if len(pts) > 1: d.line(pts, fill=Y.GOLDK, width=5)
    return rpy
def s5(t):
    s = t - CUTS[4]; img = Y.grid_paper(); d = ImageDraw.Draw(img)
    img = SP(img, lambda b: Y.stamp(b, 'TRAPPOLA', (Y.W // 2, 330), 120, Y.RED, -5), t, T(87), enter='stamp', idle='wobble', seed=16, dur=0.3, amp=0.5)
    holder = {}
    def draw(b): holder['r'] = trend_draw(b, t, t - T(88))
    if t > T(88): img = SP(img, draw, t, T(88), enter='rise', idle='float', seed=17, amp=0.3)
    if t > T(95) and 'r' not in holder: return img, False
    if t > T(90): img = SP(img, lambda b: Y.hand(ImageDraw.Draw(b), 'trend forte', (300, 470), 70, Y.GREEN_K, Y.ease((t - T(90)) / 0.5)), t, T(90), enter='none', idle='float', seed=18)
    if t > T(95): img = SP(img, lambda b: Y.circle(ImageDraw.Draw(b), 700, 1060, 300, 70, Y.ease((t - T(95)) / 0.5), Y.RED, 6, 9), t, T(95), enter='none', idle='wobble', amp=0.4)
    if t > T(95): img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('sopra', 'serif', 70, Y.INK), ('70', 'big', 84, Y.RED), ('per ore', 'serif', 70, Y.INK)], 1300), t, T(95), enter='pop', idle='float', seed=19)
    if t > T(99):
        def nv(b):
            dd = ImageDraw.Draw(b); dd.rounded_rectangle((90, 1370, 990, 1500), radius=24, fill=Y.RED)
            dd.text((Y.W // 2, 1435), 'NON VENDERE CONTRO IL TREND', font=Y.F(Y.BIG, 60), fill=Y.WHITE, anchor='mm')
        img = SP(img, nv, t, T(99), enter='stamp', idle='wobble', seed=20, dur=0.3, amp=0.4)
    img = Y.camera(img, t, CUTS[4], punches=[T(87), T(95), T(99)], shakes=[T(87), T(99)])
    img = Y.color_flash(img, t, [T(87), T(99)], Y.RED, 0.15, 0.3)
    return img, False
ev(CUTS[4], 'glitch', 0.6); ev(T(87), 'stamp'); ev(T(87), 'boom', 0.7); ev(T(88), 'swoosh_up', 0.7); ev(T(90), 'click'); ev(T(95), 'alert', 0.7); ev(T(99), 'stamp'); ev(T(99) + 0.05, 'boom', 0.6)

# ---------------- S6 ----------------
CTA_T = [T(109), T(112), T(114), T(120)]
def s6(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 50, 17, Y.GOLD, 55); d = ImageDraw.Draw(img)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('se ti è stata', 'serif', 90, Y.WHITE), ('UTILE', 'big', 110, Y.GOLD)], 420), t, CUTS[5], enter='drop', idle='float', seed=21)
    img = Y.cta_four(img, t, CTA_T, 'STRATEGIA', y0=640)
    img = Y.camera(img, t, CUTS[5], punches=CTA_T, shakes=[], push=0.03)
    return img, True
ev(CUTS[5], 'swoosh_up'); ev(CUTS[5] + 0.1, 'pop'); ev(CTA_T[0], 'pop'); ev(CTA_T[1], 'pop_hi'); ev(CTA_T[1] + 0.05, 'bubble', 0.6); ev(CTA_T[2], 'bubble'); ev(CTA_T[3], 'swoosh_up'); ev(CTA_T[3] + 0.1, 'coin')

def outro(t):
    s = t - CUTS[6]; img = Y.night_bg(t); img = Y.light_beams(img, t); img = Y.dust(img, t, 50, 19, Y.GOLD, 60)
    img = Y.pulse_rings(img, Y.W // 2, 700, s, Y.GOLD, 1.4, 3, 420)
    img = Y.logo_reveal(img, t, CUTS[6] + 0.05, Y.W // 2, 700, 400)
    img = Y.telegram_cta(img, t, CUTS[6] + 1.2, 1150)
    img = Y.camera(img, t, CUTS[6], punches=[CUTS[6] + 0.6, CUTS[6] + 1.75], shakes=[CUTS[6] + 1.75], push=0.05)
    return Y.flash(img, t, [CUTS[6]], 0.18), True
ev(CUTS[6], 'boom', 0.8); ev(CUTS[6] + 0.05, 'whoosh', 0.8); ev(CUTS[6] + 0.6, 'trin', 0.8); ev(CUTS[6] + 0.75, 'swoosh_up', 0.5)
ev(CUTS[6] + 1.2, 'whoosh', 0.9); ev(CUTS[6] + 1.45, 'pop'); ev(CUTS[6] + 1.75, 'stamp', 0.7); ev(CUTS[6] + 1.8, 'coin')
for c in CUTS[1:-1]: ev(c - 0.15, 'whoosh', 0.9)

SC = [s1, s2, s3, s4, s5, s6]
def scene(t):
    for i in range(len(SC)):
        if CUTS[i] <= t < CUTS[i + 1]: return SC[i](t)
    return outro(t)
def frame(t):
    img, dark = scene(t)
    for i, c in enumerate(CUTS[1:-1]):
        if c <= t < c + TD:
            prev, _ = scene(c - 0.01); p = (t - c) / TD; kind = TRANS[i]
            img = {'whip': lambda: Y.whip(prev, img, p, 1), 'whip_v': lambda: Y.whip_v(prev, img, p, 1), 'blur': lambda: Y.blur_cross(prev, img, p), 'zoom': lambda: Y.zoom_through(prev, img, p), 'wipe': lambda: Y.circle_wipe(prev, img, p)}[kind]()
    img = Y.captions_pop(img, t, WORDS, G, KEYS, dark, end=CUTS[5] - 0.05)
    Y.disclaimer(ImageDraw.Draw(img), dark)
    return img
def _f(i): return frame(i / Y.FPS).tobytes()
if __name__ == '__main__':
    import subprocess
    from multiprocessing import Pool
    if sys.argv[1] == 'preview':
        ts = [float(x) for x in sys.argv[2:]]
        Y.contact_sheet(frame, ts, os.path.join(D, 'preview.png'), w=180)
    else:
        n = int(DUR * Y.FPS); silent = os.path.join(D, 'muto.mp4')
        p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{Y.W}x{Y.H}', '-r', str(Y.FPS), '-i', '-',
                              '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', silent], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for b in pool.imap(_f, range(n), chunksize=4): p.stdin.write(b)
        p.stdin.close(); p.wait()
        S.music(os.path.join(D, 'base.wav'), DUR, 94, 'positivo')
        a = S.mix(os.path.join(D, 'audio.m4a'), DUR, voce=os.path.join(D, 'voce.mp3'), musica=os.path.join(D, 'base.wav'), eventi=EV, music_db=-17)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', silent, '-i', a, '-map', '0:v', '-map', '1:a', '-c', 'copy', '-shortest', '-movflags', '+faststart', os.path.join(D, 'yardfx_strategia1_rsi.mp4')], check=True)
        print('ok', DUR, len(EV))
