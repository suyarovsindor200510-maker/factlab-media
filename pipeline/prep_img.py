#!/usr/bin/env python3
"""Square AI image (exported from Canva as 1080x1920 with the square at y=420..1500) ->
sharp 1080x1920 frame: sharp square in the middle, blurred+dimmed cover copy behind it.
usage: prep_img.py <dir>   (rewrites <dir>/1..N.png in place; originals kept as raw_N.png)"""
import sys, os, glob
from PIL import Image, ImageFilter, ImageEnhance
d = sys.argv[1]
for p in sorted(glob.glob(f'{d}/[0-9]*.png')):
    n = os.path.basename(p)
    raw = f'{d}/raw_{n}'
    if not os.path.exists(raw): os.rename(p, raw)
    im = Image.open(raw).convert('RGB')
    sq = im.crop((0, 420, 1080, 1500))
    bg = sq.resize((1920, 1920), Image.LANCZOS).crop((420, 0, 1500, 1920)).filter(ImageFilter.GaussianBlur(28))
    bg = ImageEnhance.Brightness(bg).enhance(0.8)
    bg.paste(sq, (0, 420))
    bg.save(f'{d}/{n}')
    print(n, 'ok')
