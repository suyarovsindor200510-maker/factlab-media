#!/usr/bin/env python3
"""Estimate word timings for a single TTS part when no transcript is available.
usage: estwords.py <part.mp3> "<text>" <out_words.json>
Speech start/end found with ffmpeg silencedetect; words spread by letter count (+pause after , . ! ? — :)."""
import sys, re, json, subprocess
mp3, text, out = sys.argv[1:4]
dur = float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',mp3]).decode())
r = subprocess.run(['ffmpeg','-i',mp3,'-af','silencedetect=noise=-38dB:d=0.12','-f','null','-'],capture_output=True,text=True).stderr
starts=[float(x) for x in re.findall(r'silence_start: ([\d.]+)',r)]
ends=[float(x) for x in re.findall(r'silence_end: ([\d.]+)',r)]
t0 = ends[0] if starts and starts[0] < 0.05 and ends else 0.0
t1 = starts[-1] if starts and starts[-1] > dur-0.6 else dur
words=[w for w in text.split() if re.search(r'\w',w)]
wt=[]
for w in words:
    L=len(re.sub(r'\W','',w))
    p=0.0
    if re.search(r'[,:;—-]$',w): p=0.12
    if re.search(r'[.!?]$',w): p=0.2
    wt.append((L+1.0, p))
tot=sum(a+p*8 for a,p in wt)
span=max(0.3,t1-t0); t=t0; res=[]
for w,(a,p) in zip(words,wt):
    d=(a/ (tot)) * span
    res.append({'text':w,'start':round(t,3),'end':round(t+d,3),'type':'word'})
    t+=d+(p*8/tot)*span
json.dump({'words':res},open(out,'w'),ensure_ascii=False)
print(len(res),'words',round(t0,2),round(t1,2))
