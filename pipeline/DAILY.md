# FactLab daily reel — runbook

Goal: every day one ~20–30 s Uzbek fact reel for Instagram **@thefactlab.daily**, voiced by ElevenLabs **Bekzod**, published automatically by Buffer at **20:00 Asia/Seoul**.

Fixed IDs
- ElevenLabs voice: `kGOig3GPePLxobJGHo2M` (Bekzod), model `eleven_v4`, `generations_count: 1` (never more — 429 / extra credits; never retry a generation call).
- Buffer organization: `6accf09480d8092d22a4b156` (timezone Asia/Seoul). Channel: `6accf680778b240e2fe7cd28` (thefactlab.daily, Instagram).
- Public video URL: `https://suyarovsindor200510-maker.github.io/factlab-media/videos/<ID>.mp4`

## Steps (ID = today's date in Seoul, YYYY-MM-DD)

1. **Pick a topic** not in `history.json` (rotate categories: animals, human body, space, ocean, history, food, technology, geography, plants, physics). Use only well-established facts you are confident about (no shaky numbers, no myths). Prefer WebSearch to double-check any number.
2. **Write `specs/<ID>.json`** in the format of `specs/2026-10-13.json`:
   - 6 scenes: `intro`, 4 facts, `outro`. Fact kinds: `count` (n, unit, repeat for n≤6), `percent` (n, unit), `vs` (a/b with emoji,label,v), `emoji` (emoji, orbit).
   - Uzbek Latin with plain apostrophe `'` (o', g'). Titles ≤ 13 chars, subs ≤ 45 chars, each scene `voice` one or two short sentences. Whole voice ≈ 18–28 s.
   - Pick an `accent` color that fits the topic. `caption` = Instagram text with emojis, question for comments, CTA, 8–12 hashtags.
3. **Voice:** `creative_generate_speech` with the scene `voice` texts joined by blank lines (`\n\n`), voice/model above, generations_count 1. Poll `creative_get_flow_run_status` until completed; take `content_url`.
4. **Fetch audio:** write `jobs/<ID>.json` = `{"audio_url": "<content_url>"}`, commit, push. The GitHub Action "Fetch audio" puts `audio/<ID>.mp3` in the repo within ~30 s. `git pull` until it exists (poll every 10 s, max 5 min). This sandbox cannot download storage.googleapis.com directly — always go through the Action.
5. **Build:** `python3 pipeline/make.py specs/<ID>.json audio/<ID>.mp3 /tmp/fl/<ID>` (≈3–6 min). Then Read `/tmp/fl/<ID>/sheet.jpg` and check: no overlapping text, emojis render, captions readable. Fix the spec and rebuild if needed.
   - If make.py says "only N pauses found": regenerate is NOT allowed; instead merge scenes in the spec so the count matches pauses+1, or lower `d=` in silencedetect.
6. **Publish files:** copy `video.mp4` → `videos/<ID>.mp4`, `cover.jpg` → `videos/<ID>.jpg`; `git rm jobs/<ID>.json`; append to `history.json` `{"id","topic","title"}`; commit + push.
7. **Wait for Pages:** poll `gh api repos/suyarovsindor200510-maker/factlab-media/deployments?per_page=1` then `.../deployments/<id>/statuses` until `state == "success"` for the new commit sha; then wait 30 s more.
8. **Schedule in Buffer:** `create_post` with channelId above, `schedulingType: "automatic"`, `mode: "customScheduled"`, `dueAt: "<ID>T20:00:00+09:00"` (if already past 19:55, use `shareNow`), `text` = spec caption, `assets: [{video:{url: <public url>}}]`, `metadata.instagram: {type:"reel", shouldShareToFeed:true}`.
9. Report in one short Uzbek message: topic, fact titles, Buffer post status.

If any step fails irrecoverably, do not post a broken video — report the failure instead.
