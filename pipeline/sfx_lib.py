#!/usr/bin/env python3
"""Use the shared SFX library (assets/sfx_lib) in a reel.

    from sfx_lib import get, bed
    get('whoosh')                      # -> path; 'pack.name' or a bare name (first pack that has it)
    bed([(0.0, 'hook'), (2.1, 'whoosh', -4), (5.3, 'money')], 25.4, 'sfx_bed.wav')   # (time, id, gain dB)

    python3 pipeline/sfx_lib.py               # list the library
"""
import os, json, numpy as np, soundfile as sf, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, 'assets', 'sfx_lib')
SR = 48000


def index():
    return json.load(open(os.path.join(LIB, 'index.json')))['sounds']


def get(name):
    for s in index():
        if s['id'] == name or s['name'] == name:
            return os.path.join(LIB, s['file'])
    raise KeyError(f'no sfx {name!r}; have: ' + ', '.join(s['id'] for s in index()))


def load(name, gain_db=0.0, max_len=None):
    a, sr = sf.read(get(name), always_2d=True)
    if sr != SR:
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', get(name), '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True).stdout
        a = np.frombuffer(raw, np.float32).reshape(-1, 2)
    if a.shape[1] == 1: a = np.repeat(a, 2, 1)
    if max_len:                                   # e.g. cut typing to the length of the text, with a 40 ms fade
        n = int(max_len * SR); a = a[:n].copy(); f = min(len(a), int(0.04 * SR)); a[-f:] *= np.linspace(1, 0, f)[:, None]
    return a * 10 ** (gain_db / 20)


def bed(events, total, out, master_db=-6.0):
    """events: (t, id[, gain_db[, max_len]]). Writes a stereo 48 kHz SFX bed to mix under voice/music."""
    o = np.zeros((int(total * SR) + 1, 2))
    for ev in events:
        t, n = ev[0], ev[1]; g = ev[2] if len(ev) > 2 else 0.0; ml = ev[3] if len(ev) > 3 else None
        a = load(n, g + master_db, ml); i = int(t * SR); j = min(len(o), i + len(a))
        if i < len(o): o[i:j] += a[:j - i]
    pk = np.abs(o).max()
    if pk > 0.98: o *= 0.98 / pk
    sf.write(out, o.astype(np.float32), SR)
    return out


if __name__ == '__main__':
    for s in index():
        print(f"{s['id']:28s} {s['dur']:5.2f}s  {s['use']}")
