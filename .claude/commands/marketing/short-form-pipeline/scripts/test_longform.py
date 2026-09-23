#!/usr/bin/env python3
"""
Deterministic tests for the long-form clip path: transcript rebuild, time parsing,
result bookkeeping, thumb zoom geometry, and the delivery writer. No network, no
ffmpeg, no API key.

Run:  python3 test_longform.py
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fetch  # noqa: E402
import render_clips  # noqa: E402
from timeutil import parse_time_to_seconds, seconds_to_mmss  # noqa: E402

ROLLING_VTT = """WEBVTT
Kind: captions
Language: en

00:00:00.000 --> 00:00:01.500
When you teach a woman sales, she'll

00:00:01.500 --> 00:00:03.000
When you teach a woman sales, she'll
never go broke.

00:00:03.000 --> 00:00:04.500
never go broke.
Because there's always something to sell.

00:00:04.500 --> 00:00:06.000
Because there's always something to sell.
>> How do you become dangerous at sales?

00:00:06.000 --> 00:00:07.000
>> How do you become dangerous at sales?

00:00:07.000 --> 00:00:08.500
>> Mhm, you shut up. [music]
"""


class TimeUtil(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_time_to_seconds("1:30"), 90)
        self.assertEqual(parse_time_to_seconds("77:58"), 77 * 60 + 58)
        self.assertEqual(parse_time_to_seconds("01:05:10.5"), 3910.5)
        self.assertEqual(parse_time_to_seconds(42), 42.0)
        self.assertEqual(parse_time_to_seconds("42.5"), 42.5)

    def test_mmss(self):
        self.assertEqual(seconds_to_mmss(3910), "65:10")


class Reconstruct(unittest.TestCase):
    def test_rolling_captions_are_deduplicated_and_grouped(self):
        with tempfile.NamedTemporaryFile("w", suffix=".vtt", delete=False) as f:
            f.write(ROLLING_VTT)
        out = fetch.reconstruct(f.name)
        os.unlink(f.name)
        self.assertEqual(out.count("teach a woman sales"), 1)
        self.assertEqual(out.count("never go broke"), 1)
        self.assertEqual(out.count("dangerous at sales"), 1)
        lines = out.split("\n")
        self.assertEqual(len(lines), 3, out)            # narration, host turn, guest turn
        self.assertTrue(lines[1].startswith("[00:04] How do you become"))
        self.assertNotIn("[music]", out)
        self.assertNotIn(">>", out)


class ResultBookkeeping(unittest.TestCase):
    def test_upsert_replaces_same_file_and_sorts(self):
        r = render_clips.upsert_result([], {"file": "/x/02_b.mp4", "ok": True})
        r = render_clips.upsert_result(r, {"file": "/x/01_a.mp4", "ok": True})
        r = render_clips.upsert_result(r, {"file": "/x/02_b.mp4", "ok": True, "title": "redo"})
        self.assertEqual([os.path.basename(x["file"]) for x in r], ["01_a.mp4", "02_b.mp4"])
        self.assertEqual(r[1]["title"], "redo")

    def test_failed_render_keeps_slot_by_target(self):
        r = render_clips.upsert_result([], {"file": None, "_target": "/x/03_c.mp4", "ok": False})
        r = render_clips.upsert_result(r, {"file": "/x/03_c.mp4", "_target": "/x/03_c.mp4", "ok": True})
        self.assertEqual(len(r), 1)
        self.assertTrue(r[0]["ok"])

    def test_load_results_tolerates_missing_or_corrupt(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(render_clips.load_results(td), [])
            Path(td, "clips_result.json").write_text("{not json")
            self.assertEqual(render_clips.load_results(td), [])


class ZoomGeometry(unittest.TestCase):
    def test_zoom_stays_in_bounds_and_returns_720p(self):
        try:
            import numpy as np
            import pick_thumb_frame as ptf
        except ImportError:
            self.skipTest("opencv/numpy not installed")
        img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        for box in [(0, 0, 120, 120), (1800, 0, 120, 120), (900, 500, 120, 120), (0, 960, 120, 120)]:
            out = ptf.zoom_to_face(img, box)
            self.assertEqual(out.shape[:2], (720, 1280), box)

    def test_faces_below_upper_band_are_dropped(self):
        try:
            import pick_thumb_frame as ptf
        except ImportError:
            self.skipTest("opencv/numpy not installed")
        # monkeypatch the cascade so the test does not depend on Haar behaviour
        class Fake:
            def detectMultiScale(self, *a, **k):
                return [(10, 10, 100, 100), (10, 600, 100, 100)]
        import numpy as np
        old = ptf.FACE; ptf.FACE = Fake()
        try:
            kept = ptf.faces_in(np.zeros((720, 1280), dtype=np.uint8))
        finally:
            ptf.FACE = old
        self.assertEqual(kept, [(10, 10, 100, 100)])


class Captions(unittest.TestCase):
    def test_clip_srt_offsets_and_dedupes(self):
        import captions
        with tempfile.NamedTemporaryFile("w", suffix=".vtt", delete=False) as f:
            f.write(ROLLING_VTT)
        cues = captions.parse_rolling_vtt(f.name)
        os.unlink(f.name)
        self.assertEqual([t for t, _ in cues], [0.0, 1.5, 3.0, 4.5, 7.0])
        srt = captions.clip_srt(cues, start=3.0, end=8.5)
        self.assertTrue(srt.startswith("1\n00:00:00,000 --> 00:00:01,500\nBecause there's always something to sell."), srt)
        self.assertIn("00:00:01,500 --> 00:00:04,000\nHow do you become dangerous at sales?", srt)
        self.assertIn("Mhm, you shut up.", srt)
        self.assertNotIn("[music]", srt)
        self.assertNotIn(">>", srt)
        self.assertEqual(srt.count("-->"), 3)

    def test_clip_transcript_relative_times(self):
        import captions
        cues = [(120.0, "a"), (125.0, "b"), (200.0, "c")]
        out = captions.clip_transcript(cues, 120.0, 130.0)
        self.assertEqual(out, "[00:00] a\n[00:05] b")


class FinalizeDelivery(unittest.TestCase):
    def test_writes_txt_with_verbatim_description_and_timestamp_link(self):
        with tempfile.TemporaryDirectory() as td:
            mp4 = Path(td, "01_Test.mp4"); mp4.write_bytes(b"")
            json.dump([{"file": str(mp4), "ok": True, "start": "65:10", "end": "70:00", "title": "Test",
                        "thumbnail_text": "Price or **cost?**", "thumb_line": '65:12 "price or cost"',
                        "pinned_comment": "pc", "caption": "per-clip caption", "thumb_frame": None}],
                      open(Path(td, "clips_result.json"), "w"))
            desc = Path(td, "desc.txt"); desc.write_text("Line one\n\nRooting for you,\nShelby xo\n")
            Path(td, "src.en.vtt").write_text(ROLLING_VTT.replace("00:00:0", "01:05:1"))  # cues at 65:10+
            proc = subprocess.run([sys.executable, str(HERE / "finalize_delivery.py"), td, "--source-url",
                                   "https://www.youtube.com/watch?v=abc&pp=x", "--source-title", "T",
                                   "--description-file", str(desc), "--workdir", td], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            txt = Path(td, "01_Test.txt").read_text()
            self.assertIn("CAPTIONS", txt)
            self.assertIn("00:00:00,000 -->", txt)
            self.assertTrue(Path(td, "01_Test.srt").exists())
            self.assertIn("DESCRIPTION\nLine one\n\nRooting for you,\nShelby xo\n", txt)
            self.assertNotIn("per-clip caption", txt)
            self.assertIn("&t=3910s", txt)
            self.assertIn("(accent word in yellow: cost?)", txt)
            self.assertIn("| 1 | Test | 4:50 | Price or cost? |", Path(td, "README.md").read_text())


if __name__ == "__main__":
    unittest.main(verbosity=1)
