#!/usr/bin/env python3
"""FactLab daily reel builder.

usage:
  python3 pipeline/make.py <spec.json> <voice.mp3> <out_dir>      # full build
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


def split_voice(mp3, n, wd):
    """Split the voice into n segments at the n-1 longest inner pauses."""
    raw = f'{wd}/raw.wav'
    sh(f'ffmpeg -y -i "{mp3}" -ac 1 -ar 44100 "{raw}"')
    T = dur(raw)
    sil = silences(raw)
    # speech start/end
    s0 = sil[0][1] if sil and sil[0][0] < 0.05 else 0.0
    s1 = sil[-1][0] if sil and sil[-1][1] > T - 0.05 else T
    inner = [x for x in sil if x[0] > s0 + 0.3 and x[1] < s1 - 0.3]
    if len(inner) < n - 1:
        raise SystemExit(f'only {len(inner)} pauses found, need {n-1}: write each scene voice as its own paragraph')
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


def fake_timeline(spec):
    starts, durs, t = [], [], LEAD
    for s in spec['scenes']:
        d = max(1.6, len(s.get('voice', '')) / 15.5); starts.append(t); durs.append(d); t += d + GAP
    return {'starts': starts, 'durs': durs, 'total': t - GAP + TAIL}


def build_html(spec, tl, wd):
    tpl = 'story.html' if spec.get('format') == 'story' else 'template.html'
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
    tl = split_voice(mp3, n, wd)
    print('timeline', tl)
    build_html(spec, tl, wd)
    seed = sum(map(ord, spec.get('id', 'x'))) % 1000
    music(tl, wd, seed, spec)
    # mix: music ducked under voice, loudness normalised for Instagram
    sh(f'ffmpeg -y -i "{wd}/voice.wav" -i "{wd}/music.wav" -filter_complex '
       f'"[0:a]aformat=channel_layouts=stereo,volume=1.0,asplit[v][sc];[1:a]volume={spec.get("music_vol", 0.55)}[m];'
       f'[m][sc]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=350[md];'
       f'[v][md]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1.2:LRA=11[o]" -map "[o]" -ar 48000 "{wd}/audio.wav"')
    fr = f'{wd}/fr'; shutil.rmtree(fr, ignore_errors=True); os.makedirs(fr)
    NFR = int(tl['total'] * FPS)
    render(wd, [(f'{fr}/f{f:05d}.jpg', f / FPS) for f in range(NFR)], 4)
    sh(f'ffmpeg -y -framerate {FPS} -i "{fr}/f%05d.jpg" -i "{wd}/audio.wav" -vf "noise=alls=4:allf=t,format=yuv420p" '
       f'-c:v libx264 -preset medium -crf 20 -profile:v high -c:a aac -b:a 192k -shortest -movflags +faststart "{wd}/video.mp4"',
       timeout=1800)
    preview(spec, tl, wd)
    print('done', wd, tl['total'])


if __name__ == '__main__':
    main()
