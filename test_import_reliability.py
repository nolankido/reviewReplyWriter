"""Regression tests for defects reproduced during repository import."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import review_reply as rr
from test_review_reply import (
    ANGRY, GLOWING, GOOD_MODEL_OUTPUT, GOOD_NEGATIVE_REPLY,
    GOOD_FOLLOWUP_HAPPY, UPDATE_HAPPY, UPDATE_STILL_BAD,
)


class SavedDraftTests(unittest.TestCase):
    def test_context_and_multiline_review_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            review = ANGRY + "\n## The reply\nAn extra customer line."
            business = "Coffee; kind=shop <!-- cafe -->"
            path = rr.save_reply_file(
                tmp, business, review, GOOD_NEGATIVE_REPLY, "test", "warm",
                "cafe", "negative", "google", stars=2,
                offer="the next round is on us", signoff="Nolan",
                voice={"opener": "Mahalo"}, choices=2)
            draft = rr.parse_draft(path)
            self.assertEqual(draft["platform"], "google")
            self.assertEqual(draft["business"], business)
            self.assertEqual(draft["review"], review)
            self.assertEqual(draft["reply"], GOOD_NEGATIVE_REPLY)
            self.assertEqual(draft["stars"], 2)
            self.assertEqual(draft["voice"], {"opener": "Mahalo"})
            self.assertEqual(draft["choices"], 2)

    def test_legacy_platform_at_end_of_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "old.md"
            path.write_text(
                "<!-- Drafted today by test; business=Moe's Coffee; "
                "tone=warm; kind=cafe; tier=negative; platform=google -->"
                "\n\n## The review\n\n> Cold coffee\n\n"
                "## The reply\n\nA draft.\n", encoding="utf-8")
            self.assertEqual(rr.parse_draft(path)["platform"], "google")

    def test_reroll_keeps_offer_signoff_and_platform(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = rr.save_reply_file(
                tmp, "Moe's Coffee", ANGRY, "old draft", "test", "warm",
                "cafe", "negative", "google", stars=2,
                offer="the next round is on us", signoff="Nolan")
            rr.reroll_draft(path, "professional", "test", True)
            draft = rr.parse_draft(path)
            self.assertIn("the next round is on us", draft["reply"])
            self.assertIn("Nolan", draft["reply"].splitlines()[-1])
            self.assertEqual(draft["platform"], "google")
            self.assertEqual(draft["tone"], "professional")
            self.assertEqual(draft["offer"], "the next round is on us")

    def test_followup_reroll_preserves_thread_and_does_not_repeat_offer(self):
        offer = "the next round is on us"
        with tempfile.TemporaryDirectory() as tmp:
            path = rr.save_reply_file(
                tmp, "Moe's Coffee", UPDATE_STILL_BAD, "old", "test",
                "warm", "cafe", "negative", original=ANGRY,
                previous=GOOD_NEGATIVE_REPLY + "\n" + offer, offer=offer)
            rr.reroll_draft(path, "warm", "test", True)
            draft = rr.parse_draft(path)
            self.assertEqual(draft["original"], ANGRY)
            self.assertEqual(draft["previous"], GOOD_NEGATIVE_REPLY + "\n" + offer)
            self.assertNotIn(offer, draft["reply"])
            self.assertTrue(rr.validate_followup(
                draft["reply"], ANGRY, GOOD_NEGATIVE_REPLY + "\n" + offer,
                UPDATE_STILL_BAD, "Moe's Coffee", offer=offer))

    def test_followup_reroll_uses_model_thread(self):
        prompts = []
        def caller(prompt, model, temp):
            prompts.append(prompt)
            return GOOD_FOLLOWUP_HAPPY
        with tempfile.TemporaryDirectory() as tmp:
            path = rr.save_reply_file(
                tmp, "Moe's Coffee", UPDATE_HAPPY, "old", "test", "warm",
                "cafe", "positive", original=ANGRY,
                previous=GOOD_NEGATIVE_REPLY)
            rr.reroll_draft(path, "warm", "test", False, caller=caller)
            self.assertIn(ANGRY, prompts[0])
            self.assertIn(GOOD_NEGATIVE_REPLY, prompts[0])
            self.assertEqual(rr.parse_draft(path)["reply"], GOOD_FOLLOWUP_HAPPY)

    def test_failed_replace_leaves_existing_draft_intact(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = rr.save_reply_file(
                tmp, "Moe's Coffee", ANGRY, "original draft", "test",
                "warm", "cafe", "negative")
            before = Path(path).read_bytes()
            with patch.object(rr.os, "replace", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    rr.reroll_draft(path, "warm", "test", True)
            self.assertEqual(Path(path).read_bytes(), before)
            self.assertEqual(os.listdir(tmp), [Path(path).name])

    def test_batch_retains_owner_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = rr.run_batch(
                [{"review": ANGRY}], tmp, "test", True,
                defaults={"business": "Moe's Coffee", "stars": 2,
                          "offer": "the next round is on us",
                          "signoff": "Nolan", "platform": "google"})
            draft = rr.parse_draft(Path(tmp) / results[0]["file"])
            self.assertEqual(draft["stars"], 2)
            self.assertEqual(draft["offer"], "the next round is on us")
            self.assertEqual(draft["signoff"], "Nolan")


class ResponseTests(unittest.TestCase):
    def test_malformed_candidates_fall_back(self):
        for bad in (None, [], {}, 42, ""):
            with self.subTest(candidate=bad):
                reply, reason = rr.generate_with_model(
                    GLOWING, "Moe's Coffee", "warm", 5, "cafe", "test",
                    caller=lambda *args: bad)
                self.assertIsNone(reply)
                self.assertIn("twice", reason)

    def test_invalid_json_falls_back(self):
        def caller(*args):
            raise json.JSONDecodeError("invalid", "", 0)
        reply, reason = rr.generate_with_model(
            GLOWING, "Moe's Coffee", "warm", 5, "cafe", "test", caller=caller)
        self.assertIsNone(reply)
        self.assertIn("unavailable", reason)

    def test_followup_invalid_json_falls_back(self):
        def caller(*args):
            raise json.JSONDecodeError("invalid", "", 0)
        reply, reason = rr.generate_followup(
            ANGRY, GOOD_NEGATIVE_REPLY, UPDATE_HAPPY, "Moe's Coffee",
            "warm", "cafe", "test", caller=caller)
        self.assertIsNone(reply)
        self.assertIn("unavailable", reason)

    def test_ollama_rejects_invalid_response_shapes(self):
        for value in ({}, {"response": None}, {"response": []}, [], 42):
            with self.subTest(value=value):
                with patch.object(rr.urllib.request, "urlopen",
                                  return_value=io.BytesIO(json.dumps(value).encode())):
                    with self.assertRaises(ValueError):
                        rr.call_ollama("prompt", "test")

    def test_custom_signoff_is_required_at_end(self):
        self.assertFalse(rr.validate_reply(
            GOOD_MODEL_OUTPUT, GLOWING, "Moe's Coffee", 5, signoff="Nolan"))
        self.assertTrue(rr.validate_reply(
            GOOD_MODEL_OUTPUT + "\n- Nolan", GLOWING, "Moe's Coffee", 5,
            signoff="Nolan"))

    def test_followup_custom_signoff_is_required_at_end(self):
        self.assertFalse(rr.validate_followup(
            GOOD_FOLLOWUP_HAPPY, ANGRY, GOOD_NEGATIVE_REPLY, UPDATE_HAPPY,
            "Moe's Coffee", signoff="Nolan"))
        self.assertTrue(rr.validate_followup(
            GOOD_FOLLOWUP_HAPPY + "\n- Nolan", ANGRY, GOOD_NEGATIVE_REPLY,
            UPDATE_HAPPY, "Moe's Coffee", signoff="Nolan"))


class CliTests(unittest.TestCase):
    def test_batch_receives_cli_star_default(self):
        with patch.object(rr, "read_batch_csv", return_value=[]), \
                patch.object(rr, "run_batch", return_value=[]) as run, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(rr.main(["--batch", "reviews.csv", "--stars", "2",
                                      "--offline"]), 0)
        self.assertEqual(run.call_args.kwargs["defaults"]["stars"], 2)


if __name__ == "__main__":
    unittest.main()
