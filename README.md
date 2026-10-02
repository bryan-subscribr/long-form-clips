# long-form-clips

Turn one long YouTube video (20–100 min) into standalone horizontal clips of 4–5 minutes or
longer, each delivered with a thumbnail, title, description and pinned comment. Built as a
[Claude Code](https://claude.com/claude-code) workflow: Claude reads the whole transcript and
picks the clips, small Python scripts do the download, cutting, thumbnail-frame picking and
delivery. No API key needed beyond your Claude Code subscription.

Titles and thumbnail text follow a system measured on 2,795 clips from Alex Hormozi's
[@MoreMozi](https://www.youtube.com/@MoreMozi) channel: **title = the viewer's situation,
thumbnail text = the speaker's spoken payoff, zero word overlap**.

## Quick start

macOS:

```bash
brew install yt-dlp ffmpeg deno python@3.12
cd ~                     # not Documents/Desktop: iCloud offloads files and runs hang
git clone https://github.com/bryan-subscribr/long-form-clips.git
cd long-form-clips
python3 -m venv .venv
.venv/bin/pip install -r .claude/commands/marketing/short-form-pipeline/requirements.txt
bash .claude/commands/marketing/short-form-pipeline/scripts/doctor.sh
```

Windows: the same in PowerShell with `winget install Python.Python.3.12 Git.Git Gyan.FFmpeg
yt-dlp.yt-dlp DenoLand.Deno` — the exact steps are in
[`TEAM-SETUP.md`](.claude/commands/marketing/short-form-pipeline/TEAM-SETUP.md#windows-10--11).
Doctor must end with `READY=yes`; it also names the fastest video encoder the machine has.

Open Claude Code in this folder, switch to Sonnet (`/model sonnet` — the workflow is
tuned for it, about $1–2 per 90-minute video), and run:

```
/long-form-clips https://www.youtube.com/watch?v=VIDEO_ID
```

Flow: download + transcript → Claude proposes clips with titles and thumbnail text →
**you approve** → render 1920×1080 → Claude reviews every thumbnail contact sheet →
`~/Downloads/<slug>-clips/` with, per clip: `.mp4`, `.thumb.jpg`, `.srt` (captions timed to
the clip, ready for YouTube Studio → Subtitles → Upload file), `.txt` (title, thumbnail text,
description, pinned comment, source link, timed transcript), `.thumb-frame.jpg`,
`.thumb-candidates.jpg`.

Vertical Shorts instead: `/short-form-repurposing <url>` (needs `pip install openai-whisper`).

## What is in here

| Path | What |
|---|---|
| `.claude/commands/long-form-clips.md` | The horizontal-clip workflow Claude follows |
| `.claude/commands/short-form-repurposing.md` | The vertical Shorts workflow |
| `.claude/commands/marketing/short-form-pipeline/` | Scripts: fetch, render, thumb-frame picker, delivery, tests. `PRINCIPLES.md` has the selection and title rules. `TEAM-SETUP.md` has the install. |
| `.claude/skills/clip-packaging/` | The title + thumbnail-text system: 14 title archetypes, 7 thumb types, rewrite drills, worked examples, anti-patterns, scoring rubric, mechanical checker, thumbnail renderer |

## Rules the agent follows

- Every clip passes a five-point standalone test (cold viewer understands it, starts on the
  hook, one arc, ends on the payoff, no sponsor reads).
- Target 4–5 minutes or longer; 2–3 only when the idea is a natural unit; cap 20.
- Titles: plain beats clever, the speaker's own words, first person on their own channel,
  every number literally true of the clip.
- Thumbnail frame: the right speaker, eyes to camera, mouth closed or mid-smile, not mid-word.
  Never the exact second the line is spoken. Heuristics rank, a human (or Claude) confirms.
- Model: Sonnet. Batches run one fresh agent per video, never a fork of a long session.

## Tests

```bash
PY=.venv/bin/python        # Windows: .venv/Scripts/python.exe
"$PY" .claude/commands/marketing/short-form-pipeline/scripts/test_longform.py
"$PY" .claude/commands/marketing/short-form-pipeline/scripts/test_pipeline.py      # skips without the Anthropic SDK
"$PY" .claude/skills/clip-packaging/scripts/test_check_package.py
```

## Licence

Code: MIT (see `LICENSE`). `Montserrat-ExtraBold.ttf` is redistributed under the SIL Open
Font License 1.1. The clip-packaging reference lists contain publicly visible YouTube titles,
thumbnail text and view counts from @MoreMozi, included for analysis; the transcript corpus
is not included.
