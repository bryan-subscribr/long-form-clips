---
description: Turn a YouTube link into ready-to-post vertical Shorts (propose → approve → render)
argument-hint: <youtube-url>
---

You are running the **Short-Form Repurposing** workflow: turn one long-form YouTube
video into several 9:16 vertical Shorts, each edited to feel native to YouTube Shorts,
plus ready-to-post captions and pinned comments.

You (Claude) are the brain — you do the clip SELECTION. The scripts do the muscle
(download, transcribe, cut, crop, caption). No API key is needed.

**Skill directory:** `.claude/commands/marketing/short-form-pipeline`
Refer to it as `SKILL` below. The YouTube URL is: `$ARGUMENTS`
(if empty, ask the user for the link before continuing).

## Steps — follow in order

1. **Check deps.** Run `bash SKILL/scripts/doctor.sh`. If anything is missing, show
   the user the install commands it prints and STOP.

2. **Read the principles.** Read `SKILL/PRINCIPLES.md` so your selection follows them.

3. **Fetch.** Run `python3 SKILL/scripts/fetch.py "<URL>"`. Capture the `WORKDIR=...`
   value from the output. If `TRANSCRIPT=NONE`, tell the user the video has no
   captions and stop (v1 needs them for selection).

4. **Select clips.** Read `<WORKDIR>/transcript.txt`. Pick **4–6** of the strongest
   standalone moments per the principles:
   - Start ON the shock / question / claim — NO preamble ("the best hooks don't have a hook").
   - The hook should shock, set a clear expectation, and open a loop (a reason to watch to the end).
   - Curiosity = specific about WHAT happens, unknown HOW.
   - ONE complete idea per clip; end on a complete thought.
   - **Exclude** sponsor reads, subscribe/like asks, and self-promo entirely.
   - Length 20–58s (sweet spot 25–45s).
   For each clip capture: `start`, `end` (MM:SS), `title` (< 40 chars, complements the
   clip, no clickbait), `hook_line`, `open_loop`, `caption` (1–2 sentences + 3–5
   hashtags, ready to post), `pinned_comment` (sparks replies, never offensive).

5. **Propose & wait.** Show the user a table of the proposed clips (title · window ·
   hook · why). ASK them to approve, drop, or edit. **Do not render until they approve.**

6. **Render.** Write the approved clips as a JSON array to `<WORKDIR>/clips.json`, then run:
   ```
   python3 SKILL/scripts/render_clips.py \
     --workdir <WORKDIR> --clips <WORKDIR>/clips.json \
     --out "~/Downloads/<slug>-shorts"
   ```
   where `<slug>` is a short kebab-case version of the video title.

7. **Report.** Tell the user the output folder, list each clip with its caption and
   pinned comment (from the generated `METADATA.md`), and confirm the clips are
   1080×1920. Offer to cut more or adjust selections.

## Notes
- Captions are word-level from Whisper (accurate + synced) and CONTINUOUS (always on
  screen, current word highlighted).
- Keep the whole run in one folder under `~/Downloads`; never overwrite a previous
  video's folder.
- Want horizontal 16:9 long-form clips instead? Use `/long-form-clips <url>` (same
  skill, `render_clips.py --aspect 16:9`).
