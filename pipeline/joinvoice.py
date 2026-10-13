#!/usr/bin/env python3
"""Join several single-speaker voice parts (different voices) into one mp3 + one words json.

Usage: joinvoice.py <out.mp3> <out_words.json> <part1.mp3> <part1_words.json> [<part2.mp3> <part2_words.json> ...]
A 0.18 s gap is inserted between parts; word times of later parts are shifted by the
cumulative duration. Output words json: {"words":[{"text","start","end","type":"word"}, ...]}
"""
import sys, json, subprocess, tempfile, os

GAP = 0.18


def dur(p):
    return float(subprocess.check_output(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]).decode().strip())


def main():
    out_mp3, out_words, *rest = sys.argv[1:]
    pairs = list(zip(rest[0::2], rest[1::2]))
    tmp = tempfile.mkdtemp()
    gap = os.path.join(tmp, 'gap.wav')
    subprocess.check_call(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'lavfi', '-i',
                           'anullsrc=r=44100:cl=mono', '-t', str(GAP), gap])
    listing, words, t = [], [], 0.0
    for i, (mp3, wj) in enumerate(pairs):
        wav = os.path.join(tmp, f'p{i}.wav')
        subprocess.check_call(['ffmpeg', '-loglevel', 'error', '-y', '-i', mp3, '-ar', '44100', '-ac', '1', wav])
        d = dur(wav)
        data = json.load(open(wj))
        ws = data['words'] if isinstance(data, dict) else data
        for w in ws:
            if w.get('type', 'word') != 'word':
                continue
            words.append({'text': w['text'], 'start': round(w['start'] + t, 3),
                          'end': round(w['end'] + t, 3), 'type': 'word'})
        listing += [wav, gap]
        t += d + GAP
    with open(os.path.join(tmp, 'list.txt'), 'w') as f:
        for p in listing[:-1]:
            f.write(f"file '{p}'\n")
    subprocess.check_call(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'concat', '-safe', '0', '-i',
                           os.path.join(tmp, 'list.txt'), '-ar', '44100', '-b:a', '192k', out_mp3])
    json.dump({'words': words}, open(out_words, 'w'), ensure_ascii=False)
    print(f'joined {len(pairs)} parts, {len(words)} words, {t - GAP:.2f}s')


if __name__ == '__main__':
    main()
