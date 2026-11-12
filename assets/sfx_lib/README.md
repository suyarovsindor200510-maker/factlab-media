# SFX library

User-supplied sound effects for @thefactlab.daily reels. One folder per pack, all files 48 kHz stereo 16-bit wav,
trimmed, faded, peak −1 dBFS. `index.json` lists every sound with duration, loudness and suggested use.

- Add a pack: `python3 pipeline/sfx_ingest.py PACK_VIDEO.mp4 <pack> "Label1,Label2,..." --use "label1=when;..."`
- Use in a reel: `from sfx_lib import get, bed` (see `pipeline/sfx_lib.py`)
- List: `python3 pipeline/sfx_lib.py`

| pack | sounds |
|---|---|
| editwithfahi | hook, light, whoosh, typing, click, pop_in, breaking, money |
| subhangfx82 | low_rise, apply_keyboard, gear_click, riser, glass_shine, inertia_ramp |

Source files come from the channel owner; use them only in our own reels.
