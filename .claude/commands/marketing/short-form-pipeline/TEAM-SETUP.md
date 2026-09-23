# Clip pipeline — team setup

Everything lives in this repo under `.claude/`. Cloning the repo is the install.
Claude Code loads `.claude/commands/*.md` and `.claude/skills/*/SKILL.md` from the repo
root automatically, so open Claude Code **in this repo** and the commands are there.

## 1. Machine deps (once)

```bash
brew install yt-dlp ffmpeg
python3 -m pip install --user opencv-python numpy Pillow
python3 -m pip install --user openai-whisper      # only if you will burn captions (Shorts)
bash .claude/commands/marketing/short-form-pipeline/scripts/doctor.sh
```

Doctor must print "ready". On a Mac it also tells you `h264_videotoolbox` is available;
pass that to the renderer and 10-minute clips render in about a minute instead of five.

## 2. Run

In Claude Code, from the repo root:

```
/long-form-clips https://www.youtube.com/watch?v=VIDEO_ID
```

Flow: doctor → download + transcript → Claude reads the whole transcript and proposes
clips (4–5 min or longer each) with titles and thumbnail text → **you approve** → render →
Claude reviews every thumbnail contact sheet → delivery folder in `~/Downloads/<slug>-clips/`.

Per clip you get: `.mp4` (1920×1080, no captions), `.thumb.jpg` (text burned in the
MoreMozi style), `.txt` (title, thumbnail text, description, pinned comment, source link),
`.thumb-frame.jpg` (clean frame), `.thumb-candidates.jpg` (frames considered).

Vertical Shorts instead: `/short-form-repurposing <url>` (needs Whisper).

## 3. Rules the agent follows

- `PRINCIPLES.md` — clip selection (five-point standalone test, length, no sponsor reads),
  title rules (plain beats clever, first person on the speaker's own channel, every number
  literally true), thumbnail frame rule (composed, correct speaker).
- `.claude/skills/clip-packaging/` — the title + thumbnail-text system measured on 2,795
  MoreMozi clips, with the mechanical checker `scripts/check_package.py`.

## 4. Manual escape hatches

```bash
S=.claude/commands/marketing/short-form-pipeline/scripts
python3 $S/render_clips.py --workdir WORK --clips WORK/clips.json --out OUT --aspect 16:9 --no-captions --encoder h264_videotoolbox
python3 $S/pick_thumb_frame.py WORK/source.mp4 --at 77:58 --ref WORK/speaker_ref.jpg --out frame.jpg --sheet sheet.jpg
python3 $S/finalize_delivery.py OUT --source-url URL --source-title "…" --description-file OUT/CHANNEL_DESCRIPTION.txt
python3 $S/test_longform.py && python3 $S/test_pipeline.py
```

`clips_result.json` is saved after every clip. If a render dies, rerun with the remaining
clips and `--start-index N` into the same `--out`; nothing already rendered is lost.
