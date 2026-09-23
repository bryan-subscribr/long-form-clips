#!/usr/bin/env bash
# doctor.sh — verify the clip-pipeline dependencies (short-form Shorts + long-form clips).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_CLAUDE="$(cd "$HERE/../../../.." && pwd)"          # <repo>/.claude
ok=1; warn=0
check() { if command -v "$1" >/dev/null 2>&1; then echo "  ✓ $1"; else echo "  ✗ $1 MISSING"; ok=0; fi; }
pycheck() { if python3 -c "import $1" >/dev/null 2>&1; then echo "  ✓ python: $2"; else echo "  ✗ python: $2 MISSING  (pip install $3)"; ok=0; fi; }

echo "== clip pipeline doctor =="
check yt-dlp
check ffmpeg
check ffprobe
check python3
pycheck cv2   "opencv-python (thumb frame picker)" opencv-python
pycheck numpy "numpy (thumb frame picker)"          numpy
pycheck PIL   "Pillow (thumbnail text renderer)"    Pillow

if python3 -c "import whisper" >/dev/null 2>&1; then
  echo "  ✓ openai-whisper (burned captions)"
else
  echo "  ~ openai-whisper missing — only needed when burning captions (Shorts, or --aspect 16:9 without --no-captions)"
  warn=1
fi

if [ -f "$REPO_CLAUDE/skills/clip-packaging/scripts/thumb_preview.py" ]; then
  echo "  ✓ clip-packaging skill ($REPO_CLAUDE/skills/clip-packaging)"
else
  echo "  ✗ clip-packaging skill MISSING at $REPO_CLAUDE/skills/clip-packaging — pull the branch that ships it"
  ok=0
fi
if [ -f "$REPO_CLAUDE/skills/clip-packaging/assets/fonts/Montserrat-ExtraBold.ttf" ]; then
  echo "  ✓ Montserrat ExtraBold (vendored)"
else
  echo "  ~ Montserrat ExtraBold not vendored; thumbnails fall back to Arial Bold"
  warn=1
fi
if ffmpeg -hide_banner -encoders 2>/dev/null | grep -q h264_videotoolbox; then
  echo "  ✓ h264_videotoolbox available — pass --encoder h264_videotoolbox to render_clips.py for 3-5x faster renders"
fi

echo
if [ "$ok" = "1" ]; then
  [ "$warn" = "1" ] && echo "Ready (with optional pieces missing, see ~ above)." || echo "All good — ready to run."
  exit 0
else
  echo "Install the missing pieces:"
  echo "  brew install yt-dlp ffmpeg"
  echo "  python3 -m pip install --user opencv-python numpy Pillow"
  echo "  python3 -m pip install --user openai-whisper      # only for burned captions"
  exit 1
fi
