"""News day verbali FED 18/11/2026 (minuti della riunione di ottobre, ore 20:00), pubblicato alle 18:00 — voce Enea.
Ricetta NEWS: Notte -> Terminale -> Quaderno -> Notte. Ogni scena parte sulla prima parola del suo paragrafo.
S1 NOTTE     T0   STASERA · 20:00 gigante con orologio e faretto · cosa pensa davvero la FED
S2 TERMINALE T9   ESCONO i VERBALI · scheda calendario in prospettiva (20:00 Verbali FED) · RIUNIONE DI OTTOBRE · DUE membri · timbro ALZARE I TASSI
S3 NOTTE     T23  il mercato SCOMMETTE · RIALZO · a DICEMBRE · linea luminosa 3.800 sfondata dal prezzo · IL MINIMO DA UN ANNO
S4 QUADERNO  T44  se LINEA DURA: catena FED -> dollaro sale -> oro sotto pressione · se PIÙ MORBIDI: l'oro può respirare · timbro DI SOLITO, NON SEMPRE
S5 TERMINALE T70  il LIVELLO da GUARDARE: grafico a candele sotto 3.800 · sondaggio SOPRA / SOTTO
S6 NOTTE     T82  se ti è stata UTILE + 4 paletti (scrivi SOPRA/SOTTO) · outro logo + Telegram"""
import sys, os, math, json, random
sys.path.insert(0, '/home/user/bot-telegram/contenuti/yardfx_video'); import yardfx as Y; import suoni as S
from PIL import Image, ImageDraw
D = os.path.dirname(os.path.abspath(__file__))
WORDS = json.load(open(os.path.join(D, 'words.json')))
for i, s in [(38, '3.800:'), (75, '3.800.')]: WORDS[i][0] = s
G = Y.make_groups(WORDS)
T = lambda i: WORDS[i][1]
VEND = WORDS[-1][2]
KEYS = {2, 8, 11, 15, 16, 20, 28, 30, 35, 38, 40, 50, 53, 58, 62, 65, 69, 73, 75, 78, 81}
CUTS = [0, T(9), T(23), T(44), T(70), T(82), VEND + 0.3]
OUT_LEN = 4.2; DUR = CUTS[-1] + OUT_LEN
TRANS = ['whip', 'zoom', 'wipe', 'blur', 'whip_v']
TD = 0.4; TIKTOK = os.environ.get('TIKTOK') == '1'
EV = []
def ev(t, n, g=1.0): EV.append((round(t, 3), n, g))
SP = Y.sprite
def big(b, s, xy, size, col, font=Y.BIG): ImageDraw.Draw(b).text(xy, s, font=Y.F(font, size), fill=col, anchor='mm')

# ---------- S1 NOTTE: stasera alle 20 ----------
def s1(t):
    img = Y.night_bg(t); img = Y.light_beams(img, t); img = Y.dust(img, t, 45, 3, Y.GOLD, 40)
    img = Y.spotlight(img, Y.W // 2 + 50 * math.sin(t * 1.2), 90, 1000, 560, 55)
    img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('STASERA', 'big', 150, Y.WHITE), ('alle', 'serif', 110, Y.MUTE)], 430), t, -0.4, 0.45, 'float', 1)
    img = SP(img, lambda b: Y.clock_hands(b, Y.W // 2, 590, 90, t, Y.GOLD, 0.8), t, -0.3, enter='spin', idle='float', seed=2)
    if t > T(2): img = Y.pulse_rings(img, Y.W // 2, 820, t - T(2), Y.GOLD, 1.3, 3, 520)
    img = SP(img, lambda b: Y.glow_text(b, '20:00', (Y.W // 2, 820), 290, Y.GOLD, (130, 90, 20)), t, T(2), enter='stamp', idle='breathe', seed=3, dur=0.35)
    img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('leggiamo cosa pensa', 'serif', 84, Y.WHITE)], 1080), t, T(3), 0.4, 'float', 4)
    img = SP(img, lambda b: big(b, 'DAVVERO', (Y.W // 2, 1180), 110, Y.WHITE), t, T(6), enter='pop', idle='wobble', seed=5, amp=0.5)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'LA FED', (Y.W // 2, 1340), 110, Y.ease((t - T(7)) / 0.35)), t, T(7), enter='stamp', idle='breathe', seed=6, dur=0.3)
    img = Y.camera(img, t, 0, punches=[T(2), T(6), T(8)], shakes=[T(2)])
    return Y.color_flash(img, t, [T(2), T(8)], Y.GOLD, 0.15, 0.35), True
ev(0, 'boom', 0.7); ev(0.05, 'whoosh', 0.6); [ev(0.1 + k * 0.25, 'tick', 0.35) for k in range(4)]; ev(T(2), 'boom', 0.8); ev(T(2), 'ding', 0.7); ev(T(3), 'swoosh_up', 0.5); ev(T(6), 'pop'); ev(T(7), 'stamp', 0.8)

# ---------- S2 TERMINALE: i verbali ----------
QUAD = [(110, 450), (980, 480), (990, 800), (100, 780)]
def s2(t):
    img = Y.term_bg(); img = Y.light_sweep(img, t, 3.2, 200, 35); img = Y.dust(img, t, 30, 7, Y.ICE, 30)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('escono i', 'serif', 86, Y.MUTE), ('VERBALI', 'big', 120, Y.WHITE)], 340), t, T(9), enter='drop', idle='float', seed=7)
    rows = [[('20:00', Y.GOLD), 'Verbali FED' if t > T(11) else '']]
    card = Y.ui_card(rows, ['', ''], '', 900, highlight=0 if t > T(11) else None, col_w=[220, 680])
    img = Y.perspective(img, card, Y.card_flip_quad(QUAD, t, CUTS[1]))
    if t > T(11): img = Y.pulse_rings(img, 200, 670, t - T(11), Y.GOLD, 1.2, 2, 140, 3)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('della riunione di', 'serif', 74, Y.MUTE), ('OTTOBRE', 'big', 100, Y.GOLD)], 960), t, T(13), enter='right', idle='float', seed=8)
    def due(b):
        d = ImageDraw.Draw(b); Y.icon(d, 'persone', 330, 1130, 150, Y.ease((t - T(16)) / 0.5), Y.WHITE, 7, 9)
        Y.mixed_title(d, [('DUE', 'big', 120, Y.WHITE), ('membri', 'serif', 90, Y.MUTE)], 1170, cx=650)
    img = SP(img, due, t, T(16), enter='pop', idle='float', seed=9)
    img = SP(img, lambda b: Y.stamp(b, 'VOLEVANO GIÀ ALZARE I TASSI', (Y.W // 2, 1360), 66, Y.RED, -3), t, T(20), enter='stamp', idle='wobble', seed=10, dur=0.3, amp=0.4)
    img = Y.camera(img, t, CUTS[1], punches=[T(11), T(15), T(16), T(20)], shakes=[T(20)])
    img = Y.color_flash(img, t, [T(11)], Y.GOLD, 0.14, 0.3)
    return Y.color_flash(img, t, [T(20)], Y.RED, 0.15, 0.3), True
ev(CUTS[1], 'swipe'); ev(CUTS[1] + 0.05, 'whoosh', 0.6); ev(T(9), 'pop'); ev(T(11), 'click', 0.8); ev(T(11) + 0.05, 'ding', 0.6); ev(T(13), 'swipe', 0.6); ev(T(15), 'pop_hi', 0.6)
ev(T(16), 'pop'); ev(T(17), 'bubble', 0.6); ev(T(20), 'stamp'); ev(T(20) + 0.05, 'glitch', 0.4)

# ---------- S3 NOTTE: sotto i 3.800 ----------
YL = 1010
def s3(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 45, 13, Y.GOLD, 45); img = Y.light_beams(img, t + 2, n=2, strength=16)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('il mercato', 'serif', 84, Y.MUTE), ('SCOMMETTE', 'big', 110, Y.WHITE)], 320), t, T(23), enter='drop', idle='float', seed=11)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'UN RIALZO', (Y.W // 2, 455), 84, Y.ease((t - T(28)) / 0.35), Y.RED, Y.WHITE), t, T(28), enter='pop', idle='breathe', seed=12)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('a', 'serif', 80, Y.MUTE), ('DICEMBRE', 'big', 100, Y.GOLD)], 610), t, T(30), enter='right', idle='float', seed=13)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [("oggi l'oro è", 'serif', 80, Y.WHITE), ('SCESO', 'big', 110, Y.RED)], 750), t, T(31), enter='rise', idle='float', seed=14)
    if t > T(35):
        d = ImageDraw.Draw(img); a = Y.ease((t - T(35)) / 0.4); off = int(t * 40) % 30
        for xx in range(100 - off, int(100 + 880 * a), 30):
            if xx >= 100: d.line([(xx, YL), (min(xx + 18, 980), YL)], fill=Y.GOLD, width=6)
        img = Y.pulse_rings(img, Y.W // 2, YL, t - T(35), Y.GOLD, 1.3, 2, 360)
    if t > T(33):
        p = Y.ease((t - T(33)) / 1.6)
        pts = [(100 + 880 * k / 40, 830 + 300 * (k / 40) ** 1.4 + 22 * math.sin(k * 1.3)) for k in range(41)]
        k = max(2, int(len(pts) * p)); d = ImageDraw.Draw(img); d.line(pts[:k], fill=Y.RED, width=8, joint='curve')
        img = Y.glow_text(img, '•', (pts[k - 1][0], pts[k - 1][1] - 8), int(100 + 10 * math.sin(t * 6)), Y.WHITE, (160, 60, 60))
    img = SP(img, lambda b: Y.number_roll(b, 'SOTTO I 3.800', (Y.W // 2, 1250), 110, Y.RED, t, T(38), 0.6), t, T(36), enter='stamp', idle='breathe', seed=15, dur=0.3)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'IL MINIMO DA UN ANNO', (Y.W // 2, 1420), 64, Y.ease((t - T(40)) / 0.4)), t, T(40), enter='pop', idle='breathe', seed=16)
    img = Y.camera(img, t, CUTS[2], punches=[T(25), T(28), T(30), T(35), T(38) + 0.6, T(40)], shakes=[T(38) + 0.6])
    img = Y.color_flash(img, t, [T(28), T(38) + 0.6], Y.RED, 0.15, 0.3)
    return img, True
ev(CUTS[2] + 0.05, 'swoosh_up', 0.6); ev(T(23), 'pop'); ev(T(25), 'swipe', 0.5); ev(T(28), 'pop_hi'); ev(T(28), 'alert', 0.5); ev(T(30), 'swipe', 0.6); ev(T(31), 'whoosh', 0.5); ev(T(33), 'riser', 0.3)
ev(T(35), 'pop', 0.7); [ev(T(38) + k * 0.07, 'tick', 0.5) for k in range(9)]; ev(T(38) + 0.6, 'boom', 0.8); ev(T(40), 'stamp', 0.7)

# ---------- S4 QUADERNO: i due scenari ----------
CH = [(250, 'banca', 'linea dura', T(49)), (540, 'dollaro', 'dollaro sale', T(52)), (830, 'lingotto', 'oro sotto pressione', T(55))]
def s4(t):
    img = Y.grid_paper()
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('se i verbali', 'serif', 86, Y.INK), ('CONFERMANO', 'big', 100, Y.RED)], 320), t, T(44), enter='drop', idle='float', seed=17)
    for k, (x, ic, lab, t0) in enumerate(CH):
        if t < t0: continue
        def dr(b, x=x, ic=ic, lab=lab, t0=t0, k=k):
            d = ImageDraw.Draw(b); col = Y.RED if ic == 'lingotto' else Y.INK
            Y.icon(d, ic, x, 520, 150, Y.ease((t - t0) / 0.5), col, 7, 10 + k * 9)
            d.text((x, 650), lab, font=Y.F(Y.SERIF, 50 if k < 2 else 44), fill=col, anchor='mm')
        img = SP(img, dr, t, t0, enter='pop', idle='float', seed=21 + k, anchor=(x, 520))
        if k: Y.dashed_arrow(ImageDraw.Draw(img), CH[k - 1][0] + 105, 520, x - 105, 520, Y.ease((t - t0) / 0.4), Y.MUTE)
    if t > T(59):
        img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('se sono', 'serif', 86, Y.INK), ('PIÙ MORBIDI', 'big', 100, Y.GREEN_K)], 860), t, T(59), enter='drop', idle='float', seed=24)
        def gr(b):
            d = ImageDraw.Draw(b); Y.icon(d, 'lingotto', 380, 1050, 190, Y.ease((t - T(63)) / 0.5), Y.GOLDK, 8, 70)
            Y.icon(d, 'grafico_su', 610, 1030, 130, Y.ease((t - T(64)) / 0.5), Y.GREEN_K, 8, 71)
            Y.hand(d, "l'oro può respirare", (Y.W // 2, 1180), 70, Y.GREEN_K, Y.ease((t - T(63)) / 0.8))
        if t > T(63): img = SP(img, gr, t, T(63), enter='pop', idle='float', seed=25)
    img = SP(img, lambda b: Y.stamp(b, 'DI SOLITO, NON SEMPRE', (Y.W // 2, 1370), 70, Y.GOLDK, -5), t, T(66), enter='stamp', idle='wobble', seed=26, dur=0.3, amp=0.4)
    img = Y.camera(img, t, CUTS[3], punches=[T(47), T(52), T(56), T(62), T(65), T(68)], shakes=[T(56), T(68)], push=0.04)
    img = Y.color_flash(img, t, [T(49), T(57)], Y.RED, 0.15, 0.25); img = Y.color_flash(img, t, [T(62)], Y.GREEN, 0.15, 0.25)
    return img, False
ev(CUTS[3], 'whoosh', 0.7); ev(T(44), 'swoosh_up'); ev(T(47), 'pop')
for x, ic, lab, t0 in CH: ev(t0, 'bubble'); ev(t0 + 0.1, 'swipe', 0.4)
ev(T(57), 'boom', 0.6); ev(T(59), 'swoosh_up'); ev(T(62), 'pop_hi'); ev(T(63), 'trin', 0.6); ev(T(65), 'ding', 0.5); ev(T(66), 'stamp'); ev(T(68), 'pop', 0.5)

# ---------- S5 TERMINALE: il livello e il sondaggio ----------
def _cs():
    r = random.Random(11); cs = []; p = 3868
    for v in [3872, 3866, 3858, 3861, 3852, 3846, 3849, 3840, 3834, 3838, 3829, 3821, 3824, 3815, 3808, 3812, 3803, 3796, 3789, 3793, 3784, 3778, 3786, 3792]:
        o = p; c = v + r.uniform(-1.5, 1.5); h = max(o, c) + r.uniform(1, 5); l = min(o, c) - r.uniform(1, 5)
        cs.append({'o': o, 'h': h, 'l': l, 'c': c, 'g': c > o}); p = c
    return cs
CS = _cs()
def s5(t):
    img = Y.term_bg(); img = Y.light_sweep(img, t + 1.3, 3.4, 200, 30); img = Y.dust(img, t, 25, 11, Y.ICE, 30)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('il', 'serif', 86, Y.MUTE), ('LIVELLO', 'big', 120, Y.WHITE)], 320), t, T(70), enter='drop', idle='float', seed=27)
    img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('da', 'serif', 76, Y.MUTE), ('GUARDARE', 'big', 100, Y.GOLD)], 440), t, T(72), 0.35, 'float', 28)
    def chart(b):
        lv = [(3800, '3.800', Y.GOLD)] if t > T(75) else []
        py = Y.candles_chart(b, CS, (130, 560, 950, 1110), 3765, 3885, (t - CUTS[4]) / 1.2, levels=lv)
        if t > CUTS[4] + 1.2:
            step = (950 - 130) / len(CS); x = 130 + 12 + (len(CS) - 1) * step; y = py(CS[-1]['c'])
            return x, y
    holder = {}
    img = SP(img, lambda b: holder.update(p=chart(b)), t, CUTS[4], enter='rise', idle='float', seed=29, amp=0.3)
    if holder.get('p'): img = Y.pulse_rings(img, holder['p'][0], holder['p'][1], t, Y.WHITE, 1.0, 2, 80, 3)
    if t > T(75): img = Y.pulse_rings(img, Y.W // 2, 560 + (3885 - 3800) / 120 * 550, t - T(75), Y.GOLD, 1.3, 2, 300)
    for i, (txt, col, t0, ent) in enumerate([('SOPRA', Y.GREEN, T(78), 'left'), ('SOTTO', Y.RED, T(81), 'right')]):
        def box(b, i=i, txt=txt, col=col):
            d = ImageDraw.Draw(b); x0 = 70 + i * 540
            d.rounded_rectangle((x0, 1230, x0 + 400, 1410), radius=30, fill=tuple(int(v * .25) for v in col), outline=col, width=5)
            d.text((x0 + 200, 1320), txt, font=Y.F(Y.BIG, 86), fill=col, anchor='mm')
        img = SP(img, box, t, t0, enter=ent, idle='sway', seed=30 + i, amp=0.6)
    if t > T(79): ImageDraw.Draw(img).text((Y.W // 2, 1320), 'o', font=Y.F(Y.SERIF, 70), fill=Y.WHITE, anchor='mm')
    img = Y.camera(img, t, CUTS[4], punches=[T(73), T(75), T(78), T(81)], shakes=[T(75)])
    img = Y.color_flash(img, t, [T(75)], Y.GOLD, 0.15, 0.3); img = Y.color_flash(img, t, [T(78)], Y.GREEN, 0.14, 0.28)
    return Y.color_flash(img, t, [T(81)], Y.RED, 0.14, 0.28), True
ev(CUTS[4], 'swipe'); ev(CUTS[4] + 0.05, 'swoosh_up', 0.5); [ev(CUTS[4] + 0.1 + k * 0.1, 'tick', 0.3) for k in range(10)]; ev(T(72), 'pop_hi', 0.6); ev(T(75), 'ding'); ev(T(75) + 0.05, 'boom', 0.5)
ev(T(76), 'click', 0.6); ev(T(78), 'pop_hi'); ev(T(78) + 0.05, 'swipe', 0.6); ev(T(81), 'pop'); ev(T(81) + 0.05, 'swipe', 0.6)

# ---------- S6 CTA ----------
CTA_T = [T(87), T(90), T(92), T(97)]
def s6(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 50, 17, Y.GOLD, 55)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('se ti è stata', 'serif', 90, Y.WHITE), ('UTILE', 'big', 110, Y.GOLD)], 420), t, CUTS[5], enter='drop', idle='float', seed=33)
    img = Y.cta_four(img, t, CTA_T, 'SOPRA/SOTTO', y0=640)
    return Y.camera(img, t, CUTS[5], punches=CTA_T, push=0.03), True
ev(CUTS[5], 'swoosh_up'); ev(T(86), 'pop'); ev(CTA_T[0], 'pop'); ev(CTA_T[1], 'pop_hi'); ev(CTA_T[1] + 0.05, 'bubble', 0.6); ev(CTA_T[2], 'bubble'); ev(T(93), 'pop', 0.5); ev(T(95), 'pop', 0.5); ev(CTA_T[3], 'swoosh_up'); ev(CTA_T[3] + 0.1, 'coin')

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
NAME = 'yardfx_verbali_fed_18nov'
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
