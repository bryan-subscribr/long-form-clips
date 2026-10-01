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


def utf8_console() -> None:
    """Print UTF-8 whatever the console code page is.

    On Windows a piped stdout defaults to cp1252, so printing a YouTube title with an
    emoji (fetch.py prints TITLE=...) raises UnicodeEncodeError and kills the run.
    """
    import sys

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
