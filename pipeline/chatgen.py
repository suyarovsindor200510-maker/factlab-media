#!/usr/bin/env python3
"""Render realistic dark-mode messenger screens (1080x1920 PNG) for reels.
usage: chatgen.py specs.json outdir   — specs.json: {"name": {...screen...}, ...}
screen: {"title": "Jasur", "status": "online|Active now|last seen …", "msgs": [{"me": true, "t": "text", "time": "21:47"}],
         "seen": "Seen 21:47", "input": "text being typed" | "", "cursor": true, "typing": true, "blur": false}"""
import json, sys, os, html
from playwright.sync_api import sync_playwright

CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{width:540px;height:960px;background:#0b0f14;font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif;color:#e9edf1;overflow:hidden;position:relative}
.wrap{position:absolute;inset:0;background:radial-gradient(120% 70% at 50% 30%,#141b24 0%,#0b0f14 70%)}
.sb{height:34px;display:flex;justify-content:space-between;align-items:center;padding:0 22px;font-size:14px;font-weight:600;color:#f2f4f6}
.hd{height:66px;display:flex;align-items:center;gap:12px;padding:0 16px;border-bottom:1px solid #1d2630;background:#10161d}
.bk{font-size:26px;color:#4fa3ff;margin-right:2px}
.av{width:42px;height:42px;border-radius:50%;background:linear-gradient(135deg,#6a7bff,#b26bff);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:18px}
.nm{font-weight:700;font-size:17px}.st{font-size:12.5px;color:#8b97a5;margin-top:2px}.st.on{color:#3ed07a}
.body{position:absolute;top:100px;bottom:76px;left:0;right:0;padding:14px 14px;display:flex;flex-direction:column;justify-content:flex-end;gap:8px}
.day{align-self:center;font-size:12px;color:#8b97a5;background:#18202a;padding:4px 10px;border-radius:10px;margin-bottom:6px}
.m{max-width:74%;padding:9px 13px 7px;border-radius:18px;font-size:16.5px;line-height:1.3;position:relative}
.m.me{align-self:flex-end;background:linear-gradient(160deg,#3d7dff,#2f62e8);border-bottom-right-radius:6px}
.m.th{align-self:flex-start;background:#1f2731;border-bottom-left-radius:6px}
.m .tm{font-size:11px;opacity:.7;margin-left:8px;float:right;margin-top:6px}
.seen{align-self:flex-end;font-size:12.5px;color:#8b97a5;margin-top:-2px;margin-right:4px}
.ty{align-self:flex-start;background:#1f2731;border-radius:18px;padding:12px 16px;display:flex;gap:5px}
.ty i{width:8px;height:8px;border-radius:50%;background:#8b97a5;display:block}
.ft{position:absolute;bottom:0;left:0;right:0;height:76px;display:flex;align-items:center;gap:10px;padding:0 14px;background:#10161d;border-top:1px solid #1d2630}
.in{flex:1;min-height:42px;border-radius:21px;background:#1a222c;padding:10px 16px;font-size:16px;color:#e9edf1}
.in.ph{color:#66727f}
.cur{display:inline-block;width:2px;height:18px;background:#4fa3ff;vertical-align:-3px;margin-left:1px}
.snd{width:42px;height:42px;border-radius:50%;background:#2f62e8;display:flex;align-items:center;justify-content:center;font-size:18px}
.blur{filter:blur(6px) brightness(.55)}
"""


def page(s):
    msgs = ''
    for m in s.get('msgs', []):
        if m.get('day'):
            msgs += f'<div class="day">{html.escape(m["day"])}</div>'; continue
        cls = 'me' if m.get('me') else 'th'
        msgs += f'<div class="m {cls}">{html.escape(m["t"])}<span class="tm">{m.get("time","")}</span></div>'
    if s.get('seen'):
        msgs += f'<div class="seen">{html.escape(s["seen"])}</div>'
    if s.get('typing'):
        msgs += '<div class="ty"><i></i><i style="opacity:.7"></i><i style="opacity:.45"></i></div>'
    inp = s.get('input', '')
    inner = html.escape(inp) + ('<span class="cur"></span>' if s.get('cursor') else '') if inp or s.get('cursor') else 'Xabar yozing…'
    phc = '' if inp or s.get('cursor') else ' ph'
    st = s.get('status', '')
    stc = ' on' if st.lower() in ('online', 'active now', 'onlayn') else ''
    t = s.get('title', 'Jasur')
    return f"""<html><head><meta charset="utf-8"><style>{CSS}</style></head><body><div class="wrap {'blur' if s.get('blur') else ''}">
<div class="sb"><span>{s.get('clock','21:47')}</span><span>▂▄▆ ᯤ 82%</span></div>
<div class="hd"><span class="bk">‹</span><div class="av">{html.escape(t[0])}</div><div><div class="nm">{html.escape(t)}</div><div class="st{stc}">{html.escape(st)}</div></div></div>
<div class="body">{msgs}</div>
<div class="ft"><div class="in{phc}">{inner}</div><div class="snd">➤</div></div></div></body></html>"""


def main():
    specs = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 540, 'height': 960}, device_scale_factor=2)
        for name, s in specs.items():
            pg.set_content(page(s)); pg.wait_for_timeout(150)
            pg.screenshot(path=f'{out}/{name}.png'); print(name)
        b.close()


if __name__ == '__main__':
    main()
