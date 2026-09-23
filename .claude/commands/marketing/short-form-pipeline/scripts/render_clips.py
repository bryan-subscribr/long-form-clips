#!/usr/bin/env python3
"""
render_clips.py — Final step of the short-form-repurposing workflow.

Takes the clips Claude selected + approved (clips.json) and renders each one:
Whisper-transcribes just that window for accurate word-level caption timing, then
cuts + (9:16 smart crop | 16:9 letterbox) + burns CONTINUOUS word-highlight
captions. Writes the MP4s and a ready-to-post METADATA.md into the output folder.

Usage:
  python3 render_clips.py --workdir DIR --clips clips.json --out OUTDIR \
      [--aspect 9:16|16:9] [--no-captions] [--model small]

  --aspect 9:16   (default) vertical Shorts, 1080x1920, face-tracked crop, 60s cap
  --aspect 16:9   horizontal long-form clips, 1920x1080, no crop, 15 min cap
  --no-captions   skip burned-in captions (common for horizontal clips)
  --encoder       libx264 (default, ~5 min per 10-min AV1 clip) or h264_videotoolbox (macOS, 3-5x faster)
  --start-index N number the first clip NN_ from N when adding to an existing folder

clips_result.json is written after EVERY clip and merged by output file, so a
killed run keeps its bookkeeping and a re-render replaces rather than duplicates.
Long AV1 sources: run this in the background or in chunks; a 10-minute foreground
tool timeout will not lose finished clips any more, but it will stop the run.

clips.json: [{"start","end","title","hook_line","open_loop","caption","pinned_comment",
               "thumbnail_text"?, "thumb_line"?, "thumb_frame_at"?, "thumb_side"?, "thumb_ref"?}, ...]
 thumb_ref = path to any clean frame of the speaker; the picker then rejects the host's close-ups
 thumb_crop_bottom = e.g. 0.15 when the SOURCE has burned-in captions / lower-third; frames are cropped so
                     the thumb text lands on clean pixels (the MP4 is never cropped)
(start/end/thumb_frame_at accept MM:SS, HH:MM:SS or seconds; thumb_frame_at is ABSOLUTE source
 time — when present pick_thumb_frame.py ranks a ±15 s window and writes a 1280x720 JPEG next to
 the MP4 plus a *.thumb-candidates.jpg contact sheet)
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from timeutil import parse_time_to_seconds as to_sec  # noqa: E402
from video_clipper import MAX_MID_DURATION, MAX_SHORT_DURATION, VideoClipper  # noqa: E402


def load_results(out_dir: str) -> list[dict]:
    path = f"{out_dir}/clips_result.json"
    if not os.path.exists(path):
        return []
    try:
        return json.load(open(path))
    except json.JSONDecodeError:
        return []


def upsert_result(results: list[dict], entry: dict) -> list[dict]:
    """Replace the entry with the same output file, else append. Keeps NN_ order."""
    key = entry.get("file") or entry.get("_target")
    kept = [r for r in results if (r.get("file") or r.get("_target")) != key]
    kept.append(entry)
    return sorted(kept, key=lambda r: os.path.basename(r.get("file") or r.get("_target") or ""))


def save_results(out_dir: str, results: list[dict]) -> None:
    json.dump(results, open(f"{out_dir}/clips_result.json", "w"), indent=2, default=str)


def warn_if_failed(label: str, proc: subprocess.CompletedProcess) -> None:
    if proc.returncode != 0:
        tail = (proc.stderr or "").strip()[-300:]
        print(f"   WARN {label}: exit {proc.returncode} {tail}", flush=True)


def write_metadata(out_dir: str, meta: dict, results: list[dict], aspect: str = "9:16") -> None:
    kind = "Shorts" if aspect == "9:16" else "Clips"
    lines = [
        f"# {kind} from: {meta.get('title', '')}",
        f"Format: {aspect} ({'1080x1920' if aspect == '9:16' else '1920x1080'})",
        f"Source: {meta.get('url', '')}",
        "",
        "Ready-to-post titles, captions, and pinned comments for each clip.",
        "",
    ]
    for i, r in enumerate(results, 1):
        fn = os.path.basename(r["file"]) if r.get("file") else "RENDER FAILED"
        lines += [
            f"## {i}. {r.get('title', '')}  ({r.get('start')}–{r.get('end')})",
            f"**File:** {fn}",
            f"**Hook:** {r.get('hook_line', '')}",
            f"**Open loop:** {r.get('open_loop', '')}",
            *( [f"**Thumbnail text:** {r.get('thumbnail_text', '')}",
                f"**Thumb line:** {r.get('thumb_line', '')}",
                f"**Thumb frame:** {os.path.basename(r['thumb_frame']) if r.get('thumb_frame') else ''}"] if aspect == "16:9" else [] ),
            f"**Caption:** {r.get('caption', '')}",
            f"**Pinned comment:** {r.get('pinned_comment', '')}",
            "",
        ]
    Path(f"{out_dir}/METADATA.md").write_text("\n".join(lines))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--clips", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="small")
    ap.add_argument("--aspect", choices=["9:16", "16:9"], default="9:16")
    ap.add_argument("--no-captions", action="store_true")
    ap.add_argument("--start-index", type=int, default=1, help="number the first clip NN_ from here (append to an existing folder)")
    ap.add_argument("--encoder", default="libx264", help="libx264 or h264_videotoolbox (macOS hardware, much faster)")
    ap.add_argument("--append", action="store_true", help=argparse.SUPPRESS)  # always on now; kept so old commands do not break
    args = ap.parse_args()
    clip_type = "vertical_short" if args.aspect == "9:16" else "horizontal_mid"
    cap = MAX_SHORT_DURATION if args.aspect == "9:16" else MAX_MID_DURATION

    meta = json.load(open(f"{args.workdir}/meta.json"))
    src = meta["source"]
    clips = json.load(open(args.clips))
    out_dir = os.path.expanduser(args.out)
    os.makedirs(out_dir, exist_ok=True)

    vc = VideoClipper(use_whisper=False)
    vc.video_encoder = args.encoder
    model = None
    if not args.no_captions:
        import whisper  # noqa: WPS433 — only needed when burning captions

        print(f"loading whisper {args.model}...", flush=True)
        model = whisper.load_model(args.model)

    results = load_results(out_dir)
    for i, c in enumerate(clips, args.start_index):
        s, e = to_sec(c["start"]), to_sec(c["end"])
        if e - s > cap:
            print(f"WARNING clip {i}: {e - s:.0f}s exceeds {cap}s cap for {args.aspect}; will be truncated", flush=True)
        words, text = [], ""
        if model is not None:
            aud = f"{args.workdir}/seg_{i}.wav"
            warn_if_failed(f"clip {i} audio extract", subprocess.run(
                ["ffmpeg", "-y", "-ss", str(s), "-t", str(e - s), "-i", src,
                 "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", aud],
                capture_output=True, text=True,
            ))
            r = model.transcribe(aud, word_timestamps=True, language="en", verbose=False)
            words = [
                {"word": w["word"].strip(), "start": round(w["start"] + s, 3), "end": round(w["end"] + s, 3)}
                for seg in r["segments"] for w in seg.get("words", [])
            ]
            text = r["text"].strip()
        seg = {"start_time": s, "end_time": e, "text": text, "word_timestamps": words}
        safe = re.sub(r"[^\w-]", "_", c.get("title", f"clip{i}"))[:44].strip("_")
        out = f"{out_dir}/{i:02d}_{safe}.mp4"
        ok = vc.create_single_clip(src, seg, clip_type, out, captions=not args.no_captions)
        thumb_frame = None
        if c.get("thumb_frame_at") is not None:
            # Never grab the exact spoken second (mid-word). Rank a ±15 s window for a
            # composed, close-up face and keep a contact sheet for human review.
            thumb_frame = out[:-4] + ".thumb-frame.jpg"
            sheet = out[:-4] + ".thumb-candidates.jpg"
            cand_dir = f"{args.workdir}/thumbcands/{i:02d}"
            picker = subprocess.run(
                [sys.executable, str(Path(__file__).resolve().parent / "pick_thumb_frame.py"), src,
                 "--at", str(c["thumb_frame_at"]), "--side", str(c.get("thumb_side", "any")),
                 "--out", thumb_frame, "--sheet", sheet, "--cand-dir", cand_dir,
                 *(["--ref", os.path.expanduser(str(c["thumb_ref"]))] if c.get("thumb_ref") else []),
                 "--window", str(c.get("thumb_window", 15)),
                 *(["--crop-bottom", str(c["thumb_crop_bottom"])] if c.get("thumb_crop_bottom") else []),
                 *(["--ref-min", str(c["thumb_ref_min"])] if c.get("thumb_ref_min") else [])],
                capture_output=True, text=True,
            )
            if picker.stdout.strip():
                print(f"   thumb: {picker.stdout.strip().splitlines()[0]}", flush=True)
            warn_if_failed(f"clip {i} thumb picker", picker)
            if not os.path.exists(thumb_frame):
                # Fallback: plain grab at the spoken second.
                print(f"   WARN clip {i}: picker produced no frame, falling back to the spoken second", flush=True)
                warn_if_failed(f"clip {i} thumb fallback grab", subprocess.run(
                    ["ffmpeg", "-y", "-ss", str(to_sec(c["thumb_frame_at"])), "-i", src, "-frames:v", "1",
                     "-vf", "scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2",
                     "-q:v", "2", thumb_frame],
                    capture_output=True, text=True,
                ))
                if not os.path.exists(thumb_frame):
                    thumb_frame = None
        # Drop caption sidecars so the delivery folder holds only MP4s + metadata.
        for ext in (".ass", ".srt"):
            side = out[:-4] + ext
            if os.path.exists(side):
                os.remove(side)
        results = upsert_result(results, {**c, "file": out if ok else None, "_target": out, "ok": ok, "thumb_frame": thumb_frame})
        save_results(out_dir, results)          # written after EVERY clip: a killed run keeps its bookkeeping
        print(f"clip {i}: {'ok' if ok else 'FAIL'} -> {out}", flush=True)

    write_metadata(out_dir, meta, results, args.aspect)
    save_results(out_dir, results)
    print(f"\nDONE -> {out_dir}")


if __name__ == "__main__":
    main()
