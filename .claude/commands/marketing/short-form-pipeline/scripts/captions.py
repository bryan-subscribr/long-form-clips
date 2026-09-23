"""Build per-clip YouTube caption files (SRT) from the source video's auto-caption VTT.

yt-dlp auto-captions are "rolling": each cue repeats the previous line and adds a new one.
We keep the newest line of every cue with that cue's start time, drop exact/substring
repeats, then for a clip window [start, end) emit SRT entries offset to clip time so the
file uploads straight into YouTube Studio → Subtitles → Upload file.

No model tokens. Text quality is YouTube's ASR; timings are cue-accurate (~1 s).
"""

import html
import re
from pathlib import Path

from timeutil import parse_time_to_seconds

_CUE = re.compile(r"(\d\d:\d\d:\d\d\.\d+) --> (\d\d:\d\d:\d\d\.\d+)")


def parse_rolling_vtt(vtt_path: str) -> list[tuple[float, str]]:
    """Return [(start_seconds, text), ...] with rolling repeats removed."""
    kept: list[tuple[float, str]] = []
    for cue in re.split(r"\n\n+", Path(vtt_path).read_text()):
        m = _CUE.search(cue)
        if not m:
            continue
        lines = [re.sub(r"<[^>]+>", "", l).strip() for l in cue[m.end():].strip().split("\n")]
        lines = [html.unescape(l) for l in lines if l]
        if not lines:
            continue
        txt = lines[-1].replace("[music]", "").replace("[laughter]", "").lstrip("> ").strip()
        if not txt:
            continue
        if kept and kept[-1][1] == txt:
            continue
        if kept and (txt in kept[-1][1] or kept[-1][1] in txt):
            if len(txt) > len(kept[-1][1]):
                kept[-1] = (kept[-1][0], txt)
            continue
        kept.append((parse_time_to_seconds(m.group(1)), txt))
    return kept


def _srt_time(t: float) -> str:
    t = max(0.0, t)
    h, rem = divmod(int(t), 3600)
    m, s = divmod(rem, 60)
    ms = int(round((t - int(t)) * 1000))
    if ms == 1000:
        s += 1; ms = 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def clip_srt(cues: list[tuple[float, str]], start: float, end: float, max_len: float = 7.0) -> str:
    """SRT text for the window [start, end), timings relative to `start`.

    Each caption runs from its cue start to the next cue start (capped at max_len s and
    at the clip end), so text stays on screen until the next line arrives.
    """
    out = []
    n = 0
    for i, (t, txt) in enumerate(cues):
        if t < start - 0.5 or t >= end:
            continue
        nxt = cues[i + 1][0] if i + 1 < len(cues) else t + max_len
        t0 = max(t, start)
        t1 = min(nxt, t0 + max_len, end)
        if t1 - t0 < 0.3:
            continue
        n += 1
        out.append(f"{n}\n{_srt_time(t0 - start)} --> {_srt_time(t1 - start)}\n{txt}\n")
    return "\n".join(out)


def clip_transcript(cues: list[tuple[float, str]], start: float, end: float) -> str:
    """Readable [mm:ss] transcript for the window, timings relative to the clip."""
    lines = []
    for t, txt in cues:
        if start - 0.5 <= t < end:
            rel = max(0.0, t - start)
            lines.append(f"[{int(rel) // 60:02d}:{int(rel) % 60:02d}] {txt}")
    return "\n".join(lines)
