"""Recap settimana 9-13 novembre 2026 — voce Enea. Numeri dallo storico MT5 di Salvatore (lotto 0,01: 1 $ = 10 pips).
S1 NOTTE    T0   SETTIMANA DI INFLAZIONE · timbro ANCHE QUELLI SBAGLIATI · TOTALE contatore +258 PIPS
S2 TERMINALE T13 11 OPERAZIONI · 11 pallini dei trade in ordine · chip 7 VINTE / 4 PERSE
S3 TERMINALE T20 schede in 3D: LA MIGLIORE vendita a 4.050 +651 PIPS · LA PEGGIORE acquisto a 4.140 −398 PIPS
S4 NOTTE    T41  curva cumulata dei pips trade per trade · +1.621 GUADAGNATI · −1.363 PERSI
S5 QUADERNO T49  timbro SETTIMANA TOSTA · NEWS e MERCATO contro la STRATEGIA · 4 STOP SU 11 → IN POSITIVO · RISPETTARE IL PIANO
S6 NOTTE    T86  se ti è stato UTILE + 4 paletti (VERDE/ROSSO)
OUTRO            logo + Telegram (Instagram) / logo + icona e @yard_fx (TikTok)"""
import sys, os, math, json
sys.path.insert(0, '/home/user/bot-telegram/contenuti/yardfx_video'); import yardfx as Y; import suoni as S
from PIL import Image, ImageDraw
D = os.path.dirname(os.path.abspath(__file__))
WORDS = json.load(open(os.path.join(D, 'words.json'))); G = Y.make_groups(WORDS)
T = lambda i: WORDS[i][1]
VEND = WORDS[-1][2]
TRADES = [5.3, 143.6, -397.8, 150.9, -318.0, 650.5, 362.0, 4.8, -380.9, 304.0, -266.1]
KEYS = {2, 8, 11, 13, 17, 19, 21, 29, 32, 40, 43, 47, 53, 59, 67, 69, 77, 81, 85}
CUTS = [0, T(13), T(20), T(41), T(49), T(86), VEND + 0.3]
OUT_LEN = 4.2; DUR = CUTS[-1] + OUT_LEN
TRANS = ['zoom', 'whip', 'blur', 'wipe', 'whip_v']
TD = 0.4; TIKTOK = os.environ.get('TIKTOK') == '1'
EV = []
def ev(t, n, g=1.0): EV.append((round(t, 3), n, g))
SP = Y.sprite
def big(b, s, xy, size, col, font=Y.BIG): ImageDraw.Draw(b).text(xy, s, font=Y.F(font, size), fill=col, anchor='mm')

def s1(t):
    img = Y.night_bg(t); img = Y.light_beams(img, t); img = Y.dust(img, t, 45, 3, Y.GOLD, 40)
    img = Y.spotlight(img, Y.W // 2 + 50 * math.sin(t * 1.2), 100, 760, 520, 55)
    img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('settimana di', 'serif', 120, Y.WHITE)], 420), t, -0.4, 0.45, 'float', 1)
    img = SP(img, lambda b: big(b, 'INFLAZIONE', (Y.W // 2, 560), 190, Y.GOLD), t, -0.3, enter='pop', idle='breathe', seed=2)
    img = SP(img, lambda b: Y.hand(ImageDraw.Draw(b), 'tutti i trade', (Y.W // 2, 720), 80, Y.WHITE, Y.ease((t - T(3)) / 0.5)), t, T(3), enter='none', idle='float', seed=3)
    img = SP(img, lambda b: Y.stamp(b, 'ANCHE QUELLI SBAGLIATI', (Y.W // 2, 860), 70, Y.RED, -5), t, T(6), enter='stamp', idle='wobble', seed=4, dur=0.3, amp=0.4)
    if t > T(9): img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('totale', 'serif', 90, Y.MUTE)], 1030), t, T(9), enter='rise', idle='float', seed=5)
    if t > T(10):
        img = Y.pulse_rings(img, Y.W // 2, 1200, t - T(10), Y.GREEN, 1.3, 3, 520)
        s = Y.count_text(0, 258, t, T(10), 1.4, '+{:.0f}')
        img = SP(img, lambda b: Y.glow_text(b, s, (Y.W // 2, 1200), 260, Y.GREEN, (30, 90, 50)), t, T(10), enter='pop', idle='breathe', seed=6)
    if t > T(12): img = SP(img, lambda b: big(b, 'PIPS', (Y.W // 2, 1380), 110, Y.WHITE), t, T(12), enter='rise', idle='float', seed=7)
    img = Y.camera(img, t, 0, punches=[T(6), T(11) + 0.4], shakes=[T(6)])
    return Y.color_flash(img, t, [T(11) + 0.4], Y.GREEN, 0.16, 0.35), True
ev(0, 'boom', 0.7); ev(0.05, 'whoosh', 0.6); ev(T(3), 'click'); ev(T(6), 'stamp'); ev(T(9), 'swoosh_up', 0.5)
[ev(T(10) + k * 0.08, 'tick', 0.5) for k in range(16)]; ev(T(11) + 0.4, 'coin'); ev(T(11) + 0.4, 'boom', 0.6); ev(T(12), 'pop')

def dots(b, t):
    d = ImageDraw.Draw(b); n = len(TRADES)
    for i, v in enumerate(TRADES):
        a = Y.ease((t - (T(14) + i * 0.08)) / 0.25)
        if a <= 0: continue
        x = 120 + i * 84; y = 700 + 8 * math.sin(t * 3 + i); r = 30 * Y.back(a)
        win = v > 0; lit = (win and t > T(17)) or ((not win) and t > T(19))
        col = (Y.GREEN if win else Y.RED) if lit else (90, 92, 104)
        d.ellipse((x - r, y - r, x + r, y + r), fill=col)
def s2(t):
    img = Y.term_bg(); img = Y.light_sweep(img, t, 3.2, 200, 35); img = Y.dust(img, t, 30, 7, Y.ICE, 30)
    img = SP(img, lambda b: Y.glow_text(b, '11', (Y.W // 2, 380), 230, Y.GOLD, (130, 90, 20)), t, T(13), enter='spin', idle='breathe', seed=8)
    img = SP(img, lambda b: big(b, "OPERAZIONI SULL'ORO", (Y.W // 2, 540), 84, Y.WHITE), t, T(14), enter='rise', idle='float', seed=9)
    img = SP(img, lambda b: dots(b, t), t, T(14), enter='none', idle='float', seed=10, amp=0.3)
    for i, (txt, col, t0, ent) in enumerate([('7 VINTE', Y.GREEN, T(16), 'left'), ('4 PERSE', Y.RED, T(18), 'right')]):
        def box(b, i=i, txt=txt, col=col):
            d = ImageDraw.Draw(b); x0 = 90 + i * 500
            d.rounded_rectangle((x0, 900, x0 + 400, 1100), radius=30, fill=tuple(int(v * .25) for v in col), outline=col, width=5)
            d.text((x0 + 200, 1000), txt, font=Y.F(Y.BIG, 96), fill=col, anchor='mm')
        img = SP(img, box, t, t0, enter=ent, idle='sway', seed=11 + i, amp=0.6)
    img = Y.camera(img, t, CUTS[1], punches=[T(13), T(17), T(19)], shakes=[T(19)])
    img = Y.color_flash(img, t, [T(17)], Y.GREEN, 0.15, 0.3); return Y.color_flash(img, t, [T(19)], Y.RED, 0.15, 0.3), True
ev(CUTS[1], 'swipe'); ev(T(13), 'boom', 0.6); ev(T(14), 'swoosh_up', 0.5); [ev(T(14) + k * 0.08, 'pop', 0.4) for k in range(11)]; ev(T(17), 'ding'); ev(T(19), 'alert', 0.7)

def card(label, side, price, res, col, t, t_side, t_price, t_res):
    c = Image.new('RGBA', (900, 420), (0, 0, 0, 0)); d = ImageDraw.Draw(c)
    d.rounded_rectangle((0, 0, 899, 419), radius=30, fill=Y.CARD + (255,), outline=col + (255,), width=5)
    d.text((40, 60), label, font=Y.F(Y.BIG, 70), fill=col, anchor='lm')
    if t > t_side:
        sc = Y.GREEN if side == 'ACQUISTO' else Y.RED
        d.rounded_rectangle((40, 130, 300, 200), radius=14, fill=sc); d.text((170, 165), side, font=Y.F(Y.COND, 52), fill=Y.DARK, anchor='mm')
    if t > t_price: Y.type_text(d, price, (330, 166), 56, Y.WHITE, t, t_price, 20, Y.MONO, cursor=False)
    if t > t_res:
        v = Y.count_text(0, res, t, t_res, 0.8, '{:+.0f}').replace('+', '+' if res > 0 else '')
        if res < 0: v = '−' + v.lstrip('-')
        d.text((450, 320), v + ' PIPS', font=Y.F(Y.BIG, 130), fill=col, anchor='mm')
    return c
def s3(t):
    img = Y.term_bg(); img = Y.light_sweep(img, t + 1, 3.4, 200, 30); img = Y.dust(img, t, 25, 9, Y.ICE, 30)
    c1 = card('LA MIGLIORE', 'VENDITA', 'a 4.050', 651, Y.GREEN, t, T(23), T(25), T(29))
    img = Y.perspective(img, c1, Y.card_flip_quad([(110, 300), (1000, 330), (990, 720), (90, 700)], t, T(20)))
    if t > T(31):
        c2 = card('LA PEGGIORE', 'ACQUISTO', 'a 4.140', -398, Y.RED, t, T(34), T(36), T(39))
        img = Y.perspective(img, c2, Y.card_flip_quad([(90, 860), (990, 830), (1000, 1250), (110, 1270)], t, T(31)))
    img = Y.camera(img, t, CUTS[2], punches=[T(29) + 0.8, T(39) + 0.8], shakes=[T(39) + 0.8])
    img = Y.color_flash(img, t, [T(29) + 0.8], Y.GREEN, 0.15, 0.3); return Y.color_flash(img, t, [T(39) + 0.8], Y.RED, 0.15, 0.3), True
ev(CUTS[2], 'whoosh', 0.7); ev(T(20), 'swoosh_up'); ev(T(23), 'pop'); [ev(T(25) + k * 0.05, 'click', 0.3) for k in range(7)]
[ev(T(29) + k * 0.07, 'tick', 0.4) for k in range(11)]; ev(T(29) + 0.8, 'coin'); ev(T(31), 'swoosh_up'); ev(T(34), 'pop')
[ev(T(36) + k * 0.05, 'click', 0.3) for k in range(7)]; [ev(T(39) + k * 0.07, 'tick', 0.4) for k in range(11)]; ev(T(39) + 0.8, 'boom', 0.8); ev(T(39) + 0.85, 'glitch', 0.5)

CUM = [0]
for v in TRADES: CUM.append(CUM[-1] + v)
def s4(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 40, 13, Y.GOLD, 45)
    img = Y.blur_in(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('in', 'serif', 100, Y.WHITE), ('TUTTO', 'big', 120, Y.GOLD)], 330), t, CUTS[3], 0.4, 'float', 14)
    img = Y.equity_curve(img, CUM, (110, 450, 970, 950), (t - CUTS[3]) / (T(47) - CUTS[3] + 0.8), '+258' if t > T(48) else None)
    for i, (val, lab, col, t0, tl) in enumerate([(1621, 'GUADAGNATI', Y.GREEN, T(43), T(45)), (-1363, 'PERSI', Y.RED, T(47), T(48))]):
        if t < t0: continue
        y = 1150 + i * 230
        s = Y.count_text(0, abs(val), t, t0, 1.0, '{:,.0f}').replace(',', '.')
        s = ('+' if val > 0 else '−') + s
        img = SP(img, lambda b, s=s, y=y, col=col: Y.glow_text(b, s, (Y.W // 2 - 170, y), 150, col, tuple(int(v * .4) for v in col)), t, t0, enter='pop', idle='breathe', seed=15 + i)
        if t > tl: img = SP(img, lambda b, y=y, lab=lab, col=col: ImageDraw.Draw(b).text((Y.W // 2 + 150, y), lab, font=Y.F(Y.COND, 64), fill=col, anchor='lm'), t, tl, enter='left', idle='float', seed=17 + i)
    img = Y.camera(img, t, CUTS[3], punches=[T(43) + 1.0, T(47) + 1.0], shakes=[])
    return img, True
ev(CUTS[3], 'swipe'); ev(CUTS[3] + 0.2, 'riser', 0.4); [ev(T(43) + k * 0.08, 'tick', 0.4) for k in range(12)]; ev(T(43) + 1.0, 'ding'); ev(T(45), 'swipe', 0.5)
[ev(T(47) + k * 0.08, 'tick', 0.4) for k in range(12)]; ev(T(47) + 1.0, 'boom', 0.6); ev(T(48), 'swipe', 0.5)

def s5(t):
    img = Y.grid_paper()
    img = SP(img, lambda b: Y.stamp(b, 'SETTIMANA TOSTA', (Y.W // 2, 290), 96, Y.RED, -4), t, T(52), enter='stamp', idle='wobble', seed=19, dur=0.3, amp=0.4)
    def nm(b):
        d = ImageDraw.Draw(b)
        if t > T(56):
            Y.icon(d, 'calendario', 230, 540, 150, Y.ease((t - T(56)) / 0.5), Y.INK, 7, 80); d.text((230, 660), 'news', font=Y.F(Y.SERIF, 64), fill=Y.INK, anchor='mm')
        if t > T(59):
            Y.icon(d, 'grafico_giu', 540, 540, 150, Y.ease((t - T(59)) / 0.5), Y.RED, 8, 81); d.text((540, 660), 'mercato', font=Y.F(Y.SERIF, 64), fill=Y.RED, anchor='mm')
        if t > T(67):
            Y.icon(d, 'grafico_su', 850, 540, 150, Y.ease((t - T(67)) / 0.5), Y.GREEN_K, 8, 82); d.text((850, 660), 'strategia', font=Y.F(Y.SERIF, 64), fill=Y.GREEN_K, anchor='mm')
            Y.icon(d, 'croce', 850, 540, 110, Y.ease((t - T(67) - 0.3) / 0.4), Y.RED, 9, 83)
    if t > T(56): img = SP(img, nm, t, T(56), enter='none', idle='float', seed=20, amp=0.5)
    if t > T(68): img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('4 STOP', 'big', 110, Y.RED), ('su', 'serif', 90, Y.INK), ('11', 'big', 110, Y.INK)], 880), t, T(68), enter='drop', idle='float', seed=21)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'IN POSITIVO', (Y.W // 2, 1010), 90, 1, Y.GREEN_K, Y.WHITE), t, T(76), enter='stamp', idle='breathe', seed=22, dur=0.3)
    img = SP(img, lambda b: Y.hand(ImageDraw.Draw(b), 'non serve vincere sempre', (Y.W // 2, 1180), 74, Y.INK, Y.ease((t - T(78)) / 0.8)), t, T(78), enter='none', idle='float', seed=23)
    img = SP(img, lambda b: Y.stamp(b, 'RISPETTARE IL PIANO', (Y.W // 2, 1370), 84, Y.GOLDK, 4), t, T(83), enter='stamp', idle='wobble', seed=24, dur=0.3, amp=0.4)
    img = Y.camera(img, t, CUTS[4], punches=[T(53), T(69), T(77), T(85)], shakes=[T(53), T(83)], push=0.04)
    img = Y.color_flash(img, t, [T(53)], Y.RED, 0.15, 0.25); return Y.color_flash(img, t, [T(77)], Y.GREEN, 0.15, 0.3), False
ev(CUTS[4], 'whoosh', 0.7); ev(T(52), 'stamp'); ev(T(56), 'bubble'); ev(T(59), 'pop'); ev(T(59) + 0.1, 'swipe', 0.4); ev(T(67), 'pop'); ev(T(67) + 0.3, 'alert', 0.6)
ev(T(68), 'swoosh_up'); ev(T(76), 'stamp', 0.7); ev(T(77), 'trin', 0.8); ev(T(78), 'click'); ev(T(83), 'stamp'); ev(T(85), 'ding', 0.8)

CTA_T = [T(91), T(94), T(96), T(110)]
def s6(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 50, 17, Y.GOLD, 55)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('se ti è stato', 'serif', 90, Y.WHITE), ('UTILE', 'big', 110, Y.GOLD)], 420), t, CUTS[5], enter='drop', idle='float', seed=30)
    img = Y.cta_four(img, t, CTA_T, 'VERDE/ROSSO', y0=640)
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
        S.music(os.path.join(D, 'base.wav'), DUR, 96, 'positivo')
        a = S.mix(os.path.join(D, 'audio.m4a'), DUR, voce=os.path.join(D, 'voce.mp3'), musica=os.path.join(D, 'base.wav'), eventi=EV, music_db=-17)
        for tag in ['ig', 'tt']:
            lst = os.path.join(D, f'list_{tag}.txt'); open(lst, 'w').write(f"file 'main.mp4'\nfile 'outro_{tag}.mp4'\n")
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-i', a, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'copy', '-shortest', '-movflags', '+faststart',
                            os.path.join(D, f'yardfx_recap_9-13nov_{"instagram" if tag == "ig" else "tiktok"}.mp4')], check=True)
        print('ok', DUR, len(EV))
