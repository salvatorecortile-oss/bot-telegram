"""Anteprima settimana 23-27 novembre 2026 (PCE + PIL mercoledì, Thanksgiving giovedì), pubblicata lunedì 23/11 — voce Salvatore (Speechify).
Ricetta ANTEPRIMA: Notte -> Terminale -> Notte. Ogni scena parte sulla prima parola del suo paragrafo.
S1 NOTTE     T0   SETTIMANA CORTA · timbro MA PESANTE · linea del tempo LUN-VEN con MER acceso · 2 DATI · INSIEME
S2 TERMINALE T9   widget del prezzo · l'oro arriva da un CALO FORTE · candele che scendono sotto la linea 3.600
S3 TERMINALE T20  scheda calendario in prospettiva: MER 14:30 PCE, MER 14:30 PIL, GIO Thanksgiving chiusi, VEN si chiude prima · lente
S4 NOTTE     T43  SE l'INFLAZIONE esce più ALTA -> freccia rossa: l'oro può SCENDERE ANCORA
S5 NOTTE     T54  SUPPORTO 3.500 (oro) e RESISTENZA 3.600 (rossa), prezzo che pulsa in mezzo
S6 NOTTE     T65  se ti è stata UTILE + 4 paletti (seguimi, mi piace, commenta SOPRA/SOTTO, condividi)
OUTRO             logo animato + Telegram (Instagram: 'CERCAMI SU TELEGRAM'; TikTok: solo icona e @yard_fx)"""
import sys, os, math, json, random
sys.path.insert(0, '/home/user/bot-telegram/contenuti/yardfx_video'); import yardfx as Y; import suoni as S
from PIL import Image, ImageDraw
D = os.path.dirname(os.path.abspath(__file__))
WORDS = json.load(open(os.path.join(D, 'words.json')))
for i, s in [(19, '3.600.'), (59, '3.500.'), (64, '3.600.')]: WORDS[i][0] = s
G = Y.make_groups(WORDS)
T = lambda i: WORDS[i][1]
VEND = WORDS[-1][2]
KEYS = {3, 7, 14, 19, 22, 25, 28, 32, 38, 42, 47, 53, 55, 59, 62, 64, 69, 70, 74, 76, 78, 80}
CUTS = [0, T(9), T(20), T(43), T(54), T(65), VEND + 0.3]
OUT_LEN = 4.2; DUR = CUTS[-1] + OUT_LEN
TRANS = ['whip', 'blur', 'wipe', 'zoom', 'whip_v']
TD = 0.4; TIKTOK = os.environ.get('TIKTOK') == '1'
EV = []
def ev(t, n, g=1.0): EV.append((round(t, 3), n, g))
SP = Y.sprite
def big(b, s, xy, size, col, font=Y.BIG): ImageDraw.Draw(b).text(xy, s, font=Y.F(font, size), fill=col, anchor='mm')

# ---------- S1 NOTTE: settimana corta, mercoledì due dati ----------
DAYS = [('LUN', '23', ''), ('MAR', '24', ''), ('MER', '25', '2 DATI'), ('GIO', '26', 'CHIUSO'), ('VEN', '27', '')]
def s1(t):
    img = Y.night_bg(t); img = Y.light_beams(img, t); img = Y.dust(img, t, 45, 3, Y.GOLD, 40)
    img = Y.spotlight(img, Y.W // 2 + 60 * math.sin(t * 1.3), 90, 980, 560, 55)
    img = Y.blur_in(img, lambda b: big(b, 'SETTIMANA', (Y.W // 2, 400), 170, Y.WHITE), t, -0.4, 0.45, 'float', 1)
    img = SP(img, lambda b: Y.glow_text(b, 'CORTA', (Y.W // 2, 590), 230, Y.GOLD, (130, 90, 20)), t, T(1), enter='stamp', idle='breathe', seed=2, dur=0.35)
    img = SP(img, lambda b: Y.stamp(b, 'MA PESANTE', (Y.W // 2, 790), 100, Y.RED, -4), t, T(3), enter='stamp', idle='wobble', seed=3, dur=0.3, amp=0.4)
    items = [(g, n, tag if (i == 2 and t > T(6)) else '') for i, (g, n, tag) in enumerate(DAYS)]
    img = SP(img, lambda b: Y.timeline_nodes(b, items, 950, 2 if t > T(4) else None, t, T(4) - 0.2), t, T(4) - 0.2, enter='none', idle='float', seed=4, amp=0.3)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('MERCOLEDÌ', 'big', 110, Y.WHITE), ('escono', 'serif', 80, Y.MUTE)], 1190), t, T(4), enter='rise', idle='float', seed=5)
    if t > T(6): img = Y.pulse_rings(img, Y.W // 2, 1320, t - T(6), Y.GOLD, 1.3, 2, 380)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('DUE', 'big', 150, Y.GOLD), ('DATI', 'big', 150, Y.WHITE)], 1370), t, T(6), enter='pop', idle='breathe', seed=6)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'INSIEME', (Y.W // 2, 1460), 70, Y.ease((t - T(8)) / 0.4)), t, T(8), enter='pop', idle='breathe', seed=7)
    img = Y.camera(img, t, 0, punches=[T(1), T(3), T(6), T(8)], shakes=[T(3), T(6)])
    img = Y.color_flash(img, t, [T(1), T(6)], Y.GOLD, 0.15, 0.35)
    return Y.color_flash(img, t, [T(3)], Y.RED, 0.14, 0.3), True
ev(0, 'boom', 0.7); ev(0.05, 'whoosh', 0.6); ev(T(1), 'boom', 0.8); ev(T(1), 'stamp', 0.6); ev(T(3), 'stamp'); ev(T(3) + 0.05, 'glitch', 0.5)
ev(T(4) - 0.2, 'swoosh_up', 0.5); [ev(T(4) + k * 0.12, 'tick', 0.4) for k in range(5)]; ev(T(4), 'pop'); ev(T(6), 'boom', 0.7); ev(T(6), 'ding', 0.7); ev(T(8), 'pop_hi')

# ---------- S2 TERMINALE: il calo sotto 3.600 ----------
def _candles():
    r = random.Random(11); cs = []; p = 3895
    for i in range(18):
        o = p; c = o - r.uniform(-8, 34)
        if i == 17: c = 3538
        h = max(o, c) + r.uniform(3, 12); l = min(o, c) - r.uniform(3, 12)
        cs.append({'o': o, 'h': h, 'l': l, 'c': c, 'g': c > o}); p = c
    return cs
CS = _candles(); LO, HI = min(c['l'] for c in CS) - 20, max(c['h'] for c in CS) + 15
def s2(t):
    img = Y.term_bg(); img = Y.light_sweep(img, t, 3.2, 200, 35); img = Y.dust(img, t, 30, 7, Y.ICE, 30)
    Y.price_widget(ImageDraw.Draw(img), 3538.0, -8.9)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [("l'oro arriva da un", 'serif', 80, Y.MUTE)], 320), t, T(9), enter='drop', idle='float', seed=8)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('CALO', 'big', 140, Y.RED), ('FORTE', 'big', 140, Y.WHITE)], 480), t, T(13), enter='left', idle='float', seed=9)
    def chart(b):
        lv = [(3600, '3.600', Y.GOLD)] if t > T(17) else []
        Y.candles_chart(b, CS, (130, 600, 950, 1150), LO, HI, (t - T(9)) / 2.4, levels=lv)
        return b
    img = SP(img, chart, t, T(9), enter='rise', idle='float', seed=10, amp=0.3)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('è sceso', 'serif', 80, Y.MUTE), ('SOTTO', 'big', 110, Y.RED)], 1250), t, T(15), enter='right', idle='float', seed=11)
    if t > T(19): img = Y.pulse_rings(img, Y.W // 2, 1370, t - T(19), Y.RED, 1.2, 2, 300)
    img = SP(img, lambda b: Y.number_roll(b, '3.600', (Y.W // 2, 1370), 170, Y.GOLD, t, T(19), 0.6), t, T(19), enter='stamp', idle='breathe', seed=12, dur=0.3)
    img = Y.camera(img, t, CUTS[1], punches=[T(13), T(15), T(19) + 0.6], shakes=[T(19) + 0.6])
    return Y.color_flash(img, t, [T(13), T(19) + 0.6], Y.RED, 0.14, 0.3), True
ev(CUTS[1], 'swipe'); ev(T(9), 'pop', 0.7); [ev(T(9) + k * 0.13, 'tick', 0.35) for k in range(18)]; ev(T(13), 'boom', 0.7); ev(T(13) + 0.05, 'swipe', 0.6)
ev(T(15), 'whoosh', 0.6); ev(T(17), 'click', 0.6); [ev(T(19) + k * 0.07, 'tick', 0.5) for k in range(8)]; ev(T(19) + 0.6, 'stamp', 0.8)

# ---------- S3 TERMINALE: il calendario della settimana ----------
ROWS = [('MER', '14:30', 'Inflazione PCE', T(24)), ('MER', '14:30', 'PIL americano', T(28)), ('GIO', 'USA', 'Thanksgiving: chiusi', T(32)), ('VEN', 'USA', 'Si chiude prima', T(39))]
QUAD = [(90, 560), (990, 610), (1000, 1200), (80, 1170)]
def _active(t):
    a = None
    for i, (_, _, _, t0) in enumerate(ROWS):
        if t >= t0: a = i
    return a
def s3(t):
    img = Y.term_bg(); img = Y.light_sweep(img, t + 1.3, 3.4, 200, 30); img = Y.dust(img, t, 25, 11, Y.ICE, 30)
    Y.price_widget(ImageDraw.Draw(img), 3538.0, -8.9)
    if t < T(30): parts, t0d, sd = [('MERCOLEDÌ', 'big', 120, Y.WHITE), ('alle', 'serif', 80, Y.MUTE), ('14:30', 'big', 120, Y.GOLD)], T(20), 13
    elif t < T(39): parts, t0d, sd = [('GIOVEDÌ', 'big', 130, Y.WHITE), ('Thanksgiving', 'serif', 90, Y.GOLD)], T(30), 14
    else: parts, t0d, sd = [('VENERDÌ', 'big', 130, Y.WHITE), ('si chiude prima', 'serif', 80, Y.MUTE)], T(39), 15
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), parts, 360), t, t0d, enter='drop', idle='float', seed=sd)
    rows = [[(g, Y.GOLD), (h, Y.WHITE), n] if t >= t0 else ['', '', ''] for g, h, n, t0 in ROWS]
    act = _active(t); card = Y.ui_card(rows, ['', '', ''], '', 900, highlight=act, col_w=[130, 170, 600])
    q = Y.card_flip_quad(QUAD, t, CUTS[2])
    img = Y.perspective(img, card, q)
    if act is not None:
        ry = card.info['row_y'][act]; rh = card.info['rh']
        pts = [Y.map_point(card, q, x, y) for x, y in [(40, ry + 8), (860, ry + 8), (860, ry + rh - 8), (40, ry + rh - 8)]]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        img = Y.zoom_callout(img, (min(xs), min(ys), max(xs), max(ys)), (Y.W // 2, 1400), 1.05, (t - ROWS[act][3]) / 0.4)
    img = Y.camera(img, t, CUTS[2], punches=[T(22), T(25), T(28), T(30), T(32), T(38), T(39)], shakes=[T(30), T(38)])
    img = Y.color_flash(img, t, [T(22), T(30)], Y.GOLD, 0.14, 0.3)
    return Y.color_flash(img, t, [T(38)], Y.RED, 0.12, 0.3), True
ev(CUTS[2], 'swipe'); ev(CUTS[2] + 0.05, 'whoosh', 0.6); ev(T(20), 'pop'); ev(T(22), 'ding', 0.6)
for _, _, _, t0 in ROWS: ev(t0, 'click', 0.8); ev(t0 + 0.05, 'pop_hi', 0.6); ev(t0 + 0.15, 'swoosh_up', 0.4)
ev(T(30), 'whoosh', 0.7); ev(T(30) + 0.05, 'pop'); ev(T(38), 'stamp', 0.6); ev(T(39), 'whoosh', 0.6); ev(T(39) + 0.05, 'pop')

# ---------- S4 NOTTE: se l'inflazione esce più alta ----------
def s4(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 45, 17, Y.GOLD, 45); img = Y.light_beams(img, t + 2, n=2, strength=16)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('se', 'serif', 100, Y.MUTE), ("L'INFLAZIONE", 'big', 120, Y.WHITE)], 380), t, T(43), enter='drop', idle='float', seed=18)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('esce più', 'serif', 90, Y.MUTE), ('ALTA', 'big', 130, Y.RED)], 540), t, T(45), enter='left', idle='float', seed=19)
    img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('delle', 'serif', 80, Y.MUTE), ('ATTESE', 'big', 100, Y.WHITE)], 670), t, T(48), 0.35, 'float', 20)
    d = ImageDraw.Draw(img)
    if t > T(46): Y.dashed_arrow(d, 250, 760, 250, 470, Y.ease((t - T(46)) / 0.5), Y.RED)
    if t > T(50):
        img = Y.pulse_rings(img, Y.W // 2, 860, t - T(50), Y.GOLD, 1.3, 2, 360)
        img = SP(img, lambda b: Y.glow_text(b, "L'ORO", (Y.W // 2, 860), 200, Y.GOLD, (130, 90, 20)), t, T(50), enter='stamp', idle='breathe', seed=21, dur=0.35)
    d = ImageDraw.Draw(img)
    if t > T(51): Y.dashed_arrow(d, Y.W // 2, 980, Y.W // 2, 1160, Y.ease((t - T(51)) / 0.6), Y.RED)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('può', 'serif', 90, Y.MUTE), ('SCENDERE', 'big', 130, Y.RED)], 1290), t, T(51), enter='rise', idle='float', seed=22)
    img = SP(img, lambda b: Y.stamp(b, 'ANCORA', (Y.W // 2, 1400), 100, Y.RED, -4), t, T(53), enter='stamp', idle='wobble', seed=23, dur=0.3, amp=0.4)
    img = Y.camera(img, t, CUTS[3], punches=[T(45), T(50), T(52), T(53)], shakes=[T(45), T(53)])
    img = Y.color_flash(img, t, [T(50)], Y.GOLD, 0.14, 0.3)
    return Y.color_flash(img, t, [T(45), T(53)], Y.RED, 0.14, 0.3), True
ev(CUTS[3] + 0.05, 'swoosh_up', 0.6); ev(T(43), 'pop'); ev(T(45), 'boom', 0.6); ev(T(46), 'swoosh_up', 0.6); ev(T(48), 'whoosh', 0.5)
ev(T(50), 'boom', 0.7); ev(T(50), 'ding', 0.6); ev(T(51), 'swipe', 0.6); ev(T(52), 'pop'); ev(T(53), 'stamp'); ev(T(53) + 0.05, 'glitch', 0.4)

# ---------- S5 NOTTE: supporto e resistenza ----------
YR, YS = 700, 1230; YP = YS - (3538 - 3500) / 100 * (YS - YR)
def s5(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 45, 17, Y.GOLD, 45); img = Y.spotlight(img, Y.W // 2, 60, 1250, 620, 40)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('il', 'serif', 90, Y.MUTE), ('SUPPORTO', 'big', 120, Y.GOLD)], 330), t, T(54), enter='drop', idle='float', seed=25)
    img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('da', 'serif', 80, Y.MUTE), ('GUARDARE', 'big', 110, Y.WHITE)], 460), t, T(56), 0.35, 'float', 26)
    d = ImageDraw.Draw(img)
    def dline(y, col, a):
        xe = 120 + 840 * a; off = int(t * 40) % 30
        for xx in range(120 - off, int(xe), 30):
            if xx >= 120: d.line([(xx, y), (min(xx + 18, xe), y)], fill=col, width=6)
    if t > T(59):
        dline(YS, Y.GOLD, Y.ease((t - T(59)) / 0.4)); img = Y.pulse_rings(img, Y.W // 2, YS, t - T(59), Y.GOLD, 1.3, 2, 380)
        img = SP(img, lambda b: Y.number_roll(b, '3.500', (Y.W // 2, YS + 110), 150, Y.GOLD, t, T(59), 0.6), t, T(59), enter='stamp', idle='breathe', seed=27, dur=0.3)
    d = ImageDraw.Draw(img)
    if t > T(59):
        yp = YP + 8 * math.sin(t * 3)
        img = Y.pulse_rings(img, 300, yp, t, Y.WHITE, 1.0, 2, 90, 3)
        img = Y.glow_text(img, '•', (300, yp - 8), int(110 + 12 * math.sin(t * 6)), Y.WHITE, (120, 120, 160))
    d = ImageDraw.Draw(img)
    if t > T(60):
        Y.dashed_arrow(d, 300, YP - 50, 300, YR + 40, Y.ease((t - T(60)) / 0.6), Y.GREEN)
        img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('SOPRA', 'big', 90, Y.GREEN)], YP + 20, cx=560), t, T(60), enter='left', idle='float', seed=28)
    d = ImageDraw.Draw(img)
    if t > T(62):
        dline(YR, Y.RED, Y.ease((t - T(62)) / 0.4))
        img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('la', 'serif', 70, Y.MUTE), ('RESISTENZA', 'big', 90, Y.RED)], YR - 40), t, T(62), enter='drop', idle='float', seed=29)
    img = SP(img, lambda b: Y.number_roll(b, '3.600', (Y.W // 2, YR + 110), 150, Y.RED, t, T(64), 0.5), t, T(64), enter='stamp', idle='breathe', seed=30, dur=0.3)
    img = Y.camera(img, t, CUTS[4], punches=[T(57), T(59) + 0.6, T(62), T(64) + 0.5], shakes=[T(59) + 0.6])
    img = Y.color_flash(img, t, [T(59) + 0.6], Y.GOLD, 0.15, 0.32)
    return Y.color_flash(img, t, [T(64) + 0.5], Y.RED, 0.14, 0.28), True
ev(CUTS[4], 'swoosh_up', 0.6); ev(T(54), 'pop'); ev(T(57), 'swoosh_up', 0.5); ev(T(57) + 0.05, 'pop_hi', 0.6)
[ev(T(59) + k * 0.07, 'tick', 0.5) for k in range(8)]; ev(T(59) + 0.6, 'boom', 0.7); ev(T(59) + 0.6, 'ding', 0.7)
ev(T(60), 'whoosh', 0.6); ev(T(60) + 0.05, 'pop'); ev(T(62), 'swipe', 0.6); ev(T(62) + 0.05, 'pop_hi'); [ev(T(64) + k * 0.07, 'tick', 0.5) for k in range(7)]; ev(T(64) + 0.5, 'stamp', 0.8)

# ---------- S6 CTA ----------
CTA_T = [T(70), T(73), T(75), T(80)]
def s6(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 50, 17, Y.GOLD, 55)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('se ti è stata', 'serif', 90, Y.WHITE), ('UTILE', 'big', 110, Y.GOLD)], 420), t, CUTS[5], enter='drop', idle='float', seed=33)
    img = Y.cta_four(img, t, CTA_T, 'SOPRA/SOTTO', y0=640)
    return Y.camera(img, t, CUTS[5], punches=CTA_T, push=0.03), True
ev(CUTS[5], 'swoosh_up'); ev(T(69), 'pop'); ev(CTA_T[0], 'pop'); ev(CTA_T[1], 'pop_hi'); ev(CTA_T[1] + 0.05, 'bubble', 0.6); ev(CTA_T[2], 'bubble'); ev(T(76), 'pop', 0.5); ev(T(78), 'pop', 0.5); ev(CTA_T[3], 'swoosh_up'); ev(CTA_T[3] + 0.1, 'coin')

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
NAME = 'yardfx_anteprima_23nov'
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
