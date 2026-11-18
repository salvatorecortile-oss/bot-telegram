"""Strategia base #4: breakout del range asiatico — voce Speechify «Salvatore» (tempi parola per parola da Speechify), esce ven 20/11/2026 ore 10.
S1 NOTTE      T0   scatola d'oro luminosa che si disegna · SCATOLA · ALLE 9 · candela verde che la sfonda (LA ROMPE)
S2 QUADERNO   T10  'strategia BASE #4' con 4 candeline · prezzo che va di lato di notte · 01:00 → 08:00 · MASSIMO / MINIMO · timbro SCATOLA ASIATICA
S3 TERMINALE  T29  esempio didattico ACQUISTO: candele nella scatola, candela 15 MIN che CHIUDE SOPRA, STOP dentro, OBIETTIVO = altezza sopra
S4 QUADERNO   T53  VENDITA disegnata a mano: candela che chiude SOTTO, stop dentro, obiettivo = altezza sotto (frecce d'altezza)
S5 NERO-ROSSO T75  TRAPPOLA · la FINTA ROTTURA: candela che esce e rientra, X rossa
S6 TERMINALE  T86  come EVITARLA: ✓ entro solo a candela chiusa fuori · ✕ se rientra non entro
S7 NOTTE      T101 se ti è stata UTILE + 4 paletti (SCATOLA) · outro logo + Telegram
Musica: base cinematica (nuova, per variare)."""
import sys, os, math, json, random
sys.path.insert(0, '/home/user/bot-telegram/contenuti/yardfx_video'); import yardfx as Y; import suoni as S
from PIL import Image, ImageDraw, ImageFilter
D = os.path.dirname(os.path.abspath(__file__))
WORDS = json.load(open(os.path.join(D, 'words.json'))); G = Y.make_groups(WORDS)
T = lambda i: WORDS[i][1]
VEND = WORDS[-1][2]
KEYS = {5, 9, 13, 21, 24, 28, 30, 32, 39, 42, 46, 47, 54, 61, 64, 68, 76, 79, 85, 87, 92, 99}
CUTS = [0, T(10), T(29), T(53), T(75), T(86), T(101), VEND + 0.3]
OUT_LEN = 4.2; DUR = CUTS[-1] + OUT_LEN
TRANS = ['zoom', 'whip', 'blur', 'whip_v', 'wipe', 'zoom']
TD = 0.4; TIKTOK = os.environ.get('TIKTOK') == '1'
EV = []
def ev(t, n, g=1.0): EV.append((round(t, 3), n, g))
SP = Y.sprite
def big(b, s, xy, size, col, font=Y.BIG): ImageDraw.Draw(b).text(xy, s, font=Y.F(font, size), fill=col, anchor='mm')

def glow_rect(img, box, col, w, prog, blur=14):
    """rettangolo luminoso che si disegna lungo il perimetro (prog 0..1)"""
    if prog <= 0: return img
    x0, y0, x1, y1 = box; pts = [(x0, y1), (x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    L = 2 * (x1 - x0 + y1 - y0) * min(1, prog); seg = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        dl = math.dist(a, b)
        if L >= dl: seg.append(b); L -= dl
        else: f = L / dl; seg.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)); break
    m = Image.new('L', (Y.W, Y.H), 0); ImageDraw.Draw(m).line(seg, fill=255, width=w, joint='curve')
    img = Image.composite(Image.new('RGB', (Y.W, Y.H), tuple(int(v * .6) for v in col)), img, m.filter(ImageFilter.GaussianBlur(blur)))
    return Image.composite(Image.new('RGB', (Y.W, Y.H), col), img, m)

def candle(d, x, o, c, h, l, w=26, col=None):
    col = col or ((47, 179, 106) if c <= o else (224, 72, 62))   # coordinate schermo: c<o = sale
    d.line([(x, h), (x, l)], fill=col, width=4); d.rectangle((x - w / 2, min(o, c), x + w / 2, max(o, c) + 2), fill=col)

# ---------- S1 NOTTE: la scatola ----------
BOX1 = (200, 700, 880, 1030)
def s1(t):
    img = Y.night_bg(t); img = Y.light_beams(img, t); img = Y.dust(img, t, 45, 3, Y.GOLD, 40)
    img = Y.spotlight(img, Y.W // 2 + 40 * math.sin(t * 1.1), 90, 1100, 600, 50)
    img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('ogni mattina', 'serif', 104, Y.WHITE)], 330), t, -0.4, 0.4, 'float', 1)
    img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [("l'oro prepara una", 'serif', 84, Y.MUTE)], 450), t, -0.2, 0.4, 'float', 2)
    broken = t > T(9)
    if not broken: img = glow_rect(img, BOX1, Y.GOLD, 10, (t + 0.4) / 1.2)
    else:
        x0, y0, x1, y1 = BOX1; a = Y.ease((t - T(9)) / 0.3)
        img = glow_rect(img, (x0, y0 - 40 * a, x1, y1), Y.GOLD, 10, 1)
        d = ImageDraw.Draw(img); d.rectangle((640 - 60, y0 - 60 * a - 12, 640 + 60, y0 + 12), fill=(10, 14, 28))
        for k in range(6):                                                              # schegge
            ang = -math.pi / 2 + (k - 2.5) * 0.45; r = 160 * a
            d.line([(640 + math.cos(ang) * 30, y0 + math.sin(ang) * 30), (640 + math.cos(ang) * (30 + r), y0 + math.sin(ang) * (30 + r))], fill=Y.GOLD_SOFT, width=5)
    d = ImageDraw.Draw(img); r = random.Random(3)
    for i in range(12):                                                                  # candele di lato dentro la scatola
        if t < 0.1 * i - 0.3: break
        x = 245 + i * 34; m = 865 + 45 * math.sin(i * 1.7 + 0.5) + 6 * math.sin(t * 3 + i); hgt = r.uniform(30, 70)
        candle(d, x, m - hgt / 2 if i % 2 else m + hgt / 2, m + hgt / 2 if i % 2 else m - hgt / 2, m - hgt, m + hgt, 20)
    if t > T(8) - 0.05:
        a = Y.ease((t - T(8) + 0.05) / 0.5); top = 980 - 520 * a
        img = Y.pulse_rings(img, 640, top, t - T(8), Y.GREEN, 1.0, 2, 160, 3)
        d = ImageDraw.Draw(img); candle(d, 690, 980, top + 40, top, 1000, 46, Y.GREEN)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'SCATOLA', (Y.W // 2, 1140), 96, Y.ease((t - T(5)) / 0.35)), t, T(5), enter='stamp', idle='breathe', seed=3, dur=0.3)
    img = SP(img, lambda b: Y.glow_text(b, 'ALLE 9', (Y.W // 2, 1300), 150, Y.GOLD, (130, 90, 20)), t, T(6), enter='pop', idle='breathe', seed=4)
    img = SP(img, lambda b: Y.stamp(b, 'LA ROMPE', (Y.W // 2 - 120, 610), 80, Y.GREEN, -6), t, T(9), enter='stamp', idle='wobble', seed=5, dur=0.25, amp=0.4)
    img = Y.camera(img, t, 0, punches=[T(5), T(7), T(9)], shakes=[T(9)])
    img = Y.color_flash(img, t, [T(5)], Y.GOLD, 0.14, 0.3)
    return Y.color_flash(img, t, [T(9)], Y.GREEN, 0.16, 0.38), True
ev(0, 'boom', 0.6); ev(0.05, 'whoosh', 0.6); ev(0.2, 'riser', 0.3); [ev(0.1 + 0.1 * i, 'tick', 0.3) for i in range(8)]
ev(T(5), 'stamp', 0.7); ev(T(6), 'pop'); ev(T(7), 'ding', 0.6); ev(T(8), 'swoosh_up', 0.7); ev(T(9), 'boom'); ev(T(9) + 0.05, 'glitch', 0.5); ev(T(9) + 0.1, 'stamp', 0.6)

# ---------- S2 QUADERNO: cos'è la scatola asiatica ----------
ZZ = [(130, 900), (190, 790), (250, 960), (320, 820), (390, 980), (450, 790), (520, 940), (590, 800), (660, 965), (720, 860)]
def s2(t):
    img = Y.grid_paper()
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('strategia', 'serif', 96, Y.INK), ('BASE', 'big', 110, Y.INK)], 320), t, CUTS[1], enter='drop', idle='float', seed=6)
    for k in range(4):
        if t > T(12) + k * 0.1:
            img = SP(img, lambda b, k=k: Y.gold_candle(b, 390 + k * 60, 370, 500, 400 + k * 6, 465, 36, 1), t, T(12) + k * 0.1, enter='drop', idle='float', seed=40 + k)
    img = SP(img, lambda b: big(b, '#4', (680, 440), 120, Y.GOLDK), t, T(13), enter='spin', idle='breathe', seed=7)
    d = ImageDraw.Draw(img)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('di', 'serif', 70, Y.MUTE), ('NOTTE', 'big', 84, (40, 60, 120))], 640, cx=300), t, T(14), enter='left', idle='float', seed=8)
    d = ImageDraw.Draw(img)
    if t > T(14): Y.stroke(d, ZZ, Y.ease((t - T(14)) / 2.0), Y.INK, 7, seed=21, amp=2.5)
    if t > T(16):
        Y.stroke(d, [(130, 1080), (720, 1080)], Y.ease((t - T(16)) / 1.2), Y.MUTE, 4, seed=22)
        for x, lab, t0 in [(130, '01:00', T(16)), (720, '08:00', T(18))]:
            if t > t0:
                a = Y.ease((t - t0) / 0.3); d.ellipse((x - 9 * a, 1071, x + 9 * a, 1089), fill=Y.INK)
                d.text((x, 1130), lab, font=Y.F(Y.MONO, 44), fill=Y.INK, anchor='mm')
    if t > T(21):
        Y.stroke(d, [(110, 785), (960, 785)], Y.ease((t - T(21)) / 0.5), Y.GREEN_K, 6, seed=23)
        Y.tag_pointer(d, 'MASSIMO', (450, 790), (880, 720), (t - T(21)) / 0.4, Y.GREEN_K, Y.WHITE, 40)
    if t > T(24):
        Y.stroke(d, [(110, 985), (960, 985)], Y.ease((t - T(24)) / 0.5), Y.RED, 6, seed=24)
        Y.tag_pointer(d, 'MINIMO', (390, 980), (880, 1050), (t - T(24)) / 0.4, Y.RED, Y.WHITE, 40)
    if t > T(27):
        a = Y.ease((t - T(27)) / 0.4); lay = Image.new('RGBA', (Y.W, Y.H), (0, 0, 0, 0))
        ImageDraw.Draw(lay).rectangle((110, 785, 760, 985), fill=Y.GOLD + (int(70 * a),)); img.paste(lay, (0, 0), lay)
    img = SP(img, lambda b: Y.stamp(b, 'SCATOLA ASIATICA', (Y.W // 2, 1300), 84, Y.GOLDK, -4), t, T(27), enter='stamp', idle='wobble', seed=9, dur=0.3, amp=0.4)
    img = Y.camera(img, t, CUTS[1], punches=[T(13), T(21), T(24), T(27)], shakes=[T(27)], push=0.04)
    return Y.color_flash(img, t, [T(27)], Y.GOLD, 0.12, 0.25), False
ev(CUTS[1], 'swoosh_up', 0.6); ev(CUTS[1] + 0.05, 'pop'); [ev(T(12) + k * 0.1, 'pop_hi', 0.45) for k in range(4)]; ev(T(13), 'ding', 0.6)
ev(T(14), 'swipe', 0.5); ev(T(14) + 0.1, 'riser', 0.25); ev(T(16), 'click'); ev(T(18), 'click'); ev(T(21), 'pop'); ev(T(21) + 0.1, 'swipe', 0.4); ev(T(24), 'pop'); ev(T(24) + 0.1, 'swipe', 0.4); ev(T(27), 'stamp')

# ---------- dati didattici: scatola 3.980-4.010, rottura in su ----------
LO_B, HI_B = 3980.0, 4010.0; H_B = HI_B - LO_B
def _cs():
    r = random.Random(5); cs = []; p = 3995
    for i in range(20):
        o = p; c = min(HI_B - 2, max(LO_B + 2, 3995 + 12 * math.sin(i * 1.3) + r.uniform(-5, 5)))
        cs.append({'o': o, 'c': c, 'h': min(HI_B - .5, max(o, c) + r.uniform(1, 4)), 'l': max(LO_B + .5, min(o, c) - r.uniform(1, 4))}); p = c
    bi = len(cs); cs.append({'o': p, 'c': HI_B + 4, 'h': HI_B + 6, 'l': p - 2}); p = HI_B + 4
    for v in [4018, 4016, 4025, 4031, 4029, 4037, 4042]:
        o = p; cs.append({'o': o, 'c': v, 'h': max(o, v) + r.uniform(1, 3), 'l': min(o, v) - r.uniform(1, 3)}); p = v
    return cs, bi
CS, BI = _cs(); ENTRY = CS[BI]['c']; STOP = LO_B + H_B / 2; TP = HI_B + H_B
LO, HI = 3965, 4050
def s3(t):
    img = Y.term_bg(); img = Y.light_sweep(img, t + 1.5, 3.4, 200, 30); img = Y.dust(img, t, 25, 11, Y.ICE, 30)
    img = SP(img, lambda b: Y.hand(ImageDraw.Draw(b), 'esempio didattico', (Y.W // 2, 300), 76, Y.GOLD, Y.ease((t - T(29)) / 0.6)), t, T(29), enter='none', idle='float', seed=10)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'PER COMPRARE', (Y.W // 2, 420), 76, Y.ease((t - T(31)) / 0.35), Y.GREEN), t, T(31), enter='pop', idle='breathe', seed=11)
    x0, x1, y0, y1 = 110, 990, 540, 1300
    py = lambda p: y1 - (p - LO) / (HI - LO) * (y1 - y0); step = (x1 - x0) / len(CS); px = lambda i: x0 + (i + .5) * step
    d = ImageDraw.Draw(img); d.rounded_rectangle((x0 - 30, y0 - 40, x1 + 30, y1 + 30), radius=22, fill=Y.CARD, outline=Y.CARD_LINE, width=2)
    lay = Image.new('RGBA', (Y.W, Y.H), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    ld.rectangle((x0, py(HI_B), px(BI) - step / 2, py(LO_B)), fill=Y.GOLD + (40,), outline=Y.GOLD + (200,), width=3)
    xe = px(BI)
    if t > T(42): ld.rectangle((xe, py(ENTRY), xe + (x1 - xe) * Y.ease((t - T(42)) / 0.4), py(STOP)), fill=Y.RED + (60,))
    if t > T(46): ld.rectangle((xe, py(TP), xe + (x1 - xe) * Y.ease((t - T(46)) / 0.4), py(ENTRY)), fill=Y.GREEN + (45,))
    img.paste(lay, (0, 0), lay); d = ImageDraw.Draw(img)
    if t < T(34): k = int(2 + (BI - 2) * Y.ease((t - CUTS[2]) / (T(34) - CUTS[2])))
    elif t < T(50): k = BI + 1
    else: k = int(BI + 1 + (len(CS) - BI - 1) * Y.ease((t - T(50)) / 1.6))
    for i, c in enumerate(CS[:k]):
        x = px(i); col = (47, 179, 106) if c['c'] >= c['o'] else (224, 72, 62)
        if i == BI and t < T(38): ce = c['o'] + (c['c'] - c['o']) * Y.ease((t - T(34)) / 1.2); hh = max(c['o'], ce) + 1
        else: ce, hh = c['c'], c['h']
        d.line([(x, py(hh)), (x, py(c['l']))], fill=col, width=4 if i == BI else 3)
        ya, yb = sorted([py(c['o']), py(ce)]); d.rectangle((x - step * .32, ya, x + step * .32, max(yb, ya + 3)), fill=col)
    def hl(p, col, lab, t0):
        a = Y.ease((t - t0) / 0.4)
        if a <= 0: return
        y = py(p); xe2 = xe + (x1 - xe) * a
        for xx in range(int(xe), int(xe2), 22): d.line([(xx, y), (min(xx + 12, xe2), y)], fill=col, width=4)
        if a >= 1:
            f = Y.F(Y.COND, 38); tw = d.textlength(lab, font=f); d.rounded_rectangle((x1 - tw - 26, y - 25, x1, y + 25), radius=9, fill=col); d.text((x1 - 13, y), lab, font=f, fill=Y.DARK, anchor='rm')
    hl(STOP, Y.RED, 'STOP', T(42)); hl(TP, Y.GREEN, 'OBIETTIVO', T(46))
    if t > T(36): Y.tag_pointer(d, '15 MIN', (xe + 12, py(ENTRY) - 10), (xe - 170, py(ENTRY) - 170), (t - T(36)) / 0.4, Y.GOLD, Y.DARK, 38)
    if t > T(39): Y.tag_pointer(d, 'CHIUDE SOPRA', (xe, py(HI_B)), (xe - 230, py(HI_B) + 170), (t - T(39)) / 0.4, Y.GREEN, Y.DARK, 38)
    if t > T(47):                                                           # altezza della scatola copiata sopra
        a = Y.ease((t - T(47)) / 0.5); xa = x0 + 40
        for (ya, yb) in [(py(LO_B), py(HI_B)), (py(HI_B), py(HI_B) - (py(HI_B) - py(TP)) * a)]:
            d.line([(xa, ya), (xa, yb)], fill=Y.GOLD, width=5); d.polygon([(xa, yb), (xa - 12, yb + 20 * (1 if yb < ya else -1)), (xa + 12, yb + 20 * (1 if yb < ya else -1))], fill=Y.GOLD)
        if a >= 1: d.text((xa + 26, (py(HI_B) + py(TP)) / 2), "l'altezza", font=Y.F(Y.HAND if hasattr(Y, 'HAND') else Y.SERIF, 46), fill=Y.GOLD, anchor='lm')
    if t > T(34): img = Y.pulse_rings(img, xe, py(ENTRY), t - T(34), Y.GREEN, 1.1, 2, 110, 3)
    img = Y.camera(img, t, CUTS[2], punches=[T(32), T(38), T(42), T(46), T(50)], shakes=[T(39)], push=0.04)
    img = Y.color_flash(img, t, [T(39)], Y.GREEN, 0.14, 0.28); return Y.color_flash(img, t, [T(42)], Y.RED, 0.12, 0.22), True
ev(CUTS[2], 'swipe'); ev(CUTS[2] + 0.1, 'click'); [ev(CUTS[2] + 0.2 + k * 0.1, 'tick', 0.3) for k in range(12)]; ev(T(31), 'pop_hi'); ev(T(34), 'riser', 0.35)
ev(T(36), 'click', 0.7); ev(T(38), 'boom', 0.5); ev(T(39), 'ding'); ev(T(42), 'alert', 0.6); ev(T(46), 'pop_hi'); ev(T(47), 'swoosh_up', 0.5); [ev(T(50) + k * 0.2, 'tick', 0.35) for k in range(7)]; ev(T(52), 'coin', 0.8)

# ---------- S4 QUADERNO: la vendita disegnata a mano ----------
BX = (150, 640, 930, 860)
def s4(t):
    img = Y.grid_paper(); d = ImageDraw.Draw(img)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('per', 'serif', 90, Y.INK), ('VENDERE', 'big', 120, Y.RED)], 330), t, T(53), enter='drop', idle='float', seed=12)
    d = ImageDraw.Draw(img); a = Y.ease((t - CUTS[3]) / 0.8)
    x0, y0, x1, y1 = BX
    Y.stroke(d, [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)], a, Y.GOLDK, 6, seed=30, amp=2)
    for i in range(10):
        if a > i / 10:
            x = x0 + 50 + i * 60; m = 750 + 55 * math.sin(i * 1.5); hgt = 34
            candle(d, x, m - hgt if i % 2 else m + hgt, m + hgt if i % 2 else m - hgt, m - hgt - 12, m + hgt + 12, 26)
    xb = x1 - 60
    if t > T(55):
        p = Y.ease((t - T(55)) / 1.0); bot = 820 + (1000 - 820) * p
        candle(d, xb, 820, bot, 800, bot + 20, 40, Y.RED)
    if t > T(60): Y.tag_pointer(d, 'CHIUDE SOTTO', (xb, y1), (560, 1010), (t - T(60)) / 0.4, Y.RED, Y.WHITE, 40)
    if t > T(64):
        ys = (y0 + y1) / 2; Y.stroke(d, [(xb - 80, ys), (x1 + 40, ys)], Y.ease((t - T(64)) / 0.4), Y.RED, 6, seed=31)
        if t > T(64) + 0.3: d.text((x1 + 20, ys - 40), 'STOP', font=Y.F(Y.BIG, 52), fill=Y.RED, anchor='rm')
    if t > T(68):
        h = y1 - y0; a2 = Y.ease((t - T(68)) / 0.6); xa = x0 - 50
        Y.dashed_arrow(d, xa, y0, xa, y1, 1, Y.GOLDK)
        Y.dashed_arrow(d, xa, y1, xa, y1 + h * a2, 1 if a2 >= 1 else a2, Y.GREEN_K)
        if a2 >= 1:
            Y.stroke(d, [(x0, y1 + h), (x1 + 40, y1 + h)], Y.ease((t - T(68) - 0.6) / 0.4), Y.GREEN_K, 6, seed=32)
            d.text((x1 + 30, y1 + h + 50), 'OBIETTIVO', font=Y.F(Y.BIG, 52), fill=Y.GREEN_K, anchor='rm')
    if t > T(69): Y.hand(d, "l'altezza", (x0 + 120, (y1 + y1 + (y1 - y0)) / 2 + 10), 56, Y.GOLDK, Y.ease((t - T(69)) / 0.5))
    img = Y.camera(img, t, CUTS[3], punches=[T(54), T(61), T(64), T(68)], shakes=[T(61)], push=0.04)
    img = Y.color_flash(img, t, [T(54), T(61)], Y.RED, 0.12, 0.22); return img, False
ev(CUTS[3], 'whoosh', 0.7); ev(T(53), 'swoosh_up', 0.6); ev(T(54), 'pop'); [ev(CUTS[3] + 0.08 * i, 'tick', 0.3) for i in range(10)]
ev(T(55), 'riser', 0.3); ev(T(60), 'click', 0.7); ev(T(61), 'boom', 0.5); ev(T(64), 'alert', 0.5); ev(T(68), 'swipe', 0.5); ev(T(69), 'bubble', 0.6); ev(T(72), 'pop_hi', 0.6)

# ---------- S5 NERO-ROSSO: la trappola ----------
def s5(t):
    img = Y.red_silhouette_bg(t)
    img = SP(img, lambda b: Y.stamp(b, 'TRAPPOLA', (Y.W // 2, 330), 120, Y.RED, -5), t, T(76), enter='stamp', idle='wobble', seed=13, dur=0.3, amp=0.4)
    img = Y.letter_rise(img, 'LA FINTA ROTTURA', (Y.W // 2, 520), 100, Y.WHITE, t, T(77))
    img = glow_rect(img, (200, 760, 880, 1080), Y.GOLD, 8, (t - CUTS[4]) / 0.6)
    d = ImageDraw.Draw(img)
    if t > T(81):
        out = Y.ease((t - T(81)) / 0.7) * (1 - Y.ease((t - T(85)) / 0.5)); top = 900 - 330 * out
        col = Y.GREEN if t < T(85) else Y.RED
        candle(d, 640, 960, top + 30, top, 1000, 46, col)
    if t > T(85) + 0.3:
        img = Y.pulse_rings(img, 640, 900, t - T(85), Y.RED, 1.0, 2, 220, 4); d = ImageDraw.Draw(img)
        Y.icon(d, 'croce', 640, 640, 170, Y.ease((t - T(85) - 0.3) / 0.3), Y.RED, 14, 7)
    for txt, t0, y in [('ESCE', T(82), 1190), ('E RIENTRA', T(85), 1330)]:
        img = SP(img, lambda b, txt=txt, y=y: big(b, txt, (Y.W // 2, y), 100, Y.GREEN if txt == 'ESCE' else Y.RED), t, t0, enter='pop', idle='wobble', seed=14 + y, amp=0.5)
    img = Y.camera(img, t, CUTS[4], punches=[T(76), T(79), T(82), T(85)], shakes=[T(76), T(85) + 0.3])
    return Y.color_flash(img, t, [T(76), T(85) + 0.3], Y.RED, 0.16, 0.32), True
ev(CUTS[4], 'boom', 0.6); ev(T(76), 'stamp'); ev(T(76) + 0.05, 'glitch', 0.5); ev(T(77), 'swoosh_up', 0.5); [ev(T(77) + 0.035 * i, 'tick', 0.25) for i in range(0, 16, 2)]
ev(T(81), 'riser', 0.35); ev(T(82), 'pop_hi'); ev(T(85), 'swipe', 0.6); ev(T(85) + 0.3, 'alert', 0.7); ev(T(85) + 0.35, 'boom', 0.5)

# ---------- S6 TERMINALE: come evitarla ----------
def rule(b, y, parts, ok, t0, t):
    d = ImageDraw.Draw(b); col = Y.GREEN if ok else Y.RED
    d.rounded_rectangle((70, y - 90, 1010, y + 90), radius=26, fill=Y.CARD, outline=col, width=4)
    Y.mixed_title(d, parts, y + 26, cx=600)
    a = Y.ease((t - t0) / 0.35)
    if a > 0: Y.icon(d, 'spunta' if ok else 'croce', 150, y, 90, a, col, 10, 3)
def s6(t):
    img = Y.term_bg(); img = Y.light_sweep(img, t, 3.2, 200, 35); img = Y.dust(img, t, 30, 7, Y.ICE, 30)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('come', 'serif', 96, Y.MUTE), ('EVITARLA', 'big', 130, Y.GOLD)], 340), t, T(86), enter='drop', idle='float', seed=20)
    img = SP(img, lambda b: rule(b, 640, [('entro solo a', 'serif', 66, Y.WHITE), ('CANDELA CHIUSA', 'big', 76, Y.GREEN)], True, T(92), t), t, T(88), enter='left', idle='float', seed=21, amp=0.5)
    img = SP(img, lambda b: big(b, 'FUORI', (600, 790), 90, Y.GREEN), t, T(93), enter='pop', idle='wobble', seed=22, amp=0.5)
    img = SP(img, lambda b: rule(b, 1060, [('se', 'serif', 66, Y.WHITE), ('RIENTRA', 'big', 80, Y.RED)], False, T(99), t), t, T(94), enter='right', idle='float', seed=23, amp=0.5)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'NON ENTRO', (600, 1250), 80, Y.ease((t - T(99)) / 0.35), Y.RED, Y.WHITE), t, T(99), enter='stamp', idle='breathe', seed=24, dur=0.3)
    if t > T(92): img = Y.pulse_rings(img, 150, 640, t - T(92), Y.GREEN, 1.2, 2, 150)
    img = Y.camera(img, t, CUTS[5], punches=[T(87), T(92), T(98), T(99)], shakes=[T(99)])
    img = Y.color_flash(img, t, [T(92)], Y.GREEN, 0.14, 0.28); return Y.color_flash(img, t, [T(99)], Y.RED, 0.14, 0.28), True
ev(CUTS[5], 'swipe'); ev(T(86), 'pop'); ev(T(87), 'swoosh_up', 0.6); ev(T(88), 'swipe', 0.6); ev(T(92), 'ding'); ev(T(93), 'pop_hi'); ev(T(94), 'swipe', 0.6); ev(T(98), 'click', 0.6); ev(T(99), 'stamp'); ev(T(99) + 0.05, 'alert', 0.4)

# ---------- S7 CTA ----------
CTA_T = [T(106), T(109), T(111), T(114)]
def s7(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 50, 17, Y.GOLD, 55)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('se ti è stata', 'serif', 90, Y.WHITE), ('UTILE', 'big', 110, Y.GOLD)], 420), t, CUTS[6], enter='drop', idle='float', seed=33)
    img = Y.cta_four(img, t, CTA_T, 'SCATOLA', y0=640)
    return Y.camera(img, t, CUTS[6], punches=CTA_T, push=0.03), True
ev(CUTS[6], 'swoosh_up'); ev(T(105), 'pop'); ev(CTA_T[0], 'pop'); ev(CTA_T[1], 'pop_hi'); ev(CTA_T[1] + 0.05, 'bubble', 0.6); ev(CTA_T[2], 'bubble'); ev(T(112), 'pop', 0.5); ev(CTA_T[3], 'swoosh_up'); ev(CTA_T[3] + 0.1, 'coin')

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
NAME = 'yardfx_strategia4_scatola'
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
        S.music_cinematic(os.path.join(D, 'base.wav'), DUR)
        a = S.mix(os.path.join(D, 'audio.m4a'), DUR, voce=os.path.join(D, 'voce.mp3'), musica=os.path.join(D, 'base.wav'), eventi=EV, music_db=-16)
        for tag in ['ig', 'tt']:
            lst = os.path.join(D, f'list_{tag}.txt'); open(lst, 'w').write(f"file 'main.mp4'\nfile 'outro_{tag}.mp4'\n")
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-i', a, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'copy', '-shortest', '-movflags', '+faststart',
                            os.path.join(D, f'{NAME}_{"instagram" if tag == "ig" else "tiktok"}.mp4')], check=True)
        print('ok', DUR, len(EV))
