#!/usr/bin/env python3
"""Tests for check_submission.py - stdlib unittest only."""
import os
import unittest

import check_submission as cs


class PostFindingsTests(unittest.TestCase):
    def test_stale_test_count_is_a_blocker(self):
        blockers, _ = cs.post_findings(
            "Ran 99 tests\ntags: devchallenge, hf26challenge", 40, True)
        self.assertTrue(any("99" in b for b in blockers))

    def test_matching_count_and_tags_pass(self):
        blockers, _ = cs.post_findings(
            "Ran 40 tests\ntags: devchallenge, hf26challenge", 40, True)
        self.assertEqual(blockers, [])

    def test_missing_tag_is_a_blocker(self):
        blockers, _ = cs.post_findings("Ran 40 tests", 40, True)
        self.assertTrue(any("tag" in b for b in blockers))

    def test_real_review_placeholder_is_a_todo_not_a_blocker(self):
        blockers, todos = cs.post_findings(
            "Ran 40 tests\ntags: devchallenge, hf26challenge\n"
            "[REAL REVIEW TEST - replace me]", 40, True)
        self.assertEqual(blockers, [])
        self.assertTrue(any("REAL REVIEW" in t for t in todos))

    def test_failing_suite_is_a_blocker(self):
        blockers, _ = cs.post_findings(
            "Ran 40 tests\ntags: devchallenge, hf26challenge", 40,
            False)
        self.assertTrue(any("not green" in b for b in blockers))


class GalleryParseTests(unittest.TestCase):
    def test_gallery_replies_parse_with_credits(self):
        for stem, _, _ in cs.GALLERY:
            path = os.path.join(cs.EXAMPLES, f"{stem}-reply.md")
            engine, platform, reply = cs.parse_saved_reply(path)
            with self.subTest(stem=stem):
                self.assertIsNotNone(engine)
                self.assertIn(platform, cs.rr.PLATFORMS)
                self.assertGreater(len(reply.split()), 20)


if __name__ == "__main__":
    unittest.main()
