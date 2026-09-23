#!/usr/bin/env python3
"""
shortform_pipeline.py — Principle-driven YouTube Shorts repurposing pipeline.

Takes one long-form YouTube video and produces several 9:16 vertical clips,
each edited to feel like a NATIVE Short (not a raw clip), plus per-clip
metadata (title, ready-to-post caption, hook, open loop, pinned comment).

The cutting and captions are built around the viral short-form principles from
the reference podcast (see PRINCIPLES.md):

  1. "The best hooks don't have a hook" — start ON the shock, never a preamble.
  2. A great hook does three things: SHOCK (ideally visual), sets a CLEAR
     EXPECTATION, and opens a loop that gives a reason to watch to the end.
  3. Curiosity = specific about WHAT happens, but they don't know HOW.
  4. Cut ALL the fluff — sponsor reads and subscribe asks never belong in a clip.
  5. One complete idea per clip; end on a complete thought.
  6. YouTube rewards storytelling / narrative.

Architecture: Claude does the segmentation (the "brain"); VideoClipper does the
smart 9:16 face-crop + word-highlighted ASS captions (the "hands"). This fuses
the two previously split-brained scripts into one.

Usage:
  python3 shortform_pipeline.py --url URL [--max-clips 3] [--output-dir DIR]
  python3 shortform_pipeline.py --url URL --dry-run   # plan only, no render
"""

import argparse
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

import anthropic

# Reuse the rendering engine (smart crop + word-highlight ASS captions).
sys.path.insert(0, str(Path(__file__).resolve().parent))
from video_clipper import VideoClipper  # noqa: E402

# ── Models ──────────────────────────────────────────────────────────────────────
# Cheap model for the verification pass, stronger model for the judgment call.
# Keeps API cost / subscription usage down.
SEGMENTATION_MODEL = os.environ.get("SHORTFORM_SEG_MODEL", "claude-sonnet-4-6")
VERIFY_MODEL = os.environ.get("SHORTFORM_VERIFY_MODEL", "claude-haiku-4-5-20251001")

# ── Output specs ─────────────────────────────────────────────────────────────────
MIN_CLIP_SECONDS = 20
MAX_CLIP_SECONDS = 60          # YouTube Shorts hard ceiling
TRIM_OVERSHOOT_TO = 58         # if Claude overshoots, trim to just under the cap

DATA_DIR = Path(os.environ.get("PIPELINE_WORKSPACE", Path.cwd())) / "data" / "clips"

# ── Ad / CTA / self-promo guard ──────────────────────────────────────────────────
# Deterministic safety net: any candidate whose opening leans on these markers is
# a sponsor read or a subscribe ask, never a clip. (Principle 4.)
AD_MARKERS = [
    r"\bsubscribe\b", r"hit the (subscribe|like)", r"favou?r to ask",
    r"link (down )?below", r"link in (the )?(bio|description)",
    r"click the link", r"schedule a call", r"brought to you by",
    r"this (episode|video) is sponsored", r"promo code", r"use code\b",
    r"check out (our|my)", r"grow and monetize", r"book (the|any) guest",
    r"sign up", r"our (program|course|sponsor)", r"for free\b",
]
AD_MARKER_RE = re.compile("|".join(AD_MARKERS), re.IGNORECASE)


def log(msg: str) -> None:
    print(f"[shortform] {msg}", flush=True)


# ── Time helpers ─────────────────────────────────────────────────────────────────

from timeutil import parse_time_to_seconds, seconds_to_mmss  # noqa: E402,F401


# ── Anthropic ────────────────────────────────────────────────────────────────────

def get_anthropic_client() -> anthropic.Anthropic:
    key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_KEY")
    if not key:
        raise RuntimeError("No ANTHROPIC_API_KEY found. Set it before running.")
    return anthropic.Anthropic(api_key=key)


def call_claude(client: anthropic.Anthropic, model: str, prompt: str,
                max_tokens: int = 3000, retries: int = 4) -> str:
    """Call Claude with exponential backoff on rate limits / transient errors."""
    delay = 2.0
    for attempt in range(retries):
        try:
            message = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text.strip()
        except (anthropic.RateLimitError, anthropic.APIStatusError) as e:
            if attempt == retries - 1:
                raise
            log(f"Claude call failed ({type(e).__name__}); retrying in {delay:.0f}s...")
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("Claude call exhausted retries")


def extract_json(raw: str):
    """Pull the first JSON array/object out of a model response."""
    match = re.search(r"(\[[\s\S]+\]|\{[\s\S]+\})", raw)
    if not match:
        raise ValueError(f"No JSON found in response:\n{raw[:500]}")
    return json.loads(match.group(1))


# ── Transcript ───────────────────────────────────────────────────────────────────

def transcript_to_text(segments: list[dict]) -> str:
    """Render Whisper segments as a timestamped transcript for Claude."""
    return "\n".join(
        f"[{seconds_to_mmss(seg['start'])}] {seg['text'].strip()}" for seg in segments
    )


def transcript_window(segments: list[dict], center: float, window: float = 12.0) -> str:
    lo, hi = center - window, center + window
    return "\n".join(
        f"[{seconds_to_mmss(s['start'])}] {s['text'].strip()}"
        for s in segments if s["end"] >= lo and s["start"] <= hi
    )


# ── Segmentation prompt (the principles live here) ───────────────────────────────

SEGMENTATION_PROMPT = """You are a world-class YouTube Shorts editor. You turn long-form \
podcasts and interviews into vertical clips that feel NATIVE to Shorts — edited, not raw.

You will get a timestamped transcript. Find the {N} best standalone moments and return them
as clips. Judge every candidate against these rules, which come from a top short-form creator:

THE HOOK IS EVERYTHING. A great hook does three things:
  1. SHOCK — the opening throws the viewer off ("wait, what did I just hear?"). Ideally the
     shock is VISUAL, because people see faster than they hear.
  2. CLEAR EXPECTATION — within the first line the viewer knows what they're going to get.
  3. OPEN LOOP — a reason to watch to the end. Curiosity works when you are SPECIFIC about
     WHAT is going to happen but the viewer does NOT know HOW it happens yet.

"THE BEST HOOKS DON'T HAVE A HOOK." Do NOT start a clip on a preamble or a wind-up like
"I'm about to ask the craziest question" or "you won't believe what happens." Set start_time
directly ON the shocking line, question, or claim itself. The video should feel like it
already started. It must sound like a human conversation, never a robot.

CUT ALL THE FLUFF. The clip must read as a standalone Short. NEVER include:
  - sponsor reads / ad reads ("this is brought to you by...", "schedule a call", promo codes)
  - subscribe / like asks ("hit subscribe", "link below", "favor to ask")
  - meta chit-chat, filler, or wind-up before the real moment.

ONE COMPLETE IDEA per clip. It must contain exactly one framework, story, claim, or
revelation — and END on a complete thought or reaction, never mid-sentence.

LENGTH: {min_s}-{max_s} seconds. Sweet spot 25-45s.

For each clip return an object with:
  - start_time: "MM:SS" — ON the shock, no preamble
  - end_time: "MM:SS" — on a complete thought
  - title: short YouTube Shorts title, UNDER 40 characters, complements the clip and hints
    at the payoff. NOT clickbait, no "you won't believe".
  - hook_line: the exact opening sentence of the clip (the shock)
  - shock_type: "visual" or "verbal"
  - clear_expectation: one line — what the viewer knows they're going to get
  - open_loop: the specific WHAT they're curious about, with the HOW withheld
  - payoff_sentence: the line where the loop closes / the takeaway lands
  - caption: a ready-to-post Shorts caption (1-2 sentences + 3-5 relevant hashtags)
  - pinned_comment: a comment to pin that sparks emotion or an (un)popular-opinion debate,
    designed to drive replies — never offensive
  - layout_hint: one of "talking_head", "screen_share_overlay", "side_by_side", "gallery_view"
  - why: one line on why this performs on Shorts

Return ONLY a valid JSON array of exactly {N} objects. No markdown, no commentary.

TRANSCRIPT:
{TRANSCRIPT}"""


def segment_with_claude(client: anthropic.Anthropic, transcript: str, n: int) -> list[dict]:
    prompt = (
        SEGMENTATION_PROMPT
        .replace("{N}", str(n))
        .replace("{min_s}", str(MIN_CLIP_SECONDS))
        .replace("{max_s}", str(MAX_CLIP_SECONDS))
        .replace("{TRANSCRIPT}", transcript)
    )
    log(f"Segmenting with {SEGMENTATION_MODEL}...")
    raw = call_claude(client, SEGMENTATION_MODEL, prompt, max_tokens=4000)
    clips = extract_json(raw)
    if isinstance(clips, dict):
        clips = [clips]
    return clips


def guard_and_clamp(clips: list[dict]) -> list[dict]:
    """Deterministic safety net: drop ad/CTA clips, enforce length. (Principle 4.)"""
    kept = []
    for clip in clips:
        hook = clip.get("hook_line", "")
        caption_src = f"{hook} {clip.get('clear_expectation', '')}"
        if AD_MARKER_RE.search(caption_src):
            log(f"  Dropping ad/CTA-flavored clip: {clip.get('title', '?')[:40]!r}")
            continue
        try:
            start = parse_time_to_seconds(clip["start_time"])
            end = parse_time_to_seconds(clip["end_time"])
        except Exception:
            log(f"  Dropping clip with unparseable times: {clip.get('title', '?')[:40]!r}")
            continue
        dur = end - start
        if dur < MIN_CLIP_SECONDS:
            log(f"  Dropping too-short clip ({dur:.0f}s): {clip.get('title', '?')[:40]!r}")
            continue
        if dur > MAX_CLIP_SECONDS:
            log(f"  Trimming overshoot ({dur:.0f}s -> {TRIM_OVERSHOOT_TO}s): {clip.get('title', '?')[:40]!r}")
            clip["end_time"] = seconds_to_mmss(start + TRIM_OVERSHOOT_TO)
        kept.append(clip)
    return kept


# ── Cut verification (Principle 5: end on a complete thought) ─────────────────────

def verify_cut(client: anthropic.Anthropic, clip: dict, segments: list[dict]) -> dict:
    end_sec = parse_time_to_seconds(clip["end_time"])
    window = transcript_window(segments, end_sec, window=12.0)
    prompt = f"""Does this short-form clip end on a COMPLETE thought?

Proposed end time: {clip['end_time']}
Payoff line: "{clip.get('payoff_sentence', '')}"

Transcript around the end (±12s):
{window}

If the thought continues past {clip['end_time']}, give the corrected end_time where it
actually resolves. The clip must never end mid-sentence or mid-idea.

Return ONLY JSON: {{"end_is_clean": true/false, "corrected_end_time": "MM:SS", "reason": "..."}}"""
    try:
        raw = call_claude(client, VERIFY_MODEL, prompt, max_tokens=300)
        v = extract_json(raw)
    except Exception as e:
        log(f"  Cut-verify skipped ({e}); keeping {clip['end_time']}")
        return clip
    if not v.get("end_is_clean") and v.get("corrected_end_time"):
        log(f"  Cut corrected {clip['end_time']} -> {v['corrected_end_time']} ({v.get('reason','')})")
        clip["end_time"] = v["corrected_end_time"]
    return clip


# ── Main pipeline ────────────────────────────────────────────────────────────────

def process_video(url: str, client: anthropic.Anthropic, args, work_dir: str) -> list[dict]:
    results: list[dict] = []
    clipper = VideoClipper(dry_run=False, use_whisper=True)

    video_path = os.path.join(work_dir, "source.mp4")
    if not clipper.download_video(url, video_path):
        log("Download failed.")
        return []

    audio_path = os.path.join(work_dir, "audio.wav")
    if not clipper.extract_audio(video_path, audio_path):
        log("Audio extraction failed.")
        return []

    whisper_result = clipper.transcribe_with_whisper(audio_path)
    if not whisper_result:
        log("Whisper transcription failed.")
        return []

    word_timestamps = whisper_result["words"]
    segments = whisper_result["segments"]
    transcript = transcript_to_text(segments)
    log(f"Transcript: {len(segments)} segments, {len(word_timestamps)} words")

    clips = segment_with_claude(client, transcript, args.max_clips)
    clips = guard_and_clamp(clips)
    log(f"{len(clips)} clip(s) passed the guard")

    for i, clip in enumerate(clips):
        clips[i] = verify_cut(client, clip, segments)

    output_dir = args.output_dir or os.path.join(work_dir, "output")
    os.makedirs(output_dir, exist_ok=True)

    for i, clip in enumerate(clips, 1):
        start = parse_time_to_seconds(clip["start_time"])
        end = parse_time_to_seconds(clip["end_time"])
        safe = re.sub(r"[^\w\s-]", "", clip.get("title", f"clip_{i}"))[:50].replace(" ", "_")
        final_path = os.path.join(output_dir, f"{i:02d}_{safe}.mp4")

        meta = {
            "title": clip.get("title", safe),
            "start_time": clip["start_time"],
            "end_time": clip["end_time"],
            "duration_seconds": round(end - start, 1),
            "hook_line": clip.get("hook_line", ""),
            "shock_type": clip.get("shock_type", ""),
            "clear_expectation": clip.get("clear_expectation", ""),
            "open_loop": clip.get("open_loop", ""),
            "payoff_sentence": clip.get("payoff_sentence", ""),
            "caption": clip.get("caption", ""),
            "pinned_comment": clip.get("pinned_comment", ""),
            "layout_hint": clip.get("layout_hint", "talking_head"),
            "why": clip.get("why", ""),
            "source_url": url,
        }

        log(f"\n--- Clip {i}: {meta['title']} ({meta['duration_seconds']}s) ---")
        log(f"  Hook: {meta['hook_line'][:80]}")

        if args.dry_run:
            log("  [dry-run] skipping render")
            meta["local_path"] = None
            results.append(meta)
            continue

        segment = {
            "start_time": start,
            "end_time": end,
            "text": " ".join(
                s["text"] for s in segments if s["end"] > start and s["start"] < end
            ),
            "word_timestamps": word_timestamps,
        }
        ok = clipper.create_single_clip(video_path, segment, "vertical_short", final_path)
        meta["local_path"] = final_path if ok else None
        if ok:
            log(f"  Rendered: {final_path}")
        else:
            log(f"  Render failed for clip {i}")
        results.append(meta)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Principle-driven YouTube Shorts pipeline")
    parser.add_argument("--url", required=True, help="YouTube URL to repurpose")
    parser.add_argument("--max-clips", type=int, default=3, help="Clips to produce")
    parser.add_argument("--output-dir", help="Where to write final clips")
    parser.add_argument("--dry-run", action="store_true",
                        help="Plan clips + metadata without rendering (skips the ffmpeg render step)")
    args = parser.parse_args()

    client = get_anthropic_client()
    work_dir = tempfile.mkdtemp(prefix="shortform_")
    log(f"Work dir: {work_dir}")

    results = process_video(args.url, client, args, work_dir)

    print("\n" + "=" * 60)
    print(f"DONE — {len(results)} clip(s)")
    print("=" * 60)
    for r in results:
        print(f"\n  {r['title']}  [{r['start_time']}-{r['end_time']}, {r['duration_seconds']}s]")
        print(f"   Hook ({r['shock_type']}): {r['hook_line'][:90]}")
        print(f"   Open loop: {r['open_loop'][:90]}")
        print(f"   Caption: {r['caption'][:90]}")
        print(f"   Pinned: {r['pinned_comment'][:90]}")
        if r.get("local_path"):
            print(f"   File: {r['local_path']}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / "last-run-shortform.json"
    out.write_text(json.dumps(results, indent=2, default=str))
    log(f"Metadata written to {out}")


if __name__ == "__main__":
    main()
