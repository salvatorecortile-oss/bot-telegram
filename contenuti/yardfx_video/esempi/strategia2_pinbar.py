"""Strategia base #2: supporto/resistenza + pin bar — voce Enea, pubblicato il 17/11/2026.
S1 NOTTE    T0   STRATEGIA BASE #2 · il prezzo ti dice DOVE ENTRARE · una CANDELA d'oro sotto il faretto
S2 QUADERNO T16  linea del prezzo disegnata a mano che rimbalza: SUPPORTO (pavimento) e RESISTENZA (soffitto)
S3 NOTTE    T41  PIN BAR gigante luminosa · CODA LUNGA cerchiata · timbro RESPINTO
S4 TERMINALE T60 ESEMPIO DIDATTICO: grafico con supporto/resistenza, pin bar cerchiata, ACQUISTO, STOP LOSS, OBIETTIVO
S5 QUADERNO T83  timbro TRAPPOLA · candela che si forma: sembra pin bar, poi chiude e rompe il supporto · ALLA CHIUSURA
S6 NOTTE    T99  se ti è stata UTILE + 4 paletti (CANDELA) · outro logo + Telegram"""
import sys, os, math, json, random
sys.path.insert(0, '/home/user/bot-telegram/contenuti/yardfx_video'); import yardfx as Y; import suoni as S
from PIL import Image, ImageDraw
D = os.path.dirname(os.path.abspath(__file__))
WORDS = json.load(open(os.path.join(D, 'words.json'))); G = Y.make_groups(WORDS)
T = lambda i: WORDS[i][1]
VEND = WORDS[-1][2]
KEYS = {3, 9, 15, 17, 32, 43, 50, 57, 61, 66, 71, 74, 76, 80, 84, 90, 98}
CUTS = [0, T(16), T(41), T(60), T(83), T(99), VEND + 0.3]
OUT_LEN = 4.2; DUR = CUTS[-1] + OUT_LEN
TRANS = ['whip_v', 'zoom', 'wipe', 'blur', 'whip']
TD = 0.4; TIKTOK = os.environ.get('TIKTOK') == '1'
EV = []
def ev(t, n, g=1.0): EV.append((round(t, 3), n, g))
SP = Y.sprite
def big(b, s, xy, size, col, font=Y.BIG): ImageDraw.Draw(b).text(xy, s, font=Y.F(font, size), fill=col, anchor='mm')

# ---- candele didattiche: laterale tra supporto 4.000 e resistenza 4.060, pin bar sul supporto, salita fino alla resistenza
SUP, RES = 4000.0, 4060.0
def build():
    r = random.Random(7); cs = []; p = 4040.0
    def c(o, h, l, cl): cs.append({'o': o, 'h': h, 'l': l, 'c': cl, 'g': cl >= o})
    path = [4048, 4056, 4059, 4052, 4044, 4036, 4027, 4016, 4006, 4003, 4012, 4022, 4033, 4045, 4054, 4058, 4050, 4041, 4030, 4021, 4012, 4005]
    for v in path:
        o = p; cl = v + r.uniform(-1.5, 1.5); h = max(o, cl) + r.uniform(0.8, 3); l = min(o, cl) - r.uniform(0.8, 3)
        h = min(h, RES + 1.5); l = max(l, SUP - 1.5); c(o, h, l, cl); p = cl
    pi = len(cs); c(p, p + 2.2, SUP - 12, p + 5.5); p = p + 5.5          # pin bar: coda lunga sotto il supporto, chiusura sopra
    for v in [4019, 4028, 4035, 4044, 4052, 4061]:
        o = p; cl = v + r.uniform(-1, 1); h = max(o, cl) + r.uniform(0.8, 2.5); l = min(o, cl) - r.uniform(0.8, 2.5); c(o, h, l, cl); p = cl
    return cs, pi
CS, PI = build()
ENTRY = CS[PI]['c']; STOP = CS[PI]['l'] - 2.0; TP = RES

def s1(t):
    img = Y.night_bg(t); img = Y.light_beams(img, t); img = Y.dust(img, t, 45, 3, Y.GOLD, 40)
    img = Y.spotlight(img, Y.W // 2 + 40 * math.sin(t * 1.2), 100, 1120, 520, 55)
    img = Y.blur_in(img, lambda b: big(b, 'STRATEGIA BASE', (Y.W // 2, 380), 130, Y.WHITE), t, -0.4, 0.45, 'float', 1)
    img = SP(img, lambda b: Y.glow_text(b, '#2', (Y.W // 2, 550), 190, Y.GOLD, (130, 90, 20)), t, T(2), enter='spin', idle='breathe', seed=2)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('il prezzo ti dice', 'serif', 84, Y.WHITE)], 760), t, T(5), enter='rise', idle='float', seed=3)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'DOVE ENTRARE', (Y.W // 2, 860), 90, 1), t, T(8), enter='stamp', idle='breathe', seed=4, dur=0.3)
    if t > T(15) - 0.1:
        img = Y.pulse_rings(img, Y.W // 2, 1180, t - T(15), Y.GOLD, 1.3, 3, 380)
        img = SP(img, lambda b: Y.gold_candle(b, Y.W // 2, 1040, 1380, 1100, 1180, 110, 1), t, T(15) - 0.1, enter='drop', idle='float', seed=5)
    img = Y.camera(img, t, 0, punches=[T(2), T(9), T(15)], shakes=[T(15)])
    return Y.color_flash(img, t, [T(15)], Y.GOLD, 0.16, 0.35), True
ev(0, 'boom', 0.7); ev(0.05, 'whoosh', 0.6); ev(T(2), 'swoosh_up'); ev(T(2) + 0.1, 'pop_hi'); ev(T(5), 'click'); ev(T(8), 'stamp', 0.7); ev(T(15) - 0.1, 'boom', 0.7); ev(T(15), 'ding', 0.6)

ZIG = [(90, 1010), (230, 760), (370, 1080), (520, 720), (660, 1085), (800, 740), (990, 1060)]
def s2(t):
    img = Y.grid_paper(); d = ImageDraw.Draw(img)
    a = Y.ease((t - CUTS[1]) / 3.0); Y.stroke(d, ZIG, a, Y.INK, 7, seed=21, amp=3)
    if t > T(17):
        Y.stroke(d, [(70, 1095), (1010, 1085)], Y.ease((t - T(17)) / 0.5), Y.GREEN_K, 9, seed=22)
        img = SP(img, lambda b: ImageDraw.Draw(b).text((Y.W // 2, 1180), 'SUPPORTO', font=Y.F(Y.BIG, 100), fill=Y.GREEN_K, anchor='mm'), t, T(17), enter='rise', idle='float', seed=23)
        d = ImageDraw.Draw(img)
        for x in (370, 660):
            if t > T(30): Y.arrow(d, x, 1060, x + 40, 960, Y.ease((t - T(30)) / 0.4), Y.GREEN_K, 6, x)
    if t > T(32):
        Y.stroke(ImageDraw.Draw(img), [(70, 705), (1010, 715)], Y.ease((t - T(32)) / 0.5), Y.RED, 9, seed=24)
        img = SP(img, lambda b: ImageDraw.Draw(b).text((Y.W // 2, 610), 'RESISTENZA', font=Y.F(Y.BIG, 100), fill=Y.RED, anchor='mm'), t, T(32), enter='drop', idle='float', seed=25)
        d = ImageDraw.Draw(img)
        for x in (520, 800):
            if t > T(40): Y.arrow(d, x, 740, x + 40, 840, Y.ease((t - T(40)) / 0.4), Y.RED, 6, x)
    img = SP(img, lambda b: Y.serif_heading(ImageDraw.Draw(b), 'il', 'PREZZO', 330), t, T(23), enter='left', idle='float', seed=26, amp=0.5)
    img = Y.camera(img, t, CUTS[1], punches=[T(17), T(32)], shakes=[], push=0.04)
    img = Y.color_flash(img, t, [T(17)], Y.GREEN, 0.15, 0.25); return Y.color_flash(img, t, [T(32)], Y.RED, 0.15, 0.25), False
ev(CUTS[1], 'swipe'); ev(CUTS[1] + 0.1, 'riser', 0.3); ev(T(17), 'pop'); ev(T(17) + 0.05, 'swipe', 0.5); ev(T(23), 'click'); ev(T(30), 'bubble'); ev(T(32), 'pop'); ev(T(32) + 0.05, 'swipe', 0.5); ev(T(40), 'bubble')

def pin_draw(b, t, cx=Y.W // 2):
    d = ImageDraw.Draw(b)
    a = Y.ease((t - T(42)) / 0.6); top, bt, bb, low = 560, 600, 720, 1260
    d.line([(cx, top), (cx, bb + (low - bb) * a)], fill=Y.GREEN, width=16)
    d.rounded_rectangle((cx - 90, bt, cx + 90, bb), radius=14, fill=Y.GREEN)
def s3(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 40, 13, Y.GOLD, 45)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('la', 'serif', 100, Y.WHITE), ('PIN BAR', 'big', 140, Y.GOLD)], 380), t, CUTS[2], enter='drop', idle='float', seed=27)
    img = SP(img, lambda b: pin_draw(b, t), t, T(42), enter='pop', idle='float', seed=28, amp=0.5, anchor=(Y.W // 2, 700))
    if t > T(49):
        img = SP(img, lambda b: Y.circle(ImageDraw.Draw(b), Y.W // 2, 1000, 120, 300, Y.ease((t - T(49)) / 0.5), Y.GOLD, 8, 29), t, T(49), enter='none', idle='wobble', amp=0.5)
        img = SP(img, lambda b: Y.hand(ImageDraw.Draw(b), 'coda lunga', (Y.W // 2 + 290, 1000), 76, Y.GOLD, Y.ease((t - T(49)) / 0.5)), t, T(49), enter='none', idle='float', seed=30)
    if t > T(55): Y.stroke(ImageDraw.Draw(img), [(150, 1220), (930, 1220)], Y.ease((t - T(55)) / 0.4), Y.WHITE, 6, seed=31)
    img = SP(img, lambda b: Y.stamp(b, 'RESPINTO', (Y.W // 2, 1390), 110, Y.GREEN, -5), t, T(57), enter='stamp', idle='wobble', seed=32, dur=0.3, amp=0.4)
    img = Y.camera(img, t, CUTS[2], punches=[T(42), T(50), T(57)], shakes=[T(57)])
    return Y.color_flash(img, t, [T(57)], Y.GREEN, 0.15, 0.3), True
ev(CUTS[2], 'whoosh', 0.7); ev(T(42), 'pop_hi'); ev(T(42) + 0.1, 'swoosh_up', 0.5); ev(T(49), 'swipe', 0.6); ev(T(55), 'click'); ev(T(57), 'stamp'); ev(T(57) + 0.05, 'boom', 0.5)

LO, HI = SUP - 25, RES + 15
def chart(b, t):
    d = ImageDraw.Draw(b); x0, x1, y0, y1 = 110, 990, 520, 1260
    d.rounded_rectangle((x0 - 30, y0 - 50, x1 + 30, y1 + 30), radius=22, fill=Y.CARD, outline=Y.CARD_LINE, width=2)
    py = lambda p: y1 - (p - LO) / (HI - LO) * (y1 - y0); step = (x1 - x0) / len(CS)
    if t < T(70): k = int(3 + (PI - 3) * Y.ease((t - CUTS[3]) / (T(70) - CUTS[3])))
    elif t < T(80) + 0.4: k = PI + 1
    else: k = int(PI + 1 + (len(CS) - PI - 1) * Y.ease((t - T(80) - 0.4) / 1.4))
    for p, lab, col in [(SUP, 'SUPPORTO', Y.GREEN), (RES, 'RESISTENZA', Y.RED)]:
        y = py(p)
        for xx in range(x0, x1, 24): d.line([(xx, y), (xx + 12, y)], fill=col, width=3)
    lay = Image.new('RGBA', b.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(lay); xe = x0 + (PI + 0.5) * step
    if t > T(75): ld.rectangle((xe, py(ENTRY), xe + (x1 - xe) * Y.ease((t - T(75)) / 0.4), py(STOP)), fill=Y.RED + (55,))
    if t > T(80): ld.rectangle((xe, py(TP), xe + (x1 - xe) * Y.ease((t - T(80)) / 0.4), py(ENTRY)), fill=Y.GREEN + (45,))
    b.paste(lay, (0, 0), lay); d = ImageDraw.Draw(b)
    for i, c in enumerate(CS[:k]):
        x = x0 + (i + 0.5) * step; col = (47, 179, 106) if c['g'] else (224, 72, 62)
        w = 4 if i == PI else 3
        d.line([(x, py(c['h'])), (x, py(c['l']))], fill=col, width=w); ya, yb = sorted([py(c['o']), py(c['c'])]); d.rectangle((x - step * .32, ya, x + step * .32, max(yb, ya + 3)), fill=col)
    def hl(p, col, lab, t0):
        a = Y.ease((t - t0) / 0.4)
        if a <= 0: return
        y = py(p); xe2 = xe + (x1 - xe) * a
        for xx in range(int(xe), int(xe2), 22): d.line([(xx, y), (min(xx + 12, xe2), y)], fill=col, width=4)
        if a >= 1:
            f = Y.F(Y.COND, 38); tw = d.textlength(lab, font=f); d.rounded_rectangle((x1 - tw - 26, y - 25, x1, y + 25), radius=9, fill=col); d.text((x1 - 13, y), lab, font=f, fill=Y.DARK, anchor='rm')
    hl(ENTRY, Y.GOLD, 'ACQUISTO', T(74)); hl(STOP, Y.RED, 'STOP LOSS', T(75)); hl(TP, Y.GREEN, 'OBIETTIVO', T(80))
    for p, lab, col, t0 in [(SUP, 'SUPPORTO', Y.GREEN, T(66)), (RES, 'RESISTENZA', Y.RED, T(82))]:
        if t > t0: d.text((x0 + 10, py(p) + (34 if p == SUP else -34)), lab, font=Y.F(Y.COND, 40), fill=col, anchor='lm')
    return py, step, x0
def s4(t):
    img = Y.term_bg(); img = Y.light_sweep(img, t + 1.5, 3.4, 200, 30); img = Y.dust(img, t, 25, 11, Y.ICE, 30)
    img = SP(img, lambda b: Y.hand(ImageDraw.Draw(b), 'esempio didattico', (Y.W // 2, 380), 80, Y.GOLD, Y.ease((t - CUTS[3]) / 0.6)), t, CUTS[3], enter='none', idle='float', seed=33)
    holder = {}
    def dr(b): holder['g'] = chart(b, t)
    img = SP(img, dr, t, CUTS[3], enter='rise', idle='float', seed=34, amp=0.25)
    if 'g' not in holder: return Y.camera(img, t, CUTS[3]), True
    py, step, x0 = holder['g']; xe = x0 + (PI + 0.5) * step
    if t > T(70): img = Y.pulse_rings(img, xe, py(SUP), t - T(70), Y.GOLD, 1.0, 2, 120, 3)
    if t > T(70): img = SP(img, lambda b: Y.circle(ImageDraw.Draw(b), xe, (py(CS[PI]['h']) + py(CS[PI]['l'])) / 2, 45, 110, Y.ease((t - T(70)) / 0.4), Y.GOLD, 6, 35), t, T(70), enter='none', idle='wobble', amp=0.5)
    if t > T(72): img = SP(img, lambda b: Y.arrow(ImageDraw.Draw(b), xe - 170, py(ENTRY) - 220, xe - 15, py(ENTRY) - 15, Y.ease((t - T(72)) / 0.35), Y.WHITE, 7, 36), t, T(72), enter='none', idle='wobble', amp=0.4)
    img = Y.camera(img, t, CUTS[3], punches=[T(66), T(71), T(74), T(80)], shakes=[T(74)], push=0.04)
    img = Y.color_flash(img, t, [T(74)], Y.GOLD, 0.15, 0.3); return Y.color_flash(img, t, [T(80)], Y.GREEN, 0.15, 0.25), True
ev(CUTS[3], 'swipe'); ev(CUTS[3] + 0.1, 'swoosh_up'); ev(CUTS[3] + 0.2, 'click'); ev(T(66), 'tick'); ev(T(70), 'ding'); ev(T(72), 'swipe', 0.6); ev(T(74), 'coin'); ev(T(75), 'alert', 0.7); ev(T(80), 'pop_hi'); ev(T(82), 'trin', 0.7)
[ev(T(80) + 0.4 + k * 0.2, 'tick', 0.35) for k in range(7)]

def forming(b, t):
    """candela che si forma: prima sembra una pin bar, poi alla chiusura scende e rompe il supporto"""
    d = ImageDraw.Draw(b); cx = Y.W // 2; sy = 1060; o = 60
    d.line([(120, sy), (960, sy)], fill=Y.GREEN_K, width=6); d.text((140, sy + 40), 'supporto', font=Y.F(Y.SERIF, 56), fill=Y.GREEN_K, anchor='lm')
    k = Y.ease((t - T(85)) / 1.4); top = 560 + o
    if t < T(90):
        bt, bb, low = 600 + o, 700 + o, 700 + o + 420 * k                     # sembra una pin bar
        d.line([(cx, top), (cx, low)], fill=Y.GREEN_K, width=12); d.rounded_rectangle((cx - 80, bt, cx + 80, bb), radius=10, fill=Y.GREEN_K)
    else:
        c = Y.ease((t - T(90)) / 0.8); bb = 700 + o + 500 * c          # chiude sotto: candela rossa che rompe il supporto
        d.line([(cx, top), (cx, max(1180, min(1230, bb + 40)))], fill=Y.RED, width=12); d.rounded_rectangle((cx - 80, 600 + o, cx + 80, bb), radius=10, fill=Y.RED)
def s5(t):
    img = Y.grid_paper()
    img = SP(img, lambda b: Y.stamp(b, 'TRAPPOLA', (Y.W // 2, 250), 110, Y.RED, -5), t, T(84), enter='stamp', idle='wobble', seed=37, dur=0.3, amp=0.4)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('entrare', 'serif', 80, Y.INK), ('PRIMA', 'big', 96, Y.RED)], 470), t, T(85), enter='left', idle='float', seed=38)
    if t > T(85): img = SP(img, lambda b: forming(b, t), t, T(85), enter='none', idle='float', seed=39, amp=0.4)
    if t > T(90): img = SP(img, lambda b: Y.icon(ImageDraw.Draw(b), 'croce', Y.W // 2 + 230, 880, 150, Y.ease((t - T(90)) / 0.4), Y.RED, 10, 40), t, T(90), enter='pop', idle='wobble', seed=41)
    img = SP(img, lambda b: Y.hand(ImageDraw.Draw(b), 'la coda si vede davvero solo', (Y.W // 2, 1310), 66, Y.INK, Y.ease((t - T(91)) / 0.8)), t, T(91), enter='none', idle='float', seed=42)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'ALLA CHIUSURA', (Y.W // 2, 1440), 90, 1, Y.GREEN_K, Y.WHITE), t, T(97), enter='stamp', idle='breathe', seed=43, dur=0.3)
    img = Y.camera(img, t, CUTS[4], punches=[T(84), T(90), T(98)], shakes=[T(84), T(90)], push=0.04)
    img = Y.color_flash(img, t, [T(84), T(90)], Y.RED, 0.15, 0.25); return Y.color_flash(img, t, [T(98)], Y.GREEN, 0.15, 0.25), False
ev(CUTS[4], 'glitch', 0.5); ev(T(84), 'stamp'); ev(T(84) + 0.05, 'boom', 0.6); ev(T(85), 'swipe', 0.6); ev(T(85) + 0.2, 'riser', 0.4); ev(T(90), 'whoosh', 0.6); ev(T(90), 'alert', 0.8); ev(T(91), 'click'); ev(T(97), 'stamp', 0.7); ev(T(98), 'ding')

CTA_T = [T(104), T(107), T(109), T(115)]
def s6(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 50, 17, Y.GOLD, 55)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('se ti è stata', 'serif', 90, Y.WHITE), ('UTILE', 'big', 110, Y.GOLD)], 420), t, CUTS[5], enter='drop', idle='float', seed=50)
    img = Y.cta_four(img, t, CTA_T, 'CANDELA', y0=640)
    return Y.camera(img, t, CUTS[5], punches=CTA_T, push=0.03), True
ev(CUTS[5], 'swoosh_up'); ev(CUTS[5] + 0.1, 'pop'); ev(CTA_T[0], 'pop'); ev(CTA_T[1], 'pop_hi'); ev(CTA_T[1] + 0.05, 'bubble', 0.6); ev(CTA_T[2], 'bubble'); ev(CTA_T[3], 'swoosh_up'); ev(CTA_T[3] + 0.1, 'coin')

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
if __name__ == '__main__':
    import subprocess
    m = sys.argv[1]
    if m == 'preview': Y.contact_sheet(frame, [float(x) for x in sys.argv[2:]], os.path.join(D, 'preview.png'), w=180)
    elif m == 'main': enc(os.path.join(D, 'main.mp4'), 0, int(CUTS[6] * Y.FPS))
    elif m == 'outro': enc(os.path.join(D, 'outro_tt.mp4' if TIKTOK else 'outro_ig.mp4'), int(CUTS[6] * Y.FPS), int(DUR * Y.FPS))
    elif m == 'mix':
        S.music(os.path.join(D, 'base.wav'), DUR, 94, 'positivo')
        a = S.mix(os.path.join(D, 'audio.m4a'), DUR, voce=os.path.join(D, 'voce.mp3'), musica=os.path.join(D, 'base.wav'), eventi=EV, music_db=-17)
        for tag in ['ig', 'tt']:
            lst = os.path.join(D, f'list_{tag}.txt'); open(lst, 'w').write(f"file 'main.mp4'\nfile 'outro_{tag}.mp4'\n")
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-i', a, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'copy', '-shortest', '-movflags', '+faststart',
                            os.path.join(D, f'yardfx_strategia2_pinbar_{"instagram" if tag == "ig" else "tiktok"}.mp4')], check=True)
        print('ok', DUR, len(EV))
