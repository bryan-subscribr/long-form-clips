"""Shared time helpers for the short-form / long-form clip scripts.

Kept dependency-free so render_clips.py, pick_thumb_frame.py, finalize_delivery.py
and fetch.py can import it without pulling in the Anthropic SDK that
shortform_pipeline.py needs.
"""


def parse_time_to_seconds(t) -> float:
    """Parse MM:SS / HH:MM:SS / seconds (int, float, or numeric string) into float seconds."""
    if isinstance(t, (int, float)):
        return float(t)
    parts = str(t).strip().split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    return float(t)


def seconds_to_mmss(s: float) -> str:
    return f"{int(s) // 60:02d}:{int(s) % 60:02d}"
