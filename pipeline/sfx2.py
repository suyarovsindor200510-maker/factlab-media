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


if __name__ == '__main__':
    for name, fn in (('scratch', scratch), ('choir', choir), ('bassdrop', bassdrop), ('hit', hit)):
        sf.write(f'{D}/{name}.wav', fn(), SR)
        print(name, 'ok')
