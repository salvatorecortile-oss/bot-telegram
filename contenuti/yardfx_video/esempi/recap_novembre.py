"""Recap di novembre 2026 (2-27 novembre, dati MT5 di Salvatore, lotto 0,01: 1 $ = 10 pips), pubblicato sabato 28/11 — voce Salvatore (Speechify, atempo 1.08).
45 operazioni: 32 vinte, 13 perse · totale +580,21 $ = +5.802 pips · migliore BUY 04/11 3907,84 -> 4025,19 (+1.174) · peggiore SELL 25/11 3444,29 -> 3498,29 (-540)
settimane: 2-6 +3.482 · 9-13 +30 · 16-20 +864 · 23-27 +1.426
Ricetta RECAP: Notte -> Terminale -> Terminale -> Notte -> Quaderno -> Notte.
S1 NOTTE      T0   contatore +5.802 PIPS già al primo fotogramma · NOVEMBRE è finito · timbro SENZA FILTRI
S2 TERMINALE  T12  griglia di 45 quadratini che si accendono: 32 verdi (VINTE) e 13 rossi (PERSE) · timbro STOP LOSS COMPRESI
S3 TERMINALE  T23  scheda trade migliore (BUY +1.174, 4 NOV) e notifica STOP sulla peggiore (SELL −540, 25 NOV)
S4 NOTTE      T45  curva cumulata dei pips con i 4 nodi delle settimane (+3.482, +30, +864, +1.426)
S5 QUADERNO   T58  LA LEZIONE: «dal 9 al 13» linea piatta disegnata a mano + timbro SE RISPETTI LO STOP LOSS
S6 NOTTE      T80  se ti è stata UTILE + 4 paletti (commenta NOVEMBRE)
OUTRO              logo animato + Telegram (Instagram: 'CERCAMI SU TELEGRAM'; TikTok: solo icona e @yard_fx)"""
import sys, os, math, json, random
sys.path.insert(0, '/home/user/bot-telegram/contenuti/yardfx_video'); import yardfx as Y; import suoni as S
from PIL import Image, ImageDraw
D = os.path.dirname(os.path.abspath(__file__))
WORDS = json.load(open(os.path.join(D, 'words.json')))
for i, s in [(4, '5.802'), (29, '1.174'), (49, '3.482,'), (57, '1.426.')]: WORDS[i][0] = s
G = Y.make_groups(WORDS)
T = lambda i: WORDS[i][1]
VEND = WORDS[-1][2]
KEYS = {2, 4, 11, 12, 16, 19, 22, 26, 29, 33, 37, 40, 42, 44, 49, 52, 54, 57, 59, 63, 66, 70, 72, 79, 84, 85, 89, 91, 93}
CUTS = [0, T(12), T(23), T(45), T(58), T(80), VEND + 0.3]
OUT_LEN = 4.2; DUR = CUTS[-1] + OUT_LEN
TRANS = ['blur', 'whip', 'zoom', 'wipe', 'whip_v']
TD = 0.4; TIKTOK = os.environ.get('TIKTOK') == '1'
EV = []
def ev(t, n, g=1.0): EV.append((round(t, 3), n, g))
SP = Y.sprite
def big(b, s, xy, size, col, font=Y.BIG): ImageDraw.Draw(b).text(xy, s, font=Y.F(font, size), fill=col, anchor='mm')

# ---------- S1 NOTTE: il totale ----------
def s1(t):
    img = Y.night_bg(t); img = Y.light_beams(img, t); img = Y.dust(img, t, 50, 3, Y.GOLD, 50)
    img = Y.spotlight(img, Y.W // 2 + 50 * math.sin(t * 1.2), 80, 1000, 620, 55)
    img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('NOVEMBRE', 'big', 140, Y.WHITE), ('è finito', 'serif', 100, Y.MUTE)], 420), t, -0.4, 0.4, 'float', 1)
    img = Y.pulse_rings(img, Y.W // 2, 700, t, Y.GOLD, 1.5, 3, 520)
    img = SP(img, lambda b: Y.number_roll(b, '+5.802', (Y.W // 2, 700), 270, Y.GOLD, t, -0.8, 0.8), t, -0.5, enter='stamp', idle='breathe', seed=2, dur=0.35)
    img = SP(img, lambda b: big(b, 'PIPS', (Y.W // 2, 900), 130, Y.WHITE), t, -0.4, enter='pop', idle='float', seed=3)
    img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('tutti i', 'serif', 90, Y.MUTE), ('NUMERI', 'big', 120, Y.WHITE)], 1120), t, T(7), 0.35, 'float', 4)
    img = SP(img, lambda b: Y.stamp(b, 'SENZA FILTRI', (Y.W // 2, 1290), 100, Y.RED, -4), t, T(10), enter='stamp', idle='wobble', seed=5, dur=0.3, amp=0.4)
    img = Y.camera(img, t, 0, punches=[T(4), T(9), T(10)], shakes=[T(10)])
    img = Y.color_flash(img, t, [T(4)], Y.GOLD, 0.15, 0.3)
    return Y.color_flash(img, t, [T(10)], Y.RED, 0.14, 0.3), True
ev(0, 'boom', 0.8); ev(0.05, 'coin', 0.7); ev(T(2), 'pop', 0.6); ev(T(4), 'ding', 0.8); ev(T(4) + 0.05, 'trin', 0.5); ev(T(7), 'swoosh_up', 0.5); ev(T(9), 'pop_hi'); ev(T(10), 'stamp'); ev(T(10) + 0.05, 'glitch', 0.4)

# ---------- S2 TERMINALE: 45 operazioni, 32 vinte e 13 perse ----------
def grid45(b, t):
    d = ImageDraw.Draw(b); cols, rows, cs, g = 9, 5, 92, 10; x0 = Y.W / 2 - (cols * cs + (cols - 1) * g) / 2; y0 = 560
    d.rounded_rectangle((x0 - 40, y0 - 40, x0 + cols * (cs + g) - g + 40, y0 + rows * (cs + g) - g + 40), radius=28, fill=Y.CARD, outline=Y.CARD_LINE, width=3)
    for i in range(45):
        r, c = divmod(i, cols); x = x0 + c * (cs + g); y = y0 + r * (cs + g)
        on = Y.ease((t - T(13) - i * 0.012) / 0.25)
        col = (52, 54, 62)
        if i < 32 and t > T(15) + i * 0.02: col = Y.GREEN
        if i >= 32 and t > T(18) + (i - 32) * 0.04: col = Y.RED
        if on > 0:
            s = cs * (0.6 + 0.4 * on); cx, cy = x + cs / 2, y + cs / 2
            d.rounded_rectangle((cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2), radius=14, fill=col)
    return b
def s2(t):
    img = Y.term_bg(); img = Y.light_sweep(img, t, 3.2, 200, 35); img = Y.dust(img, t, 30, 7, Y.ICE, 30)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('45', 'big', 150, Y.GOLD), ('operazioni', 'serif', 90, Y.WHITE)], 380), t, T(12), enter='drop', idle='float', seed=6)
    img = SP(img, lambda b: grid45(b, t), t, T(12), enter='rise', idle='float', seed=7, amp=0.3)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('32', 'big', 140, Y.GREEN), ('VINTE', 'big', 100, Y.WHITE)], 1220, cx=300), t, T(15), enter='left', idle='float', seed=8)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('13', 'big', 140, Y.RED), ('PERSE', 'big', 100, Y.WHITE)], 1220, cx=790), t, T(18), enter='right', idle='float', seed=9)
    img = SP(img, lambda b: Y.stamp(b, 'STOP LOSS COMPRESI', (Y.W // 2, 1390), 80, Y.RED, -4), t, T(20), enter='stamp', idle='wobble', seed=10, dur=0.3, amp=0.4)
    img = Y.camera(img, t, CUTS[1], punches=[T(12), T(16), T(19), T(20)], shakes=[T(20)])
    img = Y.color_flash(img, t, [T(16)], Y.GREEN, 0.14, 0.3)
    return Y.color_flash(img, t, [T(19), T(20)], Y.RED, 0.13, 0.3), True
ev(CUTS[1], 'swipe'); ev(T(12), 'pop'); [ev(T(13) + k * 0.06, 'tick', 0.3) for k in range(10)]
ev(T(15), 'swoosh_up', 0.5); ev(T(16), 'ding', 0.8); ev(T(18), 'swipe', 0.5); ev(T(19), 'alert', 0.5); ev(T(20), 'stamp'); ev(T(20) + 0.05, 'glitch', 0.4)

# ---------- S3 TERMINALE: la migliore e la peggiore ----------
def card(b, t, t0, y, side, date, res, col):
    d = ImageDraw.Draw(b); w = 900; x0 = Y.W / 2 - w / 2; a = Y.ease((t - t0) / 0.5)
    d.rounded_rectangle((x0, y - 140, x0 + w, y + 140), radius=26, fill=Y.CARD, outline=col, width=4)
    sc = Y.GREEN if side == 'BUY' else Y.RED
    d.rounded_rectangle((x0 + 36, y - 108, x0 + 186, y - 50), radius=12, fill=sc); d.text((x0 + 111, y - 79), side, font=Y.F(Y.COND, 44), fill=Y.DARK, anchor='mm')
    d.text((x0 + 214, y - 79), 'XAUUSD', font=Y.F(Y.MONO, 36), fill=Y.WHITE, anchor='lm')
    d.text((x0 + w - 36, y - 79), date, font=Y.F(Y.MONO, 36), fill=Y.MUTE, anchor='rm')
    d.text((x0 + 40, y + 50), res, font=Y.F(Y.BIG, 120), fill=col, anchor='lm')
    d.text((x0 + w - 40, y + 70), 'PIPS', font=Y.F(Y.BIG, 70), fill=Y.WHITE, anchor='rm')
    d.rounded_rectangle((x0 + 40, y + 115, x0 + w - 40, y + 125), radius=5, fill=(40, 42, 50)); d.rounded_rectangle((x0 + 40, y + 115, x0 + 40 + (w - 80) * a, y + 125), radius=5, fill=col)
    return b
def s3(t):
    img = Y.term_bg(); img = Y.light_sweep(img, t + 1.3, 3.4, 200, 30); img = Y.dust(img, t, 25, 11, Y.ICE, 30)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('la', 'serif', 80, Y.MUTE), ('MIGLIORE', 'big', 110, Y.GREEN)], 330), t, T(23), enter='drop', idle='float', seed=11)
    img = SP(img, lambda b: card(b, t, T(26), 560, 'BUY', '4 NOV' if t > T(32) else '', '+1.174' if t > T(29) else '', Y.GREEN), t, T(26), enter='left', idle='float', seed=12, amp=0.4)
    if t > T(29): img = Y.pulse_rings(img, 330, 610, t - T(29), Y.GREEN, 1.2, 2, 260)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('la', 'serif', 80, Y.MUTE), ('PEGGIORE', 'big', 110, Y.RED)], 830), t, T(34), enter='drop', idle='float', seed=13)
    img = SP(img, lambda b: card(b, t, T(37), 1060, 'SELL', '25 NOV' if t > T(44) else '', '−540' if t > T(41) else '', Y.RED), t, T(37), enter='right', idle='float', seed=14, amp=0.4)
    img = Y.notification(img, 'MT5', 'Stop loss raggiunto', 'XAUUSD sell  −540 pips', 1280, (t - T(40)) / 0.4, Y.RED)
    img = Y.camera(img, t, CUTS[2], punches=[T(24), T(29), T(35), T(40), T(42)], shakes=[T(40)])
    img = Y.color_flash(img, t, [T(29)], Y.GREEN, 0.15, 0.3)
    return Y.color_flash(img, t, [T(40)], Y.RED, 0.15, 0.3), True
ev(CUTS[2], 'whoosh', 0.7); ev(T(23), 'pop'); ev(T(26), 'swipe', 0.6); [ev(T(29) + k * 0.06, 'tick', 0.4) for k in range(6)]; ev(T(29) + 0.3, 'coin', 0.7); ev(T(32), 'pop_hi', 0.6)
ev(T(34), 'pop'); ev(T(37), 'swipe', 0.6); ev(T(40), 'alert', 0.8); ev(T(41), 'boom', 0.6); ev(T(44), 'pop_hi', 0.6)

# ---------- S4 NOTTE: la curva delle settimane ----------
CUM = [0, 3482, 3512, 4376, 5802]; WK = [('+3.482', T(49)), ('+30', T(52)), ('+864', T(54)), ('+1.426', T(57))]
BOX = (120, 600, 960, 1180)
def s4(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 45, 13, Y.GOLD, 40); img = Y.light_beams(img, t + 2, n=2, strength=16)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('settimana per', 'serif', 90, Y.MUTE), ('SETTIMANA', 'big', 110, Y.WHITE)], 380), t, T(45), enter='drop', idle='float', seed=15)
    k = 0
    for i, (_, t0) in enumerate(WK):
        if t >= t0: k = i + 1 + min(1, (t - t0) / 0.5) - 1
    prog = k / 4 if k else 0
    if prog > 0: img = Y.equity_curve(img, CUM, BOX, prog, '+5.802' if t > T(57) + 0.6 else None)
    x0, y0, x1, y1 = BOX; lo, hi = 0, max(CUM)
    d = ImageDraw.Draw(img)
    for i, (lab, t0) in enumerate(WK):
        if t < t0 + 0.4: continue
        x = x0 + (x1 - x0) * (i + 1) / 4; y = y1 - CUM[i + 1] / hi * (y1 - y0)
        col = Y.MUTE if lab == '+30' else Y.GOLD
        Y.number_badge(d, i + 1, (x, y), Y.ease((t - t0 - 0.4) / 0.3), col)
        d.text((x if i < 3 else x - 150, y + 70 if i < 3 else y + 60), lab, font=Y.F(Y.COND, 50), fill=Y.WHITE if lab != '+30' else Y.MUTE, anchor='mm')
    img = Y.camera(img, t, CUTS[3], punches=[T(49), T(52), T(54), T(57) + 0.6], shakes=[T(57) + 0.6])
    return Y.color_flash(img, t, [T(57) + 0.6], Y.GOLD, 0.16, 0.32), True
ev(CUTS[3] + 0.05, 'swoosh_up', 0.6); ev(T(45), 'pop')
for _, t0 in WK: ev(t0, 'swoosh_up', 0.4); ev(t0 + 0.4, 'pop_hi', 0.6)
ev(T(57) + 0.6, 'boom', 0.7); ev(T(57) + 0.6, 'trin', 0.7)

# ---------- S5 QUADERNO: la lezione ----------
def s5(t):
    img = Y.grid_paper()
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('la', 'serif', 100, Y.INK), ('LEZIONE', 'big', 140, Y.GOLDK)], 360), t, T(58), enter='drop', idle='wobble', seed=16, amp=0.4)
    img = SP(img, lambda b: Y.hand(ImageDraw.Draw(b), 'dal 9 al 13', (Y.W // 2, 500), 90, Y.INK, Y.ease((t - T(60)) / 0.7)), t, T(60), enter='none', idle='float', seed=17)
    d = ImageDraw.Draw(img)
    if t > T(64):
        a = Y.ease((t - T(64)) / 0.8); r = random.Random(3)
        pts = [(150 + 780 * k / 30, 690 + r.uniform(-14, 14)) for k in range(int(30 * a) + 1)]
        if len(pts) > 1: d.line(pts, fill=Y.INK, width=7, joint='curve')
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('solo', 'serif', 90, Y.INK), ('+30', 'big', 130, Y.RED), ('pips', 'serif', 90, Y.INK)], 880), t, T(64), enter='pop', idle='float', seed=18)
    img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('una settimana', 'serif', 80, Y.INK), ('PIATTA', 'big', 110, Y.INK)], 1040), t, T(68), 0.35, 'float', 19)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('non', 'serif', 80, Y.INK), ('ROVINA', 'big', 110, Y.RED), ('il mese', 'serif', 80, Y.INK)], 1180), t, T(71), enter='left', idle='float', seed=20)
    img = SP(img, lambda b: Y.stamp(b, 'SE RISPETTI LO STOP LOSS', (Y.W // 2, 1360), 66, Y.GOLDK, -5), t, T(75), enter='stamp', idle='wobble', seed=21, dur=0.3, amp=0.4)
    img = Y.camera(img, t, CUTS[4], punches=[T(59), T(66), T(70), T(72), T(78)], shakes=[T(72), T(78)], push=0.04)
    img = Y.color_flash(img, t, [T(72)], Y.RED, 0.14, 0.25)
    return img, False
ev(CUTS[4], 'whoosh', 0.7); ev(T(58), 'swoosh_up'); ev(T(59), 'pop'); ev(T(60), 'click', 0.6); ev(T(64), 'swipe', 0.4); ev(T(66), 'pop_hi'); ev(T(68), 'whoosh', 0.5); ev(T(70), 'pop', 0.6)
ev(T(71), 'swipe', 0.6); ev(T(72), 'boom', 0.5); ev(T(75), 'stamp'); ev(T(78), 'ding', 0.6)

# ---------- S6 CTA ----------
CTA_T = [T(85), T(88), T(90), T(93)]
def s6(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 50, 17, Y.GOLD, 55)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('se ti è stata', 'serif', 90, Y.WHITE), ('UTILE', 'big', 110, Y.GOLD)], 420), t, CUTS[5], enter='drop', idle='float', seed=33)
    img = Y.cta_four(img, t, CTA_T, 'NOVEMBRE', y0=640)
    return Y.camera(img, t, CUTS[5], punches=CTA_T, push=0.03), True
ev(CUTS[5], 'swoosh_up'); ev(T(84), 'pop'); ev(CTA_T[0], 'pop'); ev(CTA_T[1], 'pop_hi'); ev(CTA_T[1] + 0.05, 'bubble', 0.6); ev(CTA_T[2], 'bubble'); ev(T(91), 'pop', 0.5); ev(CTA_T[3], 'swoosh_up'); ev(CTA_T[3] + 0.1, 'coin')

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
NAME = 'yardfx_recap_novembre'
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
        S.music(os.path.join(D, 'base.wav'), DUR, 98, 'positivo')
        a = S.mix(os.path.join(D, 'audio.m4a'), DUR, voce=os.path.join(D, 'voce.mp3'), musica=os.path.join(D, 'base.wav'), eventi=EV, music_db=-17)
        for tag in ['ig', 'tt']:
            lst = os.path.join(D, f'list_{tag}.txt'); open(lst, 'w').write(f"file 'main.mp4'\nfile 'outro_{tag}.mp4'\n")
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-i', a, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'copy', '-shortest', '-movflags', '+faststart',
                            os.path.join(D, f'{NAME}_{"instagram" if tag == "ig" else "tiktok"}.mp4')], check=True)
        print('ok', DUR, len(EV))
