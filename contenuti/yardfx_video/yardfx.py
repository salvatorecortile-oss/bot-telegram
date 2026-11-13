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
        icon(d, 'spunta', x0 + 70, y, 60, c, GREEN, 9, 50 + i)
        d.text((x0 + 125, y), it, font=F(COND, 60), fill=WHITE if dark else INK, anchor='lm')

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

# =====================================================================
# I TRE MONDI (ogni video li alterna; le firme YardFX restano in tutti)
#   NOTTE     (video 1 + 4): gancio, numeri, settimana  -> night_bg, rays, constellation, glow_icon, timeline_nodes, spotlight
#   TERMINALE (video 2 + 5 + 6): dati, livelli, trade   -> term_bg, price_widget, ui_card, perspective, zoom_callout, prob_bars
#   QUADERNO  (r601 + video 3): spiegare il perché      -> grid_paper, serif_heading, dashed_arrow (+ hand, icon, stamp)
# =====================================================================
SERIF, MONO, SANS = 'InstrumentSerif-Italic.ttf', 'JetBrainsMono-Bold.ttf', 'Inter-SemiBold.ttf'
NAVY = (8, 11, 22); NAVY2 = (18, 26, 48); ICE = (150, 190, 255); TERM = (12, 13, 16); CARD = (24, 25, 30); CARD_LINE = (48, 50, 58)
GRIDPAPER = (244, 242, 236); GRIDLINE = (214, 218, 222)

def _vgrad(top, bot):
    g = Image.linear_gradient('L').resize((W, H)); return Image.composite(Image.new('RGB', (W, H), bot), Image.new('RGB', (W, H), top), g)

_NIGHT = None
def night_bg(t, ray_origin=(W // 2, -200), rays=True):
    """NOTTE: blu-nero profondo, raggi sottili che ruotano piano, costellazione che respira, griglia di particelle in basso"""
    global _NIGHT
    if _NIGHT is None:
        b = _vgrad(NAVY, (4, 5, 10)); d = ImageDraw.Draw(b)
        for gx in range(0, W, 36):                       # griglia di particelle (prospettiva semplice)
            for k, gy in enumerate(range(1250, H, 34)):
                a = min(1, (gy - 1250) / 500); c = int(30 + 40 * a)
                d.ellipse((gx - 1.5, gy - 1.5, gx + 1.5, gy + 1.5), fill=(c // 2, c // 2 + 6, c + 20))
        _NIGHT = b
    img = _NIGHT.copy()
    if rays:
        lay = Image.new('L', (W, H), 0); ld = ImageDraw.Draw(lay); ox, oy = ray_origin
        for i in range(28):
            ang = math.pi / 2 + (i - 14) * 0.075 + 0.02 * math.sin(t * 0.4 + i)
            ld.line([(ox, oy), (ox + 2600 * math.cos(ang), oy + 2600 * math.sin(ang))], fill=22 + (i % 3) * 8, width=2)
        img = Image.composite(Image.new('RGB', (W, H), (60, 80, 140)), img, lay.filter(ImageFilter.GaussianBlur(1.2)))
    constellation(img, t)
    return img

def constellation(img, t, seed=21, n=26, box=(0, 0, W, 1150)):
    d = ImageDraw.Draw(img); r = random.Random(seed)
    pts = [(r.uniform(box[0], box[2]), r.uniform(box[1], box[3])) for _ in range(n)]
    for i, (x, y) in enumerate(pts):
        for j in range(i + 1, n):
            x2, y2 = pts[j]
            if math.hypot(x - x2, y - y2) < 190: d.line([(x, y), (x2, y2)], fill=(34, 44, 72), width=1)
    for i, (x, y) in enumerate(pts):
        a = 0.5 + 0.5 * math.sin(t * 1.3 + i); s = 2 + 2 * a
        d.ellipse((x - s, y - s, x + s, y + s), fill=tuple(int(v * (0.5 + 0.5 * a)) for v in ICE))

def spotlight(img, cx, top_y, bottom_y, width=420, strength=90, col=(255, 220, 140)):
    """faretto dall'alto su un oggetto (video 1)"""
    m = Image.new('L', (W, H), 0)
    ImageDraw.Draw(m).polygon([(cx - 40, top_y), (cx + 40, top_y), (cx + width / 2, bottom_y), (cx - width / 2, bottom_y)], fill=strength)
    ImageDraw.Draw(m).ellipse((cx - width / 2, bottom_y - 40, cx + width / 2, bottom_y + 40), fill=strength + 30)
    return Image.composite(Image.new('RGB', (W, H), col), img, m.filter(ImageFilter.GaussianBlur(40)))

def glow_icon(img, name, cx, cy, size, prog, col=GOLD, w=6):
    """icona a tratto PULITA (non tremolante) con bagliore: per i mondi Notte e Terminale"""
    if prog <= 0: return img
    m = Image.new('L', (W, H), 0); md = ImageDraw.Draw(m); paths = ICONS[name]; n = len(paths)
    for j, path in enumerate(paths):
        p = max(0, min(1, prog * n - j))
        if p <= 0: continue
        pts = [(cx + (x - 50) * size / 100, cy + (y - 50) * size / 100) for x, y in path]
        if len(path) == 2 and abs(path[0][0] - path[1][0]) < 3:
            md.ellipse((pts[0][0] - 8, pts[0][1] - 8, pts[0][0] + 8, pts[0][1] + 8), fill=255); continue
        seg = [pts[0]]; L = sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1)) * p
        for i in range(len(pts) - 1):
            dl = math.dist(pts[i], pts[i + 1])
            if L >= dl: seg.append(pts[i + 1]); L -= dl
            else:
                f = L / dl if dl else 0; seg.append((pts[i][0] + (pts[i + 1][0] - pts[i][0]) * f, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * f)); break
        md.line(seg, fill=255, width=w, joint='curve')
    img = Image.composite(Image.new('RGB', (W, H), tuple(int(v * 0.55) for v in col)), img, m.filter(ImageFilter.GaussianBlur(14)))
    return Image.composite(Image.new('RGB', (W, H), col), img, m)

def timeline_nodes(img, items, y, active, t, t0, x0=110, x1=970):
    """linea del tempo con nodi luminosi (video 4): items=[('LUN','9',''),('MAR','10','CPI'),...]"""
    a = ease((t - t0) / 0.6)
    if a <= 0: return img
    d = ImageDraw.Draw(img); n = len(items); xs = [x0 + (x1 - x0) * i / (n - 1) for i in range(n)]
    d.line([(x0, y), (x0 + (x1 - x0) * a, y)], fill=(60, 72, 110), width=4)
    if active is not None and a > 0.3: d.line([(x0, y), (xs[active], y)], fill=GOLD, width=4)
    m = Image.new('L', (W, H), 0); md = ImageDraw.Draw(m)
    for i, (g, num, tag) in enumerate(items):
        if xs[i] > x0 + (x1 - x0) * a + 1: continue
        hot = i == active; r = 22 if hot else (14 if tag else 9)
        if hot or tag: md.ellipse((xs[i] - r - 14, y - r - 14, xs[i] + r + 14, y + r + 14), fill=200 if hot else 90)
        d.ellipse((xs[i] - r, y - r, xs[i] + r, y + r), fill=GOLD if (hot or tag) else (70, 84, 130))
        d.text((xs[i], y - 60), g, font=F(MONO, 30), fill=WHITE if hot else (120, 135, 175), anchor='mm')
        d.text((xs[i], y + 62), num, font=F(BIG, 52), fill=WHITE if hot else (150, 160, 190), anchor='mm')
        if tag: d.text((xs[i], y + 115), tag, font=F(MONO, 30), fill=GOLD, anchor='mm')
    img = Image.composite(Image.new('RGB', (W, H), (140, 100, 30)), img, m.filter(ImageFilter.GaussianBlur(16)))
    d = ImageDraw.Draw(img)
    for i, (g, num, tag) in enumerate(items):
        if xs[i] <= x0 + (x1 - x0) * a + 1 and (i == active or tag):
            r = 22 if i == active else 14; d.ellipse((xs[i] - r, y - r, xs[i] + r, y + r), fill=GOLD)
            if i == active: d.ellipse((xs[i] - 8, y - 8, xs[i] + 8, y + 8), fill=WHITE)
    return img

def mixed_title(d, parts, y, cx=W // 2):
    """titolo misto (video 3 + 7): parts=[('oggi alle','serif',90,WHITE),('14:30','big',200,GOLD)] sulla stessa riga"""
    fonts = {'serif': SERIF, 'big': BIG, 'cond': COND, 'mono': MONO}
    ws = [d.textlength(s, font=F(fonts[k], sz)) for s, k, sz, c in parts]; sp = 24
    x = cx - (sum(ws) + sp * (len(parts) - 1)) / 2
    for (s, k, sz, c), wd in zip(parts, ws):
        d.text((x, y), s, font=F(fonts[k], sz), fill=c, anchor='ls'); x += wd + sp

# ---------- TERMINALE ----------
_TERM = None
def term_bg():
    """TERMINALE: grafite scura con griglia sottile a punti"""
    global _TERM
    if _TERM is None:
        _TERM = _vgrad((16, 17, 21), (9, 9, 11)); d = ImageDraw.Draw(_TERM)
        for x in range(0, W, 54):
            for y in range(0, H, 54): d.point((x, y), fill=(42, 44, 52))
    return _TERM.copy()

def price_widget(d, price, chg_pct, y=125, label='XAUUSD'):
    """widget fisso del prezzo in alto a destra (video 5): resta uguale in tutte le scene Terminale"""
    up = chg_pct >= 0; col = GREEN if up else RED
    s = f"{price:,.1f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    x1 = W - 60; x0 = x1 - 330
    d.rounded_rectangle((x0, y - 42, x1, y + 42), radius=14, fill=CARD, outline=CARD_LINE, width=2)
    d.ellipse((x0 + 22, y - 7, x0 + 36, y + 7), fill=col)
    d.text((x0 + 50, y - 14), label, font=F(MONO, 22), fill=MUTE, anchor='lm')
    d.text((x0 + 50, y + 14), s, font=F(MONO, 30), fill=WHITE, anchor='lm')
    arrow_ch = ('+' if up else '−') + f"{abs(chg_pct):.1f}%".replace('.', ',')
    d.text((x1 - 22, y), arrow_ch, font=F(MONO, 28), fill=col, anchor='rm')

def ui_card(rows, cols, title, w=900, highlight=None, col_w=None):
    """scheda tipo app (calendario economico, MT5): rows=[[...celle...]], ritorna un'immagine RGBA da posare o mettere in prospettiva"""
    rh = 96; h = 130 + rh * (len(rows) + 1) + 30
    card = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(card)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=26, fill=CARD + (255,), outline=CARD_LINE + (255,), width=3)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]): d.ellipse((30 + i * 34, 34, 50 + i * 34, 54), fill=c)
    d.text((w / 2, 44), title, font=F(MONO, 28), fill=MUTE, anchor='mm')
    col_w = col_w or [w // len(cols)] * len(cols); xs = [40]
    for cw in col_w[:-1]: xs.append(xs[-1] + cw)
    y = 110
    for x, c in zip(xs, cols): d.text((x, y + rh / 2), c, font=F(MONO, 24), fill=(110, 112, 124), anchor='lm')
    d.line([(30, y + rh), (w - 30, y + rh)], fill=CARD_LINE, width=2)
    for r, row in enumerate(rows):
        yy = y + rh * (r + 1)
        if r == highlight: d.rounded_rectangle((18, yy + 8, w - 18, yy + rh - 8), radius=16, fill=(52, 42, 18, 255))
        for x, cell in zip(xs, row):
            col = WHITE
            if isinstance(cell, tuple): cell, col = cell
            d.text((x, yy + rh / 2), cell, font=F(SANS, 38), fill=col, anchor='lm')
        if r < len(rows) - 1: d.line([(30, yy + rh), (w - 30, yy + rh)], fill=(36, 38, 44), width=1)
    card.info['row_y'] = [y + rh * (r + 1) for r in range(len(rows))]; card.info['rh'] = rh
    return card

def _coeffs(src, dst):
    import numpy as np
    A = []; B = []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B += [u, v]
    return list(np.linalg.solve(np.array(A, float), np.array(B, float)))

def perspective(img, layer, quad, shadow=True):
    """posa un livello (es. ui_card) su un quadrilatero: quad = [alto-sx, alto-dx, basso-dx, basso-sx] (video 4: schermi in prospettiva 3D)"""
    w, h = layer.size
    c = _coeffs([(0, 0), (w, 0), (w, h), (0, h)], quad)
    warped = layer.transform((W, H), Image.PERSPECTIVE, c, Image.BICUBIC)
    if shadow:
        sh = warped.getchannel('A').filter(ImageFilter.GaussianBlur(30)).point(lambda v: int(v * 0.6))
        img.paste(Image.new('RGB', (W, H), (0, 0, 0)), (0, 30), sh)
    img.paste(warped, (0, 0), warped); return img

def map_point(layer, quad, x, y):
    """dove finisce il punto (x,y) del livello dopo perspective()"""
    w, h = layer.size; c = _coeffs([(0, 0), (w, 0), (w, h), (0, h)], quad)
    import numpy as np
    a, b, cc, dd, e, f, g, hh = c
    M = np.array([[a, b, cc], [dd, e, f], [g, hh, 1]]); X = np.linalg.inv(M) @ np.array([x, y, 1]); return X[0] / X[2], X[1] / X[2]

def zoom_callout(img, src_box, dst_center, scale, prog, ring=GOLD):
    """lente di ingrandimento (video 2): ritaglia src_box, lo ingrandisce dentro un riquadro oro con linea di collegamento"""
    if prog <= 0: return img
    a = ease(prog); crop = img.crop(tuple(int(v) for v in src_box))
    cw, ch = int(crop.width * scale * (0.7 + 0.3 * a)), int(crop.height * scale * (0.7 + 0.3 * a)); crop = crop.resize((cw, ch), Image.LANCZOS)
    x, y = int(dst_center[0] - cw / 2), int(dst_center[1] - ch / 2)
    d = ImageDraw.Draw(img)
    d.line([((src_box[0] + src_box[2]) / 2, src_box[3]), (dst_center[0], y)], fill=ring, width=3)
    d.rounded_rectangle(src_box, radius=12, outline=ring, width=4)
    m = Image.new('L', (cw, ch), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, cw - 1, ch - 1), radius=22, fill=255)
    img.paste(crop, (x, y), m); ImageDraw.Draw(img).rounded_rectangle((x, y, x + cw, y + ch), radius=22, outline=ring, width=6)
    return img

def chip(d, s, xy, ok=True):
    """etichetta ✓ / ✕ (video 2)"""
    col = GREEN if ok else RED; f = F(COND, 44); tw = d.textlength(s, font=f); x, y = xy
    d.rounded_rectangle((x, y - 34, x + tw + 90, y + 34), radius=34, fill=tuple(int(v * 0.25) for v in col), outline=col, width=3)
    icon(d, 'spunta' if ok else 'croce', x + 36, y, 34, 1, col, 6, 3); d.text((x + 66, y), s, font=f, fill=col, anchor='lm')

def prob_bars(d, items, box, t, t0):
    """barre orizzontali di scenario (video 5): items=[('CPI SOPRA 3,7%','oro ↓',62,RED), ...] valori 0-100"""
    x0, y0, x1, y1 = box; a = ease((t - t0) / 0.4)
    if a <= 0: return
    d.rounded_rectangle(box, radius=24, fill=CARD, outline=CARD_LINE, width=2)
    for i, (lab, eff, v, col) in enumerate(items):
        y = y0 + 70 + i * 130; b = ease((t - t0 - 0.3 - i * 0.25) / 0.8)
        d.text((x0 + 40, y), lab, font=F(COND, 46), fill=WHITE, anchor='lm'); d.text((x1 - 40, y), eff, font=F(COND, 46), fill=col, anchor='rm')
        d.rounded_rectangle((x0 + 40, y + 34, x1 - 40, y + 58), radius=12, fill=(40, 42, 50))
        d.rounded_rectangle((x0 + 40, y + 34, x0 + 40 + (x1 - x0 - 80) * v / 100 * b, y + 58), radius=12, fill=col)

# ---------- QUADERNO ----------
_GRID = None
def grid_paper():
    """QUADERNO: carta a quadretti (video 3) con grana leggera"""
    global _GRID
    if _GRID is None:
        _GRID = Image.new('RGB', (W, H), GRIDPAPER); d = ImageDraw.Draw(_GRID)
        for x in range(0, W, 54): d.line([(x, 0), (x, H)], fill=GRIDLINE, width=1)
        for y in range(0, H, 54): d.line([(0, y), (W, y)], fill=GRIDLINE, width=1)
        r = random.Random(5)
        for _ in range(6000):
            v = r.randint(-8, 4); d.point((r.uniform(0, W), r.uniform(0, H)), fill=tuple(max(0, min(255, c + v)) for c in GRIDPAPER))
    return _GRID.copy()

def serif_heading(d, num_word, title, y, col=INK, accent=GOLDK, prog=1.0):
    """titolo numerato elegante (video 3): 'due:' in corsivo graziato + titolo in bastone grosso"""
    if prog <= 0: return
    a = ease(prog); f1 = F(SERIF, 96); f2 = F(BIG, 96)
    w1 = d.textlength(num_word, font=f1); w2 = d.textlength(title, font=f2); x = W / 2 - (w1 + 24 + w2) / 2
    d.text((x, y), num_word, font=f1, fill=accent, anchor='ls')
    d.text((x + w1 + 24, y), title, font=f2, fill=col if a >= 1 else fade(col, a, GRIDPAPER), anchor='ls')

def dashed_arrow(d, x0, y0, x1, y1, prog, col=INK, w=5, dash=18):
    """freccia tratteggiata dritta (video 3)"""
    if prog <= 0: return
    L = math.hypot(x1 - x0, y1 - y0) * min(1, prog); ux, uy = (x1 - x0) / math.hypot(x1 - x0, y1 - y0), (y1 - y0) / math.hypot(x1 - x0, y1 - y0)
    s = 0
    while s < L:
        e = min(L, s + dash); d.line([(x0 + ux * s, y0 + uy * s), (x0 + ux * e, y0 + uy * e)], fill=col, width=w); s += dash * 1.8
    if prog >= 0.98:
        a = math.atan2(y1 - y0, x1 - x0)
        d.polygon([(x1, y1), (x1 - 30 * math.cos(a - 0.45), y1 - 30 * math.sin(a - 0.45)), (x1 - 30 * math.cos(a + 0.45), y1 - 30 * math.sin(a + 0.45))], fill=col)

# =====================================================================
# ELEMENTI PER GLI ALTRI FORMATI (recap, journal, lezione, mindset, meme, CTA)
# =====================================================================
def trade_card(img, xy, side, entry, sl, tp, result, prog=1.0, w=900, symbol='XAUUSD'):
    """scheda di un trade stile app (recap / journal): side 'BUY'/'SELL', result es. '+320 pips' o '−250 pips'"""
    a = ease(prog)
    if a <= 0: return img
    win = not result.strip().startswith(('−', '-')); col = GREEN if win else RED
    h = 300; card = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(card)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=26, fill=CARD + (255,), outline=col + (255,), width=4)
    sc = GREEN if side.upper() == 'BUY' else RED
    d.rounded_rectangle((32, 30, 160, 82), radius=12, fill=sc); d.text((96, 56), side.upper(), font=F(COND, 40), fill=DARK, anchor='mm')
    d.text((185, 56), symbol, font=F(MONO, 36), fill=WHITE, anchor='lm')
    d.text((w - 36, 56), result, font=F(BIG, 64), fill=col, anchor='rm')
    for i, (lab, v, c) in enumerate([('ENTRY', entry, GOLD), ('SL', sl, RED), ('TP', tp, GREEN)]):
        x = 40 + i * (w - 80) / 3
        d.text((x, 150), lab, font=F(MONO, 26), fill=MUTE, anchor='lm'); d.text((x, 205), v, font=F(SANS, 46), fill=c, anchor='lm')
    d.rounded_rectangle((40, 250, w - 40, 262), radius=6, fill=(40, 42, 50)); d.rounded_rectangle((40, 250, 40 + (w - 80) * a, 262), radius=6, fill=col)
    x, y = xy; x = x + 80 * (1 - a)
    if a < 1: card.putalpha(card.getchannel('A').point(lambda v: int(v * a)))
    img.paste(card, (int(x - w / 2), int(y - h / 2)), card); return img

def equity_curve(img, values, box, prog, label=None, col=GOLD):
    """curva cumulata (pips o saldo) che si disegna con area sfumata e punto finale luminoso"""
    x0, y0, x1, y1 = box; n = len(values); lo, hi = min(min(values), 0), max(values)
    X = lambda i: x0 + (x1 - x0) * i / (n - 1); Y_ = lambda v: y1 - (v - lo) / (hi - lo or 1) * (y1 - y0)
    k = (n - 1) * ease(prog); pts = [(X(i), Y_(values[i])) for i in range(int(k) + 1)]
    if int(k) < n - 1:
        f = k - int(k); i = int(k); pts.append((X(i) + (X(i + 1) - X(i)) * f, Y_(values[i]) + (Y_(values[i + 1]) - Y_(values[i])) * f))
    d = ImageDraw.Draw(img); d.line([(x0, Y_(0)), (x1, Y_(0))], fill=(70, 70, 80), width=2)
    if len(pts) < 2: return img
    m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).polygon(pts + [(pts[-1][0], y1), (pts[0][0], y1)], fill=70)
    img = Image.composite(Image.new('RGB', (W, H), col), img, m.filter(ImageFilter.GaussianBlur(6)))
    gl = Image.new('L', (W, H), 0); ImageDraw.Draw(gl).line(pts, fill=255, width=10, joint='curve')
    img = Image.composite(Image.new('RGB', (W, H), col), img, gl.filter(ImageFilter.GaussianBlur(10)).point(lambda v: v // 2))
    d = ImageDraw.Draw(img); d.line(pts, fill=col, width=8, joint='curve')
    ex, ey = pts[-1]; d.ellipse((ex - 14, ey - 14, ex + 14, ey + 14), fill=WHITE, outline=col, width=5)
    if label and prog >= 1: d.text((ex - 20, ey - 50), label, font=F(BIG, 70), fill=col, anchor='rs')
    return img

def dial(img, cx, cy, r, value, prog, label, segments=10, col=GOLD):
    """quadrante a segmenti (video 1): rischio, volatilità, fiducia… value 0-100"""
    d = ImageDraw.Draw(img); on = int(segments * value / 100 * ease(prog) + 0.5)
    for i in range(segments):
        a0 = 150 + i * 240 / segments + 2; a1 = 150 + (i + 1) * 240 / segments - 2
        c = (RED if i >= segments * 0.7 else col) if i < on else (50, 52, 62)
        d.arc((cx - r, cy - r, cx + r, cy + r), a0, a1, fill=c, width=int(r * 0.22))
    d.text((cx, cy), f"{int(value * ease(prog))}%", font=F(BIG, int(r * 0.6)), fill=WHITE, anchor='mm')
    d.text((cx, cy + r * 0.62), label, font=F(MONO, int(r * 0.17)), fill=MUTE, anchor='mm'); return img

def notification(img, app, title, body, y, prog, col=GOLD):
    """notifica che scende dall'alto (video 2): es. ('MT5', 'Take profit raggiunto', 'XAUUSD +320 pips')"""
    a = ease(prog)
    if a <= 0: return img
    yy = y - 260 * (1 - a); x0, x1 = 70, W - 70
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle((x0, yy, x1, yy + 170), radius=34, fill=(36, 37, 44, 245), outline=(70, 72, 82, 255), width=2)
    d.rounded_rectangle((x0 + 30, yy + 35, x0 + 130, yy + 135), radius=24, fill=col)
    gold_mini = [(x0 + 80, yy + 50), (x0 + 80, yy + 120)]; d.line(gold_mini, fill=DARK, width=5); d.rectangle((x0 + 66, yy + 66, x0 + 94, yy + 104), fill=DARK)
    d.text((x0 + 160, yy + 52), app, font=F(MONO, 26), fill=MUTE, anchor='lm'); d.text((x1 - 34, yy + 52), 'ora', font=F(MONO, 26), fill=MUTE, anchor='rm')
    d.text((x0 + 160, yy + 95), title, font=F(SANS, 40), fill=WHITE, anchor='lm'); d.text((x0 + 160, yy + 138), body, font=F(SANS, 34), fill=(190, 192, 200), anchor='lm')
    img.paste(lay, (0, 0), lay); return img

def phone(img, screen, cx, cy, h=1100, tilt=0.0):
    """smartphone (anche inclinato, tilt -0.15..0.15) con dentro uno schermo (immagine RGB qualsiasi, es. grafico o scheda)"""
    w = int(h * 0.49); body = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(body)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=70, fill=(28, 28, 32, 255), outline=(90, 90, 100, 255), width=4)
    sw, sh = w - 36, h - 36; scr = screen.convert('RGB').resize((sw, sh)); m = Image.new('L', (sw, sh), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, sw - 1, sh - 1), radius=56, fill=255)
    body.paste(scr, (18, 18), m); d.rounded_rectangle((w / 2 - 70, 34, w / 2 + 70, 66), radius=16, fill=(10, 10, 12, 255))
    k = tilt * w
    quad = [(cx - w / 2 + k, cy - h / 2 + abs(k) * 0.4), (cx + w / 2 + k, cy - h / 2 - abs(k) * 0.4), (cx + w / 2 - k, cy + h / 2 + abs(k) * 0.4), (cx - w / 2 - k, cy + h / 2 - abs(k) * 0.4)]
    return perspective(img, body, quad)

def quote(d, lines, y, size=120, col=WHITE, accent=GOLD, bg=DARK):
    """citazione elegante per mindset: virgolette grandi in corsivo + righe; la riga che inizia con '*' va in oro bastone"""
    d.text((W / 2, y - size * 0.6), '“', font=F(SERIF, size * 2), fill=accent, anchor='mm')
    yy = y + size * 0.5
    for ln in lines:
        if ln.startswith('*'): d.text((W / 2, yy), ln[1:], font=F(BIG, int(size * 1.05)), fill=accent, anchor='mm'); yy += size * 1.15
        else: d.text((W / 2, yy), ln, font=F(SERIF, size), fill=col, anchor='mm'); yy += size * 1.0

def split_meme(top, bottom, top_label, bottom_label, prog=1.0):
    """meme a due metà (es. 'io alle 14:29' / 'io alle 14:31'): top e bottom sono immagini 1080x1920 (vengono ritagliate a metà)"""
    out = Image.new('RGB', (W, H), DARK)
    out.paste(top.crop((0, H // 4, W, H // 4 + H // 2)), (0, 0))
    if prog > 0: out.paste(bottom.crop((0, H // 4, W, H // 4 + H // 2)), (0, H // 2))
    d = ImageDraw.Draw(out); d.rectangle((0, H // 2 - 6, W, H // 2 + 6), fill=GOLD)
    for lab, y in [(top_label, 70), (bottom_label, H // 2 + 70)]:
        if y > H // 2 and prog <= 0: continue
        tw = d.textlength(lab, font=F(BIG, 70)); d.rounded_rectangle((W / 2 - tw / 2 - 26, y - 50, W / 2 + tw / 2 + 26, y + 50), radius=14, fill=WHITE)
        d.text((W / 2, y), lab, font=F(BIG, 70), fill=DARK, anchor='mm')
    return out

def shake(img, t, amp=14, freq=27):
    """scossa della camera (meme, dato che esce): sposta l'immagine di qualche pixel"""
    dx = int(amp * math.sin(t * freq)); dy = int(amp * 0.7 * math.cos(t * freq * 1.3))
    out = Image.new('RGB', (W, H), DARK); out.paste(img.resize((W + 2 * amp, H + 2 * amp)), (dx - amp, dy - amp)); return out

def comment_cta(img, word, y, prog, dark=True):
    """fumetto commento (video 3, 'SCRIVIMI COSTO'): 'Commenta GUIDA'"""
    a = ease(prog)
    if a <= 0: return img
    d = ImageDraw.Draw(img); x0, x1 = 120, W - 120; yy = y + 40 * (1 - a)
    d.rounded_rectangle((x0, yy, x1, yy + 190), radius=40, fill=CARD if dark else WHITE, outline=GOLD, width=4)
    d.polygon([(x0 + 90, yy + 188), (x0 + 60, yy + 250), (x0 + 150, yy + 188)], fill=GOLD)
    d.ellipse((x0 + 40, yy + 55, x0 + 120, yy + 135), fill=GOLD); d.text((x0 + 80, yy + 95), 'Y', font=F(BIG, 50), fill=DARK, anchor='mm')
    d.text((x0 + 150, yy + 65), 'commenta', font=F(SERIF, 62), fill=WHITE if dark else INK, anchor='lm')
    if a > 0.5: key_box(d, word, (x0 + 150 + d.textlength(word, font=F(BIG, 90)) / 2 + 10, yy + 135), 70, (a - 0.5) * 2)
    return img

def follow_card(img, prog, followers=None):
    """scheda profilo finale (video 4): avatar con candela d'oro, @yard.fx, bottone SEGUI"""
    a = ease(prog)
    if a <= 0: return img
    d = ImageDraw.Draw(img); x0, y0, x1, y1 = 140, 760 + 60 * (1 - a), W - 140, 1160 + 60 * (1 - a)
    d.rounded_rectangle((x0, y0, x1, y1), radius=36, fill=CARD, outline=CARD_LINE, width=3)
    cx, cy = x0 + 130, y0 + 130; d.ellipse((cx - 80, cy - 80, cx + 80, cy + 80), fill=DARK, outline=GOLD, width=6)
    d.line([(cx, cy - 55), (cx, cy + 55)], fill=GOLD, width=6); d.rounded_rectangle((cx - 22, cy - 32, cx + 22, cy + 30), radius=5, fill=GOLD)
    d.text((cx + 120, cy - 30), '@yard.fx', font=F(BIG, 70), fill=WHITE, anchor='lm')
    d.text((cx + 122, cy + 35), 'oro · XAUUSD · ogni giorno', font=F(MONO, 26), fill=MUTE, anchor='lm')
    bw = (x1 - x0 - 80); btn = ease((prog - 0.5) * 2)
    d.rounded_rectangle((x0 + 40, y1 - 120, x0 + 40 + bw, y1 - 40), radius=40, fill=GOLD if btn < 1 else (60, 62, 70))
    d.text((W / 2, y1 - 80), 'SEGUI' if btn < 1 else 'SEGUITO', font=F(COND, 54), fill=DARK if btn < 1 else WHITE, anchor='mm')
    return img

def poll(d, a_txt, b_txt, y, prog, a_col=GREEN, b_col=RED):
    """sondaggio sopra/sotto per chiudere con un commento"""
    p = ease(prog)
    if p <= 0: return
    for i, (s, c) in enumerate([(a_txt, a_col), (b_txt, b_col)]):
        x0 = 100 + i * 460; d.rounded_rectangle((x0, y, x0 + 420, y + 200), radius=30, fill=fade(tuple(int(v * 0.25) for v in c), p), outline=fade(c, p), width=5)
        d.text((x0 + 210, y + 100), s, font=F(BIG, 90), fill=fade(c, p), anchor='mm')
    d.text((W / 2, y + 100), 'o', font=F(SERIF, 80), fill=WHITE, anchor='mm')

def number_roll(img, value_str, xy, size, col, t, t0, dur=0.6):
    """numero che 'rotola' come un contachilometri prima di fermarsi sul valore (per dati appena usciti)"""
    if t < t0: return img
    if t - t0 < dur:
        r = random.Random(int((t - t0) * 30)); s = ''.join(str(r.randint(0, 9)) if ch.isdigit() else ch for ch in value_str)
        return glow_text(img, s, xy, size, MUTE)
    return glow_text(img, value_str, xy, size, col)

# ---------------- tempi delle parole da un MP3 registrato (voce Enea di Salvatore) ----------------
def speech_segments(mp3, noise='-32dB', min_sil=0.22):
    """tratti di voce [(inizio, fine)] trovati con le pause di ffmpeg silencedetect"""
    out = subprocess.run(['ffmpeg', '-hide_banner', '-i', mp3, '-af', f'silencedetect=noise={noise}:d={min_sil}', '-f', 'null', '-'], capture_output=True, text=True).stderr
    dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', mp3], capture_output=True, text=True).stdout)
    sil = []; st = None
    for ln in out.splitlines():
        if 'silence_start' in ln: st = float(ln.split('silence_start:')[1])
        elif 'silence_end' in ln and st is not None: sil.append((max(0, st), float(ln.split('silence_end:')[1].split('|')[0]))); st = None
    if st is not None: sil.append((st, dur))
    segs, cur = [], 0.0
    for a, b in sil:
        if a - cur > 0.08: segs.append((cur, a))
        cur = b
    if dur - cur > 0.08: segs.append((cur, dur))
    return segs

def _weight(w):
    v = sum(ch in 'aeiouàèéìòù' for ch in w.lower()); return max(1, v) + 0.15 * len(w)

def words_from_script(mp3, text):
    """Tempi parola per parola SENZA servizi esterni: le pause dell'audio dividono le frasi, dentro ogni tratto
    le parole si distribuiscono in base alle sillabe. Errore tipico 0,1-0,2 s: va bene per sottotitoli e cambi scena.
    (Se la chiave ElevenLabs ha il permesso speech_to_text si può usare la trascrizione con i tempi esatti.)"""
    words = text.split(); segs = speech_segments(mp3)
    # gruppi di parole = frasi/pezzi chiusi da punteggiatura
    chunks, cur = [], []
    for w in words:
        cur.append(w)
        if w[-1] in '.,;:?!': chunks.append(cur); cur = []
    if cur: chunks.append(cur)
    cw = [sum(_weight(w) for w in c) for c in chunks]; total_w = sum(cw)
    sd = [b - a for a, b in segs]; total_s = sum(sd)
    # assegna i pezzi ai tratti di voce in ordine, in proporzione al peso (programmazione dinamica semplice)
    import itertools
    n, m = len(chunks), len(segs)
    INF = 1e9; best = [[INF] * (m + 1) for _ in range(n + 1)]; prev = [[None] * (m + 1) for _ in range(n + 1)]
    best[0][0] = 0
    for i in range(n + 1):
        for j in range(m + 1):
            if best[i][j] >= INF: continue
            for di in range(1, n - i + 1):                         # di pezzi -> dj tratti
                for dj in range(1, m - j + 1):
                    if di > 1 and dj > 1: break
                    wv = sum(cw[i:i + di]) / total_w; sv = sum(sd[j:j + dj]) / total_s
                    c = best[i][j] + (wv - sv) ** 2 * 100 + 0.02 * (di + dj - 2)
                    if c < best[i + di][j + dj]: best[i + di][j + dj] = c; prev[i + di][j + dj] = (i, j)
    path = []; i, j = n, m
    while (i, j) != (0, 0):
        pi, pj = prev[i][j]; path.append((pi, i, pj, j)); i, j = pi, pj
    out = []
    for ci0, ci1, sj0, sj1 in reversed(path):
        ws = [w for c in chunks[ci0:ci1] for w in c]; a, b = segs[sj0][0], segs[sj1 - 1][1]
        wt = [_weight(w) for w in ws]; tot = sum(wt); t = a
        for w, x in zip(ws, wt):
            d = (b - a) * x / tot; out.append([w, round(t, 3), round(t + d, 3)]); t += d
    return out

# =====================================================================
# MOVIMENTO: niente deve stare fermo
#   - ogni elemento entra con rimbalzo (sprite) e poi galleggia/oscilla (idle)
#   - la camera spinge sempre piano in avanti, deriva, e dà colpi di zoom/scossa sulle parole chiave (camera)
#   - flash bianchi sui momenti forti (flash), polvere che sale (dust), luce che attraversa (light_sweep)
#   - transizioni: circle_wipe, whip (strisciata), zoom_through (entra dentro la scena)
#   - sottotitoli che saltano parola per parola (captions_pop)
# =====================================================================
from PIL import ImageChops

def back(x, s=1.9):
    """easing con rimbalzo oltre il bersaglio (overshoot)"""
    x = max(0.0, min(1.0, x)) - 1; return 1 + x * x * ((s + 1) * x + s)

def elastic(x):
    x = max(0.0, min(1.0, x))
    if x in (0, 1): return x
    return 2 ** (-10 * x) * math.sin((x * 10 - 0.75) * (2 * math.pi) / 3) + 1

def sprite(img, fn, t, t0=0.0, enter='pop', idle='float', seed=0, dur=0.5, exit_t=None, anchor=None, amp=1.0):
    """Disegna con fn(copia) e anima il risultato come un oggetto unico.
    enter: 'pop' (cresce con rimbalzo), 'drop' (cade dall'alto e rimbalza), 'rise' (sale dal basso), 'left'/'right' (entra di lato),
           'spin' (ruota mentre cresce), 'stamp' (arriva grande e sbatte), 'none'
    idle:  'float' (su e giù + leggera rotazione), 'breathe' (pulsa), 'wobble' (tremolio), 'sway' (dondola), None
    exit_t: se dato, l'oggetto esce rimpicciolendo da quel tempo."""
    if t < t0: return img
    base = img.copy(); r = fn(base)
    if r is not None: base = r
    diff = ImageChops.difference(base, img).convert('L')
    mask = diff.point(lambda v: 0 if v < 3 else min(255, v * 5))
    bb = mask.getbbox()
    if not bb: return img
    pad = 30; bb = (max(0, bb[0] - pad), max(0, bb[1] - pad), min(W, bb[2] + pad), min(H, bb[3] + pad))
    crop = base.crop(bb).convert('RGBA'); m = mask.crop(bb)
    cx, cy = anchor or ((bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2)
    a = (t - t0) / dur; e = ease(a); bk = back(a)
    sc, dx, dy, rot, al = 1.0, 0.0, 0.0, 0.0, 1.0
    if enter == 'pop': sc = 0.2 + 0.8 * bk; al = min(1, a * 3)
    elif enter == 'drop': dy = -500 * (1 - bk); al = min(1, a * 4)
    elif enter == 'rise': dy = 160 * (1 - bk); al = min(1, a * 2.5)
    elif enter == 'left': dx = -W * (1 - bk)
    elif enter == 'right': dx = W * (1 - bk)
    elif enter == 'spin': sc = 0.2 + 0.8 * bk; rot = -90 * (1 - e); al = min(1, a * 3)
    elif enter == 'stamp': sc = 2.2 - 1.2 * min(1, back(a, 3.0)); al = min(1, a * 4)
    ph = seed * 1.7; tt = t - t0
    if idle == 'float': dy += 9 * amp * math.sin(tt * 2.2 + ph); rot += 1.3 * amp * math.sin(tt * 1.6 + ph)
    elif idle == 'breathe': sc *= 1 + 0.035 * amp * math.sin(tt * 3.2 + ph)
    elif idle == 'wobble': rot += 2.2 * amp * math.sin(tt * 9 + ph); dx += 3 * amp * math.sin(tt * 13 + ph)
    elif idle == 'sway': rot += 3.5 * amp * math.sin(tt * 1.8 + ph); dx += 14 * amp * math.sin(tt * 1.3 + ph)
    if exit_t is not None and t > exit_t:
        k = ease((t - exit_t) / 0.3); sc *= 1 - k; al *= 1 - k
    if sc <= 0.02 or al <= 0.01: return img
    w, h = crop.size; nw, nh = max(1, int(w * sc)), max(1, int(h * sc))
    crop = crop.resize((nw, nh), Image.BICUBIC); m = m.resize((nw, nh), Image.BICUBIC)
    if abs(rot) > 0.05:
        crop = crop.rotate(rot, expand=True, resample=Image.BICUBIC); m = m.rotate(rot, expand=True, resample=Image.BICUBIC)
    if al < 1: m = m.point(lambda v: int(v * al))
    ox = int(cx + dx - crop.width / 2 + ((bb[0] + bb[2]) / 2 - cx) * sc); oy = int(cy + dy - crop.height / 2 + ((bb[1] + bb[3]) / 2 - cy) * sc)
    out = img.copy(); out.paste(crop.convert('RGB'), (ox, oy), m); return out

def camera(img, t, t0, punches=(), shakes=(), push=0.06, drift=1.0):
    """camera viva: spinta lenta in avanti da t0, deriva e rotazione leggere, colpi di zoom (punches) e scosse (shakes) ai tempi dati"""
    s = 1.0 + push * ease((t - t0) / 5.0)
    for p in punches:
        k = t - p
        if 0 <= k < 0.4: s += 0.09 * math.sin(math.pi * min(1, k / 0.4)) * (1 - k / 0.4) ** 0.5
    dx = 14 * drift * math.sin(t * 0.7); dy = 10 * drift * math.cos(t * 0.55); rot = 0.5 * drift * math.sin(t * 0.45)
    for p in shakes:
        k = t - p
        if 0 <= k < 0.45:
            amp = 22 * (1 - k / 0.45); dx += amp * math.sin(k * 70); dy += amp * 0.8 * math.cos(k * 55); rot += 0.8 * (1 - k / 0.45) * math.sin(k * 60)
    a = math.radians(rot); ca, sa = math.cos(a) / s, math.sin(a) / s
    cx, cy = W / 2, H / 2
    # mappa inversa: punto di uscita -> punto della scena
    c = (ca, sa, cx - ca * (cx + dx) - sa * (cy + dy), -sa, ca, cy + sa * (cx + dx) - ca * (cy + dy))
    return img.transform((W, H), Image.AFFINE, c, Image.BICUBIC, fillcolor=img.getpixel((5, 5)))

def flash(img, t, times, dur=0.14, col=(255, 255, 255), strength=0.75):
    """lampo sui momenti forti"""
    for p in times:
        k = t - p
        if 0 <= k < dur: return Image.blend(img, Image.new('RGB', (W, H), col), strength * (1 - k / dur))
    return img

def dust(img, t, n=40, seed=9, col=GOLD, speed=60):
    """particelle che salgono lentamente (aria viva in ogni mondo)"""
    d = ImageDraw.Draw(img); r = random.Random(seed)
    for _ in range(n):
        x0, y0, sp, sz, ph = r.uniform(0, W), r.uniform(0, H), r.uniform(0.4, 1.4), r.uniform(1.5, 4), r.uniform(0, 6.28)
        y = (y0 - t * speed * sp) % H; x = x0 + 18 * math.sin(t * 0.8 + ph)
        a = 0.35 + 0.35 * math.sin(t * 2 + ph)
        d.ellipse((x - sz, y - sz, x + sz, y + sz), fill=tuple(int(c * a) for c in col))
    return img

def light_sweep(img, t, period=3.5, width=220, strength=55):
    """banda di luce diagonale che attraversa lo schermo ogni `period` secondi"""
    k = (t % period) / period; x = -600 + k * (W + 1200)
    m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).polygon([(x, 0), (x + width, 0), (x + width - 500, H), (x - 500, H)], fill=strength)
    return Image.composite(Image.new('RGB', (W, H), (255, 240, 200)), img, m.filter(ImageFilter.GaussianBlur(60)))

def whip(img_from, img_to, prog, direction=1):
    """strisciata veloce: la scena vecchia scappa di lato con scia, la nuova entra"""
    p = ease(prog); off = int(W * p) * direction
    out = Image.new('RGB', (W, H), DARK)
    out.paste(img_from, (-off, 0)); out.paste(img_to, (W * direction - off, 0))
    if 0.05 < prog < 0.95:
        trail = Image.new('RGB', (W, H)); acc = out
        for k in (12, 24, 36): acc = Image.blend(acc, ImageChops.offset(out, k * direction, 0), 0.35)
        out = acc
    return out

def zoom_through(img_from, img_to, prog):
    """entra dentro la scena: la vecchia ingrandisce e sparisce in un lampo, la nuova arriva da più grande"""
    if prog < 0.5:
        k = ease(prog * 2); s = 1 + 0.6 * k
        a = img_from.resize((int(W * s), int(H * s)), Image.BILINEAR).crop((int((W * s - W) / 2), int((H * s - H) / 2), int((W * s + W) / 2), int((H * s + H) / 2)))
        return Image.blend(a, Image.new('RGB', (W, H), (255, 255, 255)), k * 0.8)
    k = ease((prog - 0.5) * 2); s = 1.25 - 0.25 * k
    b = img_to.resize((int(W * s), int(H * s)), Image.BILINEAR).crop((int((W * s - W) / 2), int((H * s - H) / 2), int((W * s + W) / 2), int((H * s + H) / 2)))
    return Image.blend(Image.new('RGB', (W, H), (255, 255, 255)), b, 0.2 + 0.8 * k)

def captions_pop(img, t, words, groups, keys, dark, y=1585, end=None, size=78):
    """sottotitoli animati: ogni parola salta dentro con rimbalzo quando viene detta, la parola chiave arriva nel riquadro oro che si allarga"""
    gi = None
    for g in groups:
        if words[g[0]][1] - 0.05 <= t: gi = g
    if gi is None or t > (end if end is not None else words[-1][2] + 0.3): return img
    d = ImageDraw.Draw(img); f = F(COND, size); sp = 22
    txt = [words[i][0].upper().strip('.,:;') for i in gi]
    ws = [d.textlength(w, font=f) for w in txt]
    tot = sum(ws) + sp * (len(txt) - 1)
    if tot > W - 100:                                  # parole lunghe: rimpicciolisce il gruppo per stare nello schermo
        size = int(size * (W - 100) / tot); f = F(COND, size); ws = [d.textlength(w, font=f) for w in txt]
    x = W / 2 - (sum(ws) + sp * (len(txt) - 1)) / 2
    gstart = words[gi[0]][1]; lift = 30 * (1 - back((t - gstart + 0.05) / 0.25))
    for i, w, wd in zip(gi, txt, ws):
        k = (t - words[i][1]) / 0.22; said = k >= 0
        sc = 0.75 + 0.25 * back(k) if said else 0.75
        fs = F(COND, max(8, int(size * sc))); cx = x + wd / 2; yy = y + lift - (8 * math.sin(math.pi * min(1, max(0, k))) if said else 0)
        if said and i in keys:
            bw = (wd + 28) * back(k / 0.9); d.rounded_rectangle((cx - bw / 2, yy - 46 * sc, cx + bw / 2, yy + 44 * sc), radius=12, fill=GOLD); col = DARK
        else:
            col = (WHITE if dark else INK) if said else (MUTE if dark else (175, 168, 152))
        d.text((cx, yy), w, font=fs, fill=col, anchor='mm'); x += wd + sp
    return img

def typewriter_big(img, s, xy, size, col, t, t0, per=0.05, font=BIG):
    """titolo che entra lettera per lettera, ogni lettera cade con rimbalzo"""
    d = ImageDraw.Draw(img); f = F(font, size); tw = d.textlength(s, font=f); x = xy[0] - tw / 2
    for i, ch in enumerate(s):
        k = (t - t0 - i * per) / 0.3
        cw = d.textlength(ch, font=f)
        if k > 0:
            dy = -80 * (1 - back(k)); d.text((x, xy[1] + dy), ch, font=f, fill=fade(col, min(1, k * 3), img.getpixel((int(x), int(xy[1])))), anchor='ls')
        x += cw
    return img

# ---------------- movimenti presi dai video modello ----------------
def pulse_rings(img, cx, cy, t, col=GOLD, period=1.6, n=3, rmax=420, width=4):
    """cerchi che si allargano come onde dietro un oggetto (video 1 e 7)"""
    lay = Image.new('L', (W, H), 0); d = ImageDraw.Draw(lay)
    for k in range(n):
        p = ((t / period) + k / n) % 1.0; r = 40 + rmax * ease(p)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=int(200 * (1 - p)), width=width)
    return Image.composite(Image.new('RGB', (W, H), col), img, lay)

def blur_in(img, fn, t, t0, dur=0.45, idle='float', seed=0, amp=1.0):
    """oggetto che passa da sfocato e grande a nitido (video 7 e r601), poi resta vivo"""
    if t < t0: return img
    base = img.copy(); r = fn(base)
    if r is not None: base = r
    a = ease((t - t0) / dur)
    if a < 1:
        diff = ImageChops.difference(base, img).convert('L').point(lambda v: 0 if v < 3 else min(255, v * 5))
        bl = base.filter(ImageFilter.GaussianBlur(28 * (1 - a))); m = diff.filter(ImageFilter.GaussianBlur(28 * (1 - a))).point(lambda v: int(v * a))
        out = img.copy(); out.paste(bl, (0, 0), m); return out
    return sprite(img, fn, t, t0 - 10, enter='none', idle=idle, seed=seed, amp=amp)

def type_text(d, s, xy, size, col, t, t0, cps=18, font=MONO, cursor=True, anchor='lm'):
    """testo che si scrive con il cursore che lampeggia (video 2 e 4)"""
    k = int(max(0, (t - t0)) * cps); shown = s[:k]; f = F(font, size)
    d.text(xy, shown, font=f, fill=col, anchor=anchor)
    if cursor and t >= t0 and (k < len(s) or int(t * 2.5) % 2 == 0):
        x = xy[0] + d.textlength(shown, font=f) + 6
        d.rectangle((x, xy[1] - size * 0.45, x + size * 0.08, xy[1] + size * 0.45), fill=col)

def count_text(value_from, value_to, t, t0, dur=0.8, fmt='{:.1f}', dec=','):
    """numero che conta da un valore all'altro (video 5): ritorna la stringa da disegnare"""
    v = value_from + (value_to - value_from) * ease((t - t0) / dur)
    s = fmt.format(v)
    if dec == ',': s = s.replace(',', 'X').replace('.', ',').replace('X', '.')
    return s

def color_flash(img, t, times, col=GOLD, dur=0.18, strength=0.35):
    """lampo colorato su tutto lo schermo sulla parola chiave (video 2)"""
    return flash(img, t, times, dur, col, strength)

def whip_v(img_from, img_to, prog, direction=1):
    """strisciata verticale con scia sfocata (video 4)"""
    p = ease(prog); off = int(H * p) * direction
    out = Image.new('RGB', (W, H), DARK); out.paste(img_from, (0, -off)); out.paste(img_to, (0, H * direction - off))
    if 0.05 < prog < 0.95:
        acc = out
        for k in (20, 40, 60, 80): acc = Image.blend(acc, ImageChops.offset(out, 0, k * direction), 0.3)
        out = acc
    return out

def blur_cross(img_from, img_to, prog):
    """dissolvenza attraverso la sfocatura (video 7)"""
    if prog < 0.5:
        k = prog * 2; return img_from.filter(ImageFilter.GaussianBlur(30 * k))
    k = (prog - 0.5) * 2; return Image.blend(img_from.filter(ImageFilter.GaussianBlur(30)), img_to.filter(ImageFilter.GaussianBlur(30 * (1 - k))), min(1, k * 1.5))

def light_beams(img, t, col=(120, 160, 255), n=3, strength=22):
    """fasci di luce verticali che scorrono (video 1)"""
    m = Image.new('L', (W, H), 0); d = ImageDraw.Draw(m)
    for k in range(n):
        x = (W * 1.4) * (((t * 0.25) + k / n) % 1.0) - W * 0.2; w = 40 + 30 * k
        d.rectangle((x - w / 2, 0, x + w / 2, H), fill=strength)
    return Image.composite(Image.new('RGB', (W, H), col), img, m.filter(ImageFilter.GaussianBlur(30)))

def clock_hands(img, cx, cy, r, t, col=GOLD, speed=1.0):
    """orologio luminoso con lancette che girano sempre (video 1)"""
    img = glow_icon(img, 'orologio', cx, cy, r * 2.1, 1, col, 7)
    m = Image.new('L', (W, H), 0); d = ImageDraw.Draw(m)
    for L, sp, w in [(r * 0.55, 0.6, 9), (r * 0.8, 4.0, 6)]:
        a = t * sp * speed * 2 * math.pi - math.pi / 2; d.line([(cx, cy), (cx + L * math.cos(a), cy + L * math.sin(a))], fill=255, width=w)
    img = Image.composite(Image.new('RGB', (W, H), tuple(int(v * .5) for v in col)), img, m.filter(ImageFilter.GaussianBlur(10)))
    return Image.composite(Image.new('RGB', (W, H), col), img, m)

def card_flip_quad(quad, t, t0, dur=0.7):
    """quadrilatero che entra ruotando in 3D (video 4): da inclinato e lontano alla posizione, poi oscilla"""
    a = back((t - t0) / dur, 1.4); cx = sum(p[0] for p in quad) / 4; cy = sum(p[1] for p in quad) / 4
    sc = 0.4 + 0.6 * a; tilt = (1 - a) * 0.6
    out = []
    for i, (x, y) in enumerate(quad):
        dx, dy = (x - cx) * sc, (y - cy) * sc
        side = -1 if i in (0, 3) else 1
        dy *= 1 + side * tilt * 0.5
        out.append((cx + dx + 12 * math.sin(t * 1.3 + i), cy + dy + 9 * math.cos(t * 1.1 + i * 2) + 300 * (1 - a)))
    return out

# ---------------- CALL TO ACTION con i 4 paletti ----------------
def _cta_icon(d, kind, cx, cy, s, col):
    w = max(4, int(s * 0.07))
    if kind == 'segui':
        d.ellipse((cx - s * 0.32, cy - s * 0.48, cx + s * 0.08, cy - s * 0.08), outline=col, width=w)
        d.arc((cx - s * 0.5, cy - s * 0.02, cx + s * 0.26, cy + s * 0.7), 180, 360, fill=col, width=w)
        d.line([(cx + s * 0.32, cy - s * 0.2), (cx + s * 0.32, cy + s * 0.12)], fill=col, width=w); d.line([(cx + s * 0.16, cy - s * 0.04), (cx + s * 0.48, cy - s * 0.04)], fill=col, width=w)
    elif kind == 'cuore':
        pts = [(cx + s * 0.5 * 16 * math.sin(a) ** 3 / 16, cy - s * 0.5 * (13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a)) / 16) for a in [i * 2 * math.pi / 60 for i in range(61)]]
        d.polygon(pts, fill=col)
    elif kind == 'commenta':
        d.rounded_rectangle((cx - s * 0.45, cy - s * 0.38, cx + s * 0.45, cy + s * 0.22), radius=int(s * 0.18), outline=col, width=w)
        d.polygon([(cx - s * 0.2, cy + s * 0.2), (cx - s * 0.3, cy + s * 0.45), (cx, cy + s * 0.2)], fill=col)
        for k in (-1, 0, 1): d.ellipse((cx + k * s * 0.2 - s * 0.05, cy - s * 0.13, cx + k * s * 0.2 + s * 0.05, cy - s * 0.03), fill=col)
    elif kind == 'condividi':
        d.polygon([(cx + s * 0.45, cy - s * 0.1), (cx + s * 0.05, cy - s * 0.45), (cx + s * 0.05, cy - s * 0.25), (cx - s * 0.45, cy - s * 0.15), (cx - s * 0.35, cy + s * 0.4),
                   (cx - s * 0.1, cy + s * 0.05), (cx + s * 0.05, cy + s * 0.05), (cx + s * 0.05, cy + s * 0.25)], fill=col)

CTA_STEPS = [('segui', 'SEGUI', GOLD), ('cuore', 'MI PIACE', RED), ('commenta', 'COMMENTA', WHITE), ('condividi', 'CONDIVIDI', GREEN)]
def cta_four(img, t, times, comment_word=None, y0=640, dark=True):
    """i 4 paletti della chiusura (segui, mi piace, commenta, condividi): times = 4 tempi (parole della voce) in cui ognuno salta dentro.
    Effetti sonori consigliati: pop, pop_hi, bubble, swoosh_up ai 4 tempi + coin sull'ultimo."""
    for k, ((kind, lab, col), t0) in enumerate(zip(CTA_STEPS, times)):
        if t < t0: continue
        y = y0 + k * 210
        def draw(b, kind=kind, lab=lab, col=col, y=y):
            d = ImageDraw.Draw(b); cc = col if not (kind == 'commenta' and not dark) else INK
            d.rounded_rectangle((150, y - 85, W - 150, y + 85), radius=42, fill=CARD if dark else WHITE, outline=col if col != WHITE else GOLD, width=4)
            _cta_icon(d, kind, 260, y, 120, cc)
            fs = 74 if not (kind == 'commenta' and comment_word) else 60
            d.text((350, y), lab, font=F(BIG, fs), fill=WHITE if dark else INK, anchor='lm')
            if kind == 'commenta' and comment_word:
                tw = d.textlength(lab, font=F(BIG, fs)); kw = d.textlength(comment_word, font=F(BIG, 50))
                key_box(d, comment_word, (350 + tw + 34 + kw / 2, y), 50, 1)
        img = sprite(img, draw, t, t0, enter='left' if k % 2 == 0 else 'right', idle='float', seed=40 + k, amp=0.6)
        if kind == 'cuore' and t - t0 < 0.6:   # cuoricini che volano
            d = ImageDraw.Draw(img); r = random.Random(k)
            for j in range(6):
                p = (t - t0) / 0.6; hx = 260 + r.uniform(-60, 60) + 40 * math.sin(p * 6 + j); hy = y - 120 * p * r.uniform(1, 2.2)
                _cta_icon(d, 'cuore', hx, hy, 40 * (1 - p), RED)
    return img

# ---------------- LOGO e TELEGRAM (chiusura) ----------------
_LOGO = {}
def logo_reveal(img, t, t0, cx, cy, size=380):
    """logo YardFX (sfondo già trasparente, logo_yardfx.png): entra ruotando con rimbalzo, alone oro, riflesso di luce che lo attraversa, poi galleggia"""
    if t < t0: return img
    if size not in _LOGO:
        lo = Image.open(os.path.join(D, 'logo_yardfx.png')).convert('RGBA'); _LOGO[size] = lo.resize((size, int(size * lo.height / lo.width)), Image.LANCZOS)
    lo = _LOGO[size].copy(); s = t - t0; a = back(s / 0.6)
    k = (s - 0.7) / 0.6                                   # riflesso
    if 0 < k < 1:
        sh = Image.new('L', lo.size, 0); x = -lo.width * 0.5 + k * lo.width * 2
        ImageDraw.Draw(sh).polygon([(x, 0), (x + 70, 0), (x - 130, lo.height), (x - 200, lo.height)], fill=170)
        sh = ImageChops.multiply(sh.filter(ImageFilter.GaussianBlur(14)), lo.getchannel('A'))
        lo = Image.composite(Image.new('RGBA', lo.size, (255, 245, 210, 255)), lo, sh)
    sc = max(0.05, 0.3 + 0.7 * a) * (1 + 0.025 * math.sin(s * 2.4)); rot = -200 * (1 - ease(s / 0.6)) + 1.5 * math.sin(s * 1.7)
    lo = lo.resize((max(1, int(lo.width * sc)), max(1, int(lo.height * sc))), Image.BICUBIC).rotate(rot, expand=True, resample=Image.BICUBIC)
    if s < 0.25: lo.putalpha(lo.getchannel('A').point(lambda v: int(v * s / 0.25)))
    glow = Image.new('L', (W, H), 0); r = size * 0.55 * sc
    ImageDraw.Draw(glow).ellipse((cx - r, cy - r, cx + r, cy + r), fill=int(110 * min(1, s / 0.4)))
    img = Image.composite(Image.new('RGB', (W, H), (120, 90, 25)), img, glow.filter(ImageFilter.GaussianBlur(70)))
    y = cy + 6 * math.sin(s * 2.0)
    img.paste(lo.convert('RGB'), (int(cx - lo.width / 2), int(y - lo.height / 2)), lo); return img

def telegram_icon(d, cx, cy, r, col_bg=(42, 171, 238), col=(255, 255, 255)):
    """icona aereo di carta (Telegram) disegnata"""
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col_bg)
    d.polygon([(cx - r * 0.55, cy - r * 0.02), (cx + r * 0.5, cy - r * 0.45), (cx + r * 0.3, cy + r * 0.5), (cx + r * 0.02, cy + r * 0.22)], fill=col)
    d.polygon([(cx + r * 0.02, cy + r * 0.22), (cx - r * 0.12, cy + r * 0.45), (cx - r * 0.1, cy + r * 0.12)], fill=(200, 225, 245))
    d.line([(cx - r * 0.1, cy + r * 0.12), (cx + r * 0.42, cy - r * 0.32)], fill=(170, 210, 240), width=max(2, int(r * 0.06)))

def telegram_cta(img, t, t0, y=1300, handle='@yard_fx', line='CERCAMI SU TELEGRAM'):
    """l'aereo di carta vola dentro con la scia, poi la scritta e il nome che sbatte come un timbro"""
    if t < t0: return img
    s = t - t0; a = back(s / 0.55); d = ImageDraw.Draw(img)
    tx = 230 if line else W / 2 - 190                      # senza scritta (TikTok): icona e nome sulla stessa riga, centrati
    ix = -150 + (tx + 150) * a; iy = y + 40 * (1 - ease(s / 0.55)) - 60 * math.sin(math.pi * min(1, s / 0.55)) + 5 * math.sin(s * 3)
    for k in range(1, 6):                                       # scia
        if s < 0.7: d.ellipse((ix - 40 * k - 8, iy - 8 + 6 * k, ix - 40 * k + 8, iy + 8 + 6 * k), fill=(42, 171, 238))
    telegram_icon(d, ix, iy, 70)
    if line: img = sprite(img, lambda b: ImageDraw.Draw(b).text((330, y), line, font=F(BIG, 64), fill=WHITE, anchor='lm'), t, t0 + 0.25, enter='left', idle='float', seed=61, amp=0.5)
    def pill(b):
        dd = ImageDraw.Draw(b); f = F(COND, 74); tw = dd.textlength(handle, font=f)
        cx, cy = (W / 2, y + 145) if line else (W / 2 + 70, y)
        dd.rounded_rectangle((cx - tw / 2 - 40, cy - 55, cx + tw / 2 + 40, cy + 55), radius=55, fill=(42, 171, 238)); dd.text((cx, cy), handle, font=f, fill=WHITE, anchor='mm')
    return sprite(img, pill, t, t0 + 0.55, enter='stamp', idle='breathe', seed=62, dur=0.3, amp=0.6)

# ---------------- tempi ESATTI delle parole sull'MP3 di Salvatore (allineamento audio-audio) ----------------
def words_aligned(mp3, text, workdir=None):
    """1) genera con ElevenLabs un audio di RIFERIMENTO dello stesso testo con i tempi esatti di ogni parola (voce gratuita,
          serve SOLO per il calcolo, non va mai nel video);
       2) allinea il riferimento alla voce di Salvatore con DTW sulle caratteristiche del suono (MFCC, librosa);
       3) trasferisce i tempi delle parole sulla sua registrazione. Precisione tipica: 0,05 s. Richiede `pip install librosa`."""
    import numpy as np, librosa
    workdir = workdir or os.path.dirname(os.path.abspath(mp3))
    ref = os.path.join(workdir, '_riferimento_allineamento.mp3')
    rw = tts_elevenlabs(text, ref)
    sr = 16000; hop = 160
    y1, _ = librosa.load(ref, sr=sr); y2, _ = librosa.load(mp3, sr=sr)
    def feat(y):
        m = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20, hop_length=hop, n_fft=512)
        m = (m - m.mean(axis=1, keepdims=True)) / (m.std(axis=1, keepdims=True) + 1e-6)
        e = librosa.feature.rms(y=y, hop_length=hop, frame_length=512)
        return np.vstack([m, 3 * (e - e.mean()) / (e.std() + 1e-6)])
    f1, f2 = feat(y1), feat(y2)
    _, wp = librosa.sequence.dtw(X=f1, Y=f2, metric='cosine', step_sizes_sigma=np.array([[1, 1], [0, 1], [1, 0]]), weights_mul=np.array([1, 1.3, 1.3]))
    wp = wp[::-1]; m1 = wp[:, 0] * hop / sr; m2 = wp[:, 1] * hop / sr
    def mp(tref):
        i = np.searchsorted(m1, tref); i = min(max(i, 0), len(m2) - 1); return float(m2[i])
    out = [[w, round(mp(a), 3), round(mp(b), 3)] for w, a, b in rw]
    for i in range(1, len(out)):                      # tempi sempre crescenti
        out[i][1] = max(out[i][1], out[i - 1][1] + 0.02); out[i][2] = max(out[i][2], out[i][1] + 0.05)
    return out

def words_aligned_offline(mp3, text, workdir=None, voice='it', speed=165):
    """Come words_aligned ma SENZA ElevenLabs (per quando i crediti sono finiti): il riferimento è generato in locale
    con espeak-ng (apt-get install espeak-ng), parola per parola, quindi i confini delle parole sono esatti;
    poi DTW sulle MFCC verso la voce di Salvatore. Precisione un po' inferiore a words_aligned."""
    import numpy as np, librosa, tempfile
    workdir = workdir or os.path.dirname(os.path.abspath(mp3)); sr = 16000; hop = 160
    words = text.split(); pieces = []; ref = []; t = 0.0
    tmp = os.path.join(workdir, '_espeak.wav')
    paras = [len(p.split()) for p in text.strip().split('\n\n')]; ends = set(np.cumsum(paras) - 1)
    for i, w in enumerate(words):
        clean = w.strip('.,:;?!«»"')
        subprocess.run(['espeak-ng', '-v', voice, '-s', str(speed), '-w', tmp, clean], check=True, capture_output=True)
        y, _ = librosa.load(tmp, sr=sr); y, _ = librosa.effects.trim(y, top_db=35)
        ref.append([w, t, t + len(y) / sr]); pieces.append(y); t += len(y) / sr
        gap = 0.6 if i in ends else (0.3 if w[-1] in '.,:;?!' else 0.04)
        pieces.append(np.zeros(int(sr * gap))); t += gap
    y1 = np.concatenate(pieces); y2, _ = librosa.load(mp3, sr=sr)
    def feat(y):
        m = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20, hop_length=hop, n_fft=512)
        m = (m - m.mean(axis=1, keepdims=True)) / (m.std(axis=1, keepdims=True) + 1e-6)
        e = librosa.feature.rms(y=y, hop_length=hop, frame_length=512)
        return np.vstack([m, 4 * (e - e.mean()) / (e.std() + 1e-6)])
    _, wp = librosa.sequence.dtw(X=feat(y1), Y=feat(y2), metric='cosine', step_sizes_sigma=np.array([[1, 1], [0, 1], [1, 0]]), weights_mul=np.array([1, 1.3, 1.3]))
    wp = wp[::-1]; m1 = wp[:, 0] * hop / sr; m2 = wp[:, 1] * hop / sr
    mp = lambda tr: float(m2[min(max(np.searchsorted(m1, tr), 0), len(m2) - 1)])
    out = [[w, round(mp(a), 3), round(mp(b), 3)] for w, a, b in ref]
    for i in range(1, len(out)):
        out[i][1] = max(out[i][1], out[i - 1][1] + 0.02); out[i][2] = max(out[i][2], out[i][1] + 0.05)
    return out
