#!/usr/bin/env python3
"""
fetch.py — Step 1 of the short-form-repurposing workflow.

Downloads a YouTube video + its auto-captions, and writes a clean, timestamped
transcript that Claude reads to SELECT clips. No API key, no Whisper needed here
(Whisper runs later, only on the selected clip windows, in render_clips.py).

Usage:
  python3 fetch.py "<youtube_url>" [--workdir DIR]

Prints WORKDIR=<dir> on the last lines for the caller to capture.
"""

import argparse
import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from timeutil import parse_time_to_seconds, seconds_to_mmss as mmss  # noqa: E402


def reconstruct(vtt_path: str) -> str:
    """Rebuild a readable transcript from a yt-dlp rolling auto-caption VTT.

    YouTube auto-caption cues restate the previous line with a timing lag, so a
    naive join repeats every phrase 2-3x. Keep only the newest line of each cue,
    drop cues that are substrings of their neighbour (this also drops a genuine
    short repeat like "Yeah." right after "Yeah, exactly." — acceptable), then group lines into
    speaker-turn paragraphs (a cue starting with ">>" opens a new turn) capped at
    ~700 chars so Claude can read the whole thing in a few passes.
    """
    kept: list[tuple[float, str]] = []
    for cue in re.split(r"\n\n+", Path(vtt_path).read_text()):
        m = re.search(r"(\d\d:\d\d:\d\d\.\d+) --> (\d\d:\d\d:\d\d\.\d+)", cue)
        if not m:
            continue
        lines = [re.sub(r"<[^>]+>", "", l).strip() for l in cue[m.end():].strip().split("\n")]
        lines = [html.unescape(l) for l in lines if l]
        if not lines:
            continue
        txt = lines[-1]  # rolling cues: the last line is the new text
        if kept and kept[-1][1] == txt:
            continue
        if kept and (txt in kept[-1][1] or kept[-1][1] in txt):
            if len(txt) > len(kept[-1][1]):
                kept[-1] = (kept[-1][0], txt)
            continue
        kept.append((parse_time_to_seconds(m.group(1)), txt))

    paras: list[str] = []
    cur: list[str] = []
    cur_ts = None
    for ts, t in kept:
        t = t.replace("[music]", "").replace("[laughter]", "(laughs)").strip()
        if not t:
            continue
        if t.startswith(">>") or (cur and len(" ".join(cur)) > 700):
            if cur:
                paras.append(f"[{mmss(cur_ts)}] {' '.join(cur)}")
            cur, cur_ts = [t.lstrip("> ").strip()], ts
        else:
            if cur_ts is None:
                cur_ts = ts
            cur.append(t)
    if cur:
        paras.append(f"[{mmss(cur_ts)}] {' '.join(cur)}")
    return "\n".join(paras)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--workdir")
    args = ap.parse_args()

    m = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{6,})", args.url)
    vid = m.group(1) if m else "video"
    workdir = args.workdir or os.path.expanduser(f"~/.cache/short-form-repurposing/{vid}")
    os.makedirs(workdir, exist_ok=True)

    meta = subprocess.run(
        ["yt-dlp", "--skip-download", "--print", "%(title)s\t%(duration)s\t%(id)s", args.url],
        capture_output=True, text=True,
    )
    parts = (meta.stdout.strip().split("\t") + ["", "", ""])[:3]
    title, dur, realid = parts

    subprocess.run(
        ["yt-dlp", "--write-auto-sub", "--sub-lang", "en", "--convert-subs", "vtt",
         "--skip-download", "-o", f"{workdir}/src.%(ext)s", args.url],
        capture_output=True, text=True,
    )

    src = f"{workdir}/source.mp4"
    if not os.path.exists(src):
        subprocess.run(
            ["yt-dlp", "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
             "--merge-output-format", "mp4", "-o", src, args.url]
        )

    transcript = ""
    vtts = list(Path(workdir).glob("*.vtt"))
    if vtts:
        transcript = reconstruct(str(vtts[0]))
        Path(f"{workdir}/transcript.txt").write_text(transcript)

    json.dump({
        "url": args.url, "title": title, "duration": dur,
        "video_id": realid or vid, "source": src,
        "transcript": f"{workdir}/transcript.txt", "has_transcript": bool(transcript),
    }, open(f"{workdir}/meta.json", "w"), indent=2)

    print(f"WORKDIR={workdir}")
    print(f"TITLE={title}")
    print(f"DURATION={dur}s")
    print(f"SOURCE={'ok' if os.path.exists(src) else 'MISSING'}")
    print(f"TRANSCRIPT={'ok -> ' + workdir + '/transcript.txt' if transcript else 'NONE (no auto-captions)'}")


if __name__ == "__main__":
    main()
