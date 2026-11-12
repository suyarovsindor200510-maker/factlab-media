#!/usr/bin/env python3
"""Ingest an SFX showcase video (one labelled sound after another) into the shared SFX library.

    python3 pipeline/sfx_ingest.py SRC.mp4 PACK "hook,light,whoosh,..."  [--cuts 1.17,2.3,...] [--use "hook=reel start;whoosh=scene cut"]

- Splits at the (len(labels)-1) longest silent gaps; --cuts (seconds, where each next sound/label starts) overrides.
  Always check the split against the on-screen labels (contact sheet of frames) before trusting it.
- Each piece is trimmed (52 dB below its own peak), faded (3 ms in / 20 ms out), peak-normalised to -1 dBFS, 48 kHz stereo 16-bit.
- Writes assets/sfx_lib/<pack>/<name>.wav and merges entries into assets/sfx_lib/index.json.
"""
import sys, os, json, argparse, subprocess, tempfile
import numpy as np, soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, 'assets', 'sfx_lib')
SR = 48000


def silence_cuts(a, n_cuts, gap=0.08, th_db=-45):
    """The n_cuts longest quiet gaps; each cut sits just before the next sound starts."""
    m = np.abs(a).max(1); w = int(0.01 * SR); env = np.array([m[i:i + w].max() for i in range(0, len(m), w)])
    quiet = env < 10 ** (th_db / 20); gaps = []; i = 0
    while i < len(quiet):
        if quiet[i]:
            j = i
            while j < len(quiet) and quiet[j]: j += 1
            if (j - i) * 0.01 >= gap and i > 0 and j < len(quiet): gaps.append(((j - i) * 0.01, j * 0.01 - 0.015))
            i = j
        else: i += 1
    return sorted(c for _, c in sorted(gaps, reverse=True)[:n_cuts])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('src'); ap.add_argument('pack'); ap.add_argument('labels')
    ap.add_argument('--cuts'); ap.add_argument('--use', default=''); ap.add_argument('--source', default='')
    o = ap.parse_args()
    labels = [x.strip().lower().replace(' ', '_') for x in o.labels.split(',') if x.strip()]
    tmp = tempfile.mktemp(suffix='.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', o.src, '-vn', '-ac', '2', '-ar', str(SR), tmp], check=True)
    a, _ = sf.read(tmp); os.remove(tmp); total = len(a) / SR
    if o.cuts: cuts = [float(x) for x in o.cuts.split(',')]
    else:
        cuts = silence_cuts(a, len(labels) - 1)
        print('auto cuts (longest silences):', [round(c, 2) for c in cuts])
        if len(cuts) != len(labels) - 1:
            sys.exit(f'could not split into {len(labels)} pieces automatically; pass --cuts (found {[round(c, 2) for c in cuts]})')
    bounds = [0.0] + cuts + [total]
    uses = dict(kv.split('=', 1) for kv in o.use.split(';') if '=' in kv)
    os.makedirs(os.path.join(LIB, o.pack), exist_ok=True)
    idx_p = os.path.join(LIB, 'index.json'); idx = json.load(open(idx_p)) if os.path.exists(idx_p) else {'sounds': []}
    m = np.abs(a).max(1)
    for k, n in enumerate(labels):
        i0 = int(max(0, bounds[k] - 0.01) * SR); i1 = int(bounds[k + 1] * SR); seg = a[i0:i1]
        TH = m[i0:i1].max() * 10 ** (-52 / 20)          # trim relative to the piece's own peak
        nz = np.where(m[i0:i1] > TH)[0]
        if not len(nz): print('silent:', n); continue
        b = max(0, nz[0] - int(0.004 * SR)); c = min(len(seg), nz[-1] + int(0.03 * SR)); seg = seg[b:c].copy()
        fi, fo = int(0.003 * SR), min(int(0.02 * SR), len(seg) // 2)
        seg[:fi] *= np.linspace(0, 1, fi)[:, None]; seg[-fo:] *= np.linspace(1, 0, fo)[:, None]
        seg = seg / (np.abs(seg).max() + 1e-9) * 10 ** (-1 / 20)
        rel = f'{o.pack}/{n}.wav'; sf.write(os.path.join(LIB, rel), seg.astype(np.float32), SR, subtype='PCM_16')
        rms = float(20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-9))
        e = {'id': f'{o.pack}.{n}', 'pack': o.pack, 'name': n, 'file': rel, 'dur': round(len(seg) / SR, 3),
             'rms_db': round(rms, 1), 'use': uses.get(n, ''), 'source': o.source or os.path.basename(o.src)}
        idx['sounds'] = [s for s in idx['sounds'] if s['id'] != e['id']] + [e]
        print(f"{e['id']:28s} {e['dur']:5.2f}s rms {e['rms_db']:6.1f}  {e['use']}")
    idx['sounds'].sort(key=lambda s: s['id'])
    json.dump(idx, open(idx_p, 'w'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
