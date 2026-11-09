# For each listen/<id>/job.json without out/: run whisper word timestamps + earshot reports
import json, glob, os, subprocess, sys
def sh(args, out=None):
    print('+', ' '.join(args), flush=True)
    r = subprocess.run(args, capture_output=True, text=True)
    txt = r.stdout + ('\nSTDERR:\n' + r.stderr[-3000:] if r.returncode else '')
    if out: open(out, 'w').write(txt)
    print(txt[:3000], flush=True)
    return r.returncode
for jf in sorted(glob.glob('listen/*/job.json')):
    d = os.path.dirname(jf); o = os.path.join(d, 'report')
    if os.path.exists(os.path.join(o, 'DONE')): continue
    os.makedirs(o, exist_ok=True); j = json.load(open(jf))
    v = j.get('video'); cues = j.get('cues')
    if j.get('separate'):
        src = j['separate']
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'demucs'], check=False)
        model = j.get('demucs_model', 'htdemucs_ft')
        sh([sys.executable, '-m', 'demucs', '--two-stems=vocals', '-n', model, '-o', '/tmp/sep', src], f'{o}/demucs.txt')
        stem = os.path.splitext(os.path.basename(src))[0]
        for nm in ('vocals', 'no_vocals'):
            p = f'/tmp/sep/{model}/{stem}/{nm}.wav'
            if os.path.exists(p): subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', p, os.path.join(d, nm + '.flac')])
        if os.path.exists(os.path.join(d, 'vocals.flac')): j['voice'] = os.path.join(d, 'vocals.flac')
    if j.get('voice'):
        from faster_whisper import WhisperModel
        m = WhisperModel(j.get('stt_model', 'deepdml/faster-whisper-large-v3-turbo-ct2'), device='cpu', compute_type='int8')
        import soundfile as sf, numpy as np
        a, sr = sf.read(j['voice'], dtype='float32')
        if a.ndim > 1: a = a.mean(1)
        if sr != 16000:
            import soxr; a = soxr.resample(a, sr, 16000)
        segs, info = m.transcribe(a.astype(np.float32), language=j.get('lang', 'uz'), word_timestamps=True,
                                  initial_prompt=j.get('prompt'), vad_filter=False, beam_size=5)
        words = []; lines = []
        for s in segs:
            lines.append(f'{s.start:7.2f}-{s.end:7.2f} {s.text.strip()}')
            for w in s.words or []: words.append({'w': w.word.strip(), 's': round(w.start, 2), 'e': round(w.end, 2), 'p': round(w.probability, 2)})
        json.dump({'offset': j.get('voice_offset', 0), 'words': words}, open(os.path.join(o, 'words.json'), 'w'), ensure_ascii=False, indent=0)
        open(os.path.join(o, 'transcript.txt'), 'w').write('\n'.join(lines))
        print('\n'.join(lines), flush=True)
    E = [sys.executable, '-m', 'earshot']
    if v:
        sh(E + ['measure', v, '--out', f'{o}/measure.json'], f'{o}/measure.txt')
        tl = E + ['timeline', v, '--video', v, '--detail', 'high', '--out', f'{o}/timeline.json']
        if cues: tl += ['--cues', cues]
        sh(tl, f'{o}/timeline.txt')
        sh(E + ['critique', v, '--video', v, '--out', f'{o}/critique.json'], f'{o}/critique.txt')
        sh(E + ['sheet', v, '--video', v, '-o', f'{o}/sheet.png'] + (['--cues', cues] if cues else []), f'{o}/sheet.txt')
    for k in ('sfx', 'music'):
        if j.get(k):
            sh(E + ['timeline', j[k], '--detail', 'high', '--out', f'{o}/{k}_timeline.json'] + (['--cues', cues] if cues and k == 'sfx' else []), f'{o}/{k}_timeline.txt')
            if k == 'music': sh(E + ['describe', j[k]], f'{o}/music_describe.txt')
    open(os.path.join(o, 'DONE'), 'w').write('ok')
