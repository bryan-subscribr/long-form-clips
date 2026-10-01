---
description: Break one long YouTube video into standalone horizontal 16:9 clips, 4–5 min or longer each (propose → approve → render → deliver)
argument-hint: <youtube-url> [clip-count]
---

You are running the **Long-Form Clips** workflow: turn one 20–100 min YouTube video
into several **horizontal 16:9 clips**, each **4–5 minutes or longer** (2–3 min only
when the idea is a natural unit, hard cap 20), that stand alone on the speaker's
channel, plus titles, thumbnail text, descriptions, and pinned comments.

You (Claude) are the brain — you do the clip SELECTION. The scripts do the muscle
(download, transcribe, cut, caption). No API key is needed.

**Model: run this on Sonnet.** Before anything else, if the session is on a bigger
model, tell the user to switch (`/model sonnet`) or continue only if they say so. The
work is well-specified writing with a mechanical checker behind it; Sonnet holds and
costs a fifth. For a batch of videos, spawn one `general-purpose` agent per video with
`model: sonnet` and a self-contained prompt. **Never use `fork` for a batch** — a fork
inherits the whole conversation and the parent model; four forks on a long session
blew through an org spend limit in Sep 2026. Fresh agents start empty.

**Skill directory:** `.claude/commands/marketing/short-form-pipeline` — refer to it as
`SKILL` below. **Packaging skill:** `.claude/skills/clip-packaging` (ships in this repo;
refer to it as `PKG`). Arguments: `$ARGUMENTS` — first token is the YouTube URL,
optional second token is a target clip count. If the URL is empty, ask for it before
continuing. If no count is given, let the content decide (20 min → 2–3, 35 min → 3–6,
75–100 min → 6–13).

## Steps — follow in order

1. **Check deps.** Run `bash SKILL/scripts/doctor.sh` (macOS, and Windows — Claude Code's shell
   there is Git Bash). Its last lines are `PY=…`, `ENCODER=…`, `X264_PRESET=…`, `READY=…`.
   **Use that `PY` value wherever this file says `"<PY>"`** — never a bare `python3`, which on
   Windows is usually the Microsoft Store stub — and the `ENCODER` / `X264_PRESET` values in
   step 6. If `READY=no`, show the user the FAIL lines and point them at the matching section
   of `SKILL/TEAM-SETUP.md`, then STOP.

2. **Read the rules.** Read `SKILL/PRINCIPLES.md` — especially the section
   **"Horizontal (Long-Form Clip) Mode"**. Selection follows those rules exactly.

3. **Fetch.** Run `"<PY>" SKILL/scripts/fetch.py "<URL>"`. Capture the `WORKDIR=...`
   value from the output. If `TRANSCRIPT=NONE`, tell the user the video has no
   captions and stop.

4. **Select clips.** Read `<WORKDIR>/transcript.txt`. Pick the strongest standalone
   segments. Every clip must pass the **five-point standalone test**:
   - Cold viewer understands it with zero long-form context.
   - Starts ON the shock / question / claim — no host intro, no wind-up.
   - One complete arc: setup → tension → payoff. One idea per clip.
   - Ends on the payoff or punchline, on a complete sentence.
   - No sponsor reads, subscribe asks, self-promo, or housekeeping inside the window.
   Constraints: **target 4–5 min or longer** (one throughline, several beats).
   A 2–3 min clip only occasionally, when the idea is a natural unit. Hard cap 20
   (the renderer refuses longer windows; YouTube needs a verified channel above 15).
   Prefer merging adjacent beats the host bridges over splitting them. Under ~90s →
   not a horizontal clip. **Zero overlap** between clips. Cut on sentence boundaries.
   For each clip capture: `start`, `end` (MM:SS), `hook_line`, `open_loop`,
   `caption` (1-sentence payoff + 3–5 hashtags), `pinned_comment` (sparks replies,
   never offensive). Title and thumbnail text come from the next step.

4b. **Package each clip with the `clip-packaging` skill.** Read `PKG/SKILL.md` (or
   load it via the Skill tool) and follow its run order in **batch mode** over the
   selected clips: classify format → mine the seven raw materials from each clip's
   transcript window → 5 titles / 5 thumbs → 3×3 pair grid → three ranked packages
   per clip. If the speaker is not Hormozi-class authority, read its
   `speaker-adaptation.md` first and pick the register row. Batch rules: no title
   archetype above 40% of the batch, no repeated thumb word across the batch.
   Take Package 1 of each clip as `title` and `thumbnail_text` (keep the
   `**accent**` marker), record `thumb_line` (the spoken line + timestamp),
   `thumb_frame_at` (absolute MM:SS of that spoken line), `thumb_side`
   (`left`/`right`/`any` — where the speaker sits in the two-shot) and, on any
   two-person show, `thumb_ref` (path to one clean frame of the speaker — grab it
   with ffmpeg from a moment you know is their close-up and LOOK at it). Optional per
   clip: `thumb_crop_bottom` (e.g. `0.15`) when the source has burned-in captions or
   a sponsor banner; `thumb_ref_min` to tighten identity matching if a host leaks in.
   **Language:** titles, thumbnail text, hooks, captions and pinned comments are written in
   the speaker's language (the transcript's), whatever language the operator writes to you in.
   Gate every pair against its own clip window:
   ```
   "<PY>" PKG/scripts/check_package.py \
     --title "<title>" --thumb "<thumb>" --transcript "<WORKDIR>/transcript.txt" \
     --start <start> --end <end> --thumb-line "<thumb_line>" --ban "<speaker's name, comma-separated>"
   ```
   Exit code must be 0: it fails when the thumb line is not spoken inside the window, when
   the title names the speaker, overlaps the thumb, or breaks the length/number rules.
   Fix and re-run until it is. Then reread each title against
   the **"plain beats clever"** rules in `PRINCIPLES.md`: the clip's own words, first
   person on the speaker's own channel, every number literally true of the clip.

5. **Propose & wait.** Show a table: title · window · length · hook · thumbnail text ·
   why it stands alone. ASK the user to approve, drop, or edit. **Do not render
   until they approve.** Captions default OFF for horizontal clips; ask only if the
   user has not said. Ask once for the channel's fixed description boilerplate and
   save it as `<out>/CHANNEL_DESCRIPTION.txt`.

6. **Render.** Write the approved clips as a JSON array to `<WORKDIR>/clips.json`, then:
   ```
   "<PY>" SKILL/scripts/render_clips.py \
     --workdir "<WORKDIR>" --clips "<WORKDIR>/clips.json" \
     --out "~/Downloads/<slug>-clips" --aspect 16:9 --no-captions \
     --encoder <ENCODER> --x264-preset <X264_PRESET>
   ```
   where `<slug>` is a short kebab-case version of the video title and `<ENCODER>` /
   `<X264_PRESET>` come from step 1 (a hardware encoder renders a 10-min clip in about a
   minute; libx264 takes ~5 min at `medium`, about half at `veryfast`). If a hardware
   encoder fails mid-run the renderer retries that clip on libx264 by itself. It refuses
   the whole batch up front if any window is over 20 min. **Run it in the
   background** or in chunks (`--start-index N` with a partial clips.json): a long
   source will outlast a foreground tool timeout. `clips_result.json` is saved after
   every clip, so a killed run loses nothing already rendered — rerun with the
   remaining clips and the same `--out`.

6b. **Review thumb frames.** The renderer picked each `*.thumb-frame.jpg` from a
   ±15 s window (composed face, eyes open, mouth still, close-up, correct speaker)
   and wrote `*.thumb-candidates.jpg`. **Read every contact sheet with the Read
   tool.** If the chosen frame is mid-word, mid-gesture, or the wrong person, pick
   another candidate from that sheet:
   ```
   "<PY>" SKILL/scripts/pick_thumb_frame.py "<WORKDIR>/source.mp4" --at <thumb_frame_at> \
     --cand-dir "<WORKDIR>/thumbcands/<NN>" --pick <N> --out "<clip>.thumb-frame.jpg"
   ```
   If none of the candidates work, rescan wider with the full flag set, then pick:
   ```
   "<PY>" SKILL/scripts/pick_thumb_frame.py "<WORKDIR>/source.mp4" --at <thumb_frame_at> \
     --side <left|right|any> --ref <thumb_ref> [--ref-min 0.9] [--crop-bottom 0.15] \
     --window 25 --top 9 --out <clip>.thumb-frame.jpg \
     --sheet "<clip>.thumb-candidates.jpg" --cand-dir "<WORKDIR>/thumbcands/re<NN>"
   ```

6c. **Build the delivery set.**
   ```
   "<PY>" SKILL/scripts/finalize_delivery.py "<out>" --source-url "<URL>" \
     --source-title "<title>" --description-file "<out>/CHANNEL_DESCRIPTION.txt" \
     --workdir "<WORKDIR>"
   ```
   Every clip ends up as `.mp4` + `.thumb.jpg` + `.srt` (captions timed to the clip,
   upload in YouTube Studio → Subtitles → Upload file, With timing) + `.txt` (title,
   thumb text, description, pinned comment, source window, timed transcript, the same
   captions inline) + `.thumb-frame.jpg`, plus `README.md`. `--workdir` is what makes
   the captions happen: it points at the fetch directory holding the source VTT.
   Then **Read every final `*.thumb.jpg`** once. Heuristics rank, eyes decide.

7. **Report.** Tell the user the output folder, list each clip with its title,
   thumbnail text and length (from `README.md`), point at the thumbnails, and
   confirm the clips are 1920×1080. Offer to cut more, adjust, or swap to Package
   2/3 for any clip. Titles get one more read against the "plain beats clever"
   rule in `PRINCIPLES.md` before you send.

## Notes
- Horizontal clips are **not cropped** — source is letterboxed to 1920×1080 if needed.
- Captions (when on) are Whisper word-level, bottom-aligned, 3-word continuous highlight.
  Whisper is only imported when captions are on.
- Clips longer than 20 min are refused before anything renders — split them
  (`--allow-truncate` cuts them at 20:00 instead, mid-sentence; avoid it).
- Every path goes in double quotes: Windows user folders and this repo's own location can
  contain spaces, and Git Bash drops unquoted backslashes.
- Team setup (deps, first run) is in `SKILL/TEAM-SETUP.md`.
- Keep each run in its own folder under `~/Downloads`; never overwrite a previous
  video's folder.
