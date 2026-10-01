# Clip pipeline — team setup

Everything lives in this repo under `.claude/`. Cloning the repo is the install.
Claude Code loads `.claude/commands/*.md` and `.claude/skills/*/SKILL.md` from the repo
root automatically, so open Claude Code **in this repo** and the commands are there.

## 1. Machine deps (once)

Both systems end the same way: a `.venv` inside the repo holding the Python packages, and
`doctor` printing `READY=yes`. The workflow finds that `.venv` by itself.

### macOS

```bash
brew install yt-dlp ffmpeg deno python@3.12
git clone https://github.com/bryan-subscribr/long-form-clips.git && cd long-form-clips
python3 -m venv .venv
.venv/bin/pip install -r .claude/commands/marketing/short-form-pipeline/requirements.txt
bash .claude/commands/marketing/short-form-pipeline/scripts/doctor.sh
```

A venv because Homebrew's Python refuses `pip install --user` ("externally-managed-environment").
Doctor finds `h264_videotoolbox` on a Mac: 10-minute clips render in about a minute.

### Windows 10 / 11

In **PowerShell** (not as administrator):

```powershell
winget install Python.Python.3.12 Git.Git Gyan.FFmpeg yt-dlp.yt-dlp DenoLand.Deno
setx PYTHONUTF8 1
```

Close PowerShell, open a new one (so the new programs are on PATH), then:

```powershell
git clone https://github.com/bryan-subscribr/long-form-clips.git
cd long-form-clips
py -3.12 -m venv .venv
.venv\Scripts\pip install -r .claude\commands\marketing\short-form-pipeline\requirements.txt
.venv\Scripts\python .claude\commands\marketing\short-form-pipeline\scripts\doctor.py
```

Install Claude Code for Windows and sign in; it runs its commands in Git Bash, which the
`Git.Git` package provides. Notes:

- Use Python 3.12 from winget, not the Microsoft Store: the Store's `python3` is a stub that
  only opens the Store. The workflow never calls `python3`; it uses the `.venv` that doctor reports.
- `setx PYTHONUTF8 1` makes every Python tool write UTF-8. The scripts are UTF-8 safe on their own;
  this covers everything else.
- Doctor tests the GPU encoders for real (NVIDIA `h264_nvenc`, Intel `h264_qsv`, AMD `h264_amf`)
  and names the first one that works. Without one it uses libx264 at `veryfast`: a 10-minute clip
  takes a few minutes on a laptop CPU.
- Whisper downloads its model (~460 MB) the first time YouTube withholds captions.

Doctor must print `READY=yes`. Each FAIL line names the fix.

## 2. Run

In Claude Code, from the repo root, **on Sonnet** (type `/model sonnet` first — the
workflow is tuned for it and it costs a fifth of Opus/Fable; a 90-min video runs about
$1–2 in Claude Code):

```
/long-form-clips https://www.youtube.com/watch?v=VIDEO_ID
```

Flow: doctor → download + transcript → Claude reads the whole transcript and proposes
clips (4–5 min or longer each, 20 max) with titles and thumbnail text → **you approve** → render →
Claude reviews every thumbnail contact sheet → delivery folder in `~/Downloads/<slug>-clips/`
(on Windows that is `C:\Users\<you>\Downloads\<slug>-clips\`).

Per clip you get: `.mp4` (1920×1080, no burned captions), `.thumb.jpg` (text burned in
the MoreMozi style), `.srt` (captions timed to the clip — YouTube Studio → Subtitles →
Upload file → With timing), `.txt` (title, thumbnail text, description, pinned comment,
source link, timed transcript, captions), `.thumb-frame.jpg`, `.thumb-candidates.jpg`.

Titles, thumbnail text and descriptions come out in the speaker's language, whatever
language you type to Claude in.

Vertical Shorts instead: `/short-form-repurposing <url>` (needs Whisper).

## 3. Rules the agent follows

- `PRINCIPLES.md` — clip selection (five-point standalone test, length, no sponsor reads),
  title rules (plain beats clever, first person on the speaker's own channel, every number
  literally true), thumbnail frame rule (composed, correct speaker).
- `.claude/skills/clip-packaging/` — the title + thumbnail-text system measured on 2,795
  MoreMozi clips, with the mechanical checker `scripts/check_package.py` (it fails a package
  whose thumbnail line is not spoken inside the clip, or whose title names the speaker).

## 4. Manual escape hatches

`PY` and `ENC` are the `PY=` and `ENCODER=` lines doctor printed (macOS: `.venv/bin/python`,
Windows: `.venv/Scripts/python.exe`).

```bash
S=.claude/commands/marketing/short-form-pipeline/scripts
"$PY" $S/render_clips.py --workdir WORK --clips WORK/clips.json --out OUT --aspect 16:9 --no-captions --encoder "$ENC"
"$PY" $S/pick_thumb_frame.py WORK/source.mp4 --at 77:58 --ref WORK/speaker_ref.jpg --out frame.jpg --sheet sheet.jpg
"$PY" $S/finalize_delivery.py OUT --source-url URL --source-title "…" --description-file OUT/CHANNEL_DESCRIPTION.txt --workdir WORK
"$PY" $S/test_longform.py && "$PY" $S/test_pipeline.py && "$PY" .claude/skills/clip-packaging/scripts/test_check_package.py
```

`clips_result.json` is saved after every clip. If a render dies, rerun with the remaining
clips and `--start-index N` into the same `--out`; nothing already rendered is lost.
Windows over 20 minutes are refused before anything renders; split them.
Work folders (`~/.cache/short-form-repurposing/<video_id>`, several GB each) are never cleaned
up automatically; doctor shows how much they hold.
