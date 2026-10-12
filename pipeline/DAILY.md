# FactLab daily reel — runbook (v2 "milliy story" format)

Goal: every day one 40–60 s Uzbek **discussion reel** for Instagram **@thefactlab.daily** in the style of @birfoiz_ / @shoshmang_:
relatable Uzbek family/social life topic, vivid comic illustrations, paper stickers, Bekzod voice, sound effects,
Uzbek-style music (doira/dutar), ending with a "1 yoki 2?" question so people comment. Published automatically by Buffer at **20:00 Asia/Seoul**.

Fixed IDs
- ElevenLabs voice `kGOig3GPePLxobJGHo2M` (Bekzod), model `eleven_v4`, `generations_count: 1` (never retry a generation call).
- Buffer org `6accf09480d8092d22a4b156` (Asia/Seoul), Instagram channel `6accf680778b240e2fe7cd28`.
- Canva carrier design (for full-res export): `DAHX0TkK-lI`, 5 pages 1080×1920, each with one image rect:
  p1 `PBRTYS8Q7ylWy85m-LBxkfVpCWRCh0d29`, p2 `PBsBlS4HhF2PvtBm-LBg16cqXM7csZZyW`, p3 `PBrfp44jZDRV4xLz-LBdNZygLCCwKGJZ3`,
  p4 `PBDj9l4yPWRG0CR9-LBmMYdRwC2w0HWQB`, p5 `PBTG3CXpCF2yKvtd-LBf37bJPFNV4Vny3`.
- Public URL: `https://suyarovsindor200510-maker.github.io/factlab-media/videos/<ID>.mp4`

## 0. Skip check
ID = today's date in Seoul (YYYY-MM-DD). If `history.json` has an entry whose id starts with today's ID, report "already done" and stop.

## 1. Topic (most important for reach)
- Milliy, everyday Uzbek life that everyone has an opinion on: family (farzandlar, qaynona, kelin), to'y/marosimlar, qo'shnilar, mahalla,
  pul/qarz/kredit, uy qurish, maktab/universitet, ish/oylik, mehmondorchilik, dasturxon odobi, avlodlar farqi, chet elda ishlash, telefon/ijtimoiy tarmoq.
- Must end in a clear choice: "1 — …, 2 — …" (optionally 3). Respectful humour only: no politics, no mocking religion, regions or ethnic groups, no real people.
- Not already in `history.json` (check topic + category; rotate categories).
- Any number shown must be true or clearly marked "misol" (example). Verify facts with WebSearch.

## 2. Script → voice
- 5–6 paragraphs (= scenes), 40–60 s total, Uzbek Latin with plain apostrophe `'`. Numbers written as words in the voice text.
- Scene 1 = hook question; middle = relatable story / numbers; last = "Xo'sh, siz qaysi birisiz? Birinchi — …. Ikkinchi — …. Izohda raqamini yozing!"
- `creative_generate_speech` with paragraphs joined by blank lines. Poll until done → `content_url`, `flow_id`, `node_id`.
- `creative_transcribe_audio` (model eleven_scribe_v1, same flow_id, connect_from [node_id]) → poll → `words_download_url` (free).

## 3. Images (Canva, one request at a time — parallel requests fail with "quota_exceeded")
- `generate-image`, aspectRatio `PORTRAIT_9_16`, 5 images. Prompt template:
  "Vibrant bold comic-book style digital illustration, thick clean black outlines, rich saturated colors, crisp detail, expressive faces. <SCENE with Uzbek people, Uzbek clothing (doppi, atlas, headscarf), Uzbek interiors (suzani, kurpacha, dasturxon) or places>. Vertical composition with clear empty space at the top third. No text, no letters, no logos."
  Keep the same character descriptions across scenes. The last image = two characters side by side on a plain bright background (for the 1/2 choice).
- Poll `get-generate-image-job` until SUCCESS; look at each preview; regenerate if broken (extra limbs, text, wrong culture).
- `read-design DAHX0TkK-lI open_transaction:true` → `edit-design` `update_fill` each page's rect with the new media ids → `commit` →
  `export-design` png 1080×1920 → 5 URLs (they are on export-download.canva.com).

## 4. Fetch files through GitHub Actions (this sandbox cannot download from GCS/Canva)
Write `jobs/<ID>.json`:
`{"audio_url": "<content_url>", "files": [{"url": "<words_download_url>", "path": "words/<ID>.json"}, {"url": "<png1>", "path": "assets/<ID>/1.png"}, …]}`
commit + push, then `git pull` every 10 s until `audio/<ID>.mp3`, `words/<ID>.json` and all pngs exist (log: `assets/_fetch.log`).

## 5. Spec → build
- Write `specs/<ID>.json` in the format of `specs/toy-daftari.json` (format "story"). Scene kinds: `image`, `card` (rows with counting numbers),
  `bigstat` (one big number), `choice` (badges 1/2 at `a`/`b` = [x,y] over heads). Frame is 540×960 CSS px; keep stickers at y 80–620
  (captions sit near y 700). Sticker styles: yellow, paper, red, dark, teal; optional `"sfx"` per sticker (pop, stamp, kaching, ding, fail, boing, riser, shutter).
- Timing: `at` = seconds after the scene's first word. From words json: `at ≈ (word.start − first_word_of_scene.start) / 1.06`.
- Music: ALWAYS `"uzmusic": "bazm"` (owner chose the bazm style — doira, dutar, rubob), `music_vol` 0.45. Do NOT use other styles or the NCS phonk/EDM tracks. Generator: pipeline/uzmusic.py (a new melody every seed).
- `python3 pipeline/make.py specs/<ID>.json audio/<ID>.mp3 /tmp/fl/<ID> words/<ID>.json` (≈4–7 min).
- Check: extract 6–7 frames (one per scene, after its stickers appear) and Read them — no overlapping stickers, faces not covered,
  captions readable. Fix the spec and rebuild if needed.

## 6. Publish
- `videos/<ID>.mp4` ← video.mp4, `videos/<ID>.jpg` ← cover.jpg; `git rm jobs/<ID>.json`; append to `history.json`
  `{"id","topic","category","title","format":"story","music"}`; commit + push; wait until the GitHub Pages deployment for that commit is `success`.
- Buffer `create_post`: channel above, `schedulingType: automatic`, `mode: customScheduled`, `dueAt: "<ID>T20:00:00+09:00"`
  (if already past 19:55 → `shareNow`), `metadata.instagram {type:"reel", shouldShareToFeed:true}`, video asset with `thumbnailOffset` = cover moment (ms).
- Caption: hook line, 3–6 short lines of story, the 1️⃣/2️⃣ question, "👇 Izohda raqamini yozing va … belgilang 😄",
  10–13 hashtags (#ozbekcha #reelsuz #thefactlab + topic tags).

## Fallback
If Canva image generation fails repeatedly, build the old fact format instead (`specs/2026-10-13.json` style, kinds intro/count/percent/emoji/outro,
command without words.json) so a post still goes out. Never post a broken video — report the failure instead.
