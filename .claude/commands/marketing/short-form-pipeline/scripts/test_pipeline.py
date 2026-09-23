#!/usr/bin/env python3
"""
Deterministic tests for the short-form pipeline's guard and time helpers.

These cover the non-negotiable, principle-driven logic that must hold regardless
of what Claude returns: ad/CTA reads are excluded, and clip length is enforced.
No API key or network required.

Run:  python3 test_pipeline.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import shortform_pipeline as sp  # noqa: E402


class TimeHelpers(unittest.TestCase):
    def test_parse_mmss(self):
        self.assertEqual(sp.parse_time_to_seconds("1:30"), 90)
        self.assertEqual(sp.parse_time_to_seconds("01:05:10"), 3910)
        self.assertEqual(sp.parse_time_to_seconds(42), 42.0)

    def test_roundtrip(self):
        self.assertEqual(sp.seconds_to_mmss(90), "01:30")
        self.assertEqual(sp.seconds_to_mmss(605), "10:05")


class AdGuard(unittest.TestCase):
    """Principle 4: sponsor reads and subscribe asks must never survive."""

    def test_drops_subscribe_ask(self):
        clips = [{
            "title": "Hit subscribe",
            "hook_line": "Can you please hit the subscribe button down below?",
            "clear_expectation": "a favor to ask",
            "start_time": "0:10", "end_time": "0:40",
        }]
        self.assertEqual(sp.guard_and_clamp(clips), [])

    def test_drops_sponsor_read(self):
        clips = [{
            "title": "Grow your podcast",
            "hook_line": "Do you want to grow and monetize your podcast?",
            "clear_expectation": "schedule a call down below",
            "start_time": "1:00", "end_time": "1:45",
        }]
        self.assertEqual(sp.guard_and_clamp(clips), [])

    def test_keeps_genuine_clip(self):
        clips = [{
            "title": "The best hooks have no hook",
            "hook_line": "First things first, the best hooks don't have a hook.",
            "clear_expectation": "how to open a clip so people can't scroll away",
            "start_time": "5:00", "end_time": "5:35",
        }]
        kept = sp.guard_and_clamp(clips)
        self.assertEqual(len(kept), 1)


class LengthClamp(unittest.TestCase):
    def test_drops_too_short(self):
        clips = [{"title": "x", "hook_line": "a real moment",
                  "start_time": "0:00", "end_time": "0:10"}]
        self.assertEqual(sp.guard_and_clamp(clips), [])

    def test_trims_overshoot(self):
        clips = [{"title": "long one", "hook_line": "a real standalone story",
                  "start_time": "0:00", "end_time": "2:00"}]
        kept = sp.guard_and_clamp(clips)
        self.assertEqual(len(kept), 1)
        end = sp.parse_time_to_seconds(kept[0]["end_time"])
        self.assertLessEqual(end, sp.MAX_CLIP_SECONDS)
        self.assertEqual(end, sp.TRIM_OVERSHOOT_TO)


if __name__ == "__main__":
    unittest.main(verbosity=2)
