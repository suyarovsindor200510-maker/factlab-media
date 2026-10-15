#!/usr/bin/env python3
"""Original dark minimalist indie instrumental (clean reverb guitar riff + sub bass pulse + soft kick/rim),
in the mood of moody minimal indie intros. Usage: darkmusic.py out.wav seconds [bpm]"""
import sys, numpy as np, soundfile as sf
SR = 44100
rng = np.random.default_rng(11)


def pluck(f, dur, bright=0.5):
    # Karplus-Strong string
    n = int(dur * SR); N = int(SR / f)
    buf = rng.uniform(-1, 1, N); out = np.zeros(n)
    for i in range(n):
        out[i] = buf[i % N]
        buf[i % N] = (buf[i % N] + buf[(i + 1) % N]) * 0.5 * (0.996 + 0.003 * bright)
    return out * np.linspace(1, 0.6, n)


def reverb(x, secs=2.4, wet=0.35):
    n = int(secs * SR); t = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-t * 3.2)
    ir = np.convolve(ir, np.ones(8) / 8, 'same')
    ir /= np.sqrt(np.sum(ir ** 2))
    y = np.fft.irfft(np.fft.rfft(x, len(x) + n) * np.fft.rfft(ir, len(x) + n))[:len(x)]
    return x * (1 - wet) + y * wet * 1.6


def main():
    out, T = sys.argv[1], float(sys.argv[2]); bpm = float(sys.argv[3]) if len(sys.argv) > 3 else 100
    beat = 60 / bpm; n = int((T + 3) * SR); g = np.zeros(n); b = np.zeros(n); d = np.zeros(n)
    # B minor-ish riff: two-bar sparse figure, root moves Bm - G - D - A
    hz = lambda m: 440 * 2 ** ((m - 69) / 12)
    roots = [47, 43, 50, 45]  # B2 G2 D3 A2
    riff = [(0, 71), (1.5, 74), (2, 73), (3, 69), (4, 71), (5.5, 66), (6, 69), (7, 66)]  # (beat, midi) over 2 bars
    cache = {}
    bar2 = 8 * beat; k = 0; t0 = 0.0
    while t0 < T + 1:
        for bt, m in riff:
            s = int((t0 + bt * beat) * SR)
            if s >= n: break
            if m not in cache: cache[m] = pluck(hz(m), 1.6, 0.4)
            p = cache[m]; L = min(len(p), n - s); g[s:s + L] += p[:L] * 0.5
        r = roots[k % 4]
        for q in range(8):  # sub bass pulse on every beat, very soft attack
            s = int((t0 + q * beat) * SR); L = int(beat * 0.9 * SR)
            if s + L >= n: break
            tt = np.arange(L) / SR
            b[s:s + L] += np.sin(2 * np.pi * hz(r - 12) * tt) * np.minimum(1, tt * 40) * np.exp(-tt * 2.5) * 0.55
        if k >= 1:  # drums enter on the second phrase: kick on 1 & 3, rim on 2 & 4
            for q in range(8):
                s = int((t0 + q * beat) * SR); L = int(0.35 * SR)
                if s + L >= n: break
                tt = np.arange(L) / SR
                if q % 2 == 0:
                    d[s:s + L] += np.sin(2 * np.pi * (45 + 70 * np.exp(-tt * 30)) * tt) * np.exp(-tt * 9) * 0.7
                else:
                    d[s:s + L] += rng.standard_normal(L) * np.exp(-tt * 60) * 0.18 + np.sin(2 * np.pi * 1700 * tt) * np.exp(-tt * 80) * 0.15
        t0 += bar2; k += 1
    pad = np.zeros(n); tt = np.arange(n) / SR  # airy dark pad
    for f in (hz(59), hz(62), hz(66)):
        pad += np.sin(2 * np.pi * f * tt + np.sin(2 * np.pi * 0.2 * tt)) * 0.04
    x = reverb(g, 2.8, 0.45) + b + reverb(d, 1.2, 0.2) + reverb(pad, 3, 0.6)
    x = np.tanh(x * 1.2)
    x = x[:int(T * SR)]
    fi = int(1.0 * SR); x[:fi] *= np.linspace(0, 1, fi)
    x /= np.max(np.abs(x)) + 1e-9; x *= 0.9
    # slight stereo width: delayed copy on the right
    dl = int(0.012 * SR); R = np.concatenate([np.zeros(dl), x[:-dl]])
    sf.write(out, np.stack([x, 0.7 * x + 0.3 * R], 1), SR)


if __name__ == '__main__':
    main()
