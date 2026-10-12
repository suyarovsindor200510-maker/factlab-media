#!/usr/bin/env python3
"""Synth background bed for a FactLab reel: pad + bell arpeggio + pulse + whoosh/boom on scene cuts.
usage: music.py timeline.json out.wav seed"""
import sys, json, numpy as np, soundfile as sf
from scipy.signal import lfilter, butter
tl = json.load(open(sys.argv[1])); out = sys.argv[2]; seed = int(sys.argv[3]) if len(sys.argv) > 3 else 5
SR = 44100; T = tl['total'] + .5; N = int(T * SR); st = tl['starts']
rng = np.random.default_rng(seed); L = np.zeros(N); R = np.zeros(N); tt = np.arange(N) / SR
def add(s, t0, pan=0, g=1):
    i = int(t0 * SR); n = min(len(s), N - i)
    if n > 0 and i >= 0: L[i:i+n] += s[:n]*g*(1-max(0, pan)); R[i:i+n] += s[:n]*g*(1+min(0, pan))
def lp(x, f): b, a = butter(2, f/(SR/2)); return lfilter(b, a, x)
def bpf(x, lo, hi): b, a = butter(2, [lo/(SR/2), hi/(SR/2)], 'band'); return lfilter(b, a, x)
n2f = lambda m: 440*2**((m-69)/12)
PROGS = [
    [[38,50,57,62,65],[34,46,53,58,62],[41,48,57,60,64],[36,48,55,60,67]],   # Dm Bb F C
    [[33,45,52,57,60],[29,41,48,53,57],[36,48,55,60,64],[31,43,50,55,59]],   # Am F C G
    [[40,52,59,64,67],[36,48,55,60,64],[43,50,55,62,67],[38,50,57,62,66]],   # Em C G D
    [[37,49,56,61,64],[33,45,52,57,61],[40,52,59,64,68],[35,47,54,59,63]],   # C#m A E B
]
chords = PROGS[seed % len(PROGS)]; bpm = [96, 100, 104, 92][seed % 4]
seg = T / 4
for k, ch in enumerate(chords):
    n = int((seg+1.5)*SR); x = np.arange(n)/SR; s = np.zeros(n)
    for m in ch:
        for d in (-.07, .07):
            f = n2f(m+d); s += np.sin(2*np.pi*f*x + rng.random()*6) + .3*np.sin(4*np.pi*f*x)
    s = lp(s, 900)*0.02; e = np.minimum(1, np.minimum(x/1.2, (seg+1.5-x)/1.2)); add(s*e, k*seg-0.2 if k else 0)
b = 60/bpm/2; i = 0; t = 0.0
while t < T-1.5:
    k = min(3, int(t/seg)); base = chords[k]; m = [base[2], base[3], base[4], base[3]+12, base[4], base[3]][i % 6]+12
    n = int(1.4*SR); x = np.arange(n)/SR; f = n2f(m)
    s = (np.sin(2*np.pi*f*x) + .35*np.sin(2*np.pi*f*2.01*x)*np.exp(-x*4) + .12*np.sin(2*np.pi*f*3*x)*np.exp(-x*8))*np.exp(-x*2.6)*np.minimum(1, x/.004)
    g = 0.05 if t > 1 else 0.03
    add(s, t, (-.4 if i % 2 else .4), g); add(s*.35, t+b*1.5, (.5 if i % 2 else -.5), g)
    t += b; i += 1
# soft kick pulse on quarter notes after the hook
t = st[1] - .2 if len(st) > 1 else 1
while t < st[-1]:
    n = int(.45*SR); x = np.arange(n)/SR; f = 48+70*np.exp(-x*25)
    add(np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-x*9)*0.3, t); t += 60/bpm
# hats
t = st[1] if len(st) > 1 else 1
while t < st[-1]:
    n = int(.06*SR); z = bpf(rng.standard_normal(n), 7000, 14000)*np.exp(-np.arange(n)/SR*60)*.05
    add(z, t + 30/bpm, .3); t += 60/bpm
nz = rng.standard_normal(N); sh = bpf(nz, 5000, 11000)*0.01*(0.6+0.4*np.sin(tt*0.9)); L += sh; R += np.roll(sh, 500)
def whoosh(d=.7):
    n = int(d*SR); x = np.arange(n)/SR; z = rng.standard_normal(n); o = np.zeros(n)
    for j in range(0, n, 1024):
        fc = 500+3500*np.sin(np.pi*j/n); o[j:j+1024] = bpf(z[j:j+1024], fc*.6, fc*1.6)
    return o*np.sin(np.pi*x/d)**2*.28
def boom(g=1):
    n = int(2.5*SR); x = np.arange(n)/SR; f = 38+60*np.exp(-x*6); return np.sin(2*np.pi*np.cumsum(f)/SR)*np.exp(-x*1.6)*.7*g
add(boom(.9), 0.25)
for i, s in enumerate(st[1:], 1): add(whoosh(), s-.6, (.4 if i % 2 else -.4)); add(boom(.45), s-.2)
fo = np.clip((T-tt)/2.2, 0, 1); fi = np.clip(tt/0.4, 0, 1); L *= fo*fi; R *= fo*fi
m = np.stack([L, R], 1); m /= np.max(np.abs(m))*1.1; sf.write(out, m, SR); print('music ok')
