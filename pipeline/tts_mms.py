#!/usr/bin/env python3
"""Free open-source Uzbek TTS (Meta MMS, facebook/mms-tts-uzb-script_cyrillic) — runs in the GitHub Action.
tts/<ID>.json = {"engine":"mms","items":[{"text":"... (Uzbek Latin)","path":"assets/<ID>/voice/p1.mp3","speed":1.0}]}"""
import json, glob, os, subprocess, re
import torch, numpy as np, soundfile as sf
from transformers import VitsModel, AutoTokenizer

L2C = [("o'", "ў"), ("g'", "ғ"), ("sh", "ш"), ("ch", "ч"), ("ng", "нг"), ("yo", "ё"), ("yu", "ю"), ("ya", "я"), ("ye", "е"),
       ("a", "а"), ("b", "б"), ("d", "д"), ("e", "е"), ("f", "ф"), ("g", "г"), ("h", "ҳ"), ("i", "и"), ("j", "ж"), ("k", "к"),
       ("l", "л"), ("m", "м"), ("n", "н"), ("o", "о"), ("p", "п"), ("q", "қ"), ("r", "р"), ("s", "с"), ("t", "т"), ("u", "у"),
       ("v", "в"), ("x", "х"), ("y", "й"), ("z", "з"), ("'", "ъ")]
def cyr(t):
    t = t.lower().replace('’', "'").replace('ʻ', "'").replace('`', "'")
    t = re.sub(r"\be", "э", t)
    out, i = '', 0
    while i < len(t):
        for a, b in L2C:
            if t.startswith(a, i): out += b; i += len(a); break
        else: out += t[i]; i += 1
    return out

model = VitsModel.from_pretrained("facebook/mms-tts-uzb-script_cyrillic"); tok = AutoTokenizer.from_pretrained("facebook/mms-tts-uzb-script_cyrillic")
for f in sorted(glob.glob('tts/*.json')):
    for it in json.load(open(f))['items']:
        mp3 = it['path']
        if os.path.exists(mp3) and os.path.getsize(mp3) > 0: continue
        os.makedirs(os.path.dirname(mp3), exist_ok=True)
        try:
            model.speaking_rate = it.get('speed', 1.0)
            with torch.no_grad(): wav = model(**tok(cyr(it['text']), return_tensors="pt")).waveform[0].numpy()
            w = mp3[:-4] + '.wav'; sf.write(w, wav, model.config.sampling_rate)
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', w, '-ar', '44100', '-b:a', '160k', mp3], check=True); os.remove(w)
            msg = f'{mp3} ok mms {len(wav)/model.config.sampling_rate:.2f}s'
        except Exception as e:
            msg = f'{mp3} FAILED {e}'
            if os.path.exists(mp3): os.remove(mp3)
        print(msg); open('assets/_tts.log', 'a').write(msg + '\n')
