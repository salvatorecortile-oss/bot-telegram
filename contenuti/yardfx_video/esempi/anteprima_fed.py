"""Anteprima settimana 16-20 novembre 2026 (vendite al dettaglio e verbali FED), pubblicata martedì 17/11 alle 13:00 — voce Enea.
Ricetta ANTEPRIMA: Notte -> Terminale -> Notte. Ogni scena parte sulla prima parola del suo paragrafo.
S1 NOTTE     T0   'questa SETTIMANA' · FED gigante con onde · PARLA · timbro NON SI RIUNISCE
S2 TERMINALE T10  IERI · l'oro è SCESO · grafico a candele che scende fino a 3.832 · IL MINIMO DA UN ANNO
S3 NOTTE     T22  linea del tempo LUN-VEN: OGGI 14:30 VENDITE AL DETTAGLIO -> DOMANI 20:00 VERBALI FED · timbro ALZARE I TASSI
S4 TERMINALE T45  scheda calendario in prospettiva che entra ruotando · righe GIO/VEN accese sulla voce · lente sulla riga
S5 NOTTE     T63  IL LIVELLO DA GUARDARE: linea 3.832 luminosa, prezzo che pulsa sopra, freccia SOPRA -> RESISTENZA 4.000
S6 NOTTE     T74  se ti è stata UTILE + 4 paletti (seguimi, mi piace, commenta SOPRA/SOTTO, condividi)
OUTRO             logo animato + Telegram (Instagram: 'CERCAMI SU TELEGRAM'; TikTok: solo icona e @yard_fx)"""
import sys, os, math, json, random
sys.path.insert(0, '/home/user/bot-telegram/contenuti/yardfx_video'); import yardfx as Y; import suoni as S
from PIL import Image, ImageDraw
D = os.path.dirname(os.path.abspath(__file__))
WORDS = json.load(open(os.path.join(D, 'words.json')))
for i, s in [(16, '3.832:'), (68, '3.832.'), (73, '4.000.')]: WORDS[i][0] = s
G = Y.make_groups(WORDS)
T = lambda i: WORDS[i][1]
VEND = WORDS[-1][2]
KEYS = {3, 9, 13, 16, 18, 24, 26, 32, 34, 42, 47, 51, 54, 58, 60, 66, 68, 71, 73}
CUTS = [0, T(10), T(22), T(45), T(63), T(74), VEND + 0.3]
OUT_LEN = 4.2; DUR = CUTS[-1] + OUT_LEN
TRANS = ['zoom', 'whip', 'blur', 'whip_v', 'wipe']
TD = 0.4; TIKTOK = os.environ.get('TIKTOK') == '1'
EV = []
def ev(t, n, g=1.0): EV.append((round(t, 3), n, g))
SP = Y.sprite
def big(b, s, xy, size, col, font=Y.BIG): ImageDraw.Draw(b).text(xy, s, font=Y.F(font, size), fill=col, anchor='mm')

# ---------- S1 NOTTE: la FED parla ----------
def s1(t):
    img = Y.night_bg(t); img = Y.light_beams(img, t); img = Y.dust(img, t, 45, 3, Y.GOLD, 40)
    img = Y.spotlight(img, Y.W // 2 + 60 * math.sin(t * 1.3), 90, 980, 560, 55)
    img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('questa', 'serif', 120, Y.WHITE), ('SETTIMANA', 'big', 150, Y.WHITE)], 430), t, -0.4, 0.45, 'float', 1)
    if t > T(3): img = Y.pulse_rings(img, Y.W // 2, 720, t - T(3), Y.GOLD, 1.3, 3, 520)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('la', 'serif', 100, Y.MUTE)], 560), t, T(2), enter='rise', idle='float', seed=2)
    img = SP(img, lambda b: Y.glow_text(b, 'FED', (Y.W // 2, 740), 320, Y.GOLD, (130, 90, 20)), t, T(3), enter='stamp', idle='breathe', seed=3, dur=0.35)
    img = SP(img, lambda b: big(b, 'PARLA', (Y.W // 2, 960), 140, Y.WHITE), t, T(4), enter='pop', idle='wobble', seed=4, amp=0.6)
    img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('anche se', 'serif', 90, Y.MUTE)], 1150), t, T(5), 0.35, 'float', 5)
    img = SP(img, lambda b: Y.stamp(b, 'NON SI RIUNISCE', (Y.W // 2, 1300), 92, Y.RED, -4), t, T(7), enter='stamp', idle='wobble', seed=6, dur=0.3, amp=0.4)
    img = Y.camera(img, t, 0, punches=[T(3), T(4), T(7)], shakes=[T(3), T(7)])
    img = Y.color_flash(img, t, [T(3)], Y.GOLD, 0.16, 0.4)
    return Y.color_flash(img, t, [T(7)], Y.RED, 0.14, 0.3), True
ev(0, 'boom', 0.7); ev(0.05, 'whoosh', 0.6); ev(T(2), 'swoosh_up', 0.5); ev(T(3), 'boom'); ev(T(3), 'stamp', 0.7); ev(T(4), 'pop'); ev(T(4) + 0.05, 'swipe', 0.5)
ev(T(5), 'swoosh_up', 0.5); ev(T(7), 'stamp'); ev(T(7) + 0.05, 'glitch', 0.5)

# ---------- S2 TERMINALE: ieri il minimo da un anno ----------
def _candles():
    r = random.Random(7); cs = []; p = 3958
    for i in range(18):
        o = p; c = o - r.uniform(-6, 14) - (6 if i > 10 else 0)
        if i == 17: c = 3846
        h = max(o, c) + r.uniform(2, 9); l = min(o, c) - r.uniform(2, 9)
        if i == 17: l = 3832.7
        cs.append({'o': o, 'h': h, 'l': l, 'c': c, 'g': c > o}); p = c
    return cs
CS = _candles()
def s2(t):
    img = Y.term_bg(); img = Y.light_sweep(img, t, 3.2, 200, 35); img = Y.dust(img, t, 30, 7, Y.ICE, 30)
    img = SP(img, lambda b: Y.glow_text(b, 'IERI', (Y.W // 2, 300), 150, Y.WHITE, (80, 90, 120)), t, T(10), enter='drop', idle='float', seed=7)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [("l'oro è", 'serif', 90, Y.MUTE), ('SCESO', 'big', 120, Y.RED)], 500), t, T(11), enter='left', idle='float', seed=8)
    def chart(b):
        lv = [(3832.7, '3.832', Y.RED)] if t > T(16) else []
        Y.candles_chart(b, CS, (130, 620, 950, 1110), 3820, 3975, (t - T(11)) / 1.6, levels=lv)
        if t > T(16):
            step = (950 - 130) / len(CS); x = 130 + 12 + 17 * step; y = 1110 - (3832.7 - 3820) / 155 * 490
            Y.circle(ImageDraw.Draw(b), x, y, 70, 46, Y.ease((t - T(16)) / 0.5), Y.GOLD, 6, 41)
        return b
    img = SP(img, chart, t, T(11), enter='rise', idle='float', seed=9, amp=0.3)
    if t > T(16): img = Y.pulse_rings(img, Y.W // 2, 1265, t - T(16), Y.RED, 1.2, 2, 300)
    img = SP(img, lambda b: Y.number_roll(b, '3.832', (Y.W // 2, 1265), 190, Y.RED, t, T(16), 0.7), t, T(16), enter='stamp', idle='breathe', seed=10, dur=0.3)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'IL MINIMO DA UN ANNO', (Y.W // 2, 1440), 64, Y.ease((t - T(18)) / 0.4)), t, T(18), enter='pop', idle='breathe', seed=11)
    img = Y.camera(img, t, CUTS[1], punches=[T(13), T(16) + 0.7, T(18)], shakes=[T(16) + 0.7])
    return Y.color_flash(img, t, [T(16) + 0.7], Y.RED, 0.15, 0.32), True
ev(CUTS[1], 'swipe'); ev(T(10), 'pop'); ev(T(11), 'swipe', 0.6); ev(T(13), 'swoosh_up', 0.4)
[ev(T(11) + k * 0.1, 'tick', 0.35) for k in range(16)]
[ev(T(16) + k * 0.07, 'tick', 0.5) for k in range(10)]; ev(T(16) + 0.7, 'boom', 0.8); ev(T(18), 'stamp', 0.7); ev(T(20), 'pop_hi', 0.6)

# ---------- S3 NOTTE: oggi e domani sulla linea del tempo ----------
DAYS = [('LUN', '16', ''), ('MAR', '17', 'VENDITE'), ('MER', '18', 'FED'), ('GIO', '19', ''), ('VEN', '20', '')]
def s3(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 40, 13, Y.GOLD, 40); img = Y.light_beams(img, t + 2, n=2, strength=16)
    act = 1 if t < T(30) else 2
    items = [(g, n, tag if (i == 1 and t > T(26)) or (i == 2 and t > T(34)) else '') for i, (g, n, tag) in enumerate(DAYS)]
    img = SP(img, lambda b: Y.timeline_nodes(b, items, 330, act, t, CUTS[2]), t, CUTS[2], enter='none', idle='float', seed=12, amp=0.3)
    if t < T(30):
        img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('OGGI', 'big', 120, Y.WHITE), ('alle', 'serif', 90, Y.MUTE)], 640), t, T(22), enter='drop', idle='float', seed=13)
        if t > T(24): img = Y.pulse_rings(img, Y.W // 2, 790, t - T(24), Y.GOLD, 1.4, 2, 420)
        img = SP(img, lambda b: Y.glow_text(b, '14:30', (Y.W // 2, 790), 230, Y.GOLD, (130, 90, 20)), t, T(24), enter='stamp', idle='breathe', seed=14, dur=0.35)
        img = Y.blur_in(img, lambda b: big(b, 'VENDITE', (Y.W // 2, 1010), 130, Y.WHITE), t, T(26), 0.35, 'float', 15)
        img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('al', 'serif', 80, Y.MUTE), ('DETTAGLIO', 'big', 110, Y.WHITE)], 1170), t, T(28), 0.35, 'float', 16)
        img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'AMERICANE', (Y.W // 2, 1300), 70, Y.ease((t - T(29)) / 0.4)), t, T(29), enter='pop', idle='breathe', seed=17)
    else:
        img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('DOMANI', 'big', 120, Y.WHITE), ('alle', 'serif', 90, Y.MUTE)], 640), t, T(30), enter='right', idle='float', seed=18)
        if t > T(32): img = Y.pulse_rings(img, Y.W // 2, 790, t - T(32), Y.GOLD, 1.4, 2, 420)
        img = SP(img, lambda b: Y.glow_text(b, '20:00', (Y.W // 2, 790), 230, Y.GOLD, (130, 90, 20)), t, T(32), enter='stamp', idle='breathe', seed=19, dur=0.35)
        img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('i', 'serif', 80, Y.MUTE), ('VERBALI', 'big', 120, Y.WHITE), ('della', 'serif', 80, Y.MUTE), ('FED', 'big', 120, Y.GOLD)], 1010), t, T(34), 0.35, 'float', 20)
        img = SP(img, lambda b: Y.hand(ImageDraw.Draw(b), 'si legge chi voleva già', (Y.W // 2, 1135), 66, Y.WHITE, Y.ease((t - T(37)) / 0.8)), t, T(37), enter='none', idle='float', seed=21)
        img = SP(img, lambda b: Y.stamp(b, 'ALZARE I TASSI', (Y.W // 2, 1300), 88, Y.RED, -4), t, T(42), enter='stamp', idle='wobble', seed=22, dur=0.3, amp=0.4)
    img = Y.camera(img, t, CUTS[2], punches=[T(24), T(26), T(30), T(32), T(36), T(42)], shakes=[T(24), T(42)])
    img = Y.color_flash(img, t, [T(24), T(32)], Y.GOLD, 0.15, 0.32)
    img = Y.color_flash(img, t, [T(42)], Y.RED, 0.14, 0.3)
    return Y.flash(img, t, [T(30)], 0.16), True
ev(CUTS[2] + 0.05, 'swoosh_up', 0.6); [ev(CUTS[2] + 0.1 + k * 0.12, 'tick', 0.4) for k in range(5)]
ev(T(22), 'pop'); ev(T(24), 'boom', 0.7); ev(T(24), 'ding', 0.7); ev(T(26), 'whoosh', 0.5); ev(T(26) + 0.05, 'pop_hi', 0.5); ev(T(28), 'swoosh_up', 0.5); ev(T(29), 'pop')
ev(T(30), 'whoosh', 0.8); ev(T(30) + 0.05, 'swipe', 0.6); ev(T(32), 'boom', 0.7); ev(T(32), 'ding', 0.7); ev(T(34), 'swoosh_up', 0.5); ev(T(36), 'pop_hi'); ev(T(37), 'click', 0.7)
ev(T(42), 'stamp'); ev(T(42) + 0.05, 'glitch', 0.4)

# ---------- S4 TERMINALE: calendario giovedì e venerdì ----------
ROWS = [('GIO', '14:30', 'Richieste disoccupazione', T(49)), ('GIO', '14:30', 'Philly Fed', T(54)), ('VEN', '16:00', 'Fiducia consumatori', T(60))]
QUAD = [(90, 560), (990, 610), (1000, 1150), (80, 1120)]
def _active(t):
    a = None
    for i, (_, _, _, t0) in enumerate(ROWS):
        if t >= t0: a = i
    return a
def s4(t):
    img = Y.term_bg(); img = Y.light_sweep(img, t + 1.3, 3.4, 200, 30); img = Y.dust(img, t, 25, 11, Y.ICE, 30)
    day = 'GIOVEDÌ' if t < T(56) else 'VENERDÌ'; t0d = T(45) if t < T(56) else T(56)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [(day, 'big', 130, Y.WHITE), ('alle', 'serif', 80, Y.MUTE)], 360), t, t0d, enter='drop', idle='float', seed=23 if t < T(56) else 24)
    rows = [[(g, Y.GOLD), (h, Y.WHITE), n] if t >= t0 else ['', '', ''] for g, h, n, t0 in ROWS]
    act = _active(t); card = Y.ui_card(rows, ['', '', ''], '', 900, highlight=act, col_w=[130, 170, 600])
    q = Y.card_flip_quad(QUAD, t, CUTS[3])
    img = Y.perspective(img, card, q)
    if act is not None:
        ry = card.info['row_y'][act]; rh = card.info['rh']
        pts = [Y.map_point(card, q, x, y) for x, y in [(40, ry + 8), (860, ry + 8), (860, ry + rh - 8), (40, ry + rh - 8)]]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        img = Y.zoom_callout(img, (min(xs), min(ys), max(xs), max(ys)), (Y.W // 2, 1340), 1.05, (t - ROWS[act][3]) / 0.4)
    img = Y.camera(img, t, CUTS[3], punches=[T(47), T(51), T(54), T(56), T(60)], shakes=[T(56)])
    return Y.color_flash(img, t, [T(56)], Y.GOLD, 0.14, 0.3), True
ev(CUTS[3], 'swipe'); ev(CUTS[3] + 0.05, 'whoosh', 0.6); ev(T(45), 'pop'); ev(T(47), 'tick', 0.6)
for _, _, _, t0 in ROWS: ev(t0, 'click', 0.8); ev(t0 + 0.05, 'pop_hi', 0.6); ev(t0 + 0.15, 'swoosh_up', 0.4)
ev(T(51), 'ding', 0.6); ev(T(56), 'whoosh', 0.7); ev(T(56) + 0.05, 'pop'); ev(T(58), 'tick', 0.6); ev(T(62), 'ding', 0.6)

# ---------- S5 NOTTE: i livelli ----------
Y4000, Y3832 = 650, 1180
def s5(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 45, 17, Y.GOLD, 45); img = Y.spotlight(img, Y.W // 2, 60, 1250, 620, 40)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('il', 'serif', 90, Y.MUTE), ('LIVELLO', 'big', 120, Y.WHITE)], 330), t, T(63), enter='drop', idle='float', seed=25)
    img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('da', 'serif', 80, Y.MUTE), ('GUARDARE', 'big', 110, Y.GOLD)], 460), t, T(65), 0.35, 'float', 26)
    d = ImageDraw.Draw(img)
    def dline(y, col, a):
        xe = 120 + 840 * a; off = int(t * 40) % 30
        for xx in range(120 - off, int(xe), 30):
            if xx >= 120: d.line([(xx, y), (min(xx + 18, xe), y)], fill=col, width=6)
    if t > T(68):
        dline(Y3832, Y.GOLD, Y.ease((t - T(68)) / 0.4)); img = Y.pulse_rings(img, Y.W // 2, Y3832, t - T(68), Y.GOLD, 1.3, 2, 380)
        img = SP(img, lambda b: Y.number_roll(b, '3.832', (Y.W // 2, Y3832 + 110), 150, Y.GOLD, t, T(68), 0.6), t, T(68), enter='stamp', idle='breathe', seed=27, dur=0.3)
    d = ImageDraw.Draw(img)
    if t > T(68):
        yp = Y3832 - 70 + 10 * math.sin(t * 3)
        img = Y.pulse_rings(img, 300, yp, t, Y.WHITE, 1.0, 2, 90, 3)
        img = Y.glow_text(img, '•', (300, yp - 8), int(110 + 12 * math.sin(t * 6)), Y.WHITE, (120, 120, 160))
    d = ImageDraw.Draw(img)
    if t > T(69):
        Y.dashed_arrow(d, 300, Y3832 - 120, 300, Y4000 + 40, Y.ease((t - T(69)) / 0.6), Y.GREEN)
        img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('SOPRA', 'big', 90, Y.GREEN)], 940, cx=560), t, T(69), enter='left', idle='float', seed=28)
    d = ImageDraw.Draw(img)
    if t > T(71):
        dline(Y4000, Y.RED, Y.ease((t - T(71)) / 0.4))
        img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('la', 'serif', 70, Y.MUTE), ('RESISTENZA', 'big', 90, Y.RED)], Y4000 - 40), t, T(71), enter='drop', idle='float', seed=29)
    img = SP(img, lambda b: Y.number_roll(b, '4.000', (Y.W // 2, Y4000 + 110), 150, Y.RED, t, T(73), 0.5), t, T(73), enter='stamp', idle='breathe', seed=30, dur=0.3)
    img = Y.camera(img, t, CUTS[4], punches=[T(66), T(68) + 0.6, T(71), T(73) + 0.5], shakes=[T(68) + 0.6])
    img = Y.color_flash(img, t, [T(68) + 0.6], Y.GOLD, 0.15, 0.32)
    return Y.color_flash(img, t, [T(73) + 0.5], Y.RED, 0.14, 0.28), True
ev(CUTS[4], 'swoosh_up', 0.6); ev(T(63), 'pop'); ev(T(66), 'swoosh_up', 0.5); ev(T(66) + 0.05, 'pop_hi', 0.6)
[ev(T(68) + k * 0.07, 'tick', 0.5) for k in range(8)]; ev(T(68) + 0.6, 'boom', 0.7); ev(T(68) + 0.6, 'ding', 0.7)
ev(T(69), 'whoosh', 0.6); ev(T(69) + 0.05, 'pop'); ev(T(71), 'swipe', 0.6); ev(T(71) + 0.05, 'pop_hi'); [ev(T(73) + k * 0.07, 'tick', 0.5) for k in range(7)]; ev(T(73) + 0.5, 'stamp', 0.8)

# ---------- S6 CTA ----------
CTA_T = [T(79), T(82), T(84), T(89)]
def s6(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 50, 17, Y.GOLD, 55)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('se ti è stata', 'serif', 90, Y.WHITE), ('UTILE', 'big', 110, Y.GOLD)], 420), t, CUTS[5], enter='drop', idle='float', seed=33)
    img = Y.cta_four(img, t, CTA_T, 'SOPRA/SOTTO', y0=640)
    return Y.camera(img, t, CUTS[5], punches=CTA_T, push=0.03), True
ev(CUTS[5], 'swoosh_up'); ev(T(78), 'pop'); ev(CTA_T[0], 'pop'); ev(CTA_T[1], 'pop_hi'); ev(CTA_T[1] + 0.05, 'bubble', 0.6); ev(CTA_T[2], 'bubble'); ev(T(85), 'pop', 0.5); ev(T(87), 'pop', 0.5); ev(CTA_T[3], 'swoosh_up'); ev(CTA_T[3] + 0.1, 'coin')

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
NAME = 'yardfx_anteprima_17nov'
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
