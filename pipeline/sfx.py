#!/usr/bin/env python3
"""Synthesised sound-effect kit for FactLab reels (no external assets, no licences).
Run once: python3 pipeline/sfx.py  -> writes pipeline/sfx/*.wav"""
import os, numpy as np, soundfile as sf
from scipy.signal import butter, lfilter

SR = 44100
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sfx')
rng = np.random.default_rng(7)


def t(d): return np.arange(int(d * SR)) / SR
def bp(x, lo, hi, o=2): b, a = butter(o, [lo / (SR / 2), hi / (SR / 2)], 'band'); return lfilter(b, a, x)
def lp(x, f, o=2): b, a = butter(o, f / (SR / 2)); return lfilter(b, a, x)
def hp(x, f, o=2): b, a = butter(o, f / (SR / 2), 'high'); return lfilter(b, a, x)
def norm(x, peak=0.9): return x / (np.max(np.abs(x)) + 1e-9) * peak
def env(x, a=0.002, r=None):
    n = len(x); e = np.ones(n); na = max(1, int(a * SR)); e[:na] = np.linspace(0, 1, na)
    if r: e *= np.exp(-np.arange(n) / SR / r)
    return x * e
def stereo(x, w=0.0):
    d = int(0.012 * SR * w); r = np.concatenate([np.zeros(d), x])[:len(x)] if d else x
    return np.stack([x, r], 1)


def whoosh(d=0.55, up=True):
    x = t(d); n = rng.standard_normal(len(x)); o = np.zeros(len(x)); blk = 512
    for i in range(0, len(x), blk):
        p = i / len(x); fc = 300 + 5200 * (p if up else 1 - p) ** 1.4
        o[i:i + blk] = bp(n[i:i + blk + 256], fc * 0.55, min(fc * 1.7, 20000))[:len(o[i:i + blk])]
    shape = np.sin(np.pi * np.clip(x / d, 0, 1)) ** 1.6
    return stereo(norm(o * shape, 0.8), 1)


def pop():
    x = t(0.12); f = 900 * np.exp(-x * 40) + 300
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 38)
    s += 0.3 * hp(rng.standard_normal(len(x)), 3000) * np.exp(-x * 120)
    return stereo(norm(env(s), 0.85))


def stamp():
    x = t(0.35); f = 120 * np.exp(-x * 18) + 55
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 14)
    click = lp(rng.standard_normal(len(x)), 2500) * np.exp(-x * 90)
    return stereo(norm(env(body + 0.6 * click), 0.95))


def boom():
    x = t(1.4); f = 32 + 70 * np.exp(-x * 7)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 2.6)
    s += 0.25 * lp(rng.standard_normal(len(x)), 400) * np.exp(-x * 9)
    return stereo(norm(np.tanh(2.2 * s), 0.95))


def ding():
    x = t(1.2); s = np.zeros(len(x))
    for f, a, dcy in [(1568, 1, 3.2), (2349, .5, 4.5), (3136, .35, 6), (4704, .15, 8)]:
        s += a * np.sin(2 * np.pi * f * x) * np.exp(-x * dcy)
    return stereo(norm(env(s, 0.001), 0.7), 0.6)


def kaching():
    # cash register: mechanical clack + bell pair + coin shimmer
    a = t(0.9); s = np.zeros(len(a))
    clack = lp(rng.standard_normal(int(0.05 * SR)), 3000) * np.exp(-np.arange(int(0.05 * SR)) / SR * 80)
    s[:len(clack)] += clack * 0.8
    for st, f in [(0.07, 2637), (0.16, 3520)]:
        i = int(st * SR); x = t(0.9 - st)
        s[i:i + len(x)] += (np.sin(2 * np.pi * f * x) + .4 * np.sin(2 * np.pi * f * 2.76 * x)) * np.exp(-x * 5)
    for k in range(18):
        i = int((0.16 + rng.random() * 0.4) * SR); x = t(0.08); f = 5000 + rng.random() * 4000
        s[i:i + len(x)] += 0.12 * np.sin(2 * np.pi * f * x) * np.exp(-x * 60)
    return stereo(norm(s, 0.8), 0.8)


def tick():
    x = t(0.04); s = hp(rng.standard_normal(len(x)), 2500) * np.exp(-x * 220) + 0.5 * np.sin(2 * np.pi * 2200 * x) * np.exp(-x * 160)
    return stereo(norm(s, 0.55))


def riser(d=1.2):
    x = t(d); n = rng.standard_normal(len(x)); o = np.zeros(len(x)); blk = 512
    for i in range(0, len(x), blk):
        p = i / len(x); fc = 400 + 7000 * p ** 2
        o[i:i + blk] = bp(n[i:i + blk + 256], fc * .7, min(fc * 1.4, 20000))[:len(o[i:i + blk])]
    tone = np.sin(2 * np.pi * np.cumsum(200 + 900 * (x / d) ** 2) / SR) * 0.3
    return stereo(norm((o + tone) * (x / d) ** 2, 0.7), 1)


def swish():
    return whoosh(0.28, up=True)


def boing():
    x = t(0.6); f = 180 + 120 * np.sin(2 * np.pi * 9 * x) * np.exp(-x * 4)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 5)
    return stereo(norm(env(s), 0.7))


def shutter():
    x = t(0.18); s = np.zeros(len(x))
    for st in (0.0, 0.07):
        i = int(st * SR); y = hp(rng.standard_normal(int(0.03 * SR)), 1500) * np.exp(-np.arange(int(0.03 * SR)) / SR * 150)
        s[i:i + len(y)] += y
    return stereo(norm(s, 0.6))


def bruh():
    # comic "fail" trombone-ish descending tone
    x = t(0.9); f = 233 * 2 ** (-x * 0.9)
    s = sum((1 / k) * np.sin(2 * np.pi * k * np.cumsum(f) / SR) for k in range(1, 6))
    s = lp(s, 1800) * np.minimum(1, x / 0.02) * np.exp(-x * 1.5)
    return stereo(norm(s, 0.6))


KIT = dict(whoosh=whoosh, pop=pop, stamp=stamp, boom=boom, ding=ding, kaching=kaching, tick=tick,
           riser=riser, swish=swish, boing=boing, shutter=shutter, fail=bruh)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for k, fn in KIT.items():
        sf.write(f'{OUT}/{k}.wav', fn(), SR)
    print('sfx:', ', '.join(KIT))
