# FactLab reel runbook (v4 — every 4 hours, owner's own voice narrates)

Goal: every 3 hours one 30–50 s Uzbek reel for Instagram **@thefactlab.daily** (owner Sindorbek, speaks Uzbek), published immediately via Buffer.
Style: @birfoiz_ / @shoshmang_ — vivid comic illustrations, paper stickers, sound effects, "1 yoki 2? Izohda yozing" ending.
Owner gave full permission to create and post without asking. Never post a broken, offensive or factually wrong video.

## Fixed IDs
- ElevenLabs (Creator plan since 13 Oct) model `eleven_v4`, `generations_count: 1`, never repeat a generation call (a failed one is not charged).
  **NARRATOR = owner's cloned voice "Sindorbek" `7qE9SJG22POpFvegZOWQ`** — use it for all narration and the main male role (~1 credit/char, ≈100 credits per line).
  Other voices only for extra characters: Bekzod (male) `kGOig3GPePLxobJGHo2M`; Uzbek female: Dilnoza `O72h9AUwisM6Zj4He72B` (cheerful, default),
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

## v4 — "birfoiz / shoshmang" style (learned from two reference reels, 13 Oct)
What makes those reels work (copy this, not just the look):
1. **Story, not a list.** One relatable everyday pain told as a mini-story with a twist ending
   (e.g. "taksistning bir kuni", "qaysi kurs bolani odam qiladi"). Facts topics → still frame as a story/mission.
2. **One recurring hero.** Generate a character reference first (Canva generate-image, full body, plain bg),
   then pass its media id in `imageReferences` for EVERY scene image → same face/clothes in all scenes.
3. **Many shots.** 8–12 images per 40–60 s (≈4 s each). A scene may be voiceless: `"silent": 2.8` (no `voice`) —
   a visual gag with sticker + sfx carried by music.
4. **HUD that changes every scene** (meter + clock): spec `"hud": {"label":"PUL"|"SABR"|"VAQT", "levels":[...per scene], "clock":[...]}`.
   Big drops (≥10) make the meter bounce. Keep stickers at y ≥ 110 (HUD sits at y 40–76).
5. **Header stickers** `style:"head"` with highlighted words in `[brackets]`, `\n` for 2 lines; bottom stickers for numbers (red = loss).
6. **Ending = comment + share bait**: typed input box `{"type":true,"style":"input","t":"Somsaga :)"}` +
   "… do'stingizga yuboring". One-word comment asks get more comments than 1/2.
7. **Music**: energetic 125–145 bpm, continuous from frame 1 → `"uzmusic":"shox"` (128 bpm, four-on-floor + doira), music_vol 0.4–0.45.
Example spec: `specs/2026-10-13-talaba.json`.

## Blockers (13 Oct 16:00)
- ElevenLabs: "Free Tier access has been disabled" → no new voice until the owner buys a paid plan (Starter $6 / Creator $22).
  If voice generation fails with this message: do not retry, skip the slot, report.
- Adobe connector cannot read files from github.io or Canva URLs and the sandbox cannot upload to Adobe → no Adobe outpaint for now.
- Epidemic Sound downloads are FORBIDDEN without a subscription.

## Style library — pick the style by topic (owner's rule, 13 Oct)
| Topic | Style | Reference |
|---|---|---|
| Uzbek social problem / everyday life (oila, to'y, talaba, kurs, taksi, pul…) | **STORY**: one hero, "bir kuni" arc, HUD meter+clock, 8–12 shots, silent gags, twist ending, one-word comment + share bait | v4 section, specs/2026-10-13-talaba.json |
| Amazing facts (tana, kosmos, hayvonlar, tarix, texnika) | **FACT** (provisional until owner sends references): strong hook question, numbered countdown "5 → 1", one big number per fact (bigstat/card scenes), comparison visuals (X = N ta Y), 1/2 choice ending | specs/2026-10-13-tana.json, kosmos |
New styles are added here when the owner sends reference reels: analyse (frames every 2–4 s, scene count, text layout, HUD/graphics, tempo, ending), write the recipe, then build it.

## Budget (Creator = 121 000 credits/month)
6 reels/day × 30 = 180 reels → ≤ 650 credits per reel. Keep total voice text ≤ ~600 characters per reel
(silent beats carry the rest). The free-tier block of 13 Oct is lifted by the paid plan.

## Reference analysis #2 (5 reels the owner liked, 13 Oct 20:17)
| # | Channel / topic | Look | Shots | Audio |
|---|---|---|---|---|
| 1 | "Nimaga bunaqa" — El Niño & Uzbek rain | sepia antique map + 3D globe, ONE continuous canvas, camera flies/zooms between places; thermometer HUD, red data overlays, charts, "Toshkentdan 3 209 km" labels | 0 hard cuts, ~96 s | calm narrator, deep sub-boom hits on reveals, soft pings, quiet bed (125 bpm) |
| 4 | "Nimaga bunaqa" — meat price | vintage engraving characters on parchment, chalkboard + paper charts hanging on strings, bar/line graphs animate, red stamps "-73%" | 0 cuts, ~100 s | voice-led, almost no music between phrases |
| 2 | kids-clothes-by-kilo story (ad) | warm storybook illustration, cutout characters, torn-paper headers (yellow/red/green), chalkboard explainers, map pin outro | ~25 scenes / 79 s | continuous bass-heavy beat 144 bpm |
| 3 | father-son wedding story | semi-realistic characters cut-out over scenes, 2-line header (yellow line + white line) at top, word captions bottom, moral ending | ~12 scenes / 58 s | continuous emotional beat 144 bpm |
| 5 | AI-tools explainer (host avatar) | clean white bg, 3D cartoon host at bottom, "BIRINCHISI 1/3" progress, red accent, phone/app cards, VS cards, "kommentariyada yozing" | 40 s | voice + light sfx, no music under speech |
Rules learned:
- **FACT / explainer** → "Nimaga bunaqa" recipe: one consistent visual world (map / parchment), numbers as big labeled overlays, charts that draw themselves, sub-boom on each reveal, calm voice, music low or none, sources line ("Manba: …") small at the bottom.
- **LIST / advice** (top-N, "5 ta …") → avatar/host or hero couple + "1/5" progress HUD, two-line headers, numbered stickers, ending with a comment question and "… ga yuboring".
- **STORY / social** → talaba recipe (above).
- **Religious topics** → respectful: no instrumental music (music_vol 0), soft sfx only, cite sura/hadith source on screen, no mockery, no depiction of prophets.
- Loudness of all refs ≈ −14 LUFS (we use −13; fine).

## Instagram algorithm rules (researched 13 Oct; Mosseri's stated signals)
Ranking = watch time (esp. first 3 s + completion + replays), **sends per reach** (strongest for non-followers), likes per reach. Original content only.
Our own stats (first posts): avg watch 7.9 s on ~40 s reels → people leave early; 24 shares; 0 comments.
So every reel MUST:
1. Hook in the first 1.5 s: on-screen question/shock number + motion + sound hit before any intro. Never start with "Assalomu alaykum" / slow setup.
2. Be 20–35 s (shorter = higher completion). Cut filler lines.
3. Give a reason to SEND: "… ga yuboring" (mother, wife, classmate) — sends matter more than likes.
4. Comment bait that is easy: one word / one number, asked on screen early (not only at the end), plus pin-able first comment.
5. Caption = searchable Uzbek keywords in the first line (Instagram search reads caption text more than hashtags); 3–5 hashtags are enough.
6. Ending loops back to the start (seamless replay) when possible.

## v5 kadr (2026-10-14) — bo'sh xira bantlar yo'q
Foydalanuvchi shikoyati: kvadrat rasm o'rtada, tepa/pastda katta xira bo'sh joy — feedda yomon ko'rinadi.
prep_img.py endi kvadratni 1560px ga kattalashtiradi (markaziy 1080 qoladi), y=180..1740 — kadrning ~81% rasm.
Canva promptida asosiy obyektlarni MARKAZGA qo'yishni so'ra (yon tomonlar ~14% dan kesiladi).
