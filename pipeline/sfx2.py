#!/usr/bin/env python3
"""Extra synthesized sound effects for the doc engine: scratch (record scratch), choir (angelic 'aah'),
bassdrop (cinematic sub drop), hit (comedy music hit). Writes 44.1 kHz stereo wavs into pipeline/sfx/."""
import numpy as np, soundfile as sf, os
SR = 44100
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sfx')
rng = np.random.default_rng(7)


def st(x):
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.9
    return np.stack([x, x], 1)


def env(n, a, r):
    e = np.ones(n); ai = int(a * SR); ri = int(r * SR)
    if ai: e[:ai] = np.linspace(0, 1, ai)
    if ri: e[-ri:] *= np.linspace(1, 0, ri)
    return e


def scratch():
    # two "wikka" strokes: band-passed noise + a resonant tone with fast pitch swoops
    T = 0.55; n = int(T * SR); t = np.arange(n) / SR
    f = np.where(t < 0.22, 300 + 1800 * np.sin(np.pi * t / 0.22), 300 + 1200 * np.sin(np.pi * (t - 0.22) / 0.33) ** 2)
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(ph) * 0.6 + np.sign(np.sin(ph * 0.5)) * 0.25
    noise = rng.standard_normal(n)
    # crude band-pass following the pitch: multiply noise by tone (ring-mod) then smooth
    nb = np.convolve(noise * np.sin(ph * 1.5), np.ones(6) / 6, 'same')
    x = (tone + 0.8 * nb) * env(n, 0.005, 0.08)
    gate = (np.abs(np.sin(np.pi * t / 0.22)) > 0.05) | (t > 0.22)
    return st(x * gate)


def choir():
    # sustained major chord "aah" with vibrato, detuned voices, formant emphasis and a soft reverb tail
    T = 2.6; n = int(T * SR); t = np.arange(n) / SR
    notes = [261.63, 329.63, 392.0, 523.25, 659.25]
    x = np.zeros(n)
    for k, f0 in enumerate(notes):
        for d in (-0.004, 0.0, 0.005):
            vib = 1 + 0.006 * np.sin(2 * np.pi * (5.2 + k * 0.3) * t + k)
            ph = 2 * np.pi * np.cumsum(f0 * (1 + d) * vib) / SR
            # harmonics shaped like an "aa" vowel (formants ~ 800 / 1150 / 2900 Hz)
            for h in range(1, 12):
                fh = f0 * h
                amp = (np.exp(-((fh - 800) / 350) ** 2) + 0.6 * np.exp(-((fh - 1150) / 300) ** 2) + 0.25 * np.exp(-((fh - 2900) / 500) ** 2) + 0.08 / h)
                x += amp * np.sin(h * ph)
    x *= env(n, 0.45, 1.2)
    # reverb: a few decaying echoes
    y = x.copy()
    for dly, g in ((0.061, .45), (0.097, .35), (0.143, .28), (0.211, .2), (0.301, .14)):
        i = int(dly * SR); y[i:] += g * x[:-i]
    # sparkle (bell) on top
    bell = np.sin(2 * np.pi * 1568 * t) * np.exp(-t * 3) * 0.3 + np.sin(2 * np.pi * 2093 * t) * np.exp(-t * 4) * 0.2
    return st(y / np.max(np.abs(y)) + bell)


def bassdrop():
    # cinematic drop: impact + sub sine sweeping 110 -> 32 Hz, saturated, long tail
    T = 2.4; n = int(T * SR); t = np.arange(n) / SR
    f = 32 + 78 * np.exp(-t * 2.2)
    ph = 2 * np.pi * np.cumsum(f) / SR
    sub = np.tanh(2.2 * np.sin(ph)) * np.exp(-t * 0.9)
    click = rng.standard_normal(n) * np.exp(-t * 40) * 0.6
    boom = np.sin(2 * np.pi * 55 * t) * np.exp(-t * 3) * 0.6
    x = sub + click + boom
    x *= env(n, 0.002, 0.4)
    return st(x)


def hit():
    # comedy orchestra-ish hit: stacked saw chord with fast decay + cymbal noise
    T = 0.9; n = int(T * SR); t = np.arange(n) / SR
    x = np.zeros(n)
    for f0 in (130.81, 196.0, 261.63, 329.63, 392.0):
        x += ((t * f0) % 1 * 2 - 1) * 0.3
    x *= np.exp(-t * 5)
    x += rng.standard_normal(n) * np.exp(-t * 9) * 0.25
    return st(x * env(n, 0.003, 0.1))


def notif():
    # phone notification: two bright sine tones (E6 -> B6) with soft bell decay
    T = 0.7; n = int(T * SR); t = np.arange(n) / SR
    x = np.zeros(n)
    for t0, f in ((0.0, 1318.5), (0.11, 1975.5)):
        tt = np.clip(t - t0, 0, None); on = t >= t0
        x += on * (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2 * f * tt)) * np.exp(-tt * 9)
    return st(x * env(n, 0.002, 0.05))


def glitch():
    # digital glitch: bit-crushed noise bursts + stuttering square tones, chopped in random slices
    T = 0.6; n = int(T * SR); t = np.arange(n) / SR
    x = np.zeros(n); i = 0
    while i < n:
        L = int(rng.uniform(0.012, 0.06) * SR); seg = np.arange(min(L, n - i)) / SR
        k = rng.integers(3)
        if k == 0: y = np.sign(np.sin(2 * np.pi * rng.uniform(200, 3000) * seg))
        elif k == 1: y = np.round(rng.standard_normal(len(seg)) * 3) / 3
        else: y = np.zeros(len(seg))
        x[i:i + len(seg)] = y * rng.uniform(0.3, 1); i += L
    x = np.repeat(x[::6], 6)[:n]  # sample-rate reduction -> crunchy
    return st(x * env(n, 0.002, 0.08))


def typing():
    # computer processing: fast keyboard clicks over a soft data hum with bleeps (~2.2 s)
    T = 2.2; n = int(T * SR); t = np.arange(n) / SR
    x = 0.08 * np.sin(2 * np.pi * 120 * t) * (0.6 + 0.4 * np.sin(2 * np.pi * 3 * t))
    tk = 0.0
    while tk < T - 0.05:
        i = int(tk * SR); L = int(0.025 * SR); seg = np.arange(L) / SR
        click = rng.standard_normal(L) * np.exp(-seg * 300) + 0.5 * np.sin(2 * np.pi * rng.uniform(1800, 3200) * seg) * np.exp(-seg * 400)
        x[i:i + L] += click * rng.uniform(0.4, 0.9)
        tk += rng.uniform(0.05, 0.14)
    for b in np.arange(0.3, T - 0.2, 0.45):
        i = int(b * SR); L = int(0.06 * SR); seg = np.arange(L) / SR
        x[i:i + L] += 0.35 * np.sin(2 * np.pi * rng.choice([880, 1320, 1760]) * seg) * env(L, 0.003, 0.03)
    return st(x * env(n, 0.05, 0.3))


def clock():
    # clock ticking, 5 s (tick-tock alternating pitch)
    T = 5.0; n = int(T * SR); x = np.zeros(n)
    for q, tk in enumerate(np.arange(0.05, T, 0.5)):
        i = int(tk * SR); L = int(0.03 * SR); seg = np.arange(L) / SR
        f = 3200 if q % 2 == 0 else 2500
        x[i:i + L] += (np.sin(2 * np.pi * f * seg) + rng.standard_normal(L) * 0.5) * np.exp(-seg * 250)
    return st(x)


def impact():
    # deep cinematic bass impact: sub thump 45 Hz + low boom sweep + noise crack, long dark tail
    T = 3.0; n = int(T * SR); t = np.arange(n) / SR
    f = 28 + 60 * np.exp(-t * 5)
    sub = np.tanh(2.5 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.exp(-t * 1.1)
    crack = rng.standard_normal(n) * np.exp(-t * 25) * 0.5
    crack = np.convolve(crack, np.ones(20) / 20, 'same') * 3
    tail = np.convolve(rng.standard_normal(n), np.ones(400) / 400, 'same') * np.exp(-t * 1.5) * 6
    return st((sub + crack + tail) * env(n, 0.001, 0.6))


if __name__ == '__main__':
    for name, fn in (('scratch', scratch), ('choir', choir), ('bassdrop', bassdrop), ('hit', hit), ('notif', notif), ('glitch', glitch),
                     ('typing', typing), ('clock', clock), ('impact', impact)):
        sf.write(f'{D}/{name}.wav', fn(), SR)
        print(name, 'ok')
