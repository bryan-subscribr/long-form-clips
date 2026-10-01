#!/usr/bin/env python3
"""
Tests for check_package.py — the title/thumb gate the long-form pipeline runs on every clip.
No network, no media. Run:  python3 test_check_package.py
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_package as cp  # noqa: E402

# Same shape fetch.py writes: one [MM:SS] stamp per ~45 s paragraph.
PARAGRAPHS = """[00:00] Welcome back to the show, today we're talking about sales.
[01:10] So many women tell me the prospect ghosts them after the call.
[02:30] Here is the fix: you stop chasing and you start leading the conversation.
[04:00] And that's why the follow up matters more than the pitch.
[09:00] Totally different topic about hiring your first assistant.
"""
TITLE = "If You Keep Getting Ghosted After the Call, Do This"
THUMB = "Stop **chasing**"


def transcript(text=PARAGRAPHS):
    fd, path = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


class Overlap(unittest.TestCase):
    def test_trailing_period_does_not_hide_overlap(self):
        hard, _, _ = cp.check_full("Why You Should Start Before You're Ready", "Just **start.**")
        self.assertTrue(any("OVERLAP" in h for h in hard), hard)

    def test_clean_pair_passes(self):
        hard, _, _ = cp.check_full(TITLE, THUMB)
        self.assertEqual(hard, [])


class Banned(unittest.TestCase):
    def test_whole_word_only(self):
        hard, _, _ = cp.check_full("I Asked Alexa How to Close More Deals", "Ask **better**")
        self.assertFalse(any("banned" in h for h in hard), hard)

    def test_speaker_name_from_ban_list_including_possessive(self):
        hard, _, _ = cp.check_full("Shelby's Rule for Closing Without Pressure", "Lead the **call**", ban=["shelby", "sapp"])
        self.assertIn("banned in title: 'shelby'", hard)

    def test_symbol_bans_still_substring(self):
        hard, _, _ = cp.check_full("The #1 Mistake New Closers Make on Calls", "Too **polite**")
        self.assertIn("banned in title: '#1'", hard)


class StaleYear(unittest.TestCase):
    def test_last_year_is_stale_this_year_is_not(self):
        hard, _, _ = cp.check_full(f"The Sales Skill That Paid Off Most in {cp.THIS_YEAR - 1}", "Ask **twice**")
        self.assertTrue(any("stale year" in h for h in hard), hard)
        hard, _, _ = cp.check_full(f"The Sales Skill That Pays Off Most in {cp.THIS_YEAR}", "Ask **twice**")
        self.assertFalse(any("stale year" in h for h in hard), hard)


class Transcript(unittest.TestCase):
    def test_bracket_transcript_is_parsed(self):
        segs = cp.load_transcript(transcript())
        self.assertEqual([s for s, _, _ in segs], [0.0, 70.0, 150.0, 240.0, 540.0])
        self.assertEqual(segs[1][1], 150.0)   # a paragraph ends where the next begins

    def test_unreadable_transcript_is_a_hard_fail(self):
        hard, _, _ = cp.check_full(TITLE, THUMB, transcript("just prose, no timestamps\n"))
        self.assertTrue(any("could not read" in h for h in hard), hard)

    def test_three_word_thumb_position_is_where_the_words_are(self):
        _, _, info = cp.check_full(TITLE, "Stop chasing **leads**", transcript(), start="01:00", end="05:00")
        self.assertEqual(info["thumb_hits"], ["chasing", "leads", "stop"])
        self.assertEqual(info["thumb_pos"], 90.0)   # the 02:30 paragraph, 90 s into a clip starting at 01:00

    def test_thumb_line_inside_the_window_passes(self):
        hard, _, info = cp.check_full(TITLE, THUMB, transcript(), start="01:00", end="05:00",
                                      thumb_line='02:31 "you stop chasing and you start leading"')
        self.assertEqual(hard, [])
        self.assertEqual(info["line_pos"], 90.0)

    def test_thumb_line_outside_the_window_fails(self):
        hard, _, _ = cp.check_full(TITLE, THUMB, transcript(), start="08:00", end="10:00",
                                   thumb_line="you stop chasing and you start leading")
        self.assertTrue(any("thumb line not found" in h for h in hard), hard)

    def test_paraphrase_thumb_passes_when_its_line_is_spoken(self):
        # "Lead, don't **follow**" says none of the words aloud; its source line is in the clip.
        hard, soft, _ = cp.check_full(TITLE, "Lead, don't **follow**", transcript(), start="01:00", end="05:00",
                                      thumb_line="you start leading the conversation")
        self.assertEqual(hard, [])
        self.assertFalse(any("no thumb word" in s for s in soft), soft)

    def test_line_of_only_common_words_matches_word_for_word(self):
        text = PARAGRAPHS.replace("Here is the fix:", "I realized if they can do it, I can. Here is the fix:")
        hard, _, info = cp.check_full(TITLE, "So can **I**", transcript(text), start="01:00", end="05:00",
                                      thumb_line="If they can do it, I can.")
        self.assertEqual(hard, [])
        self.assertEqual(info["line_pos"], 90.0)
        hard, _, _ = cp.check_full(TITLE, "So can **I**", transcript(), start="01:00", end="05:00",
                                   thumb_line="If they can do it, I can.")
        self.assertTrue(any("thumb line not found" in h for h in hard), hard)

    def test_tab_separated_transcript_still_works(self):
        hard, _, info = cp.check_full(TITLE, THUMB, transcript("150.0\t156.0\tyou stop chasing and start leading\n"),
                                      thumb_line="stop chasing")
        self.assertEqual(hard, [])
        self.assertEqual(info["line_pos"], 0.0)


class Cli(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(HERE / "check_package.py"), "--title", TITLE, "--thumb", THUMB,
                               "--transcript", transcript(), *args], capture_output=True, text=True, encoding="utf-8")

    def test_exit_codes(self):
        self.assertEqual(self.run_cli("--start", "01:00", "--end", "05:00", "--thumb-line", "stop chasing").returncode, 0)
        bad = self.run_cli("--start", "08:00", "--end", "10:00", "--thumb-line", "stop chasing")
        self.assertEqual(bad.returncode, 1, bad.stdout)
        self.assertIn("thumb line not found", bad.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=1)
