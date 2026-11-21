"""Recap settimana 16-20 novembre 2026 — voce Speechify «salvatore», esce sab 21/11 ore 10. Numeri SOLO dallo screenshot MT5 di Salvatore
(7 trade XAUUSD 0,01 lotti; pips = dollari x 10): +8,57 / -30,10 / -39,72 / +70,27 / +9,88 / +45,69 / +21,79 = +86,38 $ = +864 pips.
S1 NOTTE      T0   +864 PIPS luminoso · questa SETTIMANA · chip VERBALI FED / VENDITE AL DETTAGLIO · 7 TRADE sull'oro
S2 TERMINALE  T16  MARTEDÌ: schede BUY +86 · CONTRO LA DISCESA · BUY −301 e BUY −397 con timbro STOP LOSS
S3 NOTTE      T37  MERCOLEDÌ · VERBALI FED · ho cambiato DIREZIONE · SELL +703 PIPS con pioggia di monete
S4 TERMINALE  T51  GIOVEDÌ e VENERDÌ · solo SELL · TREND RIBASSISTA · schede +99 +457 +218 · curva cumulata dei pips
S5 QUADERNO   T68  grafico a cascata dei 7 trade → TOTALE · 5 VINTE / 2 PERSE · +864 PIPS
S6 POSTER     T76  la LEZIONE: CONTRO IL TREND ✕ · SEGUENDO IL TREND 4 SELL SU 4 A TARGET · PRIMA LA DIREZIONE, POI L'ENTRATA
S7 NOTTE      T102 se ti è stato UTILE + 4 paletti (VERDE/ROSSO) · outro logo + Telegram
Novità: cascata (Y.waterfall), monete (Y.confetti), mondo poster (Y.poster_bg) per la lezione, base 'positivo'."""
import sys, os, math, json, random
sys.path.insert(0, '/home/user/bot-telegram/contenuti/yardfx_video'); import yardfx as Y; import suoni as S
from PIL import Image, ImageDraw, ImageFilter
D = os.path.dirname(os.path.abspath(__file__))
WORDS = json.load(open(os.path.join(D, 'words.json')))
for i, s in [(1, '+864'), (74, '+864')]: WORDS[i][0] = s
G = Y.make_groups(WORDS)
T = lambda i: WORDS[i][1]
VEND = WORDS[-1][2]
KEYS = {1, 6, 9, 13, 21, 26, 30, 33, 36, 41, 44, 46, 49, 55, 60, 62, 64, 67, 69, 71, 74, 77, 84, 86, 90, 92, 96, 99, 101}
CUTS = [0, T(16), T(37), T(51), T(68), T(76), T(102), VEND + 0.3]
OUT_LEN = 4.2; DUR = CUTS[-1] + OUT_LEN
TRANS = ['whip', 'blur', 'zoom', 'wipe', 'whip_v', 'zoom']
TD = 0.4; TIKTOK = os.environ.get('TIKTOK') == '1'
TRADES = [('BUY', 8.57), ('BUY', -30.10), ('BUY', -39.72), ('SELL', 70.27), ('SELL', 9.88), ('SELL', 45.69), ('SELL', 21.79)]
PIPSF = [v * 10 for _, v in TRADES]            # pips esatti (totale 863,8 → +864)
PIPS = [round(p) for p in PIPSF]
EV = []
def ev(t, n, g=1.0): EV.append((round(t, 3), n, g))
SP = Y.sprite
def big(b, s, xy, size, col, font=Y.BIG): ImageDraw.Draw(b).text(xy, s, font=Y.F(font, size), fill=col, anchor='mm')
def chip(d, s, xy, col, size=44):
    f = Y.F(Y.COND, size); tw = d.textlength(s, font=f); x, y = xy
    d.rounded_rectangle((x - tw / 2 - 26, y - size * .8, x + tw / 2 + 26, y + size * .8), radius=size, fill=tuple(int(v * .22) for v in col), outline=col, width=4)
    d.text((x, y), s, font=f, fill=col, anchor='mm')
def mini_card(b, y, side, pips, t0, t, w=820):
    a = Y.ease((t - t0) / 0.45)
    if a <= 0: return
    d = ImageDraw.Draw(b); col = Y.GREEN if pips > 0 else Y.RED; x0 = (Y.W - w) / 2 + 120 * (1 - a)
    d.rounded_rectangle((x0, y - 62, x0 + w, y + 62), radius=22, fill=Y.CARD, outline=col, width=4)
    sc = Y.GREEN if side == 'BUY' else Y.RED
    d.rounded_rectangle((x0 + 30, y - 30, x0 + 170, y + 30), radius=12, fill=sc); d.text((x0 + 100, y), side, font=Y.F(Y.COND, 42), fill=Y.DARK, anchor='mm')
    d.text((x0 + w - 36, y), f"{pips:+d} PIPS".replace('-', '−'), font=Y.F(Y.BIG, 70), fill=col, anchor='rm')

# ---------- S1 NOTTE: il totale ----------
def s1(t):
    img = Y.night_bg(t); img = Y.light_beams(img, t); img = Y.dust(img, t, 50, 3, Y.GOLD, 45)
    img = Y.spotlight(img, Y.W // 2 + 40 * math.sin(t), 90, 900, 600, 55)
    img = Y.pulse_rings(img, Y.W // 2, 520, t + 0.6, Y.GREEN, 1.4, 3, 460)
    img = Y.big_counter(img, 864, (Y.W // 2, 520), 280, Y.GREEN, t + 1.3, 0, 1.2, '{:+,.0f}')
    img = SP(img, lambda b: big(b, 'PIPS', (Y.W // 2, 700), 110, Y.WHITE), t, -0.3, enter='pop', idle='breathe', seed=1)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('questa', 'serif', 80, Y.MUTE), ('SETTIMANA', 'big', 100, Y.GOLD)], 860), t, T(3), enter='rise', idle='float', seed=2)
    img = SP(img, lambda b: chip(ImageDraw.Draw(b), 'VERBALI FED', (Y.W // 2, 1000), Y.ICE), t, T(5), enter='left', idle='wobble', seed=3, amp=0.4)
    img = SP(img, lambda b: chip(ImageDraw.Draw(b), 'VENDITE AL DETTAGLIO', (Y.W // 2, 1120), Y.ICE), t, T(7), enter='right', idle='wobble', seed=4, amp=0.4)
    img = SP(img, lambda b: Y.number_roll(b, '7 TRADE', (Y.W // 2, 1290), 130, Y.GOLD, t, T(13), 0.5), t, T(13), enter='stamp', idle='breathe', seed=5, dur=0.3)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [("sull'oro", 'serif', 70, Y.WHITE)], 1420), t, T(15), enter='rise', idle='float', seed=6)
    img = Y.camera(img, t, 0, punches=[T(1), T(5), T(7), T(13)], shakes=[T(13) + 0.5])
    return Y.color_flash(img, t, [T(13) + 0.5], Y.GREEN, 0.14, 0.3), True
ev(0, 'boom', 0.7); ev(0.05, 'coin', 0.6); [ev(0.1 + k * 0.08, 'tick', 0.35) for k in range(5)]; ev(T(3), 'swoosh_up', 0.5); ev(T(5), 'pop'); ev(T(5) + 0.05, 'swipe', 0.5)
ev(T(7), 'pop'); ev(T(7) + 0.05, 'swipe', 0.5); [ev(T(13) + k * 0.06, 'tick', 0.4) for k in range(8)]; ev(T(13) + 0.5, 'ding'); ev(T(15), 'click', 0.5)

# ---------- S2 TERMINALE: martedì, i due stop ----------
def s2(t):
    img = Y.term_bg(); img = Y.light_sweep(img, t, 3.2, 200, 35); img = Y.dust(img, t, 30, 7, Y.ICE, 30)
    img = SP(img, lambda b: big(b, 'MARTEDÌ', (Y.W // 2, 320), 130, Y.WHITE), t, T(16), enter='drop', idle='float', seed=7)
    img = SP(img, lambda b: mini_card(b, 520, 'BUY', PIPS[0], T(18), t), t, T(18), enter='none', idle='float', seed=8, amp=0.4)
    img = SP(img, lambda b: chip(ImageDraw.Draw(b), 'DUE BUY CONTRO LA DISCESA', (Y.W // 2, 700), Y.GOLD, 46), t, T(24), enter='pop', idle='wobble', seed=9, amp=0.4)
    img = SP(img, lambda b: mini_card(b, 870, 'BUY', PIPS[1], T(32), t), t, T(32), enter='none', idle='float', seed=10, amp=0.4)
    img = SP(img, lambda b: mini_card(b, 1040, 'BUY', PIPS[2], T(35), t), t, T(35), enter='none', idle='float', seed=11, amp=0.4)
    img = SP(img, lambda b: Y.stamp(b, 'STOP LOSS', (Y.W // 2, 1250), 100, Y.RED, -5), t, T(30), enter='stamp', idle='wobble', seed=12, dur=0.3, amp=0.4)
    img = Y.camera(img, t, CUTS[1], punches=[T(21), T(26), T(30), T(33), T(36)], shakes=[T(30)])
    img = Y.color_flash(img, t, [T(21)], Y.GREEN, 0.12, 0.25); return Y.color_flash(img, t, [T(30), T(33), T(36)], Y.RED, 0.12, 0.25), True
ev(CUTS[1], 'swipe'); ev(T(16), 'pop'); ev(T(18), 'swipe', 0.6); ev(T(21), 'ding', 0.7); ev(T(24), 'pop', 0.6); ev(T(30), 'stamp'); ev(T(30) + 0.05, 'alert', 0.5)
ev(T(32), 'swipe', 0.6); ev(T(33), 'boom', 0.4); ev(T(35), 'swipe', 0.6); ev(T(36), 'boom', 0.4)

# ---------- S3 NOTTE: mercoledì, il sell da +703 ----------
def s3(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 50, 13, Y.GOLD, 50); img = Y.light_beams(img, t + 2, n=2, strength=16)
    img = SP(img, lambda b: big(b, 'MERCOLEDÌ', (Y.W // 2, 320), 120, Y.WHITE), t, T(37), enter='drop', idle='float', seed=13)
    img = SP(img, lambda b: chip(ImageDraw.Draw(b), 'VERBALI FED', (Y.W // 2, 450), Y.ICE), t, T(40), enter='pop', idle='wobble', seed=14, amp=0.4)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('ho cambiato', 'serif', 80, Y.MUTE), ('DIREZIONE', 'big', 104, Y.GOLD)], 620), t, T(42), enter='rise', idle='float', seed=15)
    if t > T(44): img = Y.pulse_rings(img, Y.W // 2, 800, t - T(44), Y.RED, 1.2, 2, 300)
    img = SP(img, lambda b: Y.glow_text(b, 'SELL', (Y.W // 2, 800), 200, Y.RED, (120, 40, 30)), t, T(46), enter='stamp', idle='breathe', seed=16, dur=0.3)
    img = Y.confetti(img, t, T(49) + 0.6, Y.W // 2, 1050, 60, Y.GOLD, 1.8, 5)
    if t > T(48): img = Y.big_counter(img, 703, (Y.W // 2, 1050), 230, Y.GREEN, t, T(48), 0.7, '{:+,.0f}')
    img = SP(img, lambda b: big(b, 'PIPS', (Y.W // 2, 1220), 100, Y.WHITE), t, T(50), enter='pop', idle='breathe', seed=17)
    img = Y.camera(img, t, CUTS[2], punches=[T(40), T(44), T(46), T(49) + 0.6], shakes=[T(49) + 0.6])
    return Y.color_flash(img, t, [T(49) + 0.6], Y.GREEN, 0.16, 0.35), True
ev(CUTS[2], 'whoosh', 0.7); ev(T(37), 'pop'); ev(T(40), 'pop_hi', 0.6); ev(T(42), 'swoosh_up', 0.5); ev(T(46), 'stamp', 0.7); [ev(T(48) + k * 0.07, 'tick', 0.4) for k in range(9)]
ev(T(49) + 0.6, 'boom', 0.7); ev(T(49) + 0.62, 'coin'); ev(T(49) + 0.8, 'coin', 0.6); ev(T(50), 'pop')

# ---------- S4 TERMINALE: giovedì e venerdì, solo sell ----------
CUM = []
_c = 0
for p in PIPSF: _c += p; CUM.append(_c)
def s4(t):
    img = Y.term_bg(); img = Y.light_sweep(img, t + 1.5, 3.4, 200, 30); img = Y.dust(img, t, 25, 11, Y.ICE, 30)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('GIOVEDÌ', 'big', 96, Y.WHITE), ('e', 'serif', 70, Y.MUTE), ('VENERDÌ', 'big', 96, Y.WHITE)], 330), t, T(51), enter='drop', idle='float', seed=18)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), 'SOLO SELL', (Y.W // 2 - 220, 450), 64, Y.ease((t - T(54)) / 0.35), Y.RED, Y.WHITE), t, T(54), enter='pop', idle='breathe', seed=19)
    img = SP(img, lambda b: chip(ImageDraw.Draw(b), 'TREND RIBASSISTA', (Y.W // 2 + 210, 450), Y.RED, 40), t, T(59), enter='right', idle='wobble', seed=20, amp=0.4)
    for k, (wi, y) in enumerate([(62, 600), (64, 740), (67, 880)]):
        img = SP(img, lambda b, k=k, wi=wi, y=y: mini_card(b, y, 'SELL', PIPS[4 + k], T(wi), t), t, T(wi), enter='none', idle='float', seed=21 + k, amp=0.4)
    if t > T(54):
        n = 4 + sum(1 for wi in (62, 64, 67) if t > T(wi))
        vals = [0] + CUM[:n]
        img = Y.equity_curve(img, vals, (140, 1010, 940, 1400), Y.ease((t - T(54)) / 0.8) if n == 4 else 1, None, Y.GOLD)
    img = Y.camera(img, t, CUTS[3], punches=[T(55), T(60), T(62), T(64), T(67)], shakes=[T(67)])
    return Y.color_flash(img, t, [T(62), T(64), T(67)], Y.GREEN, 0.1, 0.2), True
ev(CUTS[3], 'swipe'); ev(T(51), 'pop'); ev(T(53), 'pop', 0.6); ev(T(54), 'pop_hi'); ev(T(59), 'swipe', 0.5); ev(T(55), 'riser', 0.3)
for wi in (62, 64, 67): ev(T(wi), 'swipe', 0.5); ev(T(wi) + 0.3, 'ding', 0.6)

# ---------- S5 QUADERNO: la cascata e il totale ----------
def s5(t):
    img = Y.cream_bg(); d = ImageDraw.Draw(img)
    Y.waterfall(d, [('', p) for p in PIPSF], (90, 330, 990, 1000), t, CUTS[4] + 0.1, 0.18, False, '')
    img = SP(img, lambda b: big(b, '5 VINTE', (310, 1150), 100, Y.GREEN_K), t, T(68), enter='pop', idle='wobble', seed=24, amp=0.5)
    img = SP(img, lambda b: big(b, '2 PERSE', (770, 1150), 100, Y.RED), t, T(70), enter='pop', idle='wobble', seed=25, amp=0.5)
    img = SP(img, lambda b: Y.stamp(b, 'TOTALE +864 PIPS', (Y.W // 2, 1330), 96, Y.GOLDK, -4), t, T(73), enter='stamp', idle='wobble', seed=26, dur=0.3, amp=0.4)
    img = Y.camera(img, t, CUTS[4], punches=[T(68), T(70), T(73)], shakes=[T(73)], push=0.04)
    return Y.color_flash(img, t, [T(73)], Y.GOLD, 0.14, 0.3), False
ev(CUTS[4], 'whoosh', 0.7); [ev(CUTS[4] + 0.1 + k * 0.18, 'bubble', 0.5) for k in range(8)]; ev(T(68), 'pop'); ev(T(70), 'pop', 0.7); ev(T(73), 'stamp'); ev(T(73) + 0.05, 'coin')

# ---------- S6 POSTER: la lezione ----------
def s6(t):
    img = Y.poster_bg(t)
    img = Y.word_stack(img, [('la', 'small', T(76)), ('LEZIONE', 'big', T(77))], Y.W // 2, 330, t, Y.INK, Y.GOLDK)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('i due stop', 'serif', 74, Y.INK)], 640), t, T(78), enter='rise', idle='float', seed=27)
    img = SP(img, lambda b: big(b, 'CONTRO IL TREND', (Y.W // 2, 750), 104, Y.RED), t, T(84), enter='pop', idle='wobble', seed=28, amp=0.4)
    d = ImageDraw.Draw(img)
    if t > T(86): Y.icon(d, 'croce', 960, 750, 90, Y.ease((t - T(86)) / 0.3), Y.RED, 10, 3)
    img = SP(img, lambda b: big(b, 'SEGUENDO IL TREND', (Y.W // 2, 920), 96, Y.GREEN_K), t, T(87), enter='pop', idle='wobble', seed=29, amp=0.4)
    img = SP(img, lambda b: Y.key_box(ImageDraw.Draw(b), '4 SELL SU 4 A TARGET', (Y.W // 2, 1060), 70, Y.ease((t - T(91)) / 0.4), Y.GREEN_K, Y.WHITE), t, T(91), enter='stamp', idle='breathe', seed=30, dur=0.3)
    d = ImageDraw.Draw(img)
    if t > T(96): Y.icon(d, 'spunta', 960, 1060, 90, Y.ease((t - T(96)) / 0.3), Y.GREEN_K, 10, 4)
    img = SP(img, lambda b: Y.stamp(b, 'PRIMA LA DIREZIONE', (Y.W // 2, 1250), 80, Y.INK, -3), t, T(97), enter='stamp', idle='wobble', seed=31, dur=0.3, amp=0.4)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('poi', 'serif', 76, Y.MUTE), ("L'ENTRATA", 'big', 96, Y.GOLDK)], 1430), t, T(100), enter='rise', idle='float', seed=32)
    img = Y.camera(img, t, CUTS[5], punches=[T(77), T(84), T(91), T(97), T(100)], shakes=[T(86)], push=0.04)
    img = Y.color_flash(img, t, [T(86)], Y.RED, 0.12, 0.22); return Y.color_flash(img, t, [T(96)], Y.GREEN, 0.12, 0.22), False
ev(CUTS[5], 'swoosh_up', 0.6); ev(T(77), 'pop'); ev(T(78), 'click', 0.5); ev(T(84), 'pop'); ev(T(86), 'alert', 0.5); ev(T(87), 'pop_hi'); ev(T(91), 'stamp', 0.6); ev(T(96), 'ding'); ev(T(97), 'stamp'); ev(T(100), 'swoosh_up', 0.5)

# ---------- S7 CTA ----------
CTA_T = [T(107), T(110), T(112), T(117)]
def s7(t):
    img = Y.night_bg(t); img = Y.dust(img, t, 50, 17, Y.GOLD, 55)
    img = SP(img, lambda b: Y.mixed_title(ImageDraw.Draw(b), [('se ti è stato', 'serif', 90, Y.WHITE), ('UTILE', 'big', 110, Y.GOLD)], 420), t, CUTS[6], enter='drop', idle='float', seed=33)
    img = Y.cta_four(img, t, CTA_T, 'VERDE/ROSSO', y0=640)
    return Y.camera(img, t, CUTS[6], punches=CTA_T, push=0.03), True
ev(CUTS[6], 'swoosh_up'); ev(T(106), 'pop'); ev(CTA_T[0], 'pop'); ev(CTA_T[1], 'pop_hi'); ev(CTA_T[1] + 0.05, 'bubble', 0.6); ev(CTA_T[2], 'bubble'); ev(T(115), 'pop', 0.5); ev(CTA_T[3], 'swoosh_up'); ev(CTA_T[3] + 0.1, 'coin')

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
NAME = 'yardfx_recap_16-20nov'
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
        S.music(os.path.join(D, 'base.wav'), DUR, 96, 'positivo')
        a = S.mix(os.path.join(D, 'audio.m4a'), DUR, voce=os.path.join(D, 'voce.mp3'), musica=os.path.join(D, 'base.wav'), eventi=EV, music_db=-16)
        for tag in ['ig', 'tt']:
            lst = os.path.join(D, f'list_{tag}.txt'); open(lst, 'w').write(f"file 'main.mp4'\nfile 'outro_{tag}.mp4'\n")
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-i', a, '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'copy', '-shortest', '-movflags', '+faststart',
                            os.path.join(D, f'{NAME}_{"instagram" if tag == "ig" else "tiktok"}.mp4')], check=True)
        print('ok', DUR, len(EV))
