"""News 25 novembre 2026: PIL e PCE alle 14:30 (doppio dato sull'oro), pubblicata mercoledì 25/11 — voce Salvatore (Speechify, atempo 1.08).
Ricetta NEWS: Notte -> Terminale -> Quaderno -> Terminale. Ogni scena parte sulla prima parola del suo paragrafo.
S1 NOTTE (raggi oro)  T0   DUE DATI · alla stessa ORA · timbro VOLATILITÀ GARANTITA
S2 NOTTE (faretto)    T7   OGGI alle · 14:30 gigante · «ora italiana» a mano · INFLAZIONE PCE + PIL americano
S3 TERMINALE          T20  LE ATTESE · scheda calendario in prospettiva (PRIMA / ATTESE) con lente: core 3,1% -> 3,2%, PIL 3,5%
S4 TERMINALE          T36  barre dei due scenari: SOPRA le attese -> l'oro può SCENDERE · SOTTO -> può SALIRE
S5 QUADERNO           T50  PERCHÉ? catena a icone: inflazione alta -> tassi più alti -> dollaro più forte -> oro sotto pressione · timbro DI SOLITO, NON SEMPRE
S6 TERMINALE          T66  grafico a candele con widget del prezzo: VICINO ai 3.500 (livello da guardare) e RESISTENZA 3.600
S7 NOTTE              T81  se ti è stata UTILE + 4 paletti (seguimi, mi piace, commenta SOPRA/SOTTO, condividi)
OUTRO                      logo animato + Telegram (Instagram: 'CERCAMI SU TELEGRAM'; TikTok: solo icona e @yard_fx)"""
import sys, os, math, json, random
sys.path.insert(0, '/home/user/bot-telegram/contenuti/yardfx_video'); import yardfx as Y; import suoni as S
from PIL import Image, ImageDraw
D = os.path.dirname(os.path.abspath(__file__))
WORDS = json.load(open(os.path.join(D, 'words.json')))
for i, s in [(70, '3.500:'), (80, '3.600.')]: WORDS[i][0] = s
G = Y.make_groups(WORDS)
T = lambda i: WORDS[i][1]
VEND = WORDS[-1][2]
KEYS = {1, 4, 6, 9, 11, 15, 18, 21, 25, 27, 35, 39, 44, 47, 49, 52, 55, 58, 61, 65, 70, 75, 78, 80, 85, 86, 90, 92, 94, 96}
CUTS = [0, T(7), T(20), T(36), T(50), T(66), T(81), VEND + 0.3]
OUT_LEN = 4.2; DUR = CUTS[-1] + OUT_LEN
TRANS = ['zoom', 'whip', 'blur', 'wipe', 'whip_v', 'zoom']
TD = 0.4; TIKTOK = os.environ.get('TIKTOK') == '1'
EV = []
def ev(t, n, g=1.0): EV.append((round(t, 3), n, g))
SP = Y.sprite
def big(b, s, xy, size, col, font=Y.BIG): ImageDraw.Draw(b).text(xy, s, font=Y.F(font, size), fill=col, anchor='mm')
PRICE = (3530.0, -0.9)

# ---------- S1 NOTTE a raggi: due dati alla stessa ora ----------
def s1(t):
    img = Y.sunburst_bg(t); img = Y.dust(img, t, 45, 3, Y.GOLD, 45)
    img = Y.pulse_rings(img, Y.W // 2, 640, t, Y.GOLD, 1.5, 3, 520)
    img = SP(img, lambda b: Y.glow_text(b, 'DUE', (Y.W // 2, 520), 260, Y.GOLD, (130, 90, 20)), t, -0.4, enter='stamp', idle='breathe', seed=1, dur=0.35)
    img = SP(img, lambda b: big(b, 'DATI', (Y.W // 2, 760), 240, Y.WHITE), t, T(1), enter='pop', idle='float', seed=2)
    img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('alla stessa', 'serif', 100, Y.MUTE), ('ORA', 'big', 130, Y.GOLD)], 1000), t, T(2), 0.35, 'float', 3)
    img = SP(img, lambda b: Y.stamp(b, 'VOLATILITÀ', (Y.W // 2, 1180), 110, Y.RED, -4), t, T(5), enter='stamp', idle='wobble', seed=4, dur=0.3, amp=0.4)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'GARANTITA', (Y.W // 2, 1340), 80, Y.ease((t - T(6)) / 0.4)), t, T(6), enter='pop', idle='breathe', seed=5)
    img = Y.camera(img, t, 0, punches=[T(1), T(4), T(5), T(6)], shakes=[T(5)])
    img = Y.color_flash(img, t, [T(4)], Y.GOLD, 0.15, 0.3)
    return Y.color_flash(img, t, [T(5)], Y.RED, 0.16, 0.3), True
ev(0, 'boom', 0.8); ev(0.05, 'stamp', 0.6); ev(T(1), 'pop'); ev(T(2), 'swoosh_up', 0.5); ev(T(4), 'ding', 0.7); ev(T(5), 'stamp'); ev(T(5) + 0.05, 'glitch', 0.5); ev(T(6), 'pop_hi'); ev(T(6) + 0.1, 'riser', 0.3)

# ---------- S2 NOTTE col faretto: oggi alle 14:30 ----------
def s2(t):
    img = Y.night_bg(t); img = Y.light_beams(img, t); img = Y.dust(img, t, 45, 7, Y.GOLD, 40)
    img = Y.spotlight(img, Y.W // 2 + 50 * math.sin(t * 1.2), 80, 1000, 600, 55)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('OGGI', 'big', 130, Y.WHITE), ('alle', 'serif', 90, Y.MUTE)], 400), t, T(7), enter='drop', idle='float', seed=6)
    if t > T(9): img = Y.pulse_rings(img, Y.W // 2, 590, t - T(9), Y.GOLD, 1.4, 3, 460)
    img = SP(img, lambda b: Y.number_roll(b, '14:30', (Y.W // 2, 590), 280, Y.GOLD, t, T(9), 0.6), t, T(9), enter='stamp', idle='breathe', seed=7, dur=0.35)
    img = SP(img, lambda b: Y.hand(ImageDraw.Draw(b), 'ora italiana', (Y.W // 2, 780), 80, Y.WHITE, Y.ease((t - T(10)) / 0.7)), t, T(10), enter='none', idle='float', seed=8)
    img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('escono', 'serif', 80, Y.MUTE), ('INSIEME', 'big', 100, Y.WHITE)], 950), t, T(12), 0.35, 'float', 9)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [("l'inflazione", 'serif', 90, Y.MUTE), ('PCE', 'big', 140, Y.GOLD)], 1130), t, T(14), enter='left', idle='float', seed=10)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('e il', 'serif', 90, Y.MUTE), ('PIL', 'big', 140, Y.GOLD), ('americano', 'serif', 80, Y.MUTE)], 1300), t, T(17), enter='right', idle='float', seed=11)
    img = Y.camera(img, t, CUTS[1], punches=[T(9) + 0.6, T(12), T(15), T(18)], shakes=[T(9) + 0.6])
    return Y.color_flash(img, t, [T(9) + 0.6, T(15), T(18)], Y.GOLD, 0.14, 0.3), True
ev(CUTS[1], 'swipe'); ev(T(7), 'pop'); [ev(T(9) + k * 0.07, 'tick', 0.5) for k in range(8)]; ev(T(9) + 0.6, 'boom', 0.8); ev(T(9) + 0.6, 'ding', 0.7)
ev(T(10), 'click', 0.6); ev(T(12), 'whoosh', 0.5); ev(T(14), 'swipe', 0.6); ev(T(15), 'pop_hi'); ev(T(17), 'swipe', 0.6); ev(T(18), 'pop_hi')

# ---------- S3 TERMINALE: le attese sul calendario ----------
ROWS = [('Inflazione core', '3,1%', '3,2%', T(22), T(27)), ('PIL', '', '3,5%', T(31), T(31))]
QUAD = [(90, 600), (990, 650), (1000, 1100), (80, 1070)]
def s3(t):
    img = Y.term_bg(); img = Y.light_sweep(img, t + 1.3, 3.4, 200, 30); img = Y.dust(img, t, 25, 11, Y.ICE, 30)
    Y.price_widget(ImageDraw.Draw(img), *PRICE)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('le', 'serif', 90, Y.MUTE), ('ATTESE', 'big', 140, Y.WHITE)], 380), t, T(20), enter='drop', idle='float', seed=12)
    rows = []
    for n, pr, at, t0, tp in ROWS:
        if t < t0: rows.append(['', '', '']); continue
        rows.append([n, (pr, Y.MUTE) if t >= tp else '', (at, Y.GOLD) if (t >= T(25) or n == 'PIL') else ''])
    act = 0 if t < T(31) else 1
    card = Y.ui_card(rows, ['', 'PRIMA', 'ATTESE'], '', 900, highlight=act if t >= T(22) else None, col_w=[440, 200, 260])
    q = Y.card_flip_quad(QUAD, t, CUTS[2])
    img = Y.perspective(img, card, q)
    if t >= T(22):
        ry = card.info['row_y'][act]; rh = card.info['rh']; t0 = ROWS[act][3]
        pts = [Y.map_point(card, q, x, y) for x, y in [(40, ry + 8), (860, ry + 8), (860, ry + rh - 8), (40, ry + rh - 8)]]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        img = Y.zoom_callout(img, (min(xs), min(ys), max(xs), max(ys)), (Y.W // 2, 1300), 1.05, (t - t0) / 0.4)
    img = Y.camera(img, t, CUTS[2], punches=[T(21), T(25), T(27), T(31), T(35)], shakes=[T(25)])
    return Y.color_flash(img, t, [T(25), T(35)], Y.GOLD, 0.14, 0.3), True
ev(CUTS[2], 'swipe'); ev(CUTS[2] + 0.05, 'whoosh', 0.6); ev(T(20), 'pop'); ev(T(22), 'click', 0.8); ev(T(22) + 0.05, 'pop_hi', 0.6); ev(T(23), 'tick', 0.6)
ev(T(25), 'ding', 0.8); ev(T(27), 'click', 0.7); ev(T(29), 'tick', 0.5); ev(T(31), 'click', 0.8); ev(T(31) + 0.05, 'swoosh_up', 0.5); ev(T(35), 'ding', 0.8)

# ---------- S4 TERMINALE: i due scenari ----------
def _scen(b, t, t0, y, lab, eff, col, down):
    d = ImageDraw.Draw(b); a = Y.ease((t - t0) / 0.5)
    d.rounded_rectangle((70, y - 150, 1010, y + 150), radius=26, fill=Y.CARD, outline=col, width=4)
    d.text((120, y - 70), lab, font=Y.F(Y.BIG, 74), fill=Y.WHITE, anchor='lm')
    d.rounded_rectangle((120, y + 10, 900, y + 40), radius=14, fill=(40, 42, 50))
    d.rounded_rectangle((120, y + 10, 120 + 780 * 0.75 * a, y + 40), radius=14, fill=col)
    Y.icon(d, 'grafico_giu' if down else 'grafico_su', 930, y - 70, 110, a, col, 7, 9)
    return b
def s4(t):
    img = Y.term_bg(); img = Y.light_sweep(img, t, 3.0, 200, 30); img = Y.dust(img, t, 25, 13, Y.ICE, 30)
    Y.price_widget(ImageDraw.Draw(img), *PRICE)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('se', 'serif', 90, Y.MUTE), ("L'INFLAZIONE", 'big', 120, Y.WHITE)], 340), t, T(36), enter='drop', idle='float', seed=13)
    img = SP(img, lambda b: _scen(b, t, T(39), 580, 'SOPRA LE ATTESE', '', Y.RED, True), t, T(39), enter='left', idle='float', seed=14, amp=0.4)
    if t > T(42): img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [("l'oro può", 'serif', 70, Y.MUTE), ('SCENDERE', 'big', 90, Y.RED)], 720), t, T(42), enter='pop', idle='breathe', seed=15)
    img = SP(img, lambda b: _scen(b, t, T(45), 1010, 'SOTTO', '', Y.GREEN, False), t, T(45), enter='right', idle='float', seed=16, amp=0.4)
    if t > T(48): img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('può', 'serif', 70, Y.MUTE), ('SALIRE', 'big', 90, Y.GREEN)], 1150), t, T(48), enter='pop', idle='breathe', seed=17)
    img = Y.camera(img, t, CUTS[3], punches=[T(39), T(44), T(47), T(49)], shakes=[T(44), T(49)])
    img = Y.color_flash(img, t, [T(44)], Y.RED, 0.15, 0.3)
    return Y.color_flash(img, t, [T(49)], Y.GREEN, 0.15, 0.3), True
ev(CUTS[3] + 0.05, 'swoosh_up', 0.6); ev(T(36), 'pop'); ev(T(39), 'swipe', 0.7); ev(T(39) + 0.1, 'riser', 0.3); ev(T(42), 'pop'); ev(T(44), 'boom', 0.6)
ev(T(45), 'swipe', 0.7); ev(T(47), 'pop'); ev(T(48), 'pop_hi'); ev(T(49), 'ding', 0.8)

# ---------- S5 QUADERNO: il perché ----------
CH = [(300, 600, 'grafico_su', 'inflazione alta', T(51)), (780, 600, 'banca', 'tassi più alti', T(53)), (300, 1010, 'dollaro', 'dollaro più forte', T(56)), (780, 1010, 'lingotto', 'oro sotto pressione', T(59))]
def s5(t):
    img = Y.grid_paper()
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('PERCHÉ?', 'big', 140, Y.INK)], 360), t, T(50), enter='drop', idle='wobble', seed=18, amp=0.4)
    for k, (x, y, ic, lab, t0) in enumerate(CH):
        if t < t0: continue
        def dr(b, x=x, y=y, ic=ic, lab=lab, t0=t0, k=k):
            d = ImageDraw.Draw(b); col = Y.RED if k == 3 else Y.INK
            Y.icon(d, ic, x, y, 170, Y.ease((t - t0) / 0.5), col, 8, 10 + k * 9)
            d.text((x, y + 145), lab, font=Y.F(Y.SERIF, 56), fill=col, anchor='mm')
        img = SP(img, dr, t, t0, enter='pop', idle='float', seed=21 + k, anchor=(x, y))
        if k:
            px, py = CH[k - 1][0], CH[k - 1][1]; d = ImageDraw.Draw(img); a = Y.ease((t - t0) / 0.4)
            if py == y: Y.dashed_arrow(d, px + 130, y, x - 130, y, a, Y.MUTE)
            else: Y.dashed_arrow(d, px - 60, py + 200, x + 60, y - 120, a, Y.MUTE)
    img = SP(img, lambda b: Y.stamp(b, 'DI SOLITO, NON SEMPRE', (Y.W // 2, 1340), 74, Y.GOLDK, -5), t, T(62), enter='stamp', idle='wobble', seed=26, dur=0.3, amp=0.4)
    img = Y.camera(img, t, CUTS[4], punches=[T(51), T(53), T(56), T(59), T(64)], shakes=[T(59), T(64)], push=0.04)
    return Y.color_flash(img, t, [T(59)], Y.RED, 0.15, 0.25), False
ev(CUTS[4], 'whoosh', 0.7); ev(T(50), 'pop')
for x, y, ic, lab, t0 in CH: ev(t0, 'bubble'); ev(t0 + 0.1, 'swipe', 0.4)
ev(T(59) + 0.2, 'boom', 0.5); ev(T(62), 'stamp'); ev(T(64), 'pop', 0.5)

# ---------- S6 TERMINALE: il livello da guardare ----------
def _cs():
    r = random.Random(5); cs = []; p = 3612
    for v in [3618, 3606, 3597, 3601, 3590, 3584, 3575, 3580, 3569, 3561, 3566, 3555, 3548, 3552, 3541, 3536, 3540, 3531, 3528, 3533]:
        o = p; c = v + r.uniform(-1.5, 1.5); h = max(o, c) + r.uniform(2, 7); l = min(o, c) - r.uniform(2, 7)
        cs.append({'o': o, 'h': h, 'l': l, 'c': c, 'g': c > o}); p = c
    return cs
CS = _cs()
def s6(t):
    img = Y.term_bg(); img = Y.light_sweep(img, t + 0.7, 3.2, 200, 30); img = Y.dust(img, t, 25, 17, Y.ICE, 30)
    Y.price_widget(ImageDraw.Draw(img), *PRICE)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [("l'oro è", 'serif', 80, Y.MUTE), ('VICINO', 'big', 110, Y.WHITE), ('ai', 'serif', 80, Y.MUTE)], 330), t, T(66), enter='drop', idle='float', seed=27)
    def chart(b):
        lv = []
        if t > T(70): lv.append((3500, '3.500', Y.GOLD))
        if t > T(78): lv.append((3600, '3.600', Y.RED))
        Y.candles_chart(b, CS, (110, 560, 970, 1130), 3480, 3640, (t - T(66)) / 1.6, levels=lv)
        return b
    img = SP(img, chart, t, T(66), enter='rise', idle='float', seed=28, amp=0.3)
    if t < T(76):
        if t > T(70): img = Y.pulse_rings(img, Y.W // 2, 1280, t - T(70), Y.GOLD, 1.2, 2, 320)
        img = SP(img, lambda b: Y.number_roll(b, '3.500', (Y.W // 2, 1280), 170, Y.GOLD, t, T(70), 0.6), t, T(70), enter='stamp', idle='breathe', seed=29, dur=0.3)
        img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'IL LIVELLO DA GUARDARE', (Y.W // 2, 1420), 60, Y.ease((t - T(73)) / 0.4)), t, T(73), enter='pop', idle='breathe', seed=30)
    else:
        img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('sopra, la', 'serif', 80, Y.MUTE), ('RESISTENZA', 'big', 110, Y.RED)], 1260), t, T(76), enter='right', idle='float', seed=31)
        img = SP(img, lambda b: Y.number_roll(b, '3.600', (Y.W // 2, 1400), 150, Y.RED, t, T(80), 0.5), t, T(80), enter='stamp', idle='breathe', seed=32, dur=0.3)
    img = Y.camera(img, t, CUTS[5], punches=[T(68), T(70) + 0.6, T(73), T(76), T(80) + 0.5], shakes=[T(70) + 0.6])
    img = Y.color_flash(img, t, [T(70) + 0.6], Y.GOLD, 0.15, 0.3)
    return Y.color_flash(img, t, [T(80) + 0.5], Y.RED, 0.14, 0.28), True
ev(CUTS[5], 'swipe', 0.8); ev(T(66), 'pop'); [ev(T(66) + k * 0.1, 'tick', 0.35) for k in range(14)]
[ev(T(70) + k * 0.07, 'tick', 0.5) for k in range(8)]; ev(T(70) + 0.6, 'boom', 0.7); ev(T(70) + 0.6, 'ding', 0.6); ev(T(73), 'pop_hi')
ev(T(76), 'whoosh', 0.6); ev(T(76) + 0.05, 'pop'); ev(T(78), 'click', 0.6); [ev(T(80) + k * 0.07, 'tick', 0.5) for k in range(7)]; ev(T(80) + 0.5, 'stamp', 0.8)

# ---------- S7 CTA ----------
CTA_T = [T(86), T(89), T(91), T(96)]
def s7(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 50, 17, Y.GOLD, 55)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('se ti è stata', 'serif', 90, Y.WHITE), ('UTILE', 'big', 110, Y.GOLD)], 420), t, CUTS[6], enter='drop', idle='float', seed=33)
    img = Y.cta_four(img, t, CTA_T, 'SOPRA/SOTTO', y0=640)
    return Y.camera(img, t, CUTS[6], punches=CTA_T, push=0.03), True
ev(CUTS[6], 'swoosh_up'); ev(T(85), 'pop'); ev(CTA_T[0], 'pop'); ev(CTA_T[1], 'pop_hi'); ev(CTA_T[1] + 0.05, 'bubble', 0.6); ev(CTA_T[2], 'bubble'); ev(T(92), 'pop', 0.5); ev(T(94), 'pop', 0.5); ev(CTA_T[3], 'swoosh_up'); ev(CTA_T[3] + 0.1, 'coin')

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
NAME = 'yardfx_news_pil_pce_25nov'
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
        S.music(os.path.join(D, 'base.wav'), DUR, 100, 'tensione')
        a = S.mix(os.path.join(D, 'audio.m4a'), DUR, voce=os.path.join(D, 'voce.mp3'), musica=os.path.join(D, 'base.wav'), eventi=EV, music_db=-17)
        for tag in ['ig', 'tt']:
            lst = os.path.join(D, f'list_{tag}.txt'); open(lst, 'w').write(f"file 'main.mp4'\nfile 'outro_{tag}.mp4'\n")
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-i', a, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'copy', '-shortest', '-movflags', '+faststart',
                            os.path.join(D, f'{NAME}_{"instagram" if tag == "ig" else "tiktok"}.mp4')], check=True)
        print('ok', DUR, len(EV))
