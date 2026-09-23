# Short-Form Repurposing Pipeline

Repurpose one long-form YouTube video into several **9:16 vertical clips native to
YouTube Shorts**. Downloads, transcribes, segments with AI *around explicit viral
principles* (see `PRINCIPLES.md`), cuts, smart-crops to 9:16, and burns
word-highlighted captions — all in one pipeline.

A 60-minute episode becomes 3–5 upload-ready Shorts (plus captions + pinned-comment
suggestions) in under 25 minutes.

## Features

- **Principle-driven segmentation** — Claude finds moments using a hook checklist
  (shock → clear expectation → open loop), starts each clip *on the shock* ("the best
  hooks don't have a hook"), and **excludes sponsor reads and subscribe asks**
- **Deterministic ad/CTA guard** — a regex safety net drops any sponsor/subscribe clip
  even if the model misses it, and clamps clip length
- **Smart vertical cropping** — Face detection (MediaPipe) or audio panning to crop
  16:9 → 9:16 without losing the presenter
- **Layout-aware reformatting** — talking head, screen share overlay, side-by-side,
  and gallery view get different crop strategies
- **Word-highlighted captions** — ASS subtitles (current word highlighted) burned in
- **Whisper transcription** — local word-level timestamps for precise caption sync
- **Cut verification** — a cheap second AI pass ensures clips end on complete thoughts
- **Shorts metadata per clip** — short title, ready-to-post caption, hook line, open
  loop, and a suggested pinned comment

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   DOWNLOAD  │────▶│ TRANSCRIBE  │────▶│   SEGMENT   │────▶│     CUT     │────▶│   REFORMAT  │────▶│  CAPTIONED  │
│             │     │             │     │             │     │             │     │             │     │             │
│  yt-dlp     │     │  Whisper    │     │   Claude    │     │   FFmpeg    │     │   FFmpeg    │     │   FFmpeg    │
│             │     │  (local)    │     │   (API)     │     │  (cut)      │     │  (9:16 crop │     │  (ASS burn  │
│             │     │             │     │             │     │             │     │  + face det) │     │   overlay)  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
      │                   │                   │                   │                   │                   │
  episode.mp4        transcript.vtt      segments.json       clip_raw.mp4       clip_vert.mp4      clip_final.mp4
  (16:9 video)    (timestamped text)  (start/end/title      (landscape)         (9:16 vertical)    (captioned,
                                       + layout hint)                                                platform-ready)
```

### Pipeline Steps

| Step | Tool | Input | Output | Cost |
|------|------|-------|--------|------|
| Download | yt-dlp | YouTube URL | MP4 + VTT captions | Free |
| Transcribe | Whisper (local) | MP4/audio | Word-level timestamps | Free |
| Segment | Claude API | Transcript text | Clip metadata JSON | ~$0.50–1.00/episode |
| Cut | FFmpeg | MP4 + metadata | Individual clips (16:9) | Free |
| Vertical Crop | FFmpeg + MediaPipe | Landscape clip | 9:16 clip (1080×1920) | Free |
| Caption Burn | FFmpeg | Vertical clip + ASS | Captioned clip | Free |

**Total cost per episode:** $0.50–1.00 (Claude API only)

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| Python 3.10+ | Runtime | — |
| yt-dlp | Download YouTube videos | `brew install yt-dlp` or `pip install yt-dlp` |
| FFmpeg | Video cutting, cropping, caption burn | `brew install ffmpeg` |
| openai-whisper | Local transcription | `pip install openai-whisper` |
| mediapipe | Face detection for smart crop | `pip install mediapipe` |
| anthropic | Claude API client | `pip install anthropic` |

## Installation

```bash
# Install system dependencies
brew install yt-dlp ffmpeg

# Install Python dependencies
pip install -r requirements.txt

# Set your Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Usage

### Process a single video

```bash
python3 scripts/shortform_pipeline.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --max-clips 3
```

### Process with custom output directory

```bash
python3 scripts/shortform_pipeline.py --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --max-clips 5 --output-dir ./my-clips
```

### Plan without rendering (dry run)

```bash
python3 scripts/shortform_pipeline.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --dry-run
```

Downloads + transcribes + segments and writes the metadata, but skips the ffmpeg render.

## How It Works

### Principle-driven segmentation

The pipeline sends the transcript to Claude with a prompt (`SEGMENTATION_PROMPT`) that
encodes the viral principles in `PRINCIPLES.md`:

- **The hook checklist:** every candidate is judged on shock (ideally visual), a clear
  expectation, and an open loop — and the clip **starts on the shocking line**, not a
  preamble ("the best hooks don't have a hook").
- **Curiosity = specific WHAT, unknown HOW:** vague teasing is rejected.
- **Fluff is cut:** sponsor reads, subscribe asks, and wind-up are excluded — reinforced
  by a deterministic `AD_MARKERS` guard.
- **Single-idea constraint:** each clip is exactly one framework/story/claim.
- **Layout detection:** Claude outputs a `layout_hint` per clip for the crop step.

### Smart Vertical Cropping

Standard center-crop fails whenever screen share content is visible. The pipeline uses layout-aware cropping:

| Layout | Strategy |
|--------|----------|
| `talking_head` | Face-detected center crop (MediaPipe) or audio-panning fallback |
| `screen_share_overlay` | Stack: screen content on top, webcam bubble on bottom |
| `side_by_side` | Stack: screen on top, presenter face on bottom |
| `gallery_view` | Crop to active speaker quadrant |

### Caption System

Two caption modes:

1. **ASS word-highlight (default with Whisper):** Shows 3-4 words at a time, current word highlighted in yellow. TikTok-native look.
2. **SRT sentence-level (fallback):** When word-level timestamps aren't available. Bold white text with black outline.

### Scoring (Standalone Clipper)

The `video_clipper.py` script can find clips without Claude using a heuristic scoring system (0–40 points):

- **Hook strength (0–10):** Questions, superlatives, numbers, contrarian framing
- **Value content (0–10):** Actionable advice, revenue/growth data, personal stories
- **Standalone quality (0–10):** Clean start/end, low pronoun density, logical flow
- **Voice match (0–10):** Patterns matching the creator's speaking style

Minimum score threshold: 18/40.

## Output Specifications

| Platform | Resolution | Max Duration | Format |
|----------|-----------|-------------|--------|
| TikTok | 1080×1920 | 60s | MP4 (H.264 + AAC) |
| Instagram Reels | 1080×1920 | 90s | MP4 (H.264 + AAC) |
| YouTube Shorts | 1080×1920 | 60s | MP4 (any codec) |

## Directory Structure

```
short-form-pipeline/
├── README.md
├── SKILL.md                    # Claude Code / AI assistant instructions
├── PRINCIPLES.md               # The viral principles encoded in the pipeline
├── requirements.txt
├── data/fixtures/
│   └── reference-transcript.txt  # Excerpts used to tune the prompt + guard
└── scripts/
    ├── shortform_pipeline.py   # The pipeline / brain (segmentation, guard, metadata)
    ├── video_clipper.py         # Rendering engine / hands (smart crop + captions)
    ├── test_pipeline.py         # Deterministic tests (no API/network)
    └── clip_sender.py           # Clip delivery/review helper
```

## Customization

### Segmentation Prompt

`SEGMENTATION_PROMPT` in `shortform_pipeline.py` encodes the hook checklist, the
"no-hook hook" rule, the fluff-exclusion rules, and the metadata fields. Tune the
wording or the length window (`MIN_CLIP_SECONDS` / `MAX_CLIP_SECONDS`) there.

### Ad / CTA guard

`AD_MARKERS` in `shortform_pipeline.py` drops sponsor reads and subscribe asks even
if the model misses them. Add creator- or sponsor-specific phrases here.

### Standalone heuristic clipper

`video_clipper.py` can still run on its own (no Claude) with heuristic scoring — its
`VOICE_PATTERNS` list boosts segments that match a creator's speaking style.

### Crop Parameters

Face detection zoom factors and positioning can be tuned in `video_clipper.py`:
- `scale_factor` — Base zoom level (default 1.08 for single face)
- `desired_face_y` — Vertical face position target (default: upper 35% of frame)

## Cost Breakdown

| Volume | Daily Cost | Monthly Cost |
|--------|-----------|--------------|
| 1 episode/day (3 clips) | $0.50–1.00 | $15–30 |
| 3 episodes/day (10 clips) | $1.50–3.00 | $45–90 |
| 6 episodes/day (20 clips) | $3.00–6.00 | $90–180 |

All costs are Claude API only. Transcription, cutting, cropping, and captioning are free (local).

## License

MIT


---

<div align="center">

**🧠 [Want these built and managed for you? →](https://singlebrain.com/?utm_source=github&utm_medium=skill_repo&utm_campaign=ai_marketing_skills)**

*This is how we build agents at [Single Brain](https://singlebrain.com/?utm_source=github&utm_medium=skill_repo&utm_campaign=ai_marketing_skills) for our clients.*

[Single Grain](https://www.singlegrain.com/?utm_source=github&utm_medium=skill_repo&utm_campaign=ai_marketing_skills) · our marketing agency

📬 **[Level up your marketing with 14,000+ marketers and founders →](https://levelingup.beehiiv.com/subscribe)** *(free)*

</div>
