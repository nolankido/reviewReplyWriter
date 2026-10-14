"""Out-of-corpus checks for high-risk routing and validated Gemma transport.

Fictional cases are safety probes, not real operator outcomes.
"""
import random
import unittest
from unittest.mock import patch

import review_quality as q
import review_reply as rr
import rrw_workspace as ws
from reply_safety import DraftBlocked, policy_gaps
from rrw_risk import manual_review_findings


class SafetyEnvelopeTests(unittest.TestCase):
    def test_unapproved_benefit_paraphrases_block(self):
        for claim in ("Your next coffee is our treat.",
                      "Your next drink comes with our compliments."):
            with self.subTest(claim=claim):
                self.assertTrue(policy_gaps(claim), claim)

    def test_unsupported_completed_action_paraphrases_block(self):
        for claim in ("The barista has been dismissed.",
                      "The machine underwent repairs this morning.",
                      "An investigation has been launched."):
            with self.subTest(claim=claim):
                self.assertTrue(policy_gaps(claim), claim)

    def test_feel_free_idiom_does_not_create_benefit(self):
        self.assertEqual(policy_gaps("Please feel free to share more about your experience."), [])
        self.assertTrue(policy_gaps("Feel free to claim your free coffee."))

    def test_exact_owner_statement_remains_valid(self):
        claim = "Your next coffee is our treat."
        self.assertEqual(policy_gaps(claim, offer=claim), [])


class SeriousReviewTests(unittest.TestCase):
    def test_severe_reports_require_manual_review_even_with_high_stars(self):
        cases = ("I got food poisoning after dinner.",
                 "My peanut allergy was ignored.",
                 "An employee sexually harassed me.",
                 "A staff member threatened me.",
                 "The business exposed my private information.",
                 "My lawyer is handling this lawsuit.")
        for review in cases:
            with self.subTest(review=review):
                self.assertTrue(manual_review_findings(review))
                with self.assertRaises(DraftBlocked):
                    rr.template_reply(review, "Demo Cafe", "professional", 5,
                                      "cafe", random.Random(0), platform="google")

    def test_model_not_invoked_for_serious_allegation(self):
        calls = []
        def caller(*args):
            calls.append(args)
            return "This must not appear"
        with self.assertRaises(DraftBlocked):
            rr.generate_with_model("I got food poisoning after dinner.",
                                   "Demo Cafe", "professional", 5,
                                   "cafe", "gemma3:4b", caller=caller)
        self.assertEqual(calls, [])

    def test_sensitive_original_stays_manual_in_followups(self):
        with self.assertRaises(DraftBlocked):
            rr.template_followup("My peanut allergy was ignored.",
                                 "Thank you for the feedback.",
                                 "Update: the coffee was cold.",
                                 "Demo Cafe", "professional", "cafe", random.Random(0))

    def test_saved_draft_cannot_reuse_old_approval(self):
        findings = rr.draft_findings({
            "review": "Food poisoning after dinner.", "reply": "Thank you for the visit.",
            "business": "Demo Cafe", "platform": "google", "stars": 5})
        self.assertIn("manual review required", " ".join(findings))


class EverydayInterpretationTests(unittest.TestCase):
    def test_waiter_not_misread_as_wait(self):
        brief = q.analyze("The waiter was rude.", 1)
        self.assertIn("staff", brief["issues"])
        self.assertNotIn("wait", brief["issues"])
        self.assertNotIn("wait", rr.specifics("The waiter was rude."))
        reply = rr.template_reply("The waiter was rude.", "Demo Cafe",
                                  "professional", 1, "cafe", random.Random(0))
        self.assertIn("staff", reply.lower())

    def test_double_billing_has_named_topic_and_checked_template(self):
        review = "My card was charged twice."
        self.assertIn("billing", q.analyze(review, 1)["issues"])
        reply = rr.template_reply(review, "Demo Cafe", "professional",
                                  1, "cafe", random.Random(0), platform="google")
        self.assertIn("billing", reply.lower())
        self.assertEqual(rr.reply_gaps(reply, review, "Demo Cafe", 1, platform="google"), [])


class ConsistentGemmaTransportTests(unittest.TestCase):
    def test_cli_rejects_incomplete_and_wrong_model(self):
        for response in ({"model": "gemma3:4b", "done": False, "response": "Thank you."},
                         {"model": "different-model", "done": True, "response": "Thank you."},
                         {"model": "gemma3:4b", "done": True, "done_reason": "length",
                          "response": "Thank you."}):
            with self.subTest(response=response), patch.object(ws, "local_request", return_value=response):
                with self.assertRaises(ValueError):
                    rr.call_ollama("A review prompt", "gemma3:4b")

    def test_cli_and_browser_return_checked_receipt(self):
        response = {"model": "gemma3:4b", "done": True, "response": "Thank you.",
                    "eval_count": 22}
        with patch.object(ws, "local_request", return_value=response):
            result = rr.call_ollama("A review prompt", "gemma3:4b")
        self.assertEqual(str(result), "Thank you.")
        self.assertEqual(result.receipt["eval_count"], 22)


if __name__ == "__main__":
    unittest.main()
