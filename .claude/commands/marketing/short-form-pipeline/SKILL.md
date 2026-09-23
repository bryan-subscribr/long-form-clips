# Short-Form Repurposing Pipeline — Skill

## Preamble (runs on skill start)

```bash
# Version check (silent if up to date)
python3 telemetry/version_check.py 2>/dev/null || true

# Telemetry opt-in (first run only, then remembers your choice)
python3 telemetry/telemetry_init.py 2>/dev/null || true
```

> **Privacy:** This skill logs usage locally to `~/.ai-marketing-skills/analytics/`. Remote telemetry is opt-in only. No code, file paths, or repo content is ever collected. See `telemetry/README.md`.

---

Repurpose one long-form YouTube video into several **9:16 vertical clips that are
native to YouTube Shorts** — each edited to stand alone as a Short, not a raw clip.
The cutting and captions are built around a set of viral short-form principles (see
`PRINCIPLES.md`), so the output is optimized for the hook, the open loop, and the
comment section — not just chopped by timestamp.

## Prerequisites

- `yt-dlp` and `ffmpeg` installed
- `ANTHROPIC_API_KEY` environment variable set
- Python dependencies from `requirements.txt` installed
- Optional: `mediapipe` and `opencv-python` for face-detected smart crop

## Quick Start

```bash
python3 scripts/shortform_pipeline.py \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --max-clips 3 \
  --output-dir ./output
```

Plan the clips + metadata without rendering (download + transcribe still run):

```bash
python3 scripts/shortform_pipeline.py --url "URL" --dry-run
```

## The principles the pipeline enforces

Full detail in `PRINCIPLES.md`. In short:

- **"The best hooks don't have a hook."** Clips start *on* the shocking line — no
  preamble ("I'm about to ask the craziest question").
- **Every hook is scored on three things:** shock (ideally visual), a clear
  expectation, and an open loop (a reason to watch to the end).
- **Curiosity = specific about WHAT, unknown HOW.** Vague teasing is rejected.
- **All fluff is cut.** Sponsor reads and subscribe asks are excluded, both by the
  prompt and by a deterministic guard (`AD_MARKERS` / `guard_and_clamp`).
- **One complete idea per clip; ends on a complete thought.**
- **YouTube-native:** 9:16 vertical, storytelling-first, short complementary titles.

## Two output modes

| Mode | Command | Render flag | Output | Clip length |
|------|---------|-------------|--------|-------------|
| Vertical Shorts | `/short-form-repurposing <url>` | `--aspect 9:16` (default) | 1080×1920, face-tracked crop | 20–58s |
| Horizontal long-form clips | `/long-form-clips <url> [count]` | `--aspect 16:9 --no-captions [--encoder h264_videotoolbox]` | 1920×1080, no crop, thumb frame + contact sheet per clip | 4–5 min or longer (2–3 occasionally, cap 15) |

Rules for the horizontal mode are in `PRINCIPLES.md` → "Horizontal (Long-Form Clip) Mode".
Title + thumbnail packaging comes from `.claude/skills/clip-packaging` (ships in this repo).
Team setup: `TEAM-SETUP.md`.

## Pipeline Overview

1. **Download** — yt-dlp fetches the source video
2. **Transcribe** — Whisper produces word-level timestamps (for caption sync)
3. **Segment** — Claude finds the best moments using the hook checklist, sets each
   `start_time` *on the shock*, and excludes sponsor/subscribe regions
4. **Guard** — deterministic pass drops any ad/CTA-flavored clip and clamps length
5. **Cut Verification** — cheap Claude pass ensures each clip ends on a complete thought
6. **Render** — single ffmpeg pass: smart 9:16 face-crop + word-highlighted captions
7. **Metadata** — per clip: short title, ready-to-post caption, hook, open loop,
   pinned comment → `data/clips/last-run-shortform.json`

## Key Files

| File | Purpose |
|------|---------|
| `scripts/shortform_pipeline.py` | The pipeline (brain): segmentation, ad guard, cut verification, metadata |
| `scripts/video_clipper.py` | Rendering engine (hands): smart 9:16 crop + word-highlight ASS captions. Reused by the pipeline; also runs standalone with heuristic scoring |
| `scripts/test_pipeline.py` | Deterministic tests for the guard + time helpers (no API/network) |
| `scripts/test_longform.py` | Deterministic tests for the long-form path: transcript rebuild, result bookkeeping, zoom geometry, delivery writer |
| `scripts/render_clips.py` | Cuts approved clips (9:16 or 16:9), picks thumb frames, saves `clips_result.json` after every clip |
| `scripts/pick_thumb_frame.py` | Ranks a ±15 s window for a composed close-up of the right speaker; writes a contact sheet |
| `scripts/finalize_delivery.py` | Per-clip `.thumb.jpg` + `.txt` (title, description, pinned comment) + `README.md` |
| `scripts/timeutil.py` | Shared MM:SS / HH:MM:SS parsing, dependency-free |
| `PRINCIPLES.md` | The viral short-form principles encoded in the pipeline |
| `data/fixtures/reference-transcript.txt` | Reference excerpts used to tune the prompt + guard |

## Layout-Aware Cropping

The renderer handles four layouts, chosen by Claude's `layout_hint`:

- **`talking_head`** — Face-detected center crop (MediaPipe); audio-panning fallback
- **`screen_share_overlay`** — Screen content on top, webcam bubble on bottom
- **`side_by_side`** — Screen on top, presenter face on bottom
- **`gallery_view`** — Crops to the active-speaker quadrant

## Customization

### Segmentation prompt
`SEGMENTATION_PROMPT` in `shortform_pipeline.py` encodes the hook checklist, the
"no-hook hook" rule, and the fluff-exclusion rules. Tune wording, length window
(`MIN_CLIP_SECONDS` / `MAX_CLIP_SECONDS`), or the metadata fields there.

### Ad / CTA guard
`AD_MARKERS` in `shortform_pipeline.py` is the deterministic safety net that drops
sponsor reads and subscribe asks even if the model misses them. Add creator- or
sponsor-specific phrases here.

### Models
`SHORTFORM_SEG_MODEL` (default `claude-sonnet-4-6`) does segmentation;
`SHORTFORM_VERIFY_MODEL` (default `claude-haiku-4-5-...`) does the cheap cut-verify
pass. Override via env vars to trade cost for quality.

### Crop tuning
In `video_clipper.py`: `scale_factor` (single-face zoom, default 1.08) and
`desired_face_y` (face position, default upper 35%).

## Output

Each clip is:
- **1080×1920** (9:16 vertical), **H.264 + AAC**
- **Word-highlighted captions** burned in
- Accompanied by metadata (title, caption, hook, open loop, pinned comment)
- Ready for direct upload to YouTube Shorts (and Reels/TikTok)

## Verification

```bash
python3 scripts/test_pipeline.py            # deterministic guard + helper tests
python3 -m py_compile scripts/*.py          # syntax check
```

## Troubleshooting

- **FFmpeg filter error:** Don't use `-c:v copy` with a video filter. Only `-c:a copy` is safe.
- **Wrong output resolution:** Verify with `ffprobe -show_entries stream=width,height`.
- **Caption sync issues:** Captions are timed from Whisper word timestamps on the source; the renderer offsets them per clip.
- **Clip too long:** The guard trims any clip over 60s down to 58s.
- **A sponsor read slipped through:** add its phrasing to `AD_MARKERS`.
- **Captions are fragmented, out of order, or mistyped** (e.g. "whole rule. cup."): you're transcribing from YouTube auto-caption VTT instead of Whisper. Auto-captions are "rolling" (each cue restates prior words with a timing lag) and coarse, so word order and sync degrade. Install `openai-whisper` — the pipeline uses word-level Whisper timestamps for accurate, well-synced captions.
