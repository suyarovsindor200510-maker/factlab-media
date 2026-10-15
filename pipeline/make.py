#!/usr/bin/env python3
"""FactLab daily reel builder.

usage:
  python3 pipeline/make.py <spec.json> <voice.mp3> <out_dir> [words.json]  # full build (words.json = ElevenLabs transcript words for exact cuts/captions)
  python3 pipeline/make.py <spec.json> --preview <out_dir>         # fake-timed preview frames only (no audio)

Produces in out_dir: video.mp4 (1080x1920, 30fps), cover.jpg, and preview frames pv*.jpg.
"""
import json, os, re, subprocess, sys, shutil
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
TEMPO = 1.06
GAP = 0.32
LEAD = 0.45
TAIL = 1.4


def sh(cmd, **kw):
    return subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True, **kw)


def silences(wav):
    r = subprocess.run(f'ffmpeg -hide_banner -i "{wav}" -af silencedetect=n=-40dB:d=0.2 -f null -',
                       shell=True, capture_output=True, text=True)
    s = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', r.stderr)]
    e = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', r.stderr)]
    return list(zip(s, e))


def dur(f):
    return float(sh(f'ffprobe -v error -show_entries format=duration -of csv=p=0 "{f}"').stdout)


def split_voice(mp3, n, wd, texts=None):
    """Split the voice into n segments at pauses. With scene texts, pick the pauses that best match
    the expected boundaries (by character count); otherwise take the n-1 longest pauses."""
    raw = f'{wd}/raw.wav'
    sh(f'ffmpeg -y -i "{mp3}" -ac 1 -ar 44100 "{raw}"')
    T = dur(raw)
    sil = silences(raw)
    s0 = sil[0][1] if sil and sil[0][0] < 0.05 else 0.0
    s1 = sil[-1][0] if sil and sil[-1][1] > T - 0.05 else T
    inner = [x for x in sil if x[0] > s0 + 0.3 and x[1] < s1 - 0.3]
    if len(inner) < n - 1:
        raise SystemExit(f'only {len(inner)} pauses found, need {n-1}: write each scene voice as its own paragraph')
    if texts and len(texts) == n:
        lens = [max(1, len(t)) for t in texts]; tot = sum(lens); acc = 0; exp = []
        for l in lens[:-1]:
            acc += l; exp.append(s0 + (s1 - s0) * acc / tot)
        K = len(inner); mids = [(a + b) / 2 for a, b in inner]; ln = [b - a for a, b in inner]
        INF = 1e9
        cost = lambda j, k: abs(mids[k] - exp[j]) - 4.0 * ln[k]
        dp = [[INF] * K for _ in range(n - 1)]; bk = [[-1] * K for _ in range(n - 1)]
        for k in range(K): dp[0][k] = cost(0, k)
        for j in range(1, n - 1):
            best, bi = INF, -1
            for k in range(K):
                if k > 0 and dp[j - 1][k - 1] < best: best, bi = dp[j - 1][k - 1], k - 1
                if bi >= 0: dp[j][k] = best + cost(j, k); bk[j][k] = bi
        k = min(range(K), key=lambda q: dp[n - 2][q]); pick = []
        for j in range(n - 2, -1, -1):
            pick.append(k); k = bk[j][k]
        cuts = [inner[q] for q in reversed(pick)]
    else:
        cuts = sorted(sorted(inner, key=lambda x: x[1] - x[0], reverse=True)[:n - 1])
    bounds = [s0] + [c for pair in cuts for c in pair] + [s1]
    segs = []
    for i in range(n):
        a, b = bounds[2 * i], bounds[2 * i + 1]
        a = max(0, a - 0.04); b = min(T, b + 0.08)
        out = f'{wd}/v{i}.wav'
        sh(f'ffmpeg -y -ss {a:.3f} -to {b:.3f} -i "{raw}" -af "atempo={TEMPO},afade=t=in:d=0.02" -ar 44100 "{out}"')
        segs.append(out)
    starts, durs, t = [], [], LEAD
    for s in segs:
        d = dur(s); starts.append(round(t, 3)); durs.append(round(d, 3)); t += d + GAP
    total = round(t - GAP + TAIL, 3)
    # assemble voice track
    parts = []
    for i, s in enumerate(segs):
        parts.append(f'[{i}:a]adelay={int(starts[i]*1000)}|{int(starts[i]*1000)}[a{i}]')
    filt = ';'.join(parts) + ';' + ''.join(f'[a{i}]' for i in range(n)) + f'amix=inputs={n}:normalize=0,apad=whole_dur={total}[o]'
    ins = ' '.join(f'-i "{s}"' for s in segs)
    sh(f'ffmpeg -y {ins} -filter_complex "{filt}" -map "[o]" -t {total} -ar 44100 -ac 1 "{wd}/voice.wav"')
    tl = {'starts': starts, 'durs': durs, 'total': total}
    json.dump(tl, open(f'{wd}/timeline.json', 'w'))
    return tl


def split_by_words(mp3, spec, words, wd, tempo=None, gap=None):
    """Cut the voice at scene boundaries using word timestamps (from ElevenLabs transcription)."""
    tempo = tempo or spec.get('tempo', TEMPO); gap = GAP if gap is None else gap
    raw = f'{wd}/raw.wav'
    sh(f'ffmpeg -y -i "{mp3}" -ac 1 -ar 44100 "{raw}"')
    T = dur(raw)
    allc = [len((sc.get('voice') or '').split()) for sc in spec['scenes']]
    vidx = [i for i, c in enumerate(allc) if c > 0]          # voiced scenes; others are silent beats (sc['silent'] seconds)
    counts = [allc[i] for i in vidx]
    nW = len(words)
    if sum(counts) != nW:  # scale counts to transcript length
        acc, b = 0, []
        for c in counts[:-1]:
            acc += c; b.append(round(acc * nW / sum(counts)))
    else:
        b = []; acc = 0
        for c in counts[:-1]:
            acc += c; b.append(acc)
    idx = [0] + b + [nW]
    segs, starts, durs, wl = [], [], [], []
    t = LEAD
    for si, sc in enumerate(spec['scenes']):
        out = f'{wd}/v{si}.wav'
        if si not in vidx:
            d0 = float(sc.get('silent', 2.5))
            sh(f'ffmpeg -y -f lavfi -i anullsrc=r=44100:cl=mono -t {d0:.3f} "{out}"')
            d = dur(out); starts.append(round(t, 3)); durs.append(round(d, 3)); wl.append([]); segs.append(out); t += d + gap
            continue
        i = vidx.index(si)
        w0, w1 = words[idx[i]], words[idx[i + 1] - 1]
        a = max(0, w0['start'] - 0.06) if i == 0 else (words[idx[i] - 1]['end'] + w0['start']) / 2
        e = min(T, w1['end'] + 0.25) if i == len(counts) - 1 else (w1['end'] + words[idx[i + 1]]['start']) / 2
        sh(f'ffmpeg -y -ss {a:.3f} -to {e:.3f} -i "{raw}" -af "atempo={tempo},afade=t=in:d=0.015" -ar 44100 "{out}"')
        d = dur(out); starts.append(round(t, 3)); durs.append(round(d, 3))
        wl.append([[w['text'], round(t + (w['start'] - a) / tempo, 3), round(t + (w['end'] - a) / tempo, 3)] for w in words[idx[i]:idx[i + 1]]])
        segs.append(out); t += d + gap
    total = round(t - gap + TAIL, 3)
    parts = [f'[{i}:a]adelay={int(starts[i]*1000)}|{int(starts[i]*1000)}[a{i}]' for i in range(len(segs))]
    filt = ';'.join(parts) + ';' + ''.join(f'[a{i}]' for i in range(len(segs))) + f'amix=inputs={len(segs)}:normalize=0,apad=whole_dur={total}[o]'
    ins = ' '.join(f'-i "{x}"' for x in segs)
    sh(f'ffmpeg -y {ins} -filter_complex "{filt}" -map "[o]" -t {total} -ar 44100 -ac 1 "{wd}/voice.wav"')
    tl = {'starts': starts, 'durs': durs, 'total': total, 'words': wl}
    json.dump(tl, open(f'{wd}/timeline.json', 'w'), ensure_ascii=False)
    return tl


def sfx_track(spec, tl, wd):
    """Place sound effects on the story events (stickers, counters, badges, cuts)."""
    import numpy as np, soundfile as sf
    sdir = f'{HERE}/sfx'
    if not os.path.exists(f'{sdir}/pop.wav'):
        sh(f'python3 "{HERE}/sfx.py"')
    SR = 44100; N = int((tl['total'] + 2) * SR); mix = np.zeros((N, 2))
    cache = {}
    def put(name, t0, g=1.0):
        if t0 < 0 or not name: return
        if name not in cache:
            a, sr = sf.read(f'{sdir}/{name}.wav'); cache[name] = a if a.ndim == 2 else np.stack([a, a], 1)
        a = cache[name]; i = int(t0 * SR); n = min(len(a), N - i)
        if n > 0: mix[i:i + n] += a[:n] * g
    st = tl['starts']
    STY = {'red': 'stamp', 'dark': 'stamp', 'yellow': 'pop', 'paper': 'pop', 'teal': 'pop'}
    doc = spec.get('format') == 'doc'
    put('boom', 0.05, 0.5 if doc else 0.8)
    OVS = {'punch': ('boom', 0.45), 'stamp': ('stamp', 0.75), 'tag': ('pop', 0.4), 'name': ('pop', 0.45), 'title': ('swish', 0.5),
           'lower': ('swish', 0.35), 'polar': ('shutter', 0.5), 'big': ('ding', 0.45), 'phone': ('swish', 0.45)}
    for i, s in enumerate(spec['scenes']):
        a = st[i]
        if i > 0: put('swish' if doc else 'whoosh', a - (0.2 if doc else 0.42), 0.18 if doc else 0.55)
        for o in s.get('ov', []):
            at = a + o.get('at', 0)
            nm, g = OVS.get(o.get('type'), (None, 0))
            if o.get('sfx') is not None: nm = o['sfx']
            put(nm, at - 0.02, g or 0.5)
            if o.get('type') == 'phone':
                for q in range(len(o.get('items', []))): put('ding', a + (o.get('ats') or [None]*9)[q] if (o.get('ats') or [None]*9)[q] is not None else at + 0.45 + q * o.get('step', 0.55), 0.4)
            if o.get('type') == 'bars':
                for q in range(len(o.get('items', []))): put('pop', at + q * o.get('step', 0.35) + 0.3, 0.4)
        for k in s.get('stickers', []):
            put(k.get('sfx') or STY.get(k.get('style', 'paper'), 'pop'), a + k.get('at', 0) - 0.02, 0.7)
        if s.get('kind') == 'card':
            for r in s.get('rows', []):
                t0 = a + (r.get('at') if r.get('at') is not None else 0.5)
                for q in range(9): put('tick', t0 + q * 0.07, 0.35)
                put('kaching' if r.get('hl') else 'pop', t0 + 0.65, 0.7 if r.get('hl') else 0.6)
        if s.get('kind') == 'bigstat':
            t0 = a - 0.18 + 0.1
            for q in range(13): put('tick', t0 + q * 0.075, 0.35)
            put('kaching', a + s.get('sub_at', 1), 0.75); put('boom', a + s.get('sub_at', 1), 0.5)
        if s.get('kind') == 'choice':
            for b in s.get('badge_at', []): put('ding', a + b, 0.55)
        for e in s.get('sfx', []):
            put(e['t'], a + e.get('at', 0), e.get('g', 0.7))
    pk = np.max(np.abs(mix))
    if pk > 0.98: mix *= 0.98 / pk
    sf.write(f'{wd}/sfx.wav', mix, SR)


def resolve_word_timing(spec, tl):
    """Turn {"w": "keyword"} anchors into scene-relative seconds using the transcript word times."""
    W = tl.get('words')
    if not W: return
    import re as _re
    norm = lambda x: _re.sub(r"[^a-z0-9']", '', x.lower().replace('\u2019', "'").replace('\u02bb', "'"))
    def find(i, key, nth=1):
        k = norm(key); c = 0
        for w in W[i]:
            if norm(w[0]).startswith(k):
                c += 1
                if c == nth: return round(w[1] - tl['starts'][i], 2)
        return None
    for i, s in enumerate(spec['scenes']):
        for it in s.get('stickers', []) + s.get('rows', []) + s.get('sfx', []) + s.get('ov', []) + ([s['mcut']] if s.get('mcut') else []):
            if 'w' in it:
                v = find(i, it['w'], it.get('nth', 1))
                if v is not None: it['at'] = round(v + it.get('dt', 0), 2)
        if 'sub_w' in s:
            v = find(i, s['sub_w']); s['sub_at'] = v if v is not None else s.get('sub_at', 1)
        if 'badge_w' in s:
            s['badge_at'] = [find(i, k) or 1.0 for k in s['badge_w']]


def fake_timeline(spec):
    starts, durs, t = [], [], LEAD
    for s in spec['scenes']:
        d = max(1.6, len(s.get('voice', '')) / 15.5); starts.append(t); durs.append(d); t += d + GAP
    return {'starts': starts, 'durs': durs, 'total': t - GAP + TAIL}


def build_html(spec, tl, wd):
    tpl = {'story': 'story.html', 'doc': 'doc.html'}.get(spec.get('format'), 'template.html')
    h = open(f'{HERE}/{tpl}').read()
    h = h.replace('__FONTS__', 'file://' + HERE + '/fonts').replace('__ROOT__', 'file://' + os.path.dirname(HERE))
    h = h.replace('__SPEC__', json.dumps(spec, ensure_ascii=False)).replace('__TL__', json.dumps(tl))
    open(f'{wd}/e.html', 'w').write(h)


def _render(args):
    wd, k, K, times = args
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        pg.goto(f'file://{wd}/e.html'); pg.wait_for_function('window.READY===1', timeout=60000); pg.wait_for_timeout(400)
        for idx, (name, t) in enumerate(times):
            if idx % K != k: continue
            pg.evaluate(f'render({t})')
            pg.screenshot(path=name, type='jpeg', quality=92)
        b.close()


def render(wd, times, workers=4):
    with ProcessPoolExecutor(workers) as ex:
        list(ex.map(_render, [(wd, k, workers, times) for k in range(workers)]))


def preview(spec, tl, wd):
    times = []
    for i, (a, d) in enumerate(zip(tl['starts'], tl['durs'])):
        times.append((f'{wd}/pv{i:02d}.jpg', a + min(d * 0.7, 1.6)))
    times.append((f'{wd}/cover.jpg', spec.get('cover_t', min(tl['starts'][1] - 0.6, 1.5))))
    render(wd, times, 4)
    sh(f'ffmpeg -y -i "{wd}/pv%02d.jpg" -vf "scale=270:480,tile={len(tl["starts"])}x1" -frames:v 1 "{wd}/sheet.jpg"')


def music(tl, wd, seed, spec=None):
    root = os.path.dirname(HERE)
    if spec and spec.get('uzmusic'):
        sh(f'python3 "{HERE}/uzmusic.py" "{wd}/timeline.json" "{wd}/music.wav" {seed} {spec["uzmusic"]}')
        return
    if spec and spec.get('music'):
        # licensed-free track from music/ (NCS): start offset, fade in/out, fit to video length
        T = tl['total']; ss = spec.get('music_start', 0)
        sh(f'ffmpeg -y -ss {ss} -i "{root}/{spec["music"]}" -t {T} -af "afade=t=in:d=0.6,afade=t=out:st={T-1.8:.2f}:d=1.8,'
           f'loudnorm=I=-16:TP=-1.5" -ar 44100 -ac 2 "{wd}/music.wav"')
        return
    sh(f'python3 "{HERE}/music.py" "{wd}/timeline.json" "{wd}/music.wav" {seed}')


def main():
    spec_f = sys.argv[1]
    spec = json.load(open(spec_f))
    if sys.argv[2] == '--preview':
        wd = os.path.abspath(sys.argv[3]); os.makedirs(wd, exist_ok=True)
        tl = fake_timeline(spec); build_html(spec, tl, wd); preview(spec, tl, wd); print('preview', wd); return
    mp3, wd = sys.argv[2], os.path.abspath(sys.argv[3]); os.makedirs(wd, exist_ok=True)
    n = len(spec['scenes'])
    wf = sys.argv[4] if len(sys.argv) > 4 else None
    if wf:
        W = json.load(open(wf)); W = W.get('words', W) if isinstance(W, dict) else W
        W = [w for w in W if w.get('type', 'word') == 'word']
        tl = split_by_words(mp3, spec, W, wd, gap=spec.get('gap'))
    else:
        tl = split_voice(mp3, n, wd, [sc.get('voice', '') for sc in spec['scenes']])
    print('timeline', tl['starts'], tl['total'])
    resolve_word_timing(spec, tl)
    build_html(spec, tl, wd)
    seed = sum(map(ord, spec.get('id', 'x'))) % 1000
    music(tl, wd, seed, spec)
    # mix: music ducked under voice (+ bass lift), sound effects on top, loudness normalised for Instagram
    has_sfx = spec.get('format') in ('story', 'doc')
    if has_sfx: sfx_track(spec, tl, wd)
    mv = spec.get("music_vol", 0.2)
    # music cuts (dramatic silence before a drop): scene-level {"mcut": {"w"|"at": .., "dur": 0.3, "pre": 0.3}}
    cuts = []
    for i, s in enumerate(spec['scenes']):
        mc = s.get('mcut')
        if mc:
            t0 = tl['starts'][i] + mc.get('at', 0); cuts.append((max(0, t0 - mc.get('pre', 0.3)), t0 + mc.get('dur', 0.0)))
    mcut = ''.join(f",volume=0:enable='between(t,{a:.2f},{b:.2f})'" for a, b in cuts)
    sx = f' -i "{wd}/sfx.wav"' if has_sfx else ''
    mixin = '[v][md][fx]amix=inputs=3:normalize=0' if has_sfx else '[v][md]amix=inputs=2:normalize=0'
    fxs = f';[2:a]volume={spec.get("sfx_vol", 0.9)}[fx]' if has_sfx else ''
    sh(f'ffmpeg -y -i "{wd}/voice.wav" -i "{wd}/music.wav"{sx} -filter_complex '
       f'"[0:a]aformat=channel_layouts=stereo,highpass=f=70,acompressor=threshold=0.1:ratio=3:attack=5:release=80,volume=1.15,asplit[v][sc];'
       f'[1:a]lowpass=f=5500,bass=g=1:f=90,volume={mv}{mcut}[m];'
       f'[m][sc]sidechaincompress=threshold=0.02:ratio=10:attack=5:release=400[md]{fxs};'
       f'{mixin},alimiter=limit=0.95,loudnorm=I=-13:TP=-1.0:LRA=9[o]" -map "[o]" -ar 48000 "{wd}/audio.wav"')
    fr = f'{wd}/fr'; shutil.rmtree(fr, ignore_errors=True); os.makedirs(fr)
    NFR = int(tl['total'] * FPS)
    render(wd, [(f'{fr}/f{f:05d}.jpg', f / FPS) for f in range(NFR)], 4)
    vf = 'unsharp=5:5:0.7:5:5:0.0,eq=contrast=1.05:saturation=1.12,format=yuv420p' if spec.get('format') in ('story', 'doc') else 'noise=alls=4:allf=t,format=yuv420p'
    sh(f'ffmpeg -y -framerate {FPS} -i "{fr}/f%05d.jpg" -i "{wd}/audio.wav" -vf "{vf}" '
       f'-c:v libx264 -preset medium -crf 18 -profile:v high -c:a aac -b:a 192k -shortest -movflags +faststart "{wd}/video.mp4"',
       timeout=1800)
    preview(spec, tl, wd)
    shutil.rmtree(fr, ignore_errors=True)  # frames are ~500 MB per video; disk is limited
    print('done', wd, tl['total'])


if __name__ == '__main__':
    main()
