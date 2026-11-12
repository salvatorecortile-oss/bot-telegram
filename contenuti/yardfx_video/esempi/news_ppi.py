"""News day PPI 13/11/2026 — voce Enea di Salvatore. Storyboard (ogni scena parte sulla prima parola del suo paragrafo):
S1 NOTTE    T0   'dopo il CPI' → PPI gigante con onde → CONFERMA o SMENTITA?
S2 NOTTE    T9   orologio che gira con faretto, 'domani' 14:30 luminoso, 'inflazione alla produzione' a fuoco, chip OTTOBRE
S3 TERMINALE T20 SETTEMBRE: numero che conta +1,3% IN UN MESE · OTTOBRE ATTESE: +0,4% · barre di confronto
S4 QUADERNO T40  se esce PIÙ ALTA: catena FED→dollaro→oro giù · se esce PIÙ BASSA: oro respira · timbro DI SOLITO, NON SEMPRE
S5 TERMINALE T72 scala prezzi: l'oro SCESO sotto 4.000, cerchio sul livello, IL LIVELLO DA GUARDARE
S6 NOTTE    T86  tu cosa DICI? SOPRA / SOTTO
S7 NOTTE    T92  se ti è stato UTILE + 4 paletti (seguimi, mi piace, scrivi SOPRA/SOTTO, condividi)
OUTRO            logo animato + Telegram (Instagram: 'CERCAMI SU TELEGRAM'; TikTok: solo icona e @yard_fx)"""
import sys, os, math, json
sys.path.insert(0, '/home/user/bot-telegram/contenuti/yardfx_video'); import yardfx as Y; import suoni as S
from PIL import Image, ImageDraw
D = os.path.dirname(os.path.abspath(__file__))
WORDS = json.load(open(os.path.join(D, 'words.json'))); G = Y.make_groups(WORDS)
T = lambda i: WORDS[i][1]
VEND = WORDS[-1][2]
KEYS = {5, 8, 13, 17, 26, 35, 39, 43, 48, 54, 60, 64, 67, 77, 80, 89, 91}
CUTS = [0, T(9), T(20), T(40), T(72), T(86), T(92), VEND + 0.3]
OUT_LEN = 4.2; DUR = CUTS[-1] + OUT_LEN
TRANS = ['zoom', 'whip_v', 'wipe', 'blur', 'whip', 'zoom']
TD = 0.4; TIKTOK = os.environ.get('TIKTOK') == '1'
EV = []
def ev(t, n, g=1.0): EV.append((round(t, 3), n, g))
SP = Y.sprite
def big(b, s, xy, size, col, font=Y.BIG): ImageDraw.Draw(b).text(xy, s, font=Y.F(font, size), fill=col, anchor='mm')

def s1(t):
    img = Y.night_bg(t); img = Y.light_beams(img, t); img = Y.dust(img, t, 45, 3, Y.GOLD, 40)
    img = Y.spotlight(img, Y.W // 2 + 50 * math.sin(t * 1.2), 100, 900, 520, 55)
    img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('dopo il', 'serif', 150, Y.WHITE), ('CPI', 'big', 200, Y.WHITE)], 540), t, -0.4, 0.45, 'float', 1)
    if t > T(5): img = Y.pulse_rings(img, Y.W // 2, 800, t - T(5), Y.GOLD, 1.3, 3, 520)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('arriva il', 'serif', 90, Y.MUTE)], 650), t, T(3), enter='rise', idle='float', seed=2)
    img = SP(img, lambda b: Y.glow_text(b, 'PPI', (Y.W // 2, 830), 300, Y.GOLD, (130, 90, 20)), t, T(5), enter='stamp', idle='breathe', seed=3, dur=0.35)
    for i, (txt, col, t0, ent) in enumerate([('CONFERMA', Y.GREEN, T(6), 'left'), ('SMENTITA?', Y.RED, T(8), 'right')]):
        def box(b, i=i, txt=txt, col=col):
            d = ImageDraw.Draw(b); x0 = 70 + i * 540
            d.rounded_rectangle((x0, 1100, x0 + 400, 1280), radius=30, fill=tuple(int(v * .25) for v in col), outline=col, width=5)
            d.text((x0 + 200, 1190), txt, font=Y.F(Y.BIG, 74), fill=col, anchor='mm')
        img = SP(img, box, t, t0, enter=ent, idle='sway', seed=4 + i, amp=0.6)
    if t > T(7): ImageDraw.Draw(img).text((Y.W // 2, 1190), 'o', font=Y.F(Y.SERIF, 80), fill=Y.WHITE, anchor='mm')
    img = Y.camera(img, t, 0, punches=[T(5), T(6), T(8)], shakes=[T(5)])
    return Y.color_flash(img, t, [T(5)], Y.GOLD, 0.16, 0.4), True
ev(0, 'boom', 0.7); ev(0.05, 'whoosh', 0.6); ev(T(3), 'swoosh_up', 0.6); ev(T(5), 'boom'); ev(T(5), 'stamp', 0.7); ev(T(6), 'pop'); ev(T(6) + 0.05, 'swipe', 0.6); ev(T(8), 'pop_hi'); ev(T(8) + 0.05, 'swipe', 0.6)

def s2(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 40, 5, Y.GOLD, 40); img = Y.spotlight(img, Y.W // 2, 60, 520, 460, 60)
    img = SP(img, lambda b: Y.clock_hands(b, Y.W // 2, 330, 120, t, Y.GOLD, 0.8), t, CUTS[1], enter='spin', idle='float', seed=6)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('domani', 'serif', 120, Y.WHITE)], 600), t, T(9), enter='pop', idle='float', seed=7)
    if t > T(11): img = Y.pulse_rings(img, Y.W // 2, 770, t - T(11), Y.GOLD, 1.4, 2, 460)
    img = SP(img, lambda b: Y.glow_text(b, '14:30', (Y.W // 2, 770), 250, Y.GOLD, (130, 90, 20)), t, T(11), enter='stamp', idle='breathe', seed=8, dur=0.35)
    img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [("l'inflazione alla", 'serif', 84, Y.WHITE)], 1000), t, T(15), 0.45, 'float', 9)
    img = Y.blur_in(img, lambda b: big(b, 'PRODUZIONE', (Y.W // 2, 1110), 130, Y.WHITE), t, T(17), 0.4, 'float', 10)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'DI OTTOBRE', (Y.W // 2, 1290), 80, 1), t, T(18), enter='pop', idle='breathe', seed=11)
    img = Y.camera(img, t, CUTS[1], punches=[T(11), T(17)], shakes=[T(11)])
    return Y.color_flash(img, t, [T(11)], Y.GOLD, 0.15, 0.35), True
[ev(CUTS[1] + k * 0.5, 'tick', 0.5) for k in range(8)]; ev(CUTS[1], 'whoosh', 0.6); ev(T(9), 'pop'); ev(T(11), 'boom', 0.8); ev(T(11), 'ding', 0.7); ev(T(15), 'swoosh_up', 0.5); ev(T(17), 'pop'); ev(T(18), 'pop_hi')

def bars(b, t):
    d = ImageDraw.Draw(b); x0, x1 = 120, 960
    for i, (lab, v, col, t0) in enumerate([('SETTEMBRE', 1.3, Y.RED, T(21)), ('ATTESE OTTOBRE', 0.4, Y.GOLD, T(35))]):
        a = Y.ease((t - t0) / 0.8)
        if t < t0: continue
        y = 1290 + i * 115
        d.text((x0, y - 34), lab, font=Y.F(Y.COND, 42), fill=Y.WHITE, anchor='lm')
        d.rounded_rectangle((x0, y, x1, y + 34), radius=17, fill=(40, 42, 50))
        d.rounded_rectangle((x0, y, x0 + (x1 - x0) * v / 1.4 * a, y + 34), radius=17, fill=col)
def s3(t):
    img = Y.term_bg(); img = Y.light_sweep(img, t, 3.2, 200, 35); img = Y.dust(img, t, 30, 7, Y.ICE, 30)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('a', 'serif', 90, Y.MUTE), ('SETTEMBRE', 'big', 110, Y.WHITE)], 330), t, T(21), enter='left', idle='float', seed=12)
    if t > T(24):
        s = Y.count_text(0, 1.3, t, T(24), 1.2, '+{:.1f}%')
        img = SP(img, lambda b: Y.glow_text(b, s, (Y.W // 2, 540), 230, Y.RED, (120, 40, 30)), t, T(24), enter='pop', idle='breathe', seed=13)
    img = SP(img, lambda b: Y.hand(ImageDraw.Draw(b), 'in un mese', (Y.W // 2, 690), 74, Y.WHITE, Y.ease((t - T(29)) / 0.5)), t, T(29), enter='none', idle='float', seed=14)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('per', 'serif', 86, Y.MUTE), ('OTTOBRE', 'big', 104, Y.WHITE)], 870), t, T(32), enter='right', idle='float', seed=15)
    img = SP(img, lambda b: Y.chip(ImageDraw.Draw(b), 'ATTESE', (Y.W // 2 - 140, 960), ok=True), t, T(35), enter='pop', idle='wobble', seed=16, amp=0.4)
    if t > T(37):
        s2_ = Y.count_text(0, 0.4, t, T(37), 1.0, '+{:.1f}%')
        img = SP(img, lambda b: Y.glow_text(b, s2_, (Y.W // 2, 1130), 200, Y.GOLD, (130, 90, 20)), t, T(37), enter='pop', idle='breathe', seed=17)
    img = SP(img, lambda b: bars(b, t), t, T(21), enter='none', idle='float', seed=18, amp=0.3)
    img = Y.camera(img, t, CUTS[2], punches=[T(26), T(39)], shakes=[T(26) + 1.0])
    return Y.color_flash(img, t, [T(26) + 1.0], Y.RED, 0.15, 0.3), True
ev(CUTS[2], 'swipe'); ev(T(21), 'swipe', 0.6); [ev(T(24) + k * 0.08, 'tick', 0.5) for k in range(14)]; ev(T(26) + 1.0, 'boom', 0.8); ev(T(29), 'click'); ev(T(32), 'swipe', 0.6); ev(T(35), 'pop'); [ev(T(37) + k * 0.08, 'tick', 0.5) for k in range(12)]; ev(T(39), 'ding')

CH = [(250, 'banca', 'FED: tassi su', T(48)), (540, 'dollaro', 'dollaro sale', T(54)), (830, 'lingotto', 'oro giù', T(57))]
def s4(t):
    img = Y.grid_paper()
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('se esce', 'serif', 90, Y.INK), ('PIÙ ALTA', 'big', 110, Y.RED)], 320), t, T(42), enter='drop', idle='float', seed=19)
    img = SP(img, lambda b: Y.hand(ImageDraw.Draw(b), '= conferma il CPI', (Y.W // 2, 420), 64, Y.GOLDK, Y.ease((t - T(44)) / 0.6)), t, T(44), enter='none', idle='float', seed=20)
    for k, (x, ic, lab, t0) in enumerate(CH):
        if t < t0: continue
        def dr(b, x=x, ic=ic, lab=lab, t0=t0, k=k):
            d = ImageDraw.Draw(b); col = Y.RED if ic == 'lingotto' else Y.INK
            Y.icon(d, ic, x, 600, 160, Y.ease((t - t0) / 0.5), col, 7, 10 + k * 9)
            d.text((x, 730), lab, font=Y.F(Y.SERIF, 56), fill=col, anchor='mm')
        img = SP(img, dr, t, t0, enter='pop', idle='float', seed=21 + k, anchor=(x, 600))
        if k: Y.dashed_arrow(ImageDraw.Draw(img), CH[k - 1][0] + 110, 600, x - 110, 600, Y.ease((t - t0) / 0.4), Y.MUTE)
    if t > T(61):
        img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('se esce', 'serif', 90, Y.INK), ('PIÙ BASSA', 'big', 110, Y.GREEN_K)], 900), t, T(61), enter='drop', idle='float', seed=24)
        def gr(b):
            d = ImageDraw.Draw(b); Y.icon(d, 'lingotto', 380, 1100, 200, Y.ease((t - T(65)) / 0.5), Y.GOLDK, 8, 70)
            Y.icon(d, 'grafico_su', 600, 1080, 130, Y.ease((t - T(66)) / 0.5), Y.GREEN_K, 8, 71)
            Y.hand(d, "l'oro può respirare", (Y.W // 2, 1230), 70, Y.GREEN_K, Y.ease((t - T(65)) / 0.8))
        if t > T(65): img = SP(img, gr, t, T(65), enter='pop', idle='float', seed=25)
    img = SP(img, lambda b: Y.stamp(b, 'DI SOLITO, NON SEMPRE', (Y.W // 2, 1400), 70, Y.GOLDK, -5), t, T(68), enter='stamp', idle='wobble', seed=26, dur=0.3, amp=0.4)
    img = Y.camera(img, t, CUTS[3], punches=[T(43), T(48), T(60), T(64), T(70)], shakes=[T(60), T(68)], push=0.04)
    img = Y.color_flash(img, t, [T(43), T(60)], Y.RED, 0.15, 0.25); img = Y.color_flash(img, t, [T(64)], Y.GREEN, 0.15, 0.25)
    return img, False
ev(CUTS[3], 'whoosh', 0.7); ev(T(42), 'swoosh_up'); ev(T(43), 'pop'); ev(T(44), 'click')
for x, ic, lab, t0 in CH: ev(t0, 'bubble'); ev(t0 + 0.1, 'swipe', 0.4)
ev(T(60), 'boom', 0.6); ev(T(61), 'swoosh_up'); ev(T(64), 'pop_hi'); ev(T(65), 'trin', 0.6); ev(T(68), 'stamp')

def ladder(img, t, s):
    d = ImageDraw.Draw(img); x0, x1, y0, y1 = 120, 960, 520, 1290; lo, hi = 3900, 4100
    py = lambda p: y1 - (p - lo) / (hi - lo) * (y1 - y0)
    d.rounded_rectangle((x0 - 40, y0 - 50, x1 + 40, y1 + 50), radius=26, fill=Y.CARD, outline=Y.CARD_LINE, width=2)
    for p in range(3900, 4101, 50):
        d.line([(x0 + 150, py(p)), (x1, py(p))], fill=(40, 42, 50), width=1)
        d.text((x0 + 120, py(p)), f'{p:,}'.replace(',', '.'), font=Y.F(Y.MONO, 30), fill=Y.MUTE, anchor='rm')
    a = Y.ease((t - T(80)) / 0.4)
    if a > 0:
        y = py(4000); xe = x0 + 150 + (x1 - x0 - 150) * a; off = int(t * 40) % 26
        for xx in range(x0 + 150 - off, int(xe), 26):
            if xx >= x0 + 150: d.line([(xx, y), (min(xx + 14, xe), y)], fill=Y.GOLD, width=5)
    p = 4050 - 75 * Y.ease((t - T(77)) / 1.2) + 3 * math.sin(t * 4); y = py(p); x = x0 + 380
    d.line([(x, py(4050)), (x, y)], fill=Y.RED, width=6)
    img = Y.pulse_rings(img, x, y, t, Y.RED, 1.1, 3, 120, 3)
    img = Y.glow_text(img, '•', (x, y - 8), int(120 + 14 * math.sin(t * 6)), Y.WHITE, (120, 120, 160)); d = ImageDraw.Draw(img)
    if t > T(80): Y.circle(d, x0 + 520, py(4000), 330, 60, Y.ease((t - T(80)) / 0.5), Y.GOLD, 6, 41)
    return img
def s5(t):
    img = Y.term_bg(); img = Y.light_sweep(img, t + 1.5, 3.4, 200, 30); img = Y.dust(img, t, 25, 11, Y.ICE, 30)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [("l'oro è", 'serif', 86, Y.MUTE), ('SCESO', 'big', 110, Y.RED)], 350), t, T(75), enter='drop', idle='float', seed=27)
    img = SP(img, lambda b: ladder(b, t, t - CUTS[4]), t, CUTS[4] + 0.1, enter='rise', idle='float', seed=28, amp=0.3)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'IL LIVELLO DA GUARDARE', (Y.W // 2, 1440), 60, 1), t, T(83), enter='stamp', idle='breathe', seed=29, dur=0.3)
    img = Y.camera(img, t, CUTS[4], punches=[T(77), T(80), T(83)], shakes=[T(80)])
    return Y.color_flash(img, t, [T(80)], Y.GOLD, 0.15, 0.35), True
ev(CUTS[4], 'swipe'); ev(CUTS[4] + 0.1, 'swoosh_up'); ev(T(75), 'pop'); ev(T(77), 'whoosh', 0.6); ev(T(80), 'ding'); ev(T(80) + 0.05, 'boom', 0.6); ev(T(83), 'stamp', 0.8)

def s6(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 50, 17, Y.GOLD, 55); img = Y.pulse_rings(img, Y.W // 2, 900, t, Y.GOLD, 2.0, 2, 600, 3)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('tu cosa', 'serif', 110, Y.WHITE), ('DICI?', 'big', 130, Y.GOLD)], 600), t, CUTS[5], enter='drop', idle='float', seed=30)
    for i, (txt, col, t0, ent) in enumerate([('SOPRA', Y.GREEN, T(89), 'left'), ('SOTTO', Y.RED, T(91), 'right')]):
        def box(b, i=i, txt=txt, col=col):
            d = ImageDraw.Draw(b); x0 = 70 + i * 540
            d.rounded_rectangle((x0, 800, x0 + 400, 1000), radius=30, fill=tuple(int(v * .25) for v in col), outline=col, width=5)
            d.text((x0 + 200, 900), txt, font=Y.F(Y.BIG, 90), fill=col, anchor='mm')
        img = SP(img, box, t, t0, enter=ent, idle='sway', seed=31 + i, amp=0.6)
    if t > T(90): ImageDraw.Draw(img).text((Y.W // 2, 900), 'o', font=Y.F(Y.SERIF, 70), fill=Y.WHITE, anchor='mm')
    img = Y.camera(img, t, CUTS[5], punches=[T(89), T(91)])
    img = Y.color_flash(img, t, [T(89)], Y.GREEN, 0.15, 0.3); img = Y.color_flash(img, t, [T(91)], Y.RED, 0.15, 0.3)
    return img, True
ev(CUTS[5], 'swoosh_up'); ev(T(89), 'pop_hi'); ev(T(89) + 0.05, 'swipe', 0.6); ev(T(91), 'pop'); ev(T(91) + 0.05, 'swipe', 0.6)

CTA_T = [T(97), T(100), T(102), T(109)]
def s7(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 50, 17, Y.GOLD, 55)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('se ti è stato', 'serif', 90, Y.WHITE), ('UTILE', 'big', 110, Y.GOLD)], 420), t, CUTS[6], enter='drop', idle='float', seed=33)
    img = Y.cta_four(img, t, CTA_T, 'SOPRA/SOTTO', y0=640)
    return Y.camera(img, t, CUTS[6], punches=CTA_T, push=0.03), True
ev(CUTS[6], 'swoosh_up'); ev(CUTS[6] + 0.1, 'pop'); ev(CTA_T[0], 'pop'); ev(CTA_T[1], 'pop_hi'); ev(CTA_T[1] + 0.05, 'bubble', 0.6); ev(CTA_T[2], 'bubble'); ev(CTA_T[3], 'swoosh_up'); ev(CTA_T[3] + 0.1, 'coin')

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
        S.music(os.path.join(D, 'base.wav'), DUR, 96, 'tensione')
        a = S.mix(os.path.join(D, 'audio.m4a'), DUR, voce=os.path.join(D, 'voce.mp3'), musica=os.path.join(D, 'base.wav'), eventi=EV, music_db=-17)
        for tag in ['ig', 'tt']:
            lst = os.path.join(D, f'list_{tag}.txt'); open(lst, 'w').write(f"file 'main.mp4'\nfile 'outro_{tag}.mp4'\n")
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-i', a, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'copy', '-shortest', '-movflags', '+faststart',
                            os.path.join(D, f'yardfx_ppi_13nov_{"instagram" if tag == "ig" else "tiktok"}.mp4')], check=True)
        print('ok', DUR, len(EV))
