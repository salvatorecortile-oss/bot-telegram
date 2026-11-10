"""Musica di fondo ed effetti sonori YardFX, generati da zero (nessun copyright).
uso:  import suoni as S
      S.music('base.wav', durata, bpm=96, mood='tensione'|'positivo'|'calmo')
      eventi = [(1.2,'pop'), (3.0,'whoosh'), (4.1,'ding'), ...]
      S.mix('finale.m4a', durata, voce='voce.mp3', musica='base.wav', eventi=eventi)
Effetti: pop, pop_hi, whoosh, swoosh_up, ding, trin, coin, stamp, boom, click, tick, riser, glitch, swipe, bubble, alert
"""
import numpy as np, subprocess, wave, math, random
SR = 44100

def _t(d): return np.arange(int(SR * d)) / SR
def _env(n, a=0.005, r=0.2):
    t = np.arange(n) / SR; e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / max(r, 1e-4)); return e
def _noise(d, seed=0): return np.random.default_rng(seed).uniform(-1, 1, int(SR * d))
def _lp(x, k):  # passa-basso semplice (media mobile esponenziale)
    y = np.empty_like(x); acc = 0.0
    for i, v in enumerate(x): acc += k * (v - acc); y[i] = acc
    return y
def _hp(x, k): return x - _lp(x, k)

def pop(pitch=1.0):
    t = _t(0.12); f = 900 * pitch * np.exp(-t * 30) + 250 * pitch
    return 0.8 * np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(len(t), 0.002, 0.03)
def pop_hi(): return pop(1.6)
def bubble():
    t = _t(0.15); f = 300 + 1400 * (t / 0.15) ** 0.6
    return 0.6 * np.sin(2 * np.pi * np.cumsum(f) / SR) * _env(len(t), 0.003, 0.05)
def click():
    n = _noise(0.02, 3) * _env(int(SR * 0.02), 0.0005, 0.004); return 0.7 * _hp(n, 0.3)
def tick(): return 0.5 * np.sin(2 * np.pi * 2400 * _t(0.03)) * _env(int(SR * 0.03), 0.0005, 0.008)
def ding(freq=1318.5):
    t = _t(1.2); x = sum(a * np.sin(2 * np.pi * freq * m * t) for a, m in [(1, 1), (0.5, 2.76), (0.25, 5.4), (0.15, 8.9)])
    return 0.35 * x * _env(len(t), 0.002, 0.35)
def trin():
    a = ding(1760); b = ding(2349); out = np.zeros(len(a) + int(SR * 0.09)); out[:len(a)] += a; out[int(SR * 0.09):] += b * 0.9; return out * 0.8
def coin():
    a = ding(1975) * 0.7; b = ding(2637) * 0.7; out = np.zeros(len(a) + int(SR * 0.06)); out[:len(a)] += a; out[int(SR * 0.06):] += b; return out
def whoosh(d=0.45, up=True):
    n = _noise(d, 5); t = _t(d); k = 0.02 + 0.25 * (t / d if up else 1 - t / d)
    y = np.empty_like(n); acc = 0.0
    for i, v in enumerate(n): acc += k[i] * (v - acc); y[i] = acc
    env = np.sin(np.pi * t / d) ** 2; return 1.6 * y * env
def swoosh_up(): return whoosh(0.35, True)
def swipe(): return whoosh(0.25, False)
def stamp():
    t = _t(0.35); body = np.sin(2 * np.pi * (70 + 60 * np.exp(-t * 25)) * t) * _env(len(t), 0.001, 0.12)
    sn = _lp(_noise(0.35, 7), 0.25) * _env(len(t), 0.001, 0.04)
    return 0.9 * body + 0.6 * sn
def boom():
    t = _t(1.0); return 0.95 * np.sin(2 * np.pi * (45 + 80 * np.exp(-t * 18)) * t) * _env(len(t), 0.002, 0.35)
def riser(d=1.0):
    t = _t(d); f = 200 + 1600 * (t / d) ** 2; tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.25
    return (tone + 0.4 * _hp(_noise(d, 11), 0.2) * (t / d)) * (t / d) ** 1.5
def glitch():
    r = np.random.default_rng(13); out = []
    for _ in range(6):
        seg = r.uniform(-1, 1, int(SR * 0.018)) * r.uniform(0.3, 0.8)
        if r.random() < 0.5: seg = np.sign(np.sin(2 * np.pi * r.uniform(200, 900) * _t(0.018))) * 0.4
        out.append(seg)
    return np.concatenate(out)
def alert():
    t = _t(0.5); x = np.sin(2 * np.pi * 880 * t) * (t < 0.12) + np.sin(2 * np.pi * 1175 * t) * ((t > 0.15) & (t < 0.3))
    return 0.35 * x * _env(len(t), 0.002, 0.4)

SFX = {'pop': pop, 'pop_hi': pop_hi, 'bubble': bubble, 'click': click, 'tick': tick, 'ding': ding, 'trin': trin, 'coin': coin,
       'whoosh': whoosh, 'swoosh_up': swoosh_up, 'swipe': swipe, 'stamp': stamp, 'boom': boom, 'riser': riser, 'glitch': glitch, 'alert': alert}

# ---------------- musica ----------------
def _kick():
    t = _t(0.4); return np.sin(2 * np.pi * (50 + 110 * np.exp(-t * 30)) * t) * _env(len(t), 0.001, 0.15)
def _snare():
    t = _t(0.25); return 0.5 * _hp(_noise(0.25, 21), 0.35) * _env(len(t), 0.001, 0.07) + 0.3 * np.sin(2 * np.pi * 190 * t) * _env(len(t), 0.001, 0.05)
def _hat(o=False):
    d = 0.12 if o else 0.04; return 0.25 * _hp(_noise(d, 31), 0.6) * _env(int(SR * d), 0.0005, d / 3)
def _note(freq, d, kind='pad'):
    t = _t(d)
    if kind == 'pad':
        x = sum(np.sin(2 * np.pi * freq * m * t + m) / m for m in (1, 2, 3)) * 0.3
        return x * np.minimum(1, t / 0.4) * np.minimum(1, (d - t) / 0.4)
    if kind == 'bass': return 0.7 * np.tanh(2 * np.sin(2 * np.pi * freq * t)) * _env(len(t), 0.005, d * 0.6)
    if kind == 'pluck': return 0.3 * (np.sin(2 * np.pi * freq * t) + 0.4 * np.sin(4 * np.pi * freq * t)) * _env(len(t), 0.002, 0.18)
def _hz(semi): return 440 * 2 ** (semi / 12)

MOODS = {   # accordi in semitoni rispetto a La 440 (A)
    'tensione': [[-12, -9, -5], [-16, -12, -9], [-19, -15, -12], [-14, -10, -7]],   # Am F D(m) G
    'positivo': [[-9, -5, -2], [-14, -10, -7], [-12, -9, -5], [-16, -12, -9]],
    'calmo':    [[-12, -9, -5], [-17, -14, -10], [-16, -12, -9], [-14, -10, -7]],
}
def music(out, dur, bpm=96, mood='tensione', seed=1):
    """base trap/lo-fi: cassa, rullante, charleston, basso, accordi e arpeggio. Volume pensato per stare sotto la voce."""
    beat = 60 / bpm; n = int(SR * (dur + 1)); mix = np.zeros(n); r = random.Random(seed)
    def add(sig, at, g=1.0):
        i = int(at * SR); j = min(n, i + len(sig))
        if i < n: mix[i:j] += g * sig[:j - i]
    chords = MOODS[mood]; bar = 4 * beat; nb = int(dur / bar) + 2
    for b in range(nb):
        t0 = b * bar; ch = chords[b % len(chords)]
        for s in ch: add(_note(_hz(s + 12), bar, 'pad'), t0, 0.22)
        add(_note(_hz(ch[0] - 12), beat * 1.5, 'bass'), t0, 0.5); add(_note(_hz(ch[0] - 12), beat, 'bass'), t0 + beat * 2.5, 0.45)
        for k in range(8):
            add(_note(_hz(ch[k % 3] + 24), beat / 2, 'pluck'), t0 + k * beat / 2, 0.12)
        intro = b == 0
        for k in range(4):
            if not intro or k >= 2: add(_kick(), t0 + k * beat, 0.8 if k in (0, 2) else 0.0)
            if k in (1, 3) and not intro: add(_snare(), t0 + k * beat, 0.55)
        if not intro: add(_kick(), t0 + 3.5 * beat, 0.5)
        for k in range(16 if not intro else 0):
            add(_hat(k % 8 == 6), t0 + k * beat / 4, 0.5 if k % 2 == 0 else 0.3)
    mix = mix[:int(SR * dur)]
    fade = int(SR * 1.5); mix[-fade:] *= np.linspace(1, 0, fade)
    _write(out, mix / (np.max(np.abs(mix)) + 1e-9) * 0.8)
    return out

def _write(path, x):
    x = np.clip(x, -1, 1); d = (x * 32767).astype(np.int16)
    with wave.open(path, 'wb') as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(d.tobytes())

def sfx_track(out, dur, events, gain=0.8):
    """traccia degli effetti: events = [(tempo, 'nome'[, volume])]"""
    n = int(SR * dur); mix = np.zeros(n)
    for ev in events:
        at, name = ev[0], ev[1]; g = ev[2] if len(ev) > 2 else 1.0
        s = SFX[name](); i = int(max(0, at) * SR); j = min(n, i + len(s))
        if i < n: mix[i:j] += g * s[:j - i]
    _write(out, mix * gain / max(1.0, np.max(np.abs(mix))))
    return out

def mix(out, dur, voce=None, musica=None, eventi=(), music_db=-17, sfx_db=-7, duck=True):
    """mixa voce + musica (abbassata sotto la voce con sidechain) + effetti. Uscita AAC normalizzata -14 LUFS."""
    sfx = out + '.sfx.wav'; sfx_track(sfx, dur, eventi)
    ins = []; fc = []
    if voce: ins += ['-i', voce]
    if musica: ins += ['-i', musica]
    ins += ['-i', sfx]
    k = 0; labels = []
    if voce: fc.append(f'[{k}:a]aresample=44100,apad=whole_dur={dur},asplit=2[v][vs]'); k += 1
    if musica:
        fc.append(f'[{k}:a]aresample=44100,volume={music_db}dB,apad=whole_dur={dur}[m0]')
        if voce and duck: fc.append('[m0][vs]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=350[m]')
        else: fc.append('[m0]anull[m]')
        k += 1
    fc.append(f'[{k}:a]volume={sfx_db}dB[s]')
    ins_l = ('[v]' if voce else '') + ('[m]' if musica else '') + '[s]'; nin = (1 if voce else 0) + (1 if musica else 0) + 1
    fc.append(f'{ins_l}amix=inputs={nin}:normalize=0,loudnorm=I=-14:TP=-1.5,atrim=0:{dur}[out]')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', *ins, '-filter_complex', ';'.join(fc), '-map', '[out]', '-c:a', 'aac', '-b:a', '192k', out], check=True)
    return out
