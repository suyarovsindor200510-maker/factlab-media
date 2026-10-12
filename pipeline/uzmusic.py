#!/usr/bin/env python3
"""Uzbek-style background music generator (doira + dutar + rubob/tanbur + nay + modern sub bass).
Original synthesis, no samples, no licences. Different every seed; energy follows the video's scenes.

usage: uzmusic.py timeline.json out.wav [seed] [style]
style: "bazm" (lively, 108 bpm), "lapar" (playful, 100), "dramatic" (slow 84, tense), "modern" (oriental trap 96)
"""
import sys, json, numpy as np, soundfile as sf
from scipy.signal import butter, lfilter, fftconvolve

SR = 44100


def bp(x, lo, hi, o=2): b, a = butter(o, [lo / (SR / 2), hi / (SR / 2)], 'band'); return lfilter(b, a, x)
def lp(x, f, o=2): b, a = butter(o, f / (SR / 2)); return lfilter(b, a, x)
def hp(x, f, o=2): b, a = butter(o, f / (SR / 2), 'high'); return lfilter(b, a, x)
n2f = lambda m: 440.0 * 2 ** ((m - 69) / 12)


class Mix:
    def __init__(s, T):
        s.N = int(T * SR); s.L = np.zeros(s.N); s.R = np.zeros(s.N)
    def add(s, x, t, g=1.0, pan=0.0):
        i = int(t * SR)
        if i >= s.N or i + len(x) <= 0: return
        if i < 0: x = x[-i:]; i = 0
        n = min(len(x), s.N - i)
        s.L[i:i + n] += x[:n] * g * min(1, 1 - pan); s.R[i:i + n] += x[:n] * g * min(1, 1 + pan)


# ---------------- instruments
def ks_pluck(f, d, bright=0.6, damp=0.996, rng=None):
    """Plucked string by additive synthesis (exact pitch): harmonics with frequency-dependent decay + pick noise."""
    rng = rng or np.random.default_rng(0)
    n = int(d * SR); t = np.arange(n) / SR; s = np.zeros(n)
    base_decay = (1 - damp) * 900 + 1.2
    for h in range(1, 16):
        fh = f * h * (1 + 0.00004 * h * h)          # slight string inharmonicity
        if fh > 16000: break
        a = (1 / h) * (bright ** (0.35 * (h - 1))) * (1 if h % 2 else 0.8)
        s += a * np.sin(2 * np.pi * fh * t + rng.uniform(0, 6.28)) * np.exp(-t * base_decay * (1 + 0.35 * h))
    m = int(0.006 * SR); s[:m] += hp(rng.standard_normal(m), 2000) * np.linspace(1, 0, m) * 0.25 * bright
    return s * np.minimum(1, t / 0.0015)


def dutar(f, d, rng):
    # two strings in fourth/fifth, nasal body resonance
    s = ks_pluck(f, d, 0.55, 0.9965, rng) + 0.5 * ks_pluck(f * 2, d, 0.4, 0.995, rng)
    s = s + 0.6 * bp(s, 700, 1600)  # nasal formant
    return s * 0.5


def rubob(f, d, rng):
    s = ks_pluck(f, d, 0.85, 0.9975, rng) + 0.35 * ks_pluck(f * 1.003, d, 0.85, 0.9975, rng)  # double course
    return (s + 0.4 * bp(s, 1800, 3800)) * 0.45


def nay(freqs, durs, rng):
    """breathy flute phrase with vibrato and slides; freqs/durs lists."""
    total = sum(durs); n = int(total * SR); f = np.zeros(n); t0 = 0
    for fr, d in zip(freqs, durs):
        i0, i1 = int(t0 * SR), int((t0 + d) * SR); f[i0:i1] = fr; t0 += d
    # portamento
    k = int(0.04 * SR); f = np.convolve(f, np.ones(k) / k, 'same'); f[f < 20] = freqs[-1]
    t = np.arange(n) / SR; vib = 1 + 0.008 * np.sin(2 * np.pi * 5.2 * t) * np.minimum(1, t / 0.4)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    tone = np.sin(ph) + 0.25 * np.sin(2 * ph) + 0.08 * np.sin(3 * ph)
    breath = bp(rng.standard_normal(n), 1200, 6000) * 0.12
    env = np.minimum(1, t / 0.08) * np.minimum(1, (total - t) / 0.15)
    return lp(tone + breath, 4500) * env * 0.35


def gijjak(freqs, durs, rng):
    """bowed spike-fiddle lead: band-limited saw, vibrato, bow noise, slides"""
    total = sum(durs); n = int(total * SR); f = np.zeros(n); t0 = 0
    for fr, d in zip(freqs, durs):
        i0, i1 = int(t0 * SR), int((t0 + d) * SR); f[i0:i1] = fr; t0 += d
    k = int(0.05 * SR); f = np.convolve(np.pad(f, (k, k), 'edge'), np.ones(k) / k, 'same')[k:-k]
    t = np.arange(n) / SR; vib = 1 + 0.010 * np.sin(2 * np.pi * 5.6 * t) * np.minimum(1, t / 0.3)
    ph = 2 * np.pi * np.cumsum(f * vib) / SR
    saw = sum(((-1) ** (h + 1)) * np.sin(h * ph) / h for h in range(1, 9))
    bow = bp(rng.standard_normal(n), 2000, 7000) * 0.05
    s = bp(saw, 300, 4200) + 0.5 * bp(saw, 900, 1600) + bow
    env = np.minimum(1, t / 0.12) * np.minimum(1, (total - t) / 0.25)
    return s * env * 0.25


def pad(freqs, d):
    n = int(d * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for f in freqs:
        for det in (-0.004, 0.004):
            s += np.sin(2 * np.pi * f * (1 + det) * t) + 0.3 * np.sin(4 * np.pi * f * (1 + det) * t)
    return lp(s, 1800) * np.minimum(1, t / 0.6) * np.minimum(1, (d - t) / 0.6) * 0.06


def doira_bum(rng):
    n = int(0.45 * SR); t = np.arange(n) / SR
    f = 75 + 60 * np.exp(-t * 30)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9)
    skin = lp(rng.standard_normal(n), 900) * np.exp(-t * 40) * 0.4
    return (body + skin) * 0.9


def doira_tak(rng):
    n = int(0.25 * SR); t = np.arange(n) / SR
    slap = bp(rng.standard_normal(n), 1800, 6000) * np.exp(-t * 55)
    ring = np.sin(2 * np.pi * 620 * t) * np.exp(-t * 30) * 0.4
    return (slap + ring) * 0.55


def zil(rng, d=0.22):
    """doira jingles (metal rings) — inharmonic shimmer."""
    n = int(d * SR); t = np.arange(n) / SR; s = np.zeros(n)
    for _ in range(9):
        f = rng.uniform(4500, 11000); s += np.sin(2 * np.pi * f * t + rng.uniform(0, 6)) * np.exp(-t * rng.uniform(18, 35))
    s += hp(rng.standard_normal(n), 6000) * np.exp(-t * 25) * 1.5
    return s * 0.035


def kick808(f0, d=0.7):
    n = int(d * SR); t = np.arange(n) / SR
    f = f0 + 90 * np.exp(-t * 35)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 3.2)
    return np.tanh(1.8 * s) * 0.8


def sub(f, d):
    n = int(d * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) + 0.15 * np.sin(4 * np.pi * f * t)
    return np.tanh(1.4 * s) * np.minimum(1, t / 0.01) * np.minimum(1, (d - t) / 0.05) * 0.5


def hat(rng, open_=False):
    n = int((0.18 if open_ else 0.05) * SR); t = np.arange(n) / SR
    return hp(rng.standard_normal(n), 7000) * np.exp(-t * (18 if open_ else 90)) * 0.06


def reverb(L, R, wet=0.18, rt=1.6, rng=None):
    rng = rng or np.random.default_rng(1)
    n = int(rt * SR); t = np.arange(n) / SR
    irL = rng.standard_normal(n) * np.exp(-t * 6.9 / rt); irR = rng.standard_normal(n) * np.exp(-t * 6.9 / rt)
    irL = lp(irL, 5000); irR = lp(irR, 5000)
    irL /= np.sqrt((irL ** 2).sum()); irR /= np.sqrt((irR ** 2).sum())
    wL = fftconvolve(L, irL)[:len(L)]; wR = fftconvolve(R, irR)[:len(R)]
    return L + wet * wL, R + wet * wR


# ---------------- music theory
MODES = {
    'aeolian':  [0, 2, 3, 5, 7, 8, 10],
    'dorian':   [0, 2, 3, 5, 7, 9, 10],
    'phrygian': [0, 1, 3, 5, 7, 8, 10],
    'hijaz':    [0, 1, 4, 5, 7, 8, 10],   # augmented second — oriental colour
    'mixolyd':  [0, 2, 4, 5, 7, 9, 10],   # bright lapar feel
    'harmonic': [0, 2, 3, 5, 7, 8, 11],   # harmonic minor — what the reference reels use
}
STYLES = {
    'bazm':     dict(bpm=110, modes=['harmonic', 'hijaz'], usul='bazm', bass=True, hats=False, nay=0.5),
    'lapar':    dict(bpm=100, modes=['mixolyd', 'dorian'], usul='lapar', bass=True, hats=False, nay=0.3),
    'dramatic': dict(bpm=84, modes=['hijaz', 'phrygian'], usul='slow', bass=True, hats=False, nay=0.7),
    'modern':   dict(bpm=106, modes=['harmonic', 'hijaz'], usul='trap', bass=True, hats=True, nay=0.5),
}
# doira patterns over one bar of 8 eighths: B=bum, T=tak, t=soft tak, '.'=rest
USUL = {
    'bazm':  ['B.tTB.T.', 'B.tTBtT.'],
    'lapar': ['B.T.BtT.', 'B.TtB.Tt'],
    'slow':  ['B...T.t.', 'B..tT...'],
    'trap':  ['B...T...', 'B..BT...'],
}


def degree(scale, root, d):
    o, k = divmod(d, len(scale)); return root + 12 * o + scale[k]


def make_motif(rng, nsteps=8):
    """scale-degree motif with rhythm (in eighths), rises then settles."""
    cur = int(rng.integers(2, 5)); mot = []; left = nsteps
    while left > 0:
        dur = int(rng.choice([1, 1, 2, 2, 3])) if left > 1 else 1; dur = min(dur, left)
        mot.append((cur, dur)); left -= dur
        cur += int(rng.choice([-2, -1, -1, 1, 1, 2, 0]))
        cur = int(np.clip(cur, 0, 7))
    return mot


def render(tl, out, seed=1, style='bazm'):
    rng = np.random.default_rng(seed)
    S = STYLES.get(style, STYLES['bazm'])
    bpm = S['bpm'] + int(rng.integers(-4, 5)); e = 60 / bpm / 2      # eighth-note length
    T = tl['total'] + 1.0; M = Mix(T + 1)
    mode = MODES[rng.choice(S['modes'])]; root = int(rng.choice([57, 55, 52, 50]))   # A3/G3/E3/D3
    starts = tl['starts']; last = starts[-1] if len(starts) > 1 else T
    bar = 8 * e; nbars = int(np.ceil(T / bar)) + 1
    prog = [0, 0, 3, 4] if rng.random() < .5 else [0, 5, 3, 4]       # degree roots per bar (i, VI/iv, v)
    motA, motB = make_motif(rng), make_motif(rng)
    pat = USUL[S['usul']]

    def energy(t):   # 0 intro, 1 main, 0.6 choice/outro
        if t < 1.2 * bar: return 0.0
        if t >= last - 0.2: return 0.6
        return 1.0

    for b in range(nbars):
        t0 = b * bar; en = energy(t0)
        if t0 > T: break
        chord = prog[b % len(prog)]; cr = degree(mode, root, chord)
        # --- dutar: drone + strummed pulse on every bar
        drone = dutar(n2f(cr - 12), bar * 1.1, rng)
        M.add(drone, t0, 0.32 if en else 0.4, -0.2)
        for k in (0, 3, 6) if en else (0, 4):
            M.add(dutar(n2f(cr), e * 2.5, rng), t0 + k * e, 0.22, -0.3)
            M.add(dutar(n2f(cr + 7), e * 2.5, rng), t0 + k * e + 0.012, 0.16, -0.3)
        # --- doira
        if en > 0:
            p = pat[b % len(pat)]
            for k, ch in enumerate(p):
                tt = t0 + k * e
                if ch == 'B': M.add(doira_bum(rng), tt, 0.55 * en, 0.05); M.add(zil(rng), tt, 0.6 * en, 0.3)
                elif ch == 'T': M.add(doira_tak(rng), tt, 0.45 * en, 0.15); M.add(zil(rng, .3), tt, 0.9 * en, 0.3)
                elif ch == 't': M.add(doira_tak(rng), tt, 0.22 * en, 0.15); M.add(zil(rng, .15), tt, 0.5 * en, 0.3)
            # roll of jingles on bar end every 4 bars
            if b % 4 == 3:
                for q in range(6): M.add(zil(rng, .12), t0 + 6 * e + q * e / 3, 0.5 * en, 0.35)
        # --- modern low end
        if S['bass'] and en > 0:
            M.add(kick808(n2f(cr - 24) * 0.9), t0, 0.55 * en)
            if S['usul'] in ('trap', 'bazm'): M.add(kick808(n2f(cr - 24) * 0.9, 0.4), t0 + 5 * e, 0.35 * en)
            M.add(sub(n2f(cr - 24), bar * 0.95), t0, 0.35 * en)
        if S['hats'] and en > 0:
            for k in range(16):
                if k % 4 == 2 and rng.random() < .25:
                    for r in range(3): M.add(hat(rng), t0 + k * e / 2 + r * e / 6, 0.5 * en, 0.4)
                else: M.add(hat(rng, k % 8 == 6), t0 + k * e / 2, (0.7 if k % 2 == 0 else 0.4) * en, 0.4)
        # --- rubob melody: A A' B A'' phrasing, sometimes rests to leave room for the voice
        if en > 0 and (b % 4 != 3 or rng.random() < .3):
            mot = motA if (b // 2) % 2 == 0 else motB
            shift = [0, 0, 2, -1][b % 4] + chord
            tt = t0
            for d, du in mot:
                if rng.random() < 0.12: tt += du * e; continue
                f = n2f(degree(mode, root + 12, d + shift))
                if rng.random() < 0.25:   # grace note from above (ornament)
                    M.add(rubob(f * 2 ** (2 / 12), 0.08, rng), tt - 0.045, 0.18, 0.35)
                M.add(rubob(f, du * e + 0.4, rng), tt, 0.28 * (0.8 if en < 1 else 1), 0.35)
                tt += du * e
        # --- harmonic pad (body)
        M.add(pad([n2f(cr), n2f(degree(mode, root, chord + 2)), n2f(degree(mode, root, chord + 4))], bar * 1.05), t0, 0.9 if en else 0.6, 0.0)
        # --- lead phrase every 4 bars: gijjak or nay (long notes, oriental colour, uses the leading tone)
        if en > 0 and b % 4 == 2 and rng.random() < S['nay'] + 0.35:
            degs = [[4, 5, 6, 5, 4, 3], [7, 6, 5, 4, 2, 1, 0], [2, 3, 4, 3, 2, 1, 0]][int(rng.integers(0, 3))]
            fr = [n2f(degree(mode, root + 12, d)) for d in degs]
            du = list(rng.choice([e, e * 2, e * 2, e * 3], len(fr)))
            inst = gijjak if rng.random() < 0.6 else nay
            M.add(inst(fr, du, rng), t0 + e, 0.5, -0.3)

    L, R = reverb(M.L, M.R, 0.2, 1.8, rng)
    # gentle master: low-cut, glue
    L = hp(L, 30); R = hp(R, 30)
    tt = np.arange(len(L)) / SR
    fade = np.clip((T - tt) / 2.0, 0, 1) * np.clip(tt / 0.3, 0, 1); L *= fade; R *= fade
    m = np.stack([L, R], 1); m = np.tanh(m / (np.max(np.abs(m)) + 1e-9) * 1.3) / np.tanh(1.3)
    sf.write(out, (m * 0.9)[:int(T * SR)], SR)
    print('uzmusic', style, 'bpm', bpm, 'root', root, 'mode', [k for k, v in MODES.items() if v == mode][0])


if __name__ == '__main__':
    tl = json.load(open(sys.argv[1]))
    render(tl, sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 1, sys.argv[4] if len(sys.argv) > 4 else 'bazm')
