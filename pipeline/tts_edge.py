#!/usr/bin/env python3
"""Free Microsoft Edge neural TTS (runs in the GitHub Action, not in the sandbox).
tts/<ID>.json = {"items":[{"voice":"uz-UZ-SardorNeural","text":"...","path":"assets/<ID>/voice/p1.mp3","rate":"+0%","pitch":"+0Hz"}]}
Writes each mp3 plus <path minus .mp3>.words.json in the {"words":[{text,start,end,type}]} format used by joinvoice.py."""
import asyncio, json, glob, os, sys
import edge_tts

async def one(it):
    mp3 = it['path']; wj = mp3[:-4] + '.words.json'
    if os.path.exists(mp3) and os.path.exists(wj): return f'{mp3} exists'
    os.makedirs(os.path.dirname(mp3), exist_ok=True)
    c = edge_tts.Communicate(it['text'], it.get('voice', 'uz-UZ-SardorNeural'), rate=it.get('rate', '+0%'),
                             pitch=it.get('pitch', '+0Hz'), boundary='WordBoundary')
    words = []
    with open(mp3, 'wb') as f:
        async for ch in c.stream():
            if ch['type'] == 'audio': f.write(ch['data'])
            elif ch['type'] == 'WordBoundary':
                s = ch['offset'] / 1e7; d = ch['duration'] / 1e7
                words.append({'text': ch['text'], 'start': round(s, 3), 'end': round(s + d, 3), 'type': 'word'})
    json.dump({'words': words}, open(wj, 'w'), ensure_ascii=False)
    return f'{mp3} ok {len(words)} words'

async def main():
    for f in sorted(glob.glob('tts/*.json')):
        for it in json.load(open(f))['items']:
            try: msg = await one(it)
            except Exception as e: msg = f"{it['path']} FAILED {e}"
            print(msg); open('assets/_tts.log', 'a').write(msg + '\n')

asyncio.run(main())
