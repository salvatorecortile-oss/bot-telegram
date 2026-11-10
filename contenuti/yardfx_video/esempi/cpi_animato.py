"""Video post CPI 10/11 — versione ANIMATA con musica ed effetti sonori.
Ogni oggetto entra con rimbalzo e poi si muove sempre (galleggia, pulsa, oscilla); camera viva con colpi di zoom e scosse;
flash sui momenti forti; transizioni strisciata / zoom dentro / tendina; sottotitoli che saltano; effetti sonori su ogni comparsa."""
import sys, os, math, json
sys.path.insert(0, '/home/user/bot-telegram/contenuti/yardfx_video'); import yardfx as Y; import suoni as S
from PIL import Image, ImageDraw
D = os.path.dirname(os.path.abspath(__file__)); SRC = os.path.join(D, '..', 'd10post')
WORDS = Y.load_words(os.path.join(SRC, 'voce_words.json')); G = Y.make_groups(WORDS)
T = lambda i: WORDS[i][1]
VEND = WORDS[-1][2]; DUR = VEND + 3.0
KEYS = {5, 15, 31, 42, 50, 54, 60, 63, 71, 77, 85, 89, 97, 99}
CUTS = [0, T(20), T(43), T(64), T(86), T(94), VEND + 0.35]
TRANS = ['whip_v', 'blur', 'wipe', 'whip', 'zoom', 'flash']
TD = 0.4
EV = []                                   # effetti sonori (tempo, nome, volume)
def ev(t, name, g=1.0): EV.append((round(t, 3), name, g))
SP = lambda img, fn, t, t0, **k: Y.sprite(img, fn, t, t0, **k)

# ---------------- S1 NOTTE: il gancio ----------------
def s1(t):
    img = Y.night_bg(t); img = Y.light_beams(img, t); img = Y.dust(img, t, 45, 3, Y.GOLD, 40)
    if t > T(4): img = Y.pulse_rings(img, Y.W // 2, 815, t - T(4), Y.GOLD, 1.3, 3, 520)
    img = Y.spotlight(img, Y.W // 2 + 60 * math.sin(t * 1.3), 100, 560, 440, 65)
    img = SP(img, lambda b: Y.glow_icon(b, 'grafico_giu', Y.W // 2, 360, 190, min(1, (t + 0.3) / 0.7), Y.RED, 9), t, -0.3, enter='drop', idle='wobble', amp=0.6)
    img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('il', 'serif', 110, Y.WHITE), ('CPI', 'big', 135, Y.WHITE), ('è', 'serif', 110, Y.WHITE)], 680), t, -0.4, 0.45, 'float', 1)
    img = SP(img, lambda b: Y.glow_text(b, 'PIÙ ALTO', (Y.W // 2, 815), 215, Y.GOLD, (130, 90, 20)), t, T(4) - 0.05, enter='stamp', idle='breathe', seed=2, dur=0.35)
    img = SP(img, lambda b: Y.stamp(b, 'SOPRA LE ATTESE', (Y.W // 2 + 60, 1010), 76, Y.RED, -6), t, T(6), enter='stamp', idle='wobble', seed=3, dur=0.3, amp=0.5)
    if t > T(12) - 0.02:
        img = SP(img, lambda b: Y.number_roll(b, '−30 $', (Y.W // 2, 1250), 240, Y.RED, t, T(12), 0.55), t, T(12), enter='pop', idle='wobble', seed=4, amp=0.7)
    img = SP(img, lambda b: Y.hand(ImageDraw.Draw(b), 'subito dopo il dato', (Y.W // 2, 1400), 66, Y.WHITE, Y.ease((t - T(16)) / 0.6)), t, T(16), enter='rise', idle='float', seed=5)
    img = Y.camera(img, t, 0, punches=[T(4), T(12) + 0.55], shakes=[T(6), T(12) + 0.55])
    img = Y.flash(img, t, [T(12) + 0.55], 0.12, (255, 90, 70), 0.45)
    img = Y.color_flash(img, t, [T(4)], Y.GOLD, 0.16, 0.4)
    return img, True
ev(0.0, 'boom', 0.7); ev(0.05, 'whoosh', 0.6); ev(T(4) - 0.05, 'boom'); ev(T(4), 'pop'); ev(T(6), 'stamp')
for k in range(9): ev(T(12) + k * 0.06, 'tick', 0.7)
ev(T(12) + 0.55, 'boom'); ev(T(12) + 0.55, 'glitch', 0.6); ev(T(16), 'swoosh_up', 0.6)

# ---------------- S2 TERMINALE: i numeri ----------------
CARD = Y.ui_card([['14:30', 'CPI USA m/m', '0,3%', ('0,4%', Y.RED)], ['14:30', 'CPI core m/m', '0,2%', ('0,3%', Y.RED)], ['ven 13', 'PPI USA m/m', '—', '—']],
                 ['QUANDO', 'EVENTO', 'ATTESA', 'USCITO'], 'calendario economico · mar 10 nov', 940, highlight=0, col_w=[170, 390, 180, 180])
QUAD = [(120, 420), (1000, 470), (1010, 980), (70, 940)]
def quad_at(t, s):
    a = Y.back(s / 0.6); wob = [(14 * math.sin(t * 1.4 + i), 10 * math.cos(t * 1.1 + i * 2)) for i in range(4)]
    return [(x + dx, y + dy + 700 * (1 - a)) for (x, y), (dx, dy) in zip(QUAD, wob)]
def s2(t):
    s = t - CUTS[1]; img = Y.term_bg(); img = Y.light_sweep(img, t, 3.2, 200, 40); img = Y.dust(img, t, 30, 7, Y.ICE, 30)
    d = ImageDraw.Draw(img); Y.chapter_candles(d, 2, 5, True, 'due: i numeri', Y.ease(s / 0.5))
    img = SP(img, lambda b: Y.price_widget(ImageDraw.Draw(b), 4085 - 35 * Y.ease((t - CUTS[1]) / 3) - 2 * math.sin(t * 3), -1.3 - 0.8 * Y.ease((t - CUTS[1]) / 3)), t, CUTS[1] + 0.15, enter='right', idle='breathe', amp=0.4)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('ottobre,', 'serif', 86, Y.MUTE), ('PREZZI USA', 'big', 96, Y.WHITE)], 340), t, CUTS[1] + 0.05, enter='left', idle='float', seed=6)
    q = Y.card_flip_quad(QUAD, t, CUTS[1] + 0.2); img = Y.perspective(img, CARD, q)
    if t > T(29):
        ry = CARD.info['row_y'][0]; rh = CARD.info['rh']
        p0 = Y.map_point(CARD, q, 560, ry + 5); p1 = Y.map_point(CARD, q, 930, ry + rh - 5)
        img = SP(img, lambda b: Y.zoom_callout(b, (p0[0] - 10, p0[1] - 8, p1[0] + 6, p1[1] + 8), (Y.W // 2 + 100, 1170), 1.9, 1), t, T(29), enter='pop', idle='breathe', seed=7, amp=0.8)
    if t > T(29): d = ImageDraw.Draw(img); Y.type_text(d, '> CPI USA m/m: 0,4% (attese 0,3%)', (80, 1440), 34, Y.GOLD, t, T(31), 26)
    if t > T(38): img = SP(img, lambda b: Y.chip(ImageDraw.Draw(b), 'SOPRA LE ATTESE', (80, 1335), ok=False), t, T(38), enter='left', idle='wobble', seed=8, amp=0.4)
    img = Y.camera(img, t, CUTS[1], punches=[T(31), T(38)], shakes=[T(31)])
    img = Y.color_flash(img, t, [T(31)], Y.RED, 0.15, 0.3)
    return img, True
[ev(T(31) + k * 0.04, 'click', 0.35) for k in range(0, 32, 2)]; ev(CUTS[1] + 0.05, 'swipe'); ev(CUTS[1] + 0.15, 'pop'); ev(CUTS[1] + 0.2, 'swoosh_up', 0.8); ev(T(29), 'pop_hi'); ev(T(31), 'ding', 0.9); ev(T(38), 'alert', 0.9)

# ---------------- S3 QUADERNO: il perché ----------------
STEPS = [(250, 560, 'prezzo', 'prezzi su', T(43)), (830, 560, 'banca', 'FED: tassi su?', T(50)), (830, 1000, 'dollaro', 'dollaro forte', T(58)), (250, 1000, 'lingotto', 'oro giù', T(62))]
def s3(t):
    s = t - CUTS[2]; img = Y.grid_paper(); d = ImageDraw.Draw(img)
    Y.chapter_candles(d, 3, 5, False, 'tre: il perché', Y.ease(s / 0.5))
    img = Y.blur_in(img, lambda b: Y.serif_heading(ImageDraw.Draw(b), 'tre:', 'PERCHÉ SCENDE', 300), t, CUTS[2] + 0.1, 0.4, 'float', 9, 0.6)
    Y.underline(ImageDraw.Draw(img), 300, 900, 330, Y.ease((s - 0.4) / 0.5), Y.GOLD)
    for k, (x, y, ic, lab, t0) in enumerate(STEPS):
        if t < t0: continue
        col = Y.GOLDK if ic == 'lingotto' else Y.INK
        def draw(b, x=x, y=y, ic=ic, lab=lab, t0=t0, k=k, col=col):
            dd = ImageDraw.Draw(b); Y.icon(dd, ic, x, y, 190 if ic != 'lingotto' else 230, Y.ease((t - t0) / 0.5), col, 7, 10 + k * 9)
            dd.text((x, y + 160), lab, font=Y.F(Y.SERIF, 64), fill=Y.RED if ic == 'lingotto' else Y.INK, anchor='mm')
        img = SP(img, draw, t, t0, enter='pop', idle='float', seed=10 + k, anchor=(x, y))
        if k:
            px, py = STEPS[k - 1][0], STEPS[k - 1][1]; a = Y.ease((t - t0) / 0.4); dd = ImageDraw.Draw(img)
            if py == y: Y.dashed_arrow(dd, px + 150, y, x - 150, y, a, Y.MUTE)
            else: Y.dashed_arrow(dd, x, py + 210, x, y - 140, a, Y.MUTE) if x == px else Y.dashed_arrow(dd, px - 150, y, x + 150, y, a, Y.MUTE)
    if t > T(63):
        img = SP(img, lambda b: Y.circle(ImageDraw.Draw(b), 250, 1030, 230, 200, Y.ease((t - T(63)) / 0.5), Y.RED, 8, 31), t, T(63), enter='none', idle='wobble', amp=0.5)
        img = SP(img, lambda b: Y.stamp(b, 'ORO GIÙ', (720, 1290), 90, Y.RED, 7), t, T(63) + 0.35, enter='stamp', idle='wobble', seed=15, dur=0.3, amp=0.4)
    img = Y.camera(img, t, CUTS[2], punches=[T(50), T(58), T(63) + 0.35], shakes=[T(63) + 0.35], push=0.05)
    img = Y.color_flash(img, t, [T(63) + 0.35], Y.RED, 0.15, 0.3)
    return img, False
ev(CUTS[2] + 0.05, 'whoosh', 0.7); ev(CUTS[2] + 0.1, 'click'); 
for k, st in enumerate(STEPS): ev(st[4], 'bubble' if k % 2 else 'pop'); ev(st[4] + 0.1, 'swipe', 0.5)
ev(T(63), 'swoosh_up', 0.7); ev(T(63) + 0.35, 'stamp')

# ---------------- S4 TERMINALE: i livelli ----------------
def ladder(img, t, s):
    d = ImageDraw.Draw(img); x0, x1, y0, y1 = 120, 960, 520, 1440; lo, hi = 3950, 4200
    py = lambda p: y1 - (p - lo) / (hi - lo) * (y1 - y0)
    d.rounded_rectangle((x0 - 40, y0 - 50, x1 + 40, y1 + 50), radius=26, fill=Y.CARD, outline=Y.CARD_LINE, width=2)
    for p in range(3950, 4201, 50):
        d.line([(x0 + 150, py(p)), (x1, py(p))], fill=(40, 42, 50), width=1)
        d.text((x0 + 120, py(p)), f'{p:,}'.replace(',', '.'), font=Y.F(Y.MONO, 30), fill=Y.MUTE, anchor='rm')
    for p, lab, col, t0 in [(4000, 'LIVELLO CHIAVE', Y.GOLD, T(77)), (4150, 'RESISTENZA', Y.RED, T(80))]:
        a = Y.ease((t - t0) / 0.4)
        if a <= 0: continue
        y = py(p); xe = x0 + 150 + (x1 - x0 - 150) * a; off = int(t * 40) % 26
        for xx in range(x0 + 150 - off, int(xe), 26):
            if xx >= x0 + 150: d.line([(xx, y), (min(xx + 14, xe), y)], fill=col, width=5)
        if a >= 1:
            sc = 1 + 0.06 * math.sin(t * 5); f = Y.F(Y.COND, int(40 * sc)); tw = d.textlength(lab, font=f)
            d.rounded_rectangle((x1 - tw - 30, y - 28 * sc, x1, y + 28 * sc), radius=10, fill=col); d.text((x1 - 15, y), lab, font=f, fill=Y.DARK, anchor='rm')
    p = 4085 - 35 * Y.ease(s / 1.4) + 4 * math.sin(t * 4); y = py(p); x = x0 + 360
    d.line([(x, py(4085)), (x, y)], fill=Y.RED, width=6)
    img = Y.pulse_rings(img, x, y, t, Y.RED, 1.1, 3, 130, 3)
    img = Y.glow_text(img, '•', (x, y - 8), int(120 + 14 * math.sin(t * 6)), Y.WHITE, (120, 120, 160)); d = ImageDraw.Draw(img)
    d.text((x + 50, y), 'ORA ~4.050', font=Y.F(Y.COND, 56), fill=Y.WHITE, anchor='lm')
    if t > T(77): Y.circle(d, x0 + 520, py(4000), 330, 60, Y.ease((t - T(77)) / 0.5), Y.GOLD, 6, 41)
    return img
def s4(t):
    s = t - CUTS[3]; img = Y.term_bg(); img = Y.light_sweep(img, t + 1.5, 3.2, 200, 35); img = Y.dust(img, t, 30, 11, Y.ICE, 30)
    d = ImageDraw.Draw(img); Y.chapter_candles(d, 4, 5, True, 'quattro: i livelli', Y.ease(s / 0.5))
    img = SP(img, lambda b: Y.price_widget(ImageDraw.Draw(b), 4050.0 - 3 * math.sin(t * 3), -2.1), t, CUTS[3] + 0.1, enter='right', idle='breathe', amp=0.4)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('i livelli da', 'serif', 86, Y.MUTE), ('GUARDARE', 'big', 96, Y.WHITE)], 360), t, CUTS[3], enter='drop', idle='float', seed=16)
    img = SP(img, lambda b: ladder(b, t, s), t, CUTS[3] + 0.15, enter='rise', idle='float', seed=17, amp=0.35)
    img = Y.camera(img, t, CUTS[3], punches=[T(77), T(85)], shakes=[T(77)])
    img = Y.color_flash(img, t, [T(77)], Y.GOLD, 0.16, 0.35)
    return img, True
ev(CUTS[3] + 0.0, 'swipe'); ev(CUTS[3] + 0.1, 'pop'); ev(CUTS[3] + 0.15, 'swoosh_up'); ev(CUTS[3] + 0.3, 'whoosh', 0.5)
ev(T(77), 'ding'); ev(T(77) + 0.05, 'boom', 0.6); ev(T(80), 'swipe', 0.7); ev(T(85), 'alert', 0.8)

# ---------------- S5 NOTTE: il prossimo ----------------
def s5(t):
    s = t - CUTS[4]; img = Y.night_bg(t); img = Y.dust(img, t, 45, 13, Y.GOLD, 50)
    d = ImageDraw.Draw(img); Y.chapter_candles(d, 5, 5, True, 'cinque: il prossimo', Y.ease(s / 0.5))
    img = Y.light_beams(img, t, (200, 160, 80), 2, 20)
    img = SP(img, lambda b: Y.clock_hands(b, Y.W // 2, 330, 110, t, Y.GOLD, 0.8), t, CUTS[4], enter='spin', idle='float', seed=25)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('venerdì', 'serif', 120, Y.WHITE)], 560), t, CUTS[4] + 0.1, enter='pop', idle='float', seed=18)
    if t > T(89): img = Y.pulse_rings(img, Y.W // 2, 730, t - T(89), Y.GOLD, 1.2, 3, 480)
    img = SP(img, lambda b: Y.glow_text(b, 'PPI', (Y.W // 2, 730), 260, Y.GOLD, (130, 90, 20)), t, T(89) - 0.05, enter='spin', idle='breathe', seed=19)
    img = Y.timeline_nodes(img, [('MAR', '10', 'CPI'), ('MER', '11', ''), ('GIO', '12', ''), ('VEN', '13', 'PPI')], 1030, 3, t, CUTS[4])
    img = Y.notification(img, 'Calendario', 'Venerdì 13 · 14:30', "PPI USA: il prossimo test per l'oro", 1250 + 6 * math.sin(t * 2), (t - T(90)) / 0.4)
    img = Y.camera(img, t, CUTS[4], punches=[T(89)], shakes=[])
    return img, True
[ev(CUTS[4] + k * 0.5, 'tick', 0.6) for k in range(6)]; ev(CUTS[4], 'pop'); ev(CUTS[4] + 0.1, 'swoosh_up', 0.6); ev(T(89) - 0.05, 'boom'); ev(T(89), 'trin', 0.8); ev(T(90), 'alert')

# ---------------- S6 NOTTE: tocca a te ----------------
def s6(t):
    s = t - CUTS[5]; img = Y.night_bg(t); img = Y.dust(img, t, 50, 17, Y.GOLD, 55)
    d = ImageDraw.Draw(img); Y.chapter_candles(d, 5, 5, True, 'tocca a te', 1)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('tu cosa', 'serif', 110, Y.WHITE), ('DICI?', 'big', 130, Y.GOLD)], 560), t, CUTS[5], enter='drop', idle='float', seed=20)
    img = Y.pulse_rings(img, Y.W // 2, 880, t, Y.GOLD, 2.0, 2, 600, 3)
    for i, (txt, col, t0, ent) in enumerate([('RIMBALZO', Y.GREEN, T(97), 'left'), ('ROTTURA', Y.RED, T(99), 'right')]):
        def box(b, i=i, txt=txt, col=col):
            dd = ImageDraw.Draw(b); x0 = 70 + i * 540
            dd.rounded_rectangle((x0, 780, x0 + 400, 980), radius=30, fill=tuple(int(v * .25) for v in col), outline=col, width=5)
            dd.text((x0 + 200, 880), txt, font=Y.F(Y.BIG, 80), fill=col, anchor='mm')
        img = SP(img, box, t, t0, enter=ent, idle='sway', seed=21 + i, amp=0.6)
    if t > T(99): ImageDraw.Draw(img).text((Y.W // 2, 880), 'o', font=Y.F(Y.SERIF, 70), fill=Y.WHITE, anchor='mm')
    img = SP(img, lambda b: ImageDraw.Draw(b).text((Y.W // 2, 1060), 'dei 4.000 $', font=Y.F(Y.SERIF, 90), fill=Y.WHITE, anchor='mm'), t, T(100), enter='rise', idle='float', seed=23)
    img = SP(img, lambda b: Y.hand(ImageDraw.Draw(b), 'scrivilo nei commenti', (Y.W // 2, 1250), 72, Y.GOLD, Y.ease((t - T(102)) / 0.6)), t, T(102), enter='none', idle='float', seed=24)
    img = Y.camera(img, t, CUTS[5], punches=[T(97), T(99)], shakes=[])
    img = Y.color_flash(img, t, [T(97)], Y.GREEN, 0.15, 0.3); img = Y.color_flash(img, t, [T(99)], Y.RED, 0.15, 0.3)
    return img, True
ev(CUTS[5], 'swoosh_up'); ev(T(97), 'pop_hi'); ev(T(97) + 0.05, 'swipe', 0.6); ev(T(99), 'pop'); ev(T(99) + 0.05, 'swipe', 0.6); ev(T(100), 'click'); ev(T(102), 'bubble')

def outro(t):
    s = t - CUTS[6]; img = Y.outro(t, s); img = Y.dust(img, t, 50, 19, Y.GOLD, 60)
    img = Y.camera(img, t, CUTS[6], punches=[CUTS[6] + 0.9], push=0.08)
    return Y.flash(img, t, [CUTS[6]], 0.18), True
ev(CUTS[6], 'boom', 0.8); ev(CUTS[6] + 0.2, 'riser', 0.5); ev(CUTS[6] + 0.9, 'coin')
for i, c in enumerate(CUTS[1:-1]): ev(c - 0.15, 'whoosh', 0.9)

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
            img = {'whip': lambda: Y.whip(prev, img, p, 1), 'whip_v': lambda: Y.whip_v(prev, img, p, 1), 'blur': lambda: Y.blur_cross(prev, img, p), 'zoom': lambda: Y.zoom_through(prev, img, p), 'wipe': lambda: Y.circle_wipe(prev, img, p)}.get(kind, lambda: img)()
    img = Y.captions_pop(img, t, WORDS, G, KEYS, dark, end=VEND + 0.3)
    Y.disclaimer(ImageDraw.Draw(img), dark)
    return img

def _f(i): return frame(i / Y.FPS).tobytes()
if __name__ == '__main__':
    import subprocess
    from multiprocessing import Pool
    m = sys.argv[1]
    if m == 'preview':
        ts = [float(x) for x in sys.argv[2:]] or [0.0, 0.3, 1.5, 2.0, 5.2, 7.1, 11.0, 15.0, 22.3, 28.0, 33.5, 37.5, 40.5]
        Y.contact_sheet(frame, ts, os.path.join(D, 'preview.png'), w=180)
    else:
        n = int(DUR * Y.FPS); silent = os.path.join(D, 'video_muto.mp4')
        p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{Y.W}x{Y.H}', '-r', str(Y.FPS), '-i', '-',
                              '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', silent], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for b in pool.imap(_f, range(n), chunksize=4): p.stdin.write(b)
        p.stdin.close(); p.wait()
        S.music(os.path.join(D, 'base.wav'), DUR, 96, 'tensione')
        json.dump(EV, open(os.path.join(D, 'eventi.json'), 'w'))
        for name, voce in [('yardfx_cpi_animato.mp4', os.path.join(SRC, 'voce.mp3')), ('yardfx_cpi_animato_solo_musica.mp4', None)]:
            a = S.mix(os.path.join(D, name + '.m4a'), DUR, voce=voce, musica=os.path.join(D, 'base.wav'), eventi=EV, music_db=-16 if voce else -9)
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', silent, '-i', a, '-map', '0:v', '-map', '1:a', '-c', 'copy', '-shortest', '-movflags', '+faststart', os.path.join(D, name)], check=True)
        print('ok', DUR, len(EV), 'effetti')
