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
from timeutil import parse_time_to_seconds, seconds_to_mmss as mmss, utf8_console  # noqa: E402


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
    for cue in re.split(r"\n\n+", Path(vtt_path).read_text(encoding="utf-8", errors="replace")):
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


def ytdlp_cmd() -> list[str]:
    """yt-dlp from this Python's environment when it has one, else the one on PATH.

    YouTube breaks old yt-dlp builds every few weeks (a stale one answers HTTP 403 on the
    video stream while captions still download). A copy inside the repo's .venv is updated
    with `pip install -U yt-dlp`, the same command on every OS and no admin rights needed.
    """
    try:
        import yt_dlp  # noqa: F401
        return [sys.executable, "-m", "yt_dlp"]
    except ImportError:
        return ["yt-dlp"]


def whisper_transcript(src: str, workdir: str, model_name: str = "small") -> str:
    """Transcribe the source with openai-whisper; write segments.json; return paragraphs.

    Segments are grouped into ~700-char paragraphs stamped with the first segment's
    start, matching the shape reconstruct() produces from a VTT.
    """
    try:
        import whisper
    except ImportError:
        print("WARN openai-whisper not installed; pip install openai-whisper", flush=True)
        return ""
    model = whisper.load_model(model_name)
    result = model.transcribe(src, fp16=False, verbose=False, language="en")
    segs = [{"start": round(float(x["start"]), 3), "end": round(float(x["end"]), 3), "text": x["text"].strip()}
            for x in result["segments"] if x["text"].strip()]
    with open(f"{workdir}/segments.json", "w", encoding="utf-8") as fh:
        json.dump(segs, fh, indent=1, ensure_ascii=False)
    paras, cur, cur_ts = [], [], None
    for sg in segs:
        if cur and len(" ".join(cur)) > 700:
            paras.append(f"[{mmss(cur_ts)}] {' '.join(cur)}")
            cur, cur_ts = [], None
        if cur_ts is None:
            cur_ts = sg["start"]
        cur.append(sg["text"])
    if cur:
        paras.append(f"[{mmss(cur_ts)}] {' '.join(cur)}")
    return "\n".join(paras)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--workdir")
    ap.add_argument("--no-whisper", action="store_true", help="do not fall back to Whisper when YouTube captions are unavailable")
    ap.add_argument("--whisper-model", default="small", help="Whisper model for the fallback (tiny/base/small/medium)")
    args = ap.parse_args()
    utf8_console()

    m = re.search(r"(?:v=|youtu\.be/|shorts/)([\w-]{6,})", args.url)
    vid = m.group(1) if m else "video"
    workdir = args.workdir or os.path.expanduser(f"~/.cache/short-form-repurposing/{vid}")
    os.makedirs(workdir, exist_ok=True)

    ytdlp = ytdlp_cmd()
    meta = subprocess.run(
        [*ytdlp, "--encoding", "utf-8", "--skip-download", "--print", "%(title)s\t%(duration)s\t%(id)s", args.url],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    parts = (meta.stdout.strip().split("\t") + ["", "", ""])[:3]
    title, dur, realid = parts

    subprocess.run(
        [*ytdlp, "--write-auto-sub", "--sub-lang", "en", "--convert-subs", "vtt",
         "--skip-download", "-o", f"{workdir}/src.%(ext)s", args.url],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )

    src = f"{workdir}/source.mp4"
    download_error = ""
    if not os.path.exists(src):
        # One progress line every 10 s: the default redraws many times a second, and Claude Code
        # keeps every byte of it in the conversation.
        dl = subprocess.run(
            [*ytdlp, "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
             "--merge-output-format", "mp4", "--newline", "--progress-delta", "10", "-o", src, args.url],
            stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
        )
        sys.stderr.write(dl.stderr)
        errors = [l for l in dl.stderr.splitlines() if l.startswith("ERROR")]
        download_error = errors[-1] if errors else (f"yt-dlp exited {dl.returncode}" if dl.returncode else "")

    transcript = ""
    transcript_source = None
    vtts = sorted(Path(workdir).glob("*.vtt"))   # same pick as captions.load_cues
    if vtts:
        transcript = reconstruct(str(vtts[0]))
        transcript_source = "youtube-auto-captions"
    elif os.path.exists(src) and not args.no_whisper:
        # YouTube rate-limits the caption endpoint (HTTP 429) after a few downloads from one
        # IP even though the video itself downloads fine. Fall back to Whisper on the audio:
        # better text than YouTube ASR, segment timings ~0.5 s, and segments.json feeds
        # captions.py for per-clip SRT. ~1x realtime on CPU with the small model.
        print("no captions from YouTube (rate-limited or none) -> transcribing with Whisper", flush=True)
        transcript = whisper_transcript(src, workdir, args.whisper_model)
        transcript_source = f"whisper-{args.whisper_model}" if transcript else None
    if transcript:
        Path(f"{workdir}/transcript.txt").write_text(transcript, encoding="utf-8")

    with open(f"{workdir}/meta.json", "w", encoding="utf-8") as fh:
        json.dump({
            "url": args.url, "title": title, "duration": dur,
            "video_id": realid or vid, "source": src,
            "transcript": f"{workdir}/transcript.txt", "has_transcript": bool(transcript),
            "transcript_source": transcript_source,
        }, fh, indent=2, ensure_ascii=False)

    # Forward slashes: on Windows the caller is Git Bash, which eats unquoted backslashes.
    workdir = Path(workdir).as_posix()
    print(f"WORKDIR={workdir}")
    print(f"TITLE={title}")
    print(f"DURATION={dur}s")
    print(f"SOURCE={'ok' if os.path.exists(src) else 'MISSING'}")
    print(f"TRANSCRIPT={'ok (' + str(transcript_source) + ') -> ' + workdir + '/transcript.txt' if transcript else 'NONE (no captions and Whisper unavailable)'}")
    if not os.path.exists(src):
        # Captions can arrive while the video does not; selecting clips from a transcript with
        # no video behind it only fails later, at render time, with a stranger error.
        print(f"ERROR the video did not download: {download_error or 'no source.mp4'}", file=sys.stderr)
        if "403" in download_error or "Sign in" in download_error or "confirm" in download_error.lower():
            print("  Update yt-dlp first (pip install -U yt-dlp in the .venv; winget upgrade yt-dlp.yt-dlp / "
                  "brew upgrade yt-dlp for the system copy), then run this again.", file=sys.stderr)
        sys.exit(3)


if __name__ == "__main__":
    main()
