# FactLab reel runbook (v3 — every 3 hours, varied topics, dialogue voices)

Goal: every 3 hours one 30–50 s Uzbek reel for Instagram **@thefactlab.daily** (owner Sindorbek, speaks Uzbek), published immediately via Buffer.
Style: @birfoiz_ / @shoshmang_ — vivid comic illustrations, paper stickers, sound effects, "1 yoki 2? Izohda yozing" ending.
Owner gave full permission to create and post without asking. Never post a broken, offensive or factually wrong video.

## Fixed IDs
- ElevenLabs model `eleven_v4`, `generations_count: 1`, never repeat a generation call (a failed one is not charged).
  Voices: Bekzod (male) `kGOig3GPePLxobJGHo2M`; Uzbek female: Dilnoza `O72h9AUwisM6Zj4He72B` (cheerful, default),
  Zilola `cyPun3bl9MxcpLBX6pT0`, Malika `VTN9ql0D5MshokKncKAy` (calm), Gulnora `6Fkh9WgMXOqBcOWxX91f`, Nodira `132QLQIkg1RJGmpicuhR`, Shahnoza `eggZu1Ffe4if51TKev2v`.
- Buffer org `6accf09480d8092d22a4b156` (Asia/Seoul), Instagram channel `6accf680778b240e2fe7cd28`.
- Canva carrier design `DAHX0TkK-lI` (5 pages 1080×1920). Image rect locators:
  p1 `PBRTYS8Q7ylWy85m-LBxkfVpCWRCh0d29`, p2 `PBsBlS4HhF2PvtBm-LBg16cqXM7csZZyW`, p3 `PBrfp44jZDRV4xLz-LBdNZygLCCwKGJZ3`,
  p4 `PBDj9l4yPWRG0CR9-LBmMYdRwC2w0HWQB`, p5 `PBTG3CXpCF2yKvtd-LBf37bJPFNV4Vny3`.
- Public video URL: `https://suyarovsindor200510-maker.github.io/factlab-media/videos/<ID>.mp4`

## 0. ID + skip check
ID = `YYYY-MM-DD-<slug>` using Seoul date (e.g. `2026-10-13-tana`). Read `history.json`: do not repeat a topic from the last 30 entries; rotate the type.

## 1. Topic types (rotate; never two of the same type in a row — check the last history entry's `type`)
1. **milliy** — everyday Uzbek life discussion (family, qaynona, to'y, mahalla, pul, kasb, mehmondorchilik…); ends with 1/2 choice.
2. **tana** — amazing human-body facts (heart, blood vessels, brain, bones, senses, sleep…); cute non-gory illustrations; ends with "qaysi fakt hayratga soldi? 1/2".
3. **fakt** — other amazing facts (space, animals, nature, history, tech); same format.
4. **dialog** — any of the above told as a short dialogue Bekzod ↔ female voice (can be a funny family scene).
Verify every fact with WebSearch (numbers must be true or marked "misol"). No politics, no mocking religion/regions/people.
Every reel should include a female voice or dialogue (at least 1 female line) — vary female voices over time.

## 2. Script → voice (dialogue = several short parts)
- 4–5 scenes, 30–50 s. Each scene = 1–3 short lines. Numbers written as words in the voice text. Uzbek Latin with plain `'`.
- One `creative_generate_speech` call per line (voice = speaker). Max 4 calls at once (more → concurrency retry). Each creates its own flow.
- Poll `creative_get_flow_run_status` (flow_id + session_ids) → `content_url` (valid 2 h — fetch quickly).
- Words: `creative_transcribe_audio` (same flow_id, connect_from [node_id]) → `words_download_url`. **If this tool errors** ("missing resultType"),
  use `python3 pipeline/estwords.py part.mp3 "<text>" part.words.json` (estimates timing from text + duration; good enough for stickers).
- Join: `python3 pipeline/joinvoice.py audio/<ID>.mp3 words/<ID>.json p1.mp3 p1.words.json p2.mp3 p2.words.json …` (0.18 s gap between lines).

## 3. Images (Canva, ONE request at a time, ~40 s each)
- `generate-image` PORTRAIT_9_16 — **NOTE: results are SQUARE (1:1)**. Prompt template:
  "Vibrant bold comic-book style digital illustration, ultra sharp focus, highly detailed, crisp clean thick black outlines, rich saturated colors, anatomically correct faces and hands, no blur. <SCENE>. Subjects fully visible with margin around, centered. No text, no letters, no logos."
  Poll `get-generate-image-job` (param `jobId`) until SUCCESS; reject cut-off bodies / extra fingers / text; regenerate that one.
- Carrier: `read-design` open_transaction → per page: `update_fill` (asset_id = media id), then `resize_element` 1080×1080, `position_element` top 420 left 0,
  `crop_media` top 0 left 0 w 1080 h 1080 (keeps the whole square sharp at native size instead of a 1.9× upscaled crop) → `commit` → `export-design` png 1080×1920 (pro).
- After fetching run `python3 pipeline/prep_img.py assets/<ID>` (sharp square in the middle, blurred copy behind; originals kept as raw_N.png).
  Frame layout: image occupies y≈210–750 (CSS px of 540×960); stickers go at y 70–180 (top bar) and y 800–860 (bottom bar).

## 4. Fetch files (sandbox cannot download from GCS/Canva)
`python3 pipeline/imgjob.py <ID> < urls.txt` → jobs/<ID>-img.json; voice parts: `jobs/<ID>-voice.json` = `{"files":[{"url","path":"assets/<ID>/voice/pN.mp3"},…]}`.
Commit + push; `git pull --rebase` until files exist (Action "Fetch audio"; log `assets/_fetch.log`). Do it right after generating (URLs expire).

## 5. Spec → build
- `specs/<ID>.json` like `specs/2026-10-13-tana.json` (format "story", scenes `image`/`choice`, stickers with `w` keyword anchors, `sfx`).
- `"uzmusic": "bazm"`, `music_vol` 0.3–0.45 (0 = no music is fine). No NCS tracks, no credit line.
- `python3 pipeline/make.py specs/<ID>.json audio/<ID>.mp3 <outdir> words/<ID>.json` in background (nohup, 4–7 min).
- Check frames (ffmpeg hstack of one frame per scene, taken ≥1.5 s after scene start): images sharp, stickers not overlapping faces/badges, text readable.

## 6. Publish (immediately)
- `videos/<ID>.mp4` + `.jpg`; delete jobs files; append to `history.json` `{"id","topic","category","type","title","format":"story","music"}`; commit + push.
- Wait until the "pages build and deployment" run for that commit is `completed success` (`gh api repos/.../actions/runs?per_page=1`), else Buffer says "Video could not be read".
- Buffer `create_post`: `schedulingType automatic`, `mode shareNow`, `metadata.instagram {type:"reel", shouldShareToFeed:true}`, video asset + `thumbnailOffset`.
- Caption: hook, 3–5 short lines, 1️⃣/2️⃣ question, "👇 Izohda raqamini yozing …", 10–13 hashtags (#ozbekcha #reelsuz #thefactlab + topic).

## Failure rules
Image or voice generation fails twice → skip this slot, report why. ElevenLabs "Free Tier access disabled" / quota → report, do not loop.

## Engine v3.1 (motion)
story.html now has: alternating Ken-Burns camera per scene (zoom up to 1.14), 110 bpm beat pulse on the image, idle wobble on stickers, confetti burst when a sticker lands (`"nofx":true` on a sticker disables it). No config needed.
Epidemic Sound download is FORBIDDEN (no subscription) → keep own `uzmusic` generator. Motion/HyperFrames are paid/unsuitable.
