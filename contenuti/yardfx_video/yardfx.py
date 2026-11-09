"""Kit grafico dello stile video YardFX (@yard.fx). Vedi ../GUIDA_STILE_YARDFX.md.

Uso tipico in uno script di montaggio:
    import sys; sys.path.insert(0, 'contenuti/yardfx_video'); import yardfx as Y
    WORDS = Y.tts_elevenlabs(testo, 'voce.mp3')          # oppure Y.load_words('words.json')
    def frame(t): ...  (usa Y.dark_bg, Y.cream_bg, Y.chapter_candles, Y.captions, ...)
    Y.render(frame, durata, 'voce.mp3', 'video.mp4')
Tutte le funzioni disegnano su immagini PIL 1080x1920. Le funzioni con `prog` (0..1) animano il tratto.
"""
import os, math, json, random, base64, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter

D = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
BIG, HAND, COND, COND6 = 'Anton.ttf', 'Caveat.ttf', 'BC-800.ttf', 'BC-600.ttf'
# palette
DARK = (13, 12, 10); CREAM = (246, 241, 230); INK = (30, 27, 22); YEL = (238, 196, 92)
GOLD = (214, 166, 58); GOLDK = (170, 120, 25); GOLD_SOFT = (245, 214, 130)
WHITE = (240, 236, 226); MUTE = (150, 142, 128)
RED = (224, 72, 62); GREEN = (70, 200, 120); GREEN_K = (36, 146, 88)
_fc = {}
def F(name, s):
    k = (name, s)
    if k not in _fc: _fc[k] = ImageFont.truetype(os.path.join(D, 'fonts', name), s)
    return _fc[k]
def ease(x): x = max(0.0, min(1.0, x)); return 1 - (1 - x) ** 3
def fade(col, a, bg=DARK): return tuple(int(b + (c - b) * a) for c, b in zip(col, bg))

# ---------------- voce ----------------
def tts_elevenlabs(text, out_mp3, voice='JBFqnCBsd6RMkjVDRZzb', model='eleven_v4'):
    """Genera l'MP3 con ElevenLabs (chiave iniettata dal proxy) e restituisce [[parola, inizio, fine], ...].
    Voce Enea (aQ9s2C5T9TIPvAFtHWuA) solo con piano a pagamento; altrimenti George (default) o Brian (nPczCjzI2devNBz1zQrb)."""
    req = out_mp3 + '.req.json'; res = out_mp3 + '.tts.json'
    json.dump({'text': text, 'model_id': model, 'voice_settings': {'stability': 0.5, 'similarity_boost': 0.75}}, open(req, 'w'), ensure_ascii=False)
    subprocess.run(['curl', '-sS', '-X', 'POST', f'https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps',
                    '-H', 'xi-api-key: proxy-injected', '-H', 'Content-Type: application/json', '--data', '@' + req, '-o', res], check=True)
    r = json.load(open(res))
    if 'audio_base64' not in r: raise RuntimeError(r)
    open(out_mp3, 'wb').write(base64.b64decode(r['audio_base64']))
    a = r['alignment']; words = []; cur = ''; s = pe = 0
    for c, b, e in zip(a['characters'], a['character_start_times_seconds'], a['character_end_times_seconds']):
        if c.isspace():
            if cur: words.append([cur, s, pe]); cur = ''
            continue
        if not cur: s = b
        cur += c; pe = e
    if cur: words.append([cur, s, pe])
    json.dump(words, open(os.path.splitext(out_mp3)[0] + '_words.json', 'w'), ensure_ascii=False)
    return words

def words_from_whisper(mp3):
    """Per un MP3 registrato/caricato da Salvatore: tempi parola per parola con faster-whisper (pip install faster-whisper)."""
    from faster_whisper import WhisperModel
    segs, _ = WhisperModel('small', compute_type='int8').transcribe(mp3, language='it', word_timestamps=True)
    return [[w.word.strip(), w.start, w.end] for s in segs for w in s.words]

def load_words(path): return json.load(open(path))

# ---------------- sfondi ----------------
def dark_bg(t, seed=7):
    """nero caldo con alone oro al centro e brillantini che pulsano"""
    img = Image.new('RGB', (W, H), DARK)
    g = Image.new('L', (W, H), 0); ImageDraw.Draw(g).ellipse((80, 500, W - 80, 1300), fill=70)
    img = Image.composite(Image.new('RGB', (W, H), (70, 52, 16)), img, g.filter(ImageFilter.GaussianBlur(200)))
    d = ImageDraw.Draw(img); r = random.Random(seed)
    for _ in range(70):
        x, y = r.uniform(0, W), r.uniform(0, H); ph = r.uniform(0, 6.28); sp = r.uniform(0.6, 1.6)
        a = 0.5 + 0.5 * math.sin(t * sp * 2 + ph); s = 1 + 2.5 * a * r.uniform(0.4, 1)
        d.ellipse((x - s, y - s, x + s, y + s), fill=tuple(int(v * (0.3 + 0.7 * a)) for v in GOLD))
    return img
_PAPER = None
def cream_bg():
    """carta crema con grana"""
    global _PAPER
    if _PAPER is None:
        r = random.Random(3); _PAPER = Image.new('RGB', (W, H), CREAM); d = ImageDraw.Draw(_PAPER)
        for _ in range(9000):
            v = r.randint(-9, 5); d.point((r.uniform(0, W), r.uniform(0, H)), fill=tuple(max(0, min(255, c + v)) for c in CREAM))
    return _PAPER.copy()
def yellow_bg(): return Image.new('RGB', (W, H), YEL)

def circle_wipe(img_from, img_to, prog, center=(W // 2, H // 2)):
    """tendina circolare: la scena nuova si apre da un cerchio che cresce (prog 0..1, durata consigliata 0.4 s)"""
    if prog <= 0: return img_from
    if prog >= 1: return img_to
    r = ease(prog) * math.hypot(W, H)
    m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).ellipse((center[0] - r, center[1] - r, center[0] + r, center[1] + r), fill=255)
    out = Image.composite(img_to, img_from, m)
    ImageDraw.Draw(out).ellipse((center[0] - r, center[1] - r, center[0] + r, center[1] + r), outline=GOLD, width=8)
    return out

# ---------------- firme fisse ----------------
def chapter_candles(d, n, tot, dark, label, prog=1.0):
    """candeline dei capitoli in alto a sinistra (al posto della barra del tempo) + nome capitolo a mano"""
    for i in range(tot):
        x = 70 + i * 34; on = i < n
        col = GOLD if on else ((60, 56, 46) if dark else (205, 198, 182))
        d.line([(x, 92), (x, 158)], fill=col, width=3); d.rectangle((x - 9, 104, x + 9, 146), fill=col)
    hand(d, label, (70 + tot * 34 + 14, 125), 50, GOLD if dark else GOLDK, prog, anchor='lm')

def gold_candle(img, cx, top, bot, body_top, body_bot, w=120, grow=1.0):
    """la candela d'oro luminosa (apertura e chiusura); grow 0..1 la fa crescere dal basso"""
    if grow <= 0: return img
    g = ease(grow); mid = body_bot
    top = mid - (mid - top) * g; body_top = mid - (mid - body_top) * g
    gl = Image.new('L', (W, H), 0); ImageDraw.Draw(gl).rectangle((cx - w, body_top - 40, cx + w, body_bot + 40), fill=int(150 * g))
    img = Image.composite(Image.new('RGB', (W, H), (110, 80, 20)), img, gl.filter(ImageFilter.GaussianBlur(70)))
    d = ImageDraw.Draw(img)
    d.line([(cx, top), (cx, bot)], fill=GOLD, width=10)
    d.rounded_rectangle((cx - w / 2, body_top, cx + w / 2, body_bot), radius=10, fill=GOLD)
    if body_bot - body_top > 30: d.rectangle((cx - w / 2 + 12, body_top + 12, cx - w / 2 + 26, body_bot - 12), fill=GOLD_SOFT)
    return img

def outro(t, s):
    """chiusura fissa: candela d'oro, SEGUIMI, SCRIVIMI IN DM, @yard.fx. s = secondi dall'inizio della chiusura"""
    img = dark_bg(t); img = gold_candle(img, W / 2, 300, 700, 400, 620, 100, s / 0.6); d = ImageDraw.Draw(img)
    a = ease((s - 0.3) / 0.4)
    d.text((W / 2, 880), 'SEGUIMI', font=F(BIG, 170), fill=fade(WHITE, a), anchor='mm')
    d.text((W / 2, 1020), 'E SCRIVIMI IN DM', font=F(BIG, 80), fill=fade(GOLD, a), anchor='mm')
    hand(d, 'per entrare nella community', (W / 2, 1110), 58, WHITE, ease((s - 0.6) / 0.6))
    if s > 0.9:
        d.rounded_rectangle((W / 2 - 200, 1190, W / 2 + 200, 1280), radius=45, fill=GOLD)
        d.text((W / 2, 1235), '@yard.fx', font=F(COND, 62), fill=DARK, anchor='mm')
    return img

def disclaimer(d, dark):
    d.text((W / 2, H - 70), 'Contenuto informativo. Il trading comporta rischi.', font=F(COND6, 28), fill=(110, 104, 92) if dark else (150, 143, 128), anchor='mm')

# ---------------- sottotitoli ----------------
def make_groups(words, maxw=3):
    """gruppi di max 3 parole, spezzati su punteggiatura"""
    groups, cur = [], []
    for i, (w, s, e) in enumerate(words):
        cur.append(i)
        if w[-1] in '.,?:!' or len(cur) == maxw: groups.append(cur); cur = []
    if cur: groups.append(cur)
    return groups

def captions(img, t, words, groups, keys, dark, y=1585, end=None):
    """parola per parola: la parola detta si accende, le parole in `keys` (indici) vanno nel riquadro oro"""
    d = ImageDraw.Draw(img); gi = None
    for g in groups:
        if words[g[0]][1] - 0.05 <= t: gi = g
    if gi is None or t > (end if end is not None else words[-1][2] + 0.3): return
    f = F(COND, 76); sp = 22
    txt = [words[i][0].upper().strip('.,:;') for i in gi]
    ws = [d.textlength(w, font=f) for w in txt]; x = W / 2 - (sum(ws) + sp * (len(txt) - 1)) / 2
    for i, w, wd in zip(gi, txt, ws):
        said = words[i][1] <= t
        if said and i in keys:
            d.rounded_rectangle((x - 14, y - 46, x + wd + 14, y + 44), radius=12, fill=GOLD); col = DARK
        else:
            col = (WHITE if dark else INK) if said else (MUTE if dark else (175, 168, 152))
        d.text((x, y), w, font=f, fill=col, anchor='lm'); x += wd + sp

def find_word(words, prefix, after=0):
    """indice della prima parola che inizia con prefix (senza maiuscole) dal tempo `after`"""
    for i, w in enumerate(words):
        if w[1] >= after and w[0].lower().strip(".,:;?!'").startswith(prefix.lower()): return i
    raise KeyError(prefix)

# ---------------- testo ----------------
def pop(d, s, xy, size, col, t, t0, font=BIG, anchor='mm'):
    """testo che entra con un piccolo zoom"""
    a = ease((t - t0) / 0.18)
    if a <= 0: return
    d.text(xy, s, font=F(font, int(size * (0.86 + 0.14 * a))), fill=col, anchor=anchor)

def hand(d, s, xy, size, col, prog=1.0, anchor='mm'):
    """scrittura a mano che compare lettera per lettera"""
    if prog <= 0: return
    k = max(1, int(len(s) * min(1, prog)))
    if prog < 1 and anchor == 'mm':
        x, y = xy; full = d.textlength(s, font=F(HAND, size))
        d.text((x - full / 2, y), s[:k], font=F(HAND, size), fill=col, anchor='lm')
    else:
        d.text(xy, s[:k], font=F(HAND, size), fill=col, anchor=anchor)

def glow_text(img, s, xy, size, col, halo=(90, 70, 20), a=1.0, font=BIG):
    """numero/titolo grande con alone luminoso"""
    if a <= 0: return img
    m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).text(xy, s, font=F(font, size), fill=int(255 * a), anchor='mm')
    img = Image.composite(Image.new('RGB', (W, H), halo), img, m.filter(ImageFilter.GaussianBlur(28)).point(lambda v: int(v * .7)))
    return Image.composite(Image.new('RGB', (W, H), col), img, m)

def key_box(d, s, xy, size, prog=1.0, fill=GOLD, col=DARK):
    """parola dentro riquadro pieno che si allarga da sinistra"""
    if prog <= 0: return
    f = F(BIG, size); tw = d.textlength(s, font=f); x, y = xy
    x0 = x - tw / 2 - 20; x1 = x0 + (tw + 40) * ease(prog)
    d.rounded_rectangle((x0, y - size * 0.62, x1, y + size * 0.62), radius=14, fill=fill)
    if prog > 0.6: d.text(xy, s, font=f, fill=col, anchor='mm')

def stamp(img, s, cxy, size, col, angle, a=1.0):
    """timbro inclinato con doppio bordo e inchiostro consumato; entra con a 0..1 (scala da grande a normale)"""
    if a <= 0: return
    f = F(BIG, size); tw = int(ImageDraw.Draw(img).textlength(s, font=f))
    lay = Image.new('RGBA', (tw + 80, size + 70), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle((6, 6, tw + 74, size + 64), radius=14, outline=col + (235,), width=7)
    d.rounded_rectangle((18, 18, tw + 62, size + 52), radius=8, outline=col + (160,), width=3)
    d.text(((tw + 80) / 2, (size + 70) / 2 + 2), s, font=f, fill=col + (235,), anchor='mm')
    r = random.Random(4); px = lay.load()
    for _ in range(int(lay.width * lay.height * 0.05)):
        x, y = r.randrange(lay.width), r.randrange(lay.height)
        if px[x, y][3]: px[x, y] = px[x, y][:3] + (px[x, y][3] // 3,)
    sc = 1.6 - 0.6 * ease(a)
    lay = lay.resize((int(lay.width * sc), int(lay.height * sc))).rotate(angle, expand=True, resample=Image.BICUBIC)
    if a < 1: lay.putalpha(lay.getchannel('A').point(lambda v: int(v * ease(a))))
    img.paste(lay, (int(cxy[0] - lay.width / 2), int(cxy[1] - lay.height / 2)), lay)

def strike_swap(d, old, new, y, prog, old_col=(160, 152, 138), new_col=RED, size=140):
    """vecchio valore barrato in rosso → freccia → valore nuovo"""
    d.text((330, y), old, font=F(BIG, size - 10), fill=old_col, anchor='mm')
    stroke(d, [(220, y + 10), (440, y - 10)], ease(prog / 0.4), RED, 9, seed=40)
    arrow(d, 470, y, 600, y, ease((prog - 0.4) / 0.3), INK if old_col != WHITE else WHITE, 6, 41)
    if prog > 0.7: d.text((760, y), new, font=F(BIG, size), fill=new_col, anchor='mm')

# ---------------- disegno a mano ----------------
def wobble(pts, seed, amp=2.2):
    r = random.Random(seed); out = []
    for i in range(len(pts) - 1):
        (x0, y0), (x1, y1) = pts[i], pts[i + 1]
        n = max(2, int(math.hypot(x1 - x0, y1 - y0) / 14))
        for k in range(n):
            f = k / n; out.append((x0 + (x1 - x0) * f + r.uniform(-amp, amp), y0 + (y1 - y0) * f + r.uniform(-amp, amp)))
    out.append(pts[-1]); return out
def stroke(d, pts, prog, col, w=6, seed=1, amp=2.2):
    if prog <= 0: return
    p = wobble(pts, seed, amp); k = max(2, int(len(p) * min(1, prog)))
    d.line(p[:k], fill=col, width=w, joint='curve')
def circle_pts(cx, cy, rx, ry, turns=1.12, n=60):
    return [(cx + rx * math.cos(-2.3 + 2 * math.pi * turns * i / n), cy + ry * math.sin(-2.3 + 2 * math.pi * turns * i / n)) for i in range(n + 1)]
def circle(d, cx, cy, rx, ry, prog, col=RED, w=9, seed=11):
    """cerchio a mano attorno a una parola/numero"""
    stroke(d, circle_pts(cx, cy, rx, ry), prog, col, w, seed, 3)
def arrow(d, x0, y0, x1, y1, prog, col, w=6, seed=3):
    stroke(d, [(x0, y0), ((x0 + x1) / 2 + 12, (y0 + y1) / 2 - 10), (x1, y1)], prog, col, w, seed)
    if prog >= 0.98:
        a = math.atan2(y1 - y0, x1 - x0)
        for s in (-1, 1): d.line([(x1, y1), (x1 - 26 * math.cos(a + s * 0.5), y1 - 26 * math.sin(a + s * 0.5))], fill=col, width=w)
def underline(d, x0, x1, y, prog, col=GOLD, seed=8): stroke(d, [(x0, y), (x1, y - 8)], prog, col, 6, seed)
def marker(img, box, prog, col=YEL, alpha=200):
    """evidenziatore dietro un testo (disegnare il testo dopo)"""
    if prog <= 0: return
    x0, y0, x1, y1 = box; m = Image.new('L', img.size, 0)
    ImageDraw.Draw(m).polygon([(x0, y0 + 6), (x0 + (x1 - x0) * prog, y0), (x0 + (x1 - x0) * prog, y1 - 4), (x0 - 4, y1)], fill=alpha)
    img.paste(Image.new('RGB', img.size, col), (0, 0), m)

# icone a tratto (coordinate su 100x100)
ICONS = {
    'carrello': [[(5, 20), (20, 20), (32, 65), (82, 65), (92, 32), (25, 32)], [(38, 82), (39, 83)], [(72, 82), (73, 83)]],
    'prezzo': [[(10, 50), (45, 15), (88, 15), (88, 58), (53, 92), (10, 50)], [(70, 32), (72, 33)]],
    'banca': [[(8, 38), (50, 10), (92, 38), (8, 38)], [(18, 44), (18, 80)], [(38, 44), (38, 80)], [(62, 44), (62, 80)], [(82, 44), (82, 80)], [(6, 88), (94, 88)]],
    'lingotto': [[(10, 75), (25, 40), (75, 40), (90, 75), (10, 75)], [(25, 40), (32, 55), (68, 55), (75, 40)]],
    'calendario': [[(12, 22), (88, 22), (88, 90), (12, 90), (12, 22)], [(12, 40), (88, 40)], [(30, 10), (30, 30)], [(70, 10), (70, 30)]],
    'orologio': [[(50, 8), (80, 20), (92, 50), (80, 80), (50, 92), (20, 80), (8, 50), (20, 20), (50, 8)], [(50, 50), (50, 25)], [(50, 50), (70, 60)]],
    'dollaro': [[(72, 25), (50, 18), (30, 28), (32, 45), (68, 55), (70, 72), (50, 82), (28, 75)], [(50, 6), (50, 94)]],
    'fabbrica': [[(8, 90), (8, 45), (35, 60), (35, 45), (62, 60), (62, 20), (78, 20), (78, 90), (8, 90)]],
    'persone': [[(30, 30), (31, 31)], [(70, 30), (71, 31)], [(12, 85), (18, 55), (42, 55), (48, 85)], [(52, 85), (58, 55), (82, 55), (88, 85)]],
    'scudo': [[(50, 8), (88, 22), (84, 60), (50, 92), (16, 60), (12, 22), (50, 8)], [(32, 50), (45, 63), (70, 38)]],
    'spunta': [[(15, 52), (40, 76), (88, 24)]],
    'croce': [[(20, 20), (80, 80)], [(80, 20), (20, 80)]],
    'grafico_su': [[(8, 85), (35, 55), (55, 68), (90, 20)], [(70, 20), (90, 20), (90, 40)]],
    'grafico_giu': [[(8, 20), (35, 50), (55, 38), (90, 85)], [(70, 85), (90, 85), (90, 65)]],
    'bandiera': [[(15, 95), (15, 8)], [(15, 10), (85, 10), (85, 55), (15, 55)], [(15, 25), (85, 25)], [(15, 40), (85, 40)]],
}
def icon(d, name, cx, cy, size, prog, col, w=6, seed=5):
    paths = ICONS[name]; n = len(paths)
    for j, path in enumerate(paths):
        pts = [(cx + (x - 50) * size / 100, cy + (y - 50) * size / 100) for x, y in path]
        if len(path) == 2 and abs(path[0][0] - path[1][0]) < 3 and abs(path[0][1] - path[1][1]) < 3:
            if prog > (j + 0.5) / n: d.ellipse((pts[0][0] - 9, pts[0][1] - 9, pts[0][0] + 9, pts[0][1] + 9), outline=col, width=w)
            continue
        stroke(d, pts, prog * n - j, col, w, seed + j)

def chain(d, items, y, t, t0, dt, col, dark):
    """catena causa → effetto: items = [(icona, etichetta), ...] su una riga, ognuno compare dopo dt secondi"""
    n = len(items); xs = [W / (n + 1) * (i + 1) for i in range(n)]; sz = min(170, W / (n + 1) * 0.62); gap = sz * 0.55
    for i, (ic, lab) in enumerate(items):
        a = ease((t - t0 - i * dt) / 0.6)
        if a <= 0: continue
        icon(d, ic, xs[i], y, sz, a, col, 7, 10 + i * 7)
        hand(d, lab, (xs[i], y + sz * 0.85), 52 if n < 4 else 44, MUTE if not dark else WHITE, ease((t - t0 - i * dt - 0.2) / 0.5))
        if i > 0: arrow(d, xs[i - 1] + gap, y, xs[i] - gap, y, a, MUTE, 5, 30 + i)

# ---------------- grafici ----------------
def candles_chart(img, cs, box, lo, hi, prog=1.0, zones=(), levels=(), panel=True):
    """grafico a candele ridisegnato (mai screenshot).
    cs: [{'o','h','l','c','g'}]; zones: [(da, a, 'ENTRY', colore)]; levels: [(prezzo, 'TESTO', colore)]; prog fa comparire le candele"""
    x0, y0, x1, y1 = box; d = ImageDraw.Draw(img)
    py = lambda p: y1 - (p - lo) / (hi - lo) * (y1 - y0)
    if panel: d.rounded_rectangle((x0 - 20, y0 - 40, x1 + 20, y1 + 40), radius=22, fill=(20, 19, 24), outline=(50, 46, 40), width=2)
    for a, b, lab, col in zones:
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(lay).rectangle((x0 + (x1 - x0) * 0.35, py(b), x1, py(a)), fill=col + (60,), outline=col + (220,), width=3)
        img.paste(lay, (0, 0), lay)
    d = ImageDraw.Draw(img); step = (x1 - x0) / len(cs); k = int(len(cs) * ease(prog))
    for i, c in enumerate(cs[:k]):
        x = x0 + 12 + i * step; col = (47, 179, 106) if c['g'] else (224, 72, 62)
        d.line([(x, py(min(c['h'], hi))), (x, py(max(c['l'], lo)))], fill=col, width=3)
        ya, yb = sorted([py(c['o']), py(c['c'])]); d.rectangle((x - step * .32, ya, x + step * .32, max(yb, ya + 3)), fill=col)
    for a, b, lab, col in zones:
        y = (py(a) + py(b)) / 2; tw = d.textlength(lab, font=F(COND, 44))
        d.rounded_rectangle((x1 - tw - 46, y - 30, x1 - 10, y + 30), radius=10, fill=col); d.text((x1 - 28, y), lab, font=F(COND, 44), fill=DARK, anchor='rm')
    for p, lab, col in levels:
        y = py(p)
        for xx in range(int(x0), int(x1), 26): d.line([(xx, y), (xx + 14, y)], fill=col, width=4)
        tw = d.textlength(lab, font=F(COND, 40)); d.rounded_rectangle((x0, y - 28, x0 + tw + 30, y + 28), radius=10, fill=col)
        d.text((x0 + 15, y), lab, font=F(COND, 40), fill=DARK, anchor='lm')
    return py

def banner(d, s, y, col, prog=1.0):
    """banner del risultato ('TAKE PROFIT · +2R', 'STOP PRESO')"""
    if prog <= 0: return
    w = 780 * ease(prog); d.rounded_rectangle((W / 2 - w / 2, y - 40, W / 2 + w / 2, y + 40), radius=16, fill=col)
    if prog > 0.7: d.text((W / 2, y), s, font=F(COND, 62), fill=DARK, anchor='mm')

def week_strip(d, t, t0, days, active, marks, y=1180):
    """schede LUN-VEN: days=[('LUN','10'),...], marks={indice:'CPI'}, active=indice acceso"""
    a = ease((t - t0) / 0.4)
    if a <= 0: return
    n = len(days); gap = W / (n + 0.5)
    for i, (g, num) in enumerate(days):
        cx = gap * (i + 0.75); hot = i == active; on = i in marks
        col = GOLD if hot else (GOLDK if on else (60, 56, 46))
        d.rounded_rectangle((cx - 85, y, cx + 85, y + 220), radius=16, fill=fade((52, 40, 14) if hot else (22, 20, 16), a), outline=fade(col, a), width=4)
        d.text((cx, y + 50), g, font=F(COND, 44), fill=fade(WHITE if hot else MUTE, a), anchor='mm')
        d.text((cx, y + 120), num, font=F(BIG, 70), fill=fade(WHITE, a), anchor='mm')
        if on: d.text((cx, y + 185), marks[i], font=F(COND, 40), fill=fade(GOLD, a), anchor='mm')

def checklist(d, items, box, t, t0, dt=0.55, dark=True):
    """riquadro con voci che si spuntano una alla volta"""
    x0, y0, x1, y1 = box; a = ease((t - t0) / 0.4)
    if a <= 0: return
    d.rounded_rectangle(box, radius=22, fill=fade((20, 18, 14), a) if dark else None, outline=fade(GOLD, a), width=4)
    for i, it in enumerate(items):
        c = ease((t - t0 - 0.4 - dt * i) / 0.35)
        if c <= 0: continue
        y = y0 + 80 + i * 92
        d.text((x0 + 70, y), it, font=F(COND, 60), fill=WHITE if dark else INK, anchor='lm')
        icon(d, 'spunta', x1 - 90, y, 70, c, GREEN, 9, 50 + i)

def big_counter(img, value, xy, size, col, t, t0, dur=1.2, fmt='{:+,.0f}', halo=(30, 80, 50)):
    """numero che conta da 0 al valore con alone (pips, percentuali)"""
    a = ease((t - t0) / dur)
    if (t - t0) <= 0: return img
    s = fmt.format(value * a).replace(',', '.')
    return glow_text(img, s, xy, size, col, halo)

# ---------------- render ----------------
def render(frame, dur, audio, out, fps=FPS, pad_audio=True):
    """frame(t)->PIL RGB 1080x1920; audio mp3/m4a; scrive mp4 h264 pronto per TikTok/Reel"""
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-', '-i', audio]
    cmd += (['-filter_complex', f'[1:a]apad=whole_dur={dur},loudnorm=I=-14:TP=-1.5[a]', '-map', '0:v', '-map', '[a]'] if pad_audio else ['-map', '0:v', '-map', '1:a'])
    cmd += ['-c:a', 'aac', '-b:a', '192k', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'medium', '-movflags', '+faststart', '-t', str(dur), out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(int(dur * fps)): p.stdin.write(frame(i / fps).convert('RGB').tobytes())
    p.stdin.close(); p.wait()
    if p.returncode: raise RuntimeError('ffmpeg ha fallito')
    return out

def contact_sheet(frame, times, out, w=216):
    """anteprima: fotogrammi affiancati per controllare il montaggio prima del render"""
    ims = [frame(t).convert('RGB').resize((w, int(w * 16 / 9))) for t in times]
    s = Image.new('RGB', ((w + 4) * len(ims), ims[0].height), 'white')
    for i, im in enumerate(ims): s.paste(im, (i * (w + 4), 0))
    s.save(out); return out

def music_pad(dur, out, root=110.0):
    """base musicale soft senza copyright (accordo minore con tremolo ed eco), per mindset e meme"""
    fr = [root, root * 2, root * 2.378, root * 2.997, root * 4]
    cmd = ['ffmpeg', '-v', 'error', '-y']
    for f in fr: cmd += ['-f', 'lavfi', '-i', f'sine=f={f}:d={dur}']
    cmd += ['-filter_complex', '[0][1][2][3][4]amix=inputs=5:weights=0.9 0.6 0.45 0.4 0.15,tremolo=f=0.4:d=0.35,aecho=0.8:0.7:420|860:0.35|0.22,lowpass=f=1800,'
            f'afade=t=in:d=1.5,afade=t=out:st={dur - 2}:d=2,loudnorm=I=-16', '-c:a', 'aac', '-b:a', '160k', out]
    subprocess.run(cmd, check=True); return out
