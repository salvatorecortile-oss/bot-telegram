"""Strategia base #3: incrocio EMA 9/21 con filtro EMA 200 — voce Enea, pubblicato il 18/11/2026.
Ricetta STRATEGIA BASE: Quaderno -> Terminale -> Notte (qui alternati scena per scena).
S1 NOTTE     T0   DUE LINEE luminose che si INCROCIANO (lampo sul punto d'incrocio) · una TERZA linea · ti dice se FIDARTI
S2 QUADERNO  T13  'Strategia base #3' con 3 candeline (numero della serie, detto a voce) · legenda disegnata a mano:
                  EMA 9 linea mossa = VELOCE · EMA 21 linea morbida = LENTA · EMA 200 linea dritta = DIREZIONE
S3 NOTTE     T37  LA REGOLA: chip COMPRO · '9 incrocia SOPRA la 21' ✓ · timbro SOLO SE · 'prezzo SOPRA la 200' ✓ · per VENDERE il CONTRARIO
S4 TERMINALE T59  esempio didattico: candele XAUUSD con EMA 9/21/200, incrocio cerchiato, STOP sotto l'ultimo minimo, OBIETTIVO 2 × RISCHIO
S5 QUADERNO  T70  timbro TRAPPOLA · prezzo in LATERALE con le due linee che si intrecciano · X rosse sugli incroci · FALSI SEGNALI
S6 NOTTE     T83  se ti è stata UTILE + 4 paletti (commenta EMA) · outro logo + Telegram"""
import sys, os, math, json, random
sys.path.insert(0, '/home/user/bot-telegram/contenuti/yardfx_video'); import yardfx as Y; import suoni as S
from PIL import Image, ImageDraw
D = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, D)
import dati_ema as dati
WORDS = json.load(open(os.path.join(D, 'words.json'))); G = Y.make_groups(WORDS)
T = lambda i: WORDS[i][1]
VEND = WORDS[-1][2]
KEYS = {4, 7, 12, 18, 23, 29, 32, 36, 39, 44, 47, 54, 56, 60, 61, 64, 65, 69, 71, 77, 81}
CUTS = [0, T(13), T(37), T(59), T(70), T(83), VEND + 0.3]
OUT_LEN = 4.2; DUR = CUTS[-1] + OUT_LEN
TRANS = ['blur', 'whip', 'zoom', 'wipe', 'whip_v']
TD = 0.4; TIKTOK = os.environ.get('TIKTOK') == '1'
EV = []
def ev(t, n, g=1.0): EV.append((round(t, 3), n, g))
SP = Y.sprite
ICE = Y.ICE
def big(b, s, xy, size, col, font=Y.BIG): ImageDraw.Draw(b).text(xy, s, font=Y.F(font, size), fill=col, anchor='mm')

def glow_line(img, pts, col, w, prog, blur=12):
    """linea luminosa che si disegna (prog 0..1)"""
    from PIL import ImageFilter
    if prog <= 0: return img
    k = max(2, int(len(pts) * min(1, prog))); m = Image.new('L', (Y.W, Y.H), 0); ImageDraw.Draw(m).line(pts[:k], fill=255, width=w, joint='curve')
    img = Image.composite(Image.new('RGB', (Y.W, Y.H), tuple(int(v * 0.6) for v in col)), img, m.filter(ImageFilter.GaussianBlur(blur)))
    return Image.composite(Image.new('RGB', (Y.W, Y.H), col), img, m)

# ---------- S1 NOTTE: due linee che si incrociano ----------
def wave(t, a, f, ph, y0, slope):
    return [(x, y0 + slope * (x - 540) + a * math.sin(x * f + ph + t * 0.8)) for x in range(60, 1021, 12)]
def s1(t):
    img = Y.night_bg(t); img = Y.light_beams(img, t); img = Y.dust(img, t, 45, 3, Y.GOLD, 40)
    img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('DUE', 'big', 150, Y.WHITE), ('linee', 'serif', 130, Y.WHITE)], 400), t, -0.4, 0.45, 'float', 1)
    img = glow_line(img, wave(t, 50, 0.011, 0, 880, 0.32), Y.GOLD, 9, (t + 0.4) / 1.0)
    img = glow_line(img, wave(t, 25, 0.007, 1.5, 880, -0.30), ICE, 9, (t - 0.1) / 1.0)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('che si', 'serif', 86, Y.MUTE), ('INCROCIANO', 'big', 110, Y.GOLD)], 560), t, T(3), enter='rise', idle='float', seed=2)
    if t > T(4): img = Y.pulse_rings(img, 540, 880, t - T(4), Y.WHITE, 1.2, 3, 300)
    if t > T(6):
        img = glow_line(img, [(x, 1130 - 0.08 * (x - 60)) for x in range(60, 1021, 20)], Y.WHITE, 12, (t - T(6)) / 0.8, 16)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('e una', 'serif', 86, Y.MUTE), ('TERZA', 'big', 120, Y.WHITE)], 1250), t, T(6), enter='left', idle='float', seed=3)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('ti dice se', 'serif', 80, Y.MUTE)], 1360), t, T(9), enter='rise', idle='float', seed=4)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'FIDARTI', (Y.W // 2, 1450), 84, Y.ease((t - T(12)) / 0.35)), t, T(12), enter='stamp', idle='breathe', seed=5, dur=0.3)
    img = Y.camera(img, t, 0, punches=[T(4), T(7), T(12)], shakes=[T(4)])
    img = Y.color_flash(img, t, [T(4)], Y.GOLD, 0.16, 0.35)
    return Y.color_flash(img, t, [T(12)], Y.GOLD, 0.14, 0.3), True
ev(0, 'boom', 0.7); ev(0.05, 'whoosh', 0.6); ev(0.3, 'swoosh_up', 0.5); ev(T(3), 'swipe', 0.5); ev(T(4), 'boom', 0.8); ev(T(4) + 0.05, 'ding', 0.6)
ev(T(6), 'whoosh', 0.6); ev(T(7), 'pop'); ev(T(9), 'click', 0.6); ev(T(12), 'stamp', 0.8)

# ---------- S2 QUADERNO: le tre medie ----------
LEG = [('EMA 9', 'veloce', Y.GOLDK, 680, T(18), T(23), 34, 0.045), ('EMA 21', 'lenta', (40, 110, 190), 960, T(25), T(29), 18, 0.018), ('EMA 200', 'DIREZIONE', Y.INK, 1240, T(31), T(36), 3, 0.004)]
def s2(t):
    img = Y.grid_paper()
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('strategia', 'serif', 96, Y.INK), ('BASE', 'big', 110, Y.INK)], 330), t, CUTS[1], enter='drop', idle='float', seed=6)
    for k in range(3):
        if t > T(15) + k * 0.12:
            img = SP(img, lambda b, k=k: Y.gold_candle(b, 400 + k * 70, 380, 520, 410 + k * 8, 480, 40, 1), t, T(15) + k * 0.12, enter='drop', idle='float', seed=40 + k)
    img = SP(img, lambda b: big(b, '#3', (680, 455), 120, Y.GOLDK), t, T(16), enter='spin', idle='breathe', seed=7)
    for i, (lab, desc, col, y, t0, t1, amp, fr) in enumerate(LEG):
        if t < t0: continue
        def dr(b, lab=lab, desc=desc, col=col, y=y, t0=t0, t1=t1, amp=amp, fr=fr, i=i):
            d = ImageDraw.Draw(b)
            d.text((90, y - 80), lab, font=Y.F(Y.BIG, 92), fill=col, anchor='lm')
            pts = [(x, y + 40 + amp * math.sin(x * fr + i)) for x in range(90, 991, 10)]
            Y.stroke(d, pts, Y.ease((t - t0) / 0.8), col, 10 if i == 2 else 7, seed=50 + i, amp=1.5)
            if t > t1:
                if i < 2: Y.hand(d, desc, (990, y - 80), 80, col, Y.ease((t - t1) / 0.5), anchor='rm')
        img = SP(img, dr, t, t0, enter='left', idle='float', seed=8 + i, amp=0.5)
        if i == 2 and t > t1:
            img = SP(img, lambda b: Y.stamp(b, 'DIREZIONE', (760, 1150), 70, Y.RED, -5), t, t1, enter='stamp', idle='wobble', seed=11, dur=0.3, amp=0.4)
            Y.arrow(ImageDraw.Draw(img), 900, 1290, 1010, 1240, Y.ease((t - t1) / 0.4), Y.RED, 6, 12)
    img = Y.camera(img, t, CUTS[1], punches=[T(16), T(18), T(25), T(31), T(36)], shakes=[T(36)], push=0.04)
    return Y.color_flash(img, t, [T(36)], Y.RED, 0.12, 0.25), False
ev(CUTS[1], 'swoosh_up', 0.6); ev(CUTS[1] + 0.05, 'pop'); [ev(T(15) + k * 0.12, 'pop_hi', 0.5) for k in range(3)]; ev(T(16), 'ding', 0.6)
for lab, desc, col, y, t0, t1, a, f in LEG: ev(t0, 'swipe', 0.6); ev(t0 + 0.1, 'click', 0.6); ev(t1, 'pop' if t1 != T(36) else 'stamp')
ev(T(19), 'bubble', 0.5); ev(T(26), 'bubble', 0.5); ev(T(32), 'bubble', 0.5)

# ---------- S3 NOTTE: la regola ----------
def rule_row(b, y, parts, ok_t, t):
    d = ImageDraw.Draw(b); d.rounded_rectangle((70, y - 80, 1010, y + 80), radius=28, fill=(20, 26, 48), outline=(70, 84, 130), width=3)
    Y.mixed_title(d, parts, y + 28, cx=560)
    if t > ok_t:
        a = Y.ease((t - ok_t) / 0.35); Y.icon(d, 'spunta', 140, y, 80, a, Y.GREEN, 9, 3)
def s3(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 45, 13, Y.GOLD, 45); img = Y.spotlight(img, Y.W // 2, 60, 700, 520, 45)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('la', 'serif', 100, Y.MUTE), ('REGOLA', 'big', 140, Y.WHITE)], 340), t, T(37), enter='drop', idle='float', seed=13)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'COMPRO', (Y.W // 2, 470), 90, Y.ease((t - T(39)) / 0.35), Y.GREEN), t, T(39), enter='pop', idle='breathe', seed=14)
    img = SP(img, lambda b: rule_row(b, 670, [('la', 'serif', 70, Y.MUTE), ('9', 'big', 100, Y.GOLD), ('incrocia', 'serif', 70, Y.WHITE), ('SOPRA', 'big', 86, Y.GREEN), ('la', 'serif', 70, Y.MUTE), ('21', 'big', 100, ICE)], T(46), t), t, T(41), enter='left', idle='float', seed=15, amp=0.5)
    img = SP(img, lambda b: Y.stamp(b, 'SOLO SE', (Y.W // 2, 850), 80, Y.GOLD, -4), t, T(47), enter='stamp', idle='wobble', seed=16, dur=0.3, amp=0.4)
    img = SP(img, lambda b: rule_row(b, 1030, [('il prezzo è', 'serif', 66, Y.WHITE), ('SOPRA', 'big', 86, Y.GREEN), ('la', 'serif', 70, Y.MUTE), ('200', 'big', 100, Y.WHITE)], T(54), t), t, T(49), enter='right', idle='float', seed=17, amp=0.5)
    if t > T(54): img = Y.pulse_rings(img, 140, 1030, t - T(54), Y.GREEN, 1.2, 2, 160)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('per', 'serif', 80, Y.MUTE), ('VENDERE', 'big', 110, Y.RED)], 1250), t, T(55), enter='rise', idle='float', seed=18)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('il', 'serif', 80, Y.MUTE), ('CONTRARIO', 'big', 110, Y.WHITE)], 1390), t, T(57), enter='rise', idle='wobble', seed=19, amp=0.5)
    img = Y.camera(img, t, CUTS[2], punches=[T(39), T(44), T(47), T(54), T(56)], shakes=[T(47)])
    img = Y.color_flash(img, t, [T(39), T(54)], Y.GREEN, 0.14, 0.28)
    return Y.color_flash(img, t, [T(56)], Y.RED, 0.14, 0.28), True
ev(CUTS[2] + 0.05, 'whoosh', 0.6); ev(T(37), 'pop'); ev(T(39), 'pop_hi'); ev(T(39) + 0.05, 'swipe', 0.5); ev(T(41), 'swipe', 0.6); ev(T(42), 'tick', 0.5); ev(T(44), 'pop', 0.6); ev(T(46), 'ding', 0.7)
ev(T(47), 'stamp'); ev(T(49), 'swipe', 0.6); ev(T(52), 'pop', 0.6); ev(T(54), 'ding', 0.7); ev(T(54) + 0.05, 'coin', 0.5); ev(T(55), 'swoosh_up', 0.6); ev(T(56), 'pop'); ev(T(57), 'pop_hi', 0.6)

# ---------- S4 TERMINALE: esempio didattico ----------
CS, E9, E21, E200, XI, ENTRY, STOP, TP, HIT = dati.build(1)
B0 = 8; CS, E9, E21, E200 = CS[B0:], E9[B0:], E21[B0:], E200[B0:]; XI -= B0; HIT -= B0
LO, HI = 3765, 3892
def chart(b, t):
    d = ImageDraw.Draw(b); x0, x1, y0, y1 = 100, 990, 520, 1290
    d.rounded_rectangle((x0 - 30, y0 - 50, x1 + 30, y1 + 40), radius=22, fill=Y.CARD, outline=Y.CARD_LINE, width=2)
    py = lambda p: y1 - (p - LO) / (HI - LO) * (y1 - y0); step = (x1 - x0) / len(CS); px = lambda i: x0 + (i + 0.5) * step
    if t < T(60): k = int(4 + (XI + 1 - 4) * Y.ease((t - CUTS[3]) / (T(60) - CUTS[3])))
    elif t < T(65): k = XI + 1
    else: k = int(XI + 1 + (len(CS) - XI - 1) * Y.ease((t - T(65)) / 1.8))
    lay = Image.new('RGBA', b.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(lay); xe = px(XI)
    if t > T(61): ld.rectangle((xe, py(ENTRY), xe + (x1 - xe) * Y.ease((t - T(61)) / 0.4), py(STOP)), fill=Y.RED + (55,))
    if t > T(65): ld.rectangle((xe, py(TP), xe + (x1 - xe) * Y.ease((t - T(65)) / 0.4), py(ENTRY)), fill=Y.GREEN + (45,))
    b.paste(lay, (0, 0), lay); d = ImageDraw.Draw(b)
    for i, c in enumerate(CS[:k]):
        x = px(i); col = (47, 179, 106) if c['g'] else (224, 72, 62)
        d.line([(x, py(c['h'])), (x, py(c['l']))], fill=col, width=3); ya, yb = sorted([py(c['o']), py(c['c'])]); d.rectangle((x - step * .32, ya, x + step * .32, max(yb, ya + 3)), fill=col)
    for e, col, w, lab in [(E200, Y.WHITE, 6, '200'), (E21, ICE, 5, '21'), (E9, Y.GOLD, 5, '9')]:
        pts = [(px(i), py(e[i])) for i in range(k)]
        if len(pts) > 1: d.line(pts, fill=col, width=w, joint='curve'); d.text((pts[-1][0] + 14, pts[-1][1]), lab, font=Y.F(Y.COND, 34), fill=col, anchor='lm')
    def hl(p, col, lab, t0):
        a = Y.ease((t - t0) / 0.4)
        if a <= 0: return
        y = py(p); xe2 = xe + (x1 - xe) * a
        for xx in range(int(xe), int(xe2), 22): d.line([(xx, y), (min(xx + 12, xe2), y)], fill=col, width=4)
        if a >= 1 and lab:
            f = Y.F(Y.COND, 38); tw = d.textlength(lab, font=f); d.rounded_rectangle((x1 - tw - 26, y - 25, x1, y + 25), radius=9, fill=col); d.text((x1 - 13, y), lab, font=f, fill=Y.DARK, anchor='rm')
    hl(ENTRY, Y.GOLD, '', T(60)); hl(STOP, Y.RED, 'STOP', T(61)); hl(TP, Y.GREEN, 'OBIETTIVO', T(65))
    return py, px
def s4(t):
    img = Y.term_bg(); img = Y.light_sweep(img, t + 1.5, 3.4, 200, 30); img = Y.dust(img, t, 25, 11, Y.ICE, 30)
    img = SP(img, lambda b: Y.hand(ImageDraw.Draw(b), 'esempio didattico', (Y.W // 2, 380), 80, Y.GOLD, Y.ease((t - T(59)) / 0.6)), t, T(59), enter='none', idle='float', seed=20)
    holder = {}
    def dr(b): holder['g'] = chart(b, t)
    img = SP(img, dr, t, CUTS[3], enter='rise', idle='float', seed=21, amp=0.25)
    if 'g' in holder:
        py, px = holder['g']; xe = px(XI); ye = py((E9[XI] + E21[XI]) / 2)
        if t > T(60):
            img = Y.pulse_rings(img, xe, ye, t - T(60), Y.GOLD, 1.0, 2, 110, 3)
            img = SP(img, lambda b: Y.circle(ImageDraw.Draw(b), xe, ye, 50, 50, Y.ease((t - T(60)) / 0.4), Y.GOLD, 6, 22), t, T(60), enter='none', idle='wobble', amp=0.5)
        if t > T(63):
            lo_i = min(range(XI - 8, XI + 1), key=lambda i: CS[i]['l'])
            img = SP(img, lambda b: Y.arrow(ImageDraw.Draw(b), px(lo_i) - 120, py(STOP) + 150, px(lo_i) - 8, py(CS[lo_i]['l']) + 12, Y.ease((t - T(63)) / 0.35), Y.WHITE, 6, 23), t, T(63), enter='none', idle='wobble', amp=0.4)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'DUE VOLTE IL RISCHIO', (Y.W // 2, 1450), 64, Y.ease((t - T(66)) / 0.4)), t, T(66), enter='pop', idle='breathe', seed=24)
    img = Y.camera(img, t, CUTS[3], punches=[T(60), T(61), T(65), T(66)], shakes=[T(61)], push=0.04)
    img = Y.color_flash(img, t, [T(61)], Y.RED, 0.13, 0.25); return Y.color_flash(img, t, [T(65)], Y.GREEN, 0.14, 0.28), True
ev(CUTS[3], 'swipe'); ev(CUTS[3] + 0.1, 'click'); [ev(CUTS[3] + 0.2 + k * 0.12, 'tick', 0.3) for k in range(9)]; ev(T(60), 'ding'); ev(T(61), 'alert', 0.7); ev(T(63), 'swipe', 0.5); ev(T(64), 'pop', 0.6)
ev(T(65), 'pop_hi'); [ev(T(65) + 0.1 + k * 0.18, 'tick', 0.35) for k in range(8)]; ev(T(66), 'coin'); ev(T(69), 'trin', 0.6)

# ---------- S5 QUADERNO: la trappola ----------
def side(t, ph, amp, fr): return [(x, 1000 + amp * math.sin(x * fr + ph)) for x in range(90, 991, 10)]
def s5(t):
    img = Y.grid_paper()
    img = SP(img, lambda b: Y.stamp(b, 'TRAPPOLA', (Y.W // 2, 300), 120, Y.RED, -6), t, T(71), enter='stamp', idle='wobble', seed=25, dur=0.3, amp=0.4)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('quando il prezzo va in', 'serif', 70, Y.INK)], 520), t, T(72), enter='rise', idle='float', seed=26)
    img = SP(img, lambda b: big(b, 'LATERALE', (Y.W // 2, 640), 130, Y.INK), t, T(77), enter='pop', idle='wobble', seed=27, amp=0.5)
    d = ImageDraw.Draw(img); a = Y.ease((t - T(72)) / 1.6)
    Y.stroke(d, [(90, 820), (990, 820)], a, Y.MUTE, 4, seed=30); Y.stroke(d, [(90, 1180), (990, 1180)], a, Y.MUTE, 4, seed=31)
    l1 = side(t, 0, 90, 0.022); l2 = side(t, 1.1, 60, 0.014)
    Y.stroke(d, l1, a, Y.GOLDK, 7, seed=32, amp=1.5); Y.stroke(d, l2, a, (40, 110, 190), 7, seed=33, amp=1.5)
    xs = [x for (x, y1), (_, y2), (_, y3), (_, y4) in zip(l1, l2, l1[1:], l2[1:]) if (y1 - y2) * (y3 - y4) < 0]
    for j, x in enumerate(xs):
        t0 = T(79) + j * 0.14
        if t > t0:
            y = 1000 + 90 * math.sin(x * 0.022)
            Y.icon(d, 'croce', x, y, 70, Y.ease((t - t0) / 0.3), Y.RED, 8, 60 + j)
    img = SP(img, lambda b: Y.stamp(b, 'FALSI SEGNALI', (Y.W // 2, 1360), 100, Y.RED, 4), t, T(81), enter='stamp', idle='wobble', seed=28, dur=0.3, amp=0.4)
    img = Y.camera(img, t, CUTS[4], punches=[T(71), T(77), T(81)], shakes=[T(71), T(81)], push=0.04)
    return Y.color_flash(img, t, [T(71), T(81)], Y.RED, 0.14, 0.28), False
ev(CUTS[4], 'whoosh', 0.7); ev(T(71), 'stamp'); ev(T(71) + 0.05, 'boom', 0.5); ev(T(72), 'click', 0.6); ev(T(72) + 0.2, 'riser', 0.3); ev(T(77), 'pop')
[ev(T(79) + j * 0.14, 'pop_hi' if j % 2 else 'pop', 0.5) for j in range(6)]; ev(T(81), 'stamp'); ev(T(81) + 0.05, 'glitch', 0.5)

# ---------- S6 CTA ----------
CTA_T = [T(88), T(91), T(93), T(96)]
def s6(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 50, 17, Y.GOLD, 55)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('se ti è stata', 'serif', 90, Y.WHITE), ('UTILE', 'big', 110, Y.GOLD)], 420), t, CUTS[5], enter='drop', idle='float', seed=33)
    img = Y.cta_four(img, t, CTA_T, 'EMA', y0=640)
    return Y.camera(img, t, CUTS[5], punches=CTA_T, push=0.03), True
ev(CUTS[5], 'swoosh_up'); ev(T(87), 'pop'); ev(CTA_T[0], 'pop'); ev(CTA_T[1], 'pop_hi'); ev(CTA_T[1] + 0.05, 'bubble', 0.6); ev(CTA_T[2], 'bubble'); ev(T(94), 'pop', 0.5); ev(CTA_T[3], 'swoosh_up'); ev(CTA_T[3] + 0.1, 'coin')

def outro(t):
    s = t - CUTS[6]; img = Y.night_bg(t); img = Y.light_beams(img, t); img = Y.dust(img, t, 50, 19, Y.GOLD, 60)
    img = Y.pulse_rings(img, Y.W // 2, 700, s, Y.GOLD, 1.4, 3, 420)
    img = Y.logo_reveal(img, t, CUTS[6] + 0.05, Y.W // 2, 700, 400)
    img = Y.telegram_cta(img, t, CUTS[6] + 1.2, 1150, line='' if TIKTOK else 'CERCAMI SU TELEGRAM')
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
        if c <= t < c + TD and i < len(TRANS):
            prev, _ = scene(c - 0.01); p = (t - c) / TD
            img = {'whip': lambda: Y.whip(prev, img, p, 1), 'whip_v': lambda: Y.whip_v(prev, img, p, 1), 'blur': lambda: Y.blur_cross(prev, img, p), 'zoom': lambda: Y.zoom_through(prev, img, p), 'wipe': lambda: Y.circle_wipe(prev, img, p)}[TRANS[i]]()
    img = Y.captions_pop(img, t, WORDS, G, KEYS, dark, end=CUTS[5] - 0.05)
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
NAME = 'yardfx_strategia3_ema'
if __name__ == '__main__':
    import subprocess
    m = sys.argv[1]
    if m == 'preview':
        Y.contact_sheet(frame, [float(x) for x in sys.argv[2:]], os.path.join(D, 'preview.png'), w=180)
    elif m == 'main':
        enc(os.path.join(D, 'main.mp4'), 0, int(CUTS[6] * Y.FPS))
    elif m == 'outro':
        enc(os.path.join(D, 'outro_tt.mp4' if TIKTOK else 'outro_ig.mp4'), int(CUTS[6] * Y.FPS), int(DUR * Y.FPS))
    elif m == 'mix':
        S.music(os.path.join(D, 'base.wav'), DUR, 96, 'tensione')
        a = S.mix(os.path.join(D, 'audio.m4a'), DUR, voce=os.path.join(D, 'voce.mp3'), musica=os.path.join(D, 'base.wav'), eventi=EV, music_db=-17)
        for tag in ['ig', 'tt']:
            lst = os.path.join(D, f'list_{tag}.txt'); open(lst, 'w').write(f"file 'main.mp4'\nfile 'outro_{tag}.mp4'\n")
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-i', a, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'copy', '-shortest', '-movflags', '+faststart',
                            os.path.join(D, f'{NAME}_{"instagram" if tag == "ig" else "tiktok"}.mp4')], check=True)
        print('ok', DUR, len(EV))
