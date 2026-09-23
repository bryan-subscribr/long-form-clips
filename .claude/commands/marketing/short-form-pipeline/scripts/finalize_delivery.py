#!/usr/bin/env python3
"""
finalize_delivery.py — turn a render_clips.py output folder into a per-clip delivery set.

For every rendered clip:
  NN_title.mp4              (already there)
  NN_title.thumb.jpg        thumbnail text burned via clip-packaging/thumb_preview.py
  NN_title.srt              YouTube-uploadable captions, timed to the clip (from the source auto-caption VTT)
  NN_title.txt              TITLE / THUMBNAIL TEXT / DESCRIPTION / PINNED COMMENT / SOURCE WINDOW / TRANSCRIPT / CAPTIONS
  README.md                 index table

Usage:
  python3 finalize_delivery.py OUTDIR --source-url URL --source-title "…" \
      [--description-file channel_description.txt] [--workdir WORKDIR]

--workdir           the fetch.py work directory; its *.vtt is used for per-clip captions.
                    Without it (or without a VTT) the caption sections are skipped with a note.

--description-file  a fixed channel description used VERBATIM for every clip (most creators
                    run one boilerplate). Without it, the per-clip caption from clips.json is used.
"""
import argparse, json, os, re, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from timeutil import parse_time_to_seconds as sec  # noqa: E402
from captions import clip_srt, clip_transcript, parse_rolling_vtt  # noqa: E402

def _find_preview() -> Path:
    """clip-packaging ships in this repo at .claude/skills/clip-packaging; fall back to a personal install."""
    here = Path(__file__).resolve()
    candidates = [
        here.parents[4] / "skills" / "clip-packaging" / "scripts" / "thumb_preview.py",   # <repo>/.claude/skills/...
        Path.home() / ".claude/skills/clip-packaging/scripts/thumb_preview.py",
    ]
    for c in candidates:
        if c.exists():
            return c
    return candidates[0]


PREVIEW = _find_preview()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--source-url", required=True)
    ap.add_argument("--source-title", default="")
    ap.add_argument("--description-file", default=None)
    ap.add_argument("--workdir", default=None, help="fetch.py workdir; its *.vtt feeds per-clip captions")
    args = ap.parse_args()
    if not PREVIEW.exists():
        sys.exit(f"clip-packaging skill not found (looked for {PREVIEW}). It ships in this repo under .claude/skills/clip-packaging — pull the branch.")
    OUT = Path(os.path.expanduser(args.out))
    fixed_desc = Path(args.description_file).read_text().rstrip("\n") if args.description_file else None

    cues = None
    if args.workdir:
        vtts = sorted(Path(os.path.expanduser(args.workdir)).glob("*.vtt"))
        if vtts:
            cues = parse_rolling_vtt(str(vtts[0]))
        else:
            print(f"WARN no *.vtt in {args.workdir}; captions skipped")

    results = json.load(open(OUT / "clips_result.json"))
    index = ["# Clip delivery", f"Source: {args.source_title}", args.source_url, "",
             "Per clip: `.mp4` video · `.thumb.jpg` thumbnail (text burned) · `.srt` captions for YouTube Studio → Subtitles → Upload · "
             "`.txt` title + description + pinned comment + timed transcript · `.thumb-frame.jpg` clean frame · `.thumb-candidates.jpg` the frames considered.", "",
             "| # | Title | Length | Thumb text |", "|---|---|---|---|"]
    for i, r in enumerate(results, 1):
        if not r.get("ok") or not r.get("file"):
            index.append(f"| {i} | {r.get('title','')} | RENDER FAILED | |")
            continue
        mp4 = Path(r["file"]); stem = mp4.with_suffix("")
        thumb = Path(str(stem) + ".thumb.jpg")
        if r.get("thumb_frame") and Path(r["thumb_frame"]).exists() and r.get("thumbnail_text"):
            proc = subprocess.run([sys.executable, str(PREVIEW), r["thumb_frame"], r["thumbnail_text"], "-o", str(thumb)],
                                  capture_output=True, text=True)
            if proc.returncode != 0:
                print(f"WARN clip {i} thumbnail: exit {proc.returncode} {proc.stderr.strip()[-300:]}")
        s, e = sec(r["start"]), sec(r["end"])
        length = f"{int(e - s) // 60}:{int(e - s) % 60:02d}"
        ts_link = f"{args.source_url}{'&' if '?' in args.source_url else '?'}t={int(s)}s"
        thumb_plain = re.sub(r"\*\*", "", r.get("thumbnail_text", ""))
        m_acc = re.search(r"\*\*(.+?)\*\*", r.get("thumbnail_text", ""))
        accent = m_acc.group(1) if m_acc else "-"
        description = fixed_desc if fixed_desc is not None else r.get("caption", "")
        srt_path = Path(str(stem) + ".srt")
        if cues is not None:
            srt_text = clip_srt(cues, s, e)
            srt_path.write_text(srt_text)
            transcript_block = ["TRANSCRIPT (clip time)", clip_transcript(cues, s, e), "",
                                f"CAPTIONS — upload {srt_path.name} in YouTube Studio → Subtitles → Upload file (With timing)", srt_text.rstrip("\n"), ""]
        else:
            transcript_block = ["TRANSCRIPT", "(no source captions available — rerun with --workdir pointing at the fetch directory)", ""]
        txt = [
            "TITLE", r["title"], "",
            "THUMBNAIL TEXT", thumb_plain, f"(accent word in yellow: {accent})", f"(spoken at {r.get('thumb_line', '')})", "",
            "DESCRIPTION", description, "",
            "PINNED COMMENT", r.get("pinned_comment", ""), "",
            "SOURCE WINDOW", f"{r['start']} – {r['end']}  ({length})", ts_link,
            f"Hook: {r.get('hook_line', '')}", f"Open loop: {r.get('open_loop', '')}", "",
            *transcript_block,
            "FILES", mp4.name, thumb.name if thumb.exists() else "(thumbnail render failed)",
            *([srt_path.name] if srt_path.exists() else []), "",
        ]
        Path(str(stem) + ".txt").write_text("\n".join(txt))
        index.append(f"| {i} | {r['title']} | {length} | {thumb_plain} |")
    (OUT / "README.md").write_text("\n".join(index) + "\n")
    print("finalized", len(results), "clips ->", OUT)


if __name__ == "__main__":
    main()
