#!/usr/bin/env python3
"""Tests for review_reply.py - stdlib unittest only.

    python3 -m unittest
"""
import contextlib
import io
import os
import random
import tempfile
import unittest

import review_reply as rr

GLOWING = ("The oat milk latte was perfect and the barista remembered "
           "my name. Cozy seats, quick service - my new favorite spot.")
ANGRY = ("Cold coffee, a 25 minute wait, and nobody even looked up. "
         "Really disappointing for the price - I won't be back.")
MIXED = ("Beautiful room and a stunning ocean view, but check-in took "
         "forever and the shower water pressure was weak.")

GOOD_NEGATIVE_REPLY = (
    "Thank you for telling us straight - we appreciate the honesty. "
    "You mentioned the coffee and the wait, and you are right on both. "
    "We are genuinely sorry; that's on us. Please message us directly "
    "and the next round is on us, no fuss. We hope you'll stop by "
    "again soon.\n\n- The Moe's Coffee team")


class SentimentTests(unittest.TestCase):
    def test_stars_decide(self):
        self.assertTrue(rr.is_negative(GLOWING, 2))
        self.assertFalse(rr.is_negative(ANGRY, 5))

    def test_words_decide_without_stars(self):
        self.assertTrue(rr.is_negative(ANGRY))
        self.assertFalse(rr.is_negative(GLOWING))

    def test_specifics_come_from_the_review(self):
        specs = rr.specifics(GLOWING)
        self.assertIn("oat milk latte", specs)
        self.assertIn("coffee", rr.specifics(ANGRY))


class ValidatorTests(unittest.TestCase):
    def test_good_reply_passes(self):
        self.assertTrue(rr.validate_reply(
            GOOD_NEGATIVE_REPLY, ANGRY, "Moe's Coffee", 2))

    def test_missing_thanks_fails(self):
        reply = GOOD_NEGATIVE_REPLY.replace(
            "Thank you for telling us straight - we appreciate the "
            "honesty.", "Here is our response to your comments today.")
        self.assertIn("an opening thank-you",
                      rr.reply_gaps(reply, ANGRY, "Moe's Coffee", 2))

    def test_generic_reply_fails_on_specifics(self):
        reply = ("Thank you so much for your feedback, we appreciate "
                 "every word of it. We are sorry you were unhappy and "
                 "we will make it right with a refund. We hope you'll "
                 "stop by again soon for a much better visit.\n\n"
                 "- The Moe's Coffee team")
        gaps = rr.reply_gaps(reply, ANGRY, "Moe's Coffee", 2)
        self.assertTrue(any("specific detail" in g for g in gaps))

    def test_negative_without_offer_fails(self):
        reply = GOOD_NEGATIVE_REPLY.replace(
            "Please message us directly and the next round is on us, "
            "no fuss.", "We have talked about it as a team already.")
        gaps = rr.reply_gaps(reply, ANGRY, "Moe's Coffee", 2)
        self.assertTrue(any("offer" in g for g in gaps))

    def test_placeholder_fails(self):
        reply = GOOD_NEGATIVE_REPLY.replace("Moe's Coffee", "[NAME]")
        gaps = rr.reply_gaps(reply, ANGRY, "Moe's Coffee", 2)
        self.assertTrue(any("placeholder" in g for g in gaps))

    def test_curly_apostrophe_business_name_passes(self):
        # Models type Moe's with a typographic apostrophe; the name
        # check must not fail a reply for its typography.
        reply = GOOD_MODEL_OUTPUT.replace("Moe's", "Moe\u2019s")
        self.assertTrue(rr.validate_reply(reply, GLOWING, "Moe's Coffee",
                                          5))

    def test_complimentary_offer_counts(self):
        # "A complimentary upgrade on your next visit" is a concrete
        # offer in plain English; the checker must recognise it.
        reply = GOOD_NEGATIVE_REPLY.replace(
            "Please message us directly and the next round is on us, "
            "no fuss.", "Please accept a complimentary upgrade on your "
            "next visit, with our thanks.")
        self.assertTrue(rr.validate_reply(reply, ANGRY, "Moe's Coffee",
                                          2))

    def test_invented_email_fails(self):
        reply = (GOOD_NEGATIVE_REPLY.replace(
            "We hope you'll stop by again soon.",
            "Reach me at owner@moescoffee.example. We hope you'll stop "
            "by again soon."))
        gaps = rr.reply_gaps(reply, ANGRY, "Moe's Coffee", 2)
        self.assertTrue(any("contact details" in g for g in gaps))


class TemplateTests(unittest.TestCase):
    def test_templates_always_validate(self):
        cases = [(GLOWING, 5, "cafe"), (ANGRY, 2, "cafe"),
                 (MIXED, 3, "stay"), (ANGRY, 1, "shop"),
                 (GLOWING, None, "service"), (MIXED, None, "stay")]
        for review, stars, kind in cases:
            for tone in rr.TONES:
                for seed in (1, 2, 3):
                    reply = rr.template_reply(
                        review, "Moe's Coffee", tone, stars, kind,
                        random.Random(seed))
                    with self.subTest(kind=kind, tone=tone, seed=seed,
                                      stars=stars):
                        self.assertTrue(rr.validate_reply(
                            reply, review, "Moe's Coffee", stars),
                            rr.reply_gaps(reply, review, "Moe's Coffee",
                                          stars))

    def test_template_names_the_business(self):
        reply = rr.template_reply(GLOWING, "Kai Loft", "warm", 5, "stay",
                                  random.Random(1))
        self.assertIn("Kai Loft", reply)


GOOD_MODEL_OUTPUT = (
    "Thank you for the kind words - we appreciate every one of them. "
    "You mentioned the oat milk latte, and our barista will be thrilled "
    "to hear it landed. We put real care into mornings like that. "
    "We hope you'll stop by again soon.\n\n- The Moe's Coffee team")


class ModelPathTests(unittest.TestCase):
    def gen(self, caller):
        return rr.generate_with_model(GLOWING, "Moe's Coffee", "warm", 5,
                                      "cafe", "gemma3:4b", caller=caller)

    def test_first_try_success(self):
        reply, engine = self.gen(lambda p, m, t: GOOD_MODEL_OUTPUT)
        self.assertEqual(reply, GOOD_MODEL_OUTPUT)
        self.assertNotIn("retry", engine)

    def test_coached_retry_recovers_and_runs_cool(self):
        prompts, temps = [], []

        def flaky(prompt, model, temp):
            prompts.append(prompt)
            temps.append(temp)
            return "Thanks." if len(prompts) == 1 else GOOD_MODEL_OUTPUT

        reply, engine = self.gen(flaky)
        self.assertEqual(reply, GOOD_MODEL_OUTPUT)
        self.assertIn("after one format retry", engine)
        self.assertIn("missing:", prompts[1])
        self.assertLess(temps[1], temps[0])

    def test_two_failures_fall_back(self):
        reply, reason = self.gen(lambda p, m, t: "nope")
        self.assertIsNone(reply)
        self.assertIn("twice", reason)

    def test_unavailable_model_falls_back(self):
        def down(prompt, model, temp):
            raise OSError("connection refused")

        reply, reason = self.gen(down)
        self.assertIsNone(reply)
        self.assertIn("unavailable", reason)


class TierTests(unittest.TestCase):
    def test_stars_map_to_tiers(self):
        self.assertEqual(rr.review_tier(ANGRY, 1), "negative")
        self.assertEqual(rr.review_tier(ANGRY, 2), "negative")
        self.assertEqual(rr.review_tier(MIXED, 3), "mixed")
        self.assertEqual(rr.review_tier(GLOWING, 5), "positive")

    def test_three_stars_all_complaint_is_negative(self):
        self.assertEqual(rr.review_tier(ANGRY, 3), "negative")

    def test_words_map_to_tiers(self):
        self.assertEqual(rr.review_tier(MIXED), "mixed")
        self.assertEqual(rr.review_tier(ANGRY), "negative")
        self.assertEqual(rr.review_tier(GLOWING), "positive")

    def test_split_specifics_files_topics(self):
        delights, issues = rr.split_specifics(MIXED)
        self.assertIn("ocean view", delights)
        self.assertTrue("check-in" in issues or "shower" in issues)


class MixedTierTests(unittest.TestCase):
    def test_mixed_without_acknowledgment_fails(self):
        reply = ("Thank you so much - we appreciate the kind words "
                 "about the ocean view and the beautiful room, and we "
                 "are thrilled the bed was so comfortable for your "
                 "stay with us at Kai Loft. We hope you'll stop by "
                 "again soon.\n\n- The Kai Loft team")
        gaps = rr.reply_gaps(reply, MIXED, "Kai Loft", 3)
        self.assertTrue(any("acknowledgment" in g for g in gaps))

    def test_mixed_templates_validate(self):
        for tone in rr.TONES:
            for seed in (1, 2, 3):
                reply = rr.template_reply(MIXED, "Kai Loft", tone, 3,
                                          "stay", random.Random(seed))
                with self.subTest(tone=tone, seed=seed):
                    self.assertTrue(rr.validate_reply(
                        reply, MIXED, "Kai Loft", 3),
                        rr.reply_gaps(reply, MIXED, "Kai Loft", 3))

    def test_mixed_prompt_names_the_tier(self):
        prompt = rr.build_prompt(MIXED, "Kai Loft", "warm", 3, "stay")
        self.assertIn("mixed", prompt)


class ProfileTests(unittest.TestCase):
    OFFER = "a free pastry of your choice"

    def test_generic_offer_fails_when_standing_offer_set(self):
        gaps = rr.reply_gaps(GOOD_NEGATIVE_REPLY, ANGRY, "Moe's Coffee",
                             2, offer=self.OFFER)
        self.assertTrue(any("standing offer" in g for g in gaps))

    def test_template_uses_standing_offer_verbatim(self):
        reply = rr.template_reply(ANGRY, "Moe's Coffee", "warm", 2,
                                  "cafe", random.Random(1),
                                  offer=self.OFFER)
        self.assertIn(self.OFFER, reply)
        self.assertTrue(rr.validate_reply(reply, ANGRY, "Moe's Coffee",
                                          2, offer=self.OFFER))

    def test_prompt_carries_the_offer_verbatim(self):
        prompt = rr.build_prompt(ANGRY, "Moe's Coffee", "warm", 2,
                                 "cafe", offer=self.OFFER)
        self.assertIn(self.OFFER, prompt)

    def test_custom_signoff_is_used_and_stripped_from_body(self):
        reply = rr.template_reply(GLOWING, "Moe's Coffee", "warm", 5,
                                  "cafe", random.Random(1),
                                  signoff="Moe & Ana")
        # The sign-off is the owner's - but a reply must name the
        # business, so the name rides along when the sign-off omits it.
        self.assertTrue(reply.rstrip().endswith(
            "- Moe & Ana, Moe's Coffee"))
        self.assertTrue(rr.validate_reply(
            reply, GLOWING, "Moe's Coffee", 5, signoff="Moe & Ana"))

    def test_profile_save_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "profiles.json")
            rr.save_profile("moes", {"business": "Moe's Coffee",
                                     "kind": "cafe"}, path)
            loaded = rr.load_profiles(path)
            self.assertEqual(loaded["moes"]["business"], "Moe's Coffee")
            self.assertEqual(rr.load_profiles(
                os.path.join(tmp, "missing.json")), {})


class BatchTests(unittest.TestCase):
    ROWS = [
        {"review": GLOWING, "business": "Moe's Coffee", "kind": "cafe",
         "tone": "warm", "stars": "5"},
        {"review": ANGRY, "business": "Moe's Coffee", "kind": "cafe",
         "tone": "warm", "stars": "2"},
        {"review": "   ", "business": "Moe's Coffee"},
    ]

    def test_batch_offline_writes_files_and_skips_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            results = rr.run_batch(self.ROWS, tmp, "gemma3:4b", True,
                                   seed=5)
            self.assertEqual(len(results), 3)
            files = [r["file"] for r in results if r["file"]]
            self.assertEqual(len(files), 2)
            self.assertEqual(len(set(files)), 2)
            for name in files:
                self.assertTrue(os.path.exists(os.path.join(tmp, name)))
            self.assertIn("skipped", results[2]["engine"])
            self.assertEqual(results[0]["tier"], "positive")
            self.assertEqual(results[1]["tier"], "negative")

    def test_batch_model_path_credits_the_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [dict(self.ROWS[0])]
            results = rr.run_batch(
                rows, tmp, "gemma3:4b", False,
                caller=lambda p, m, t: GOOD_MODEL_OUTPUT)
            self.assertIn("gemma3:4b", results[0]["engine"])

    def test_batch_csv_parsing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "in.csv")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("review,business,stars\n")
                fh.write('"Cold coffee, long wait",Moe\'s Coffee,2\n')
            rows = rr.read_batch_csv(path)
            self.assertEqual(rows[0]["review"], "Cold coffee, long wait")
            self.assertEqual(rows[0]["stars"], "2")


class FactGuardTests(unittest.TestCase):
    LEO_REPLY = (
        "Thank you so much for the wonderful words - we appreciate "
        "every one of them. You mentioned the oat milk latte, and we "
        "especially loved hearing that Leo remembered your name; he "
        "puts so much effort into the morning rush. We hope you'll "
        "stop by again soon.\n\n- The Moe's Coffee team")

    def test_invented_staff_name_is_flagged(self):
        self.assertIn("Leo", rr.invented_details(
            self.LEO_REPLY, GLOWING, "Moe's Coffee"))
        gaps = rr.reply_gaps(self.LEO_REPLY, GLOWING, "Moe's Coffee", 5)
        self.assertTrue(any("invented detail" in g for g in gaps))

    def test_grounded_names_pass(self):
        self.assertEqual(rr.invented_details(
            GOOD_MODEL_OUTPUT, GLOWING, "Moe's Coffee"), [])
        self.assertTrue(rr.validate_reply(
            GOOD_MODEL_OUTPUT, GLOWING, "Moe's Coffee", 5))

    def test_grounded_number_passes_invented_number_fails(self):
        grounded = GOOD_NEGATIVE_REPLY.replace(
            "the coffee and the wait",
            "the coffee and the 25 minute wait")
        self.assertEqual(rr.invented_details(
            grounded, ANGRY, "Moe's Coffee"), [])
        invented = GOOD_NEGATIVE_REPLY.replace(
            "the next round is on us",
            "a $50 credit toward your next visit, on us")
        self.assertIn("$50", rr.invented_details(
            invented, ANGRY, "Moe's Coffee"))

    def test_prompt_forbids_inventing(self):
        prompt = rr.build_prompt(GLOWING, "Moe's Coffee", "warm", 5,
                                 "cafe")
        self.assertIn("Never invent", prompt)
        self.assertIn("by their role", prompt)


class PlatformTests(unittest.TestCase):
    def test_word_bounds_follow_the_platform(self):
        short = ("Thank you for the kind words about the oat milk "
                 "latte - we appreciate them all. We hope you'll stop "
                 "by again soon.\n\n- The Moe's Coffee team")
        # ~25 words: fine for google, too thin for airbnb's range.
        self.assertTrue(rr.validate_reply(
            short, GLOWING, "Moe's Coffee", 5, platform="google"))
        self.assertFalse(rr.validate_reply(
            short, GLOWING, "Moe's Coffee", 5, platform="airbnb"))

    def test_templates_validate_on_every_platform(self):
        cases = [(GLOWING, 5, "cafe"), (ANGRY, 2, "cafe"),
                 (MIXED, 3, "stay")]
        for review, stars, kind in cases:
            for platform in rr.PLATFORMS:
                reply = rr.template_reply(review, "Moe's Coffee",
                                          "warm", stars, kind,
                                          random.Random(2))
                with self.subTest(platform=platform, stars=stars):
                    self.assertTrue(rr.validate_reply(
                        reply, review, "Moe's Coffee", stars,
                        platform=platform),
                        (platform, rr.reply_gaps(
                            reply, review, "Moe's Coffee", stars,
                            platform=platform)))

    def test_prompt_carries_the_platform_range(self):
        prompt = rr.build_prompt(GLOWING, "Moe's Coffee", "warm", 5,
                                 "cafe", platform="airbnb")
        self.assertIn("50 to 220 words", prompt)
        self.assertIn("airbnb", prompt)


class LedgerTests(unittest.TestCase):
    def test_record_and_top_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ledger.json")
            rr.record_gaps("Moe's Coffee", [
                "your standing offer, word for word ('x')",
                "an apology"], path)
            rr.record_gaps("Moe's Coffee", [
                "your standing offer, word for word ('x')"], path)
            top = rr.top_gaps("Moe's Coffee", path)
            self.assertEqual(top[0], "the standing offer, word for "
                                     "word")
            self.assertEqual(rr.top_gaps("Nobody", path), [])

    def test_gap_keys_are_categories(self):
        self.assertEqual(rr.gap_key("an opening thank-you"),
                         "the opening thank-you")
        self.assertEqual(rr.gap_key("an invented detail (Leo)"),
                         "no invented details")

    def test_model_misses_are_recorded_and_emphasised(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ledger.json")
            prompts = []

            def flaky(prompt, model, temp):
                prompts.append(prompt)
                return "Thanks." if len(prompts) == 1 \
                    else GOOD_MODEL_OUTPUT

            rr.generate_with_model(GLOWING, "Moe's Coffee", "warm", 5,
                                   "cafe", "gemma3:4b", caller=flaky,
                                   ledger_path=path)
            entry = rr.load_ledger(path)["Moe's Coffee"]
            self.assertTrue(entry)
            # And the next run's prompt names the repeat miss.
            prompts.clear()
            rr.generate_with_model(GLOWING, "Moe's Coffee", "warm", 5,
                                   "cafe", "gemma3:4b", caller=flaky,
                                   ledger_path=path)
            self.assertIn("most often miss", prompts[0])


VOICE_SAMPLES = [
    "Mahalo for stopping by, friend. Thanks for stopping by and "
    "thanks for the kind words about the latte art.\n\n"
    "- Keola, Moe's Coffee",
    "Mahalo for the honest note. Thanks for stopping by even when "
    "the line was long - we owe you a faster morning.\n\n"
    "- Keola, Moe's Coffee",
    "Mahalo for telling us. Thanks for stopping by and giving us "
    "the chance to make the next cup right.\n\n- Keola, Moe's Coffee",
]


class VoiceTests(unittest.TestCase):
    def test_learns_signoff_opener_and_phrases(self):
        voice = rr.learn_voice(VOICE_SAMPLES)
        self.assertEqual(voice["signoff"], "Keola, Moe's Coffee")
        self.assertTrue(voice["opener"].startswith("mahalo for"))
        self.assertIn("thanks for", voice["phrases"])
        self.assertGreater(voice["avg_words"], 10)

    def test_voice_reaches_the_prompt(self):
        voice = rr.learn_voice(VOICE_SAMPLES)
        prompt = rr.build_prompt(GLOWING, "Moe's Coffee", "warm", 5,
                                 "cafe", voice=voice)
        self.assertIn("owner's own voice", prompt)
        self.assertIn("thanks for", prompt)

    def test_voice_signoff_is_enforced(self):
        in_voice = GOOD_MODEL_OUTPUT.replace(
            "- The Moe's Coffee team", "- Keola, Moe's Coffee")
        reply, engine = rr.generate_with_model(
            GLOWING, "Moe's Coffee", "warm", 5, "cafe", "gemma3:4b",
            caller=lambda p, m, t: in_voice,
            voice={"signoff": "Keola, Moe's Coffee"})
        self.assertEqual(reply, in_voice)
        self.assertNotIn("retry", engine)


class TriageTests(unittest.TestCase):
    def _draft(self, tmp, review, reply, stars, name_business):
        return rr.save_reply_file(
            tmp, name_business, review, reply, "test engine", "warm",
            "cafe", rr.review_tier(review, stars))

    def test_parse_draft_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self._draft(tmp, GLOWING, GOOD_MODEL_OUTPUT, 5,
                               "Moe's Coffee")
            draft = rr.parse_draft(path)
            self.assertEqual(draft["business"], "Moe's Coffee")
            self.assertEqual(draft["tier"], "positive")
            self.assertEqual(draft["review"], GLOWING)
            self.assertIn("oat milk latte", draft["reply"])

    def test_triage_approve_and_aside_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._draft(tmp, GLOWING, GOOD_MODEL_OUTPUT, 5,
                        "Moe's Coffee")
            self._draft(tmp, ANGRY, GOOD_NEGATIVE_REPLY, 2,
                        "Moe's Coffee")
            answers = iter(["a", "s"])
            state = rr.triage(tmp, "gemma3:4b", True,
                              input_fn=lambda prompt: next(answers),
                              print_fn=lambda *a: None)
            statuses = sorted(v["status"] for v in state.values())
            self.assertEqual(statuses, ["approved", "aside"])
            reloaded = rr.load_triage(tmp)
            self.assertEqual(len(reloaded), 2)

    def test_triage_reroll_replaces_the_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            stale = ("Thank you for the feedback about the oat milk "
                     "latte, we appreciate it a lot and we will pass "
                     "it along to everyone here. We hope you'll stop "
                     "by again soon.\n\n- The Moe's Coffee team")
            path = self._draft(tmp, GLOWING, stale, 5, "Moe's Coffee")
            answers = iter(["r", "a"])
            rr.triage(tmp, "gemma3:4b", False,
                      caller=lambda p, m, t: GOOD_MODEL_OUTPUT,
                      input_fn=lambda prompt: next(answers),
                      print_fn=lambda *a: None)
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("gemma3:4b", text)
            self.assertIn("barista will be thrilled", text)

    def test_triage_quit_leaves_drafts_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._draft(tmp, GLOWING, GOOD_MODEL_OUTPUT, 5,
                        "Moe's Coffee")
            state = rr.triage(tmp, "gemma3:4b", True,
                              input_fn=lambda prompt: "q",
                              print_fn=lambda *a: None)
            self.assertEqual(state, {})


UPDATE_HAPPY = ("Update: came back and the replacement coffee was "
                "hot and fast. Faith restored - this is my spot "
                "again.")
UPDATE_STILL_BAD = ("Update: tried again and the coffee was cold a "
                    "second time. Really disappointed, worse than "
                    "before.")
GOOD_FOLLOWUP_HAPPY = (
    "Thank you for coming back and updating this - it honestly "
    "made our day. The replacement coffee being hot and fast is "
    "exactly what we hoped you'd get this time around. Faith "
    "restored goes both ways here. You're welcome back any time "
    "at Moe's Coffee.\n\n- The Moe's Coffee team")
STANDING_OFFER = "the next round is on us"


class FollowupTests(unittest.TestCase):
    def test_happy_followup_passes(self):
        self.assertTrue(rr.validate_followup(
            GOOD_FOLLOWUP_HAPPY, ANGRY, GOOD_NEGATIVE_REPLY,
            UPDATE_HAPPY, "Moe's Coffee", offer=STANDING_OFFER),
            rr.followup_gaps(GOOD_FOLLOWUP_HAPPY, ANGRY,
                             GOOD_NEGATIVE_REPLY, UPDATE_HAPPY,
                             "Moe's Coffee", offer=STANDING_OFFER))

    def test_repeating_the_spent_offer_fails(self):
        reply = ("Thank you for the update - we're sorry it still "
                 "isn't right. The coffee being cold a second time "
                 "is on us, truly. Come in and the next round is on "
                 "us, just like we said. We hope you'll stop by "
                 "again.\n\n- The Moe's Coffee team")
        gaps = rr.followup_gaps(reply, ANGRY, GOOD_NEGATIVE_REPLY,
                                UPDATE_STILL_BAD, "Moe's Coffee",
                                offer=STANDING_OFFER)
        self.assertTrue(any("no repeat" in g for g in gaps))
        self.assertTrue(any("escalation" in g for g in gaps))

    def test_fresh_opener_without_acknowledgment_fails(self):
        reply = ("Thank you so much for your feedback, we appreciate "
                 "every word of it. The coffee is something we take "
                 "real pride in here at Moe's Coffee, and your kind "
                 "words mean a lot to the whole team working here. "
                 "We hope you'll stop by again soon.\n\n"
                 "- The Moe's Coffee team")
        gaps = rr.followup_gaps(reply, ANGRY, GOOD_NEGATIVE_REPLY,
                                UPDATE_HAPPY, "Moe's Coffee",
                                offer=STANDING_OFFER)
        self.assertTrue(any("acknowledgment of the update" in g
                            for g in gaps))

    def test_template_followups_validate(self):
        for update in (UPDATE_HAPPY, UPDATE_STILL_BAD):
            for tone in rr.TONES:
                for seed in (1, 2):
                    reply = rr.template_followup(
                        ANGRY, GOOD_NEGATIVE_REPLY, update,
                        "Moe's Coffee", tone, "cafe",
                        random.Random(seed), offer=STANDING_OFFER)
                    with self.subTest(tone=tone, seed=seed,
                                      update=update[:12]):
                        self.assertTrue(rr.validate_followup(
                            reply, ANGRY, GOOD_NEGATIVE_REPLY, update,
                            "Moe's Coffee", offer=STANDING_OFFER),
                            rr.followup_gaps(
                                reply, ANGRY, GOOD_NEGATIVE_REPLY,
                                update, "Moe's Coffee",
                                offer=STANDING_OFFER))

    def test_generate_followup_first_try(self):
        reply, engine = rr.generate_followup(
            ANGRY, GOOD_NEGATIVE_REPLY, UPDATE_HAPPY, "Moe's Coffee",
            "warm", "cafe", "gemma3:4b",
            caller=lambda p, m, t: GOOD_FOLLOWUP_HAPPY,
            offer=STANDING_OFFER)
        self.assertEqual(reply, GOOD_FOLLOWUP_HAPPY)
        self.assertNotIn("retry", engine)

    def test_followup_prompt_names_the_thread(self):
        prompt = rr.build_followup_prompt(
            ANGRY, GOOD_NEGATIVE_REPLY, UPDATE_STILL_BAD,
            "Moe's Coffee", "warm", "cafe", offer=STANDING_OFFER)
        self.assertIn("continuing conversation", prompt)
        self.assertIn("Do NOT repeat it", prompt)


REPLY_RICH = GOOD_MODEL_OUTPUT
REPLY_THIN = (
    "Thank you so much for the kind words - we appreciate every one "
    "of them. The oat milk latte is the drink we are proudest of, "
    "and hearing it was perfect makes the whole morning better. "
    "We hope you'll stop by again soon.\n\n- The Moe's Coffee team")


class BestOfTwoTests(unittest.TestCase):
    def gen(self, outputs, choices=2):
        calls = []

        def caller(prompt, model, temp):
            calls.append(temp)
            return outputs[len(calls) - 1]

        result = rr.generate_with_model(
            GLOWING, "Moe's Coffee", "warm", 5, "cafe", "gemma3:4b",
            caller=caller, choices=choices)
        return result, calls

    def test_richer_draft_wins_either_order(self):
        (reply, engine), _ = self.gen([REPLY_THIN, REPLY_RICH])
        self.assertEqual(reply, REPLY_RICH)
        self.assertIn("best of 2", engine)
        (reply, engine), _ = self.gen([REPLY_RICH, REPLY_THIN])
        self.assertEqual(reply, REPLY_RICH)
        self.assertIn("best of 2", engine)

    def test_invalid_second_keeps_the_first(self):
        (reply, engine), _ = self.gen([REPLY_THIN, "junk"])
        self.assertEqual(reply, REPLY_THIN)
        self.assertNotIn("best of", engine)

    def test_choices_one_samples_once(self):
        _, calls = self.gen([REPLY_RICH], choices=1)
        self.assertEqual(len(calls), 1)


class TourTests(unittest.TestCase):
    def test_tour_walks_every_step_offline(self):
        with tempfile.TemporaryDirectory() as tmp:
            rr.save_reply_file(tmp, "Moe's Coffee", GLOWING,
                               GOOD_MODEL_OUTPUT, "test engine",
                               "warm", "cafe", "positive")
            lines = []
            rr.tour("gemma3:4b", True, tmp, print_fn=lines.append)
            text = "\n".join(lines)
            for step in ("Step 1", "Step 2", "Step 3", "Step 4",
                         "Step 5", "Tour done"):
                self.assertIn(step, text)
            self.assertIn("1 drafts saved", text)
            self.assertIn("template engine", text)


class DoctorTests(unittest.TestCase):
    def test_doctor_reports_the_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ledger.json")
            rr.record_gaps("Moe's Coffee", ["an apology"], path)
            original = rr.LEDGER_PATH
            rr.LEDGER_PATH = path
            try:
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    rr.doctor("gemma3:4b")
            finally:
                rr.LEDGER_PATH = original
            out = buf.getvalue()
            self.assertIn("Moe's Coffee drafts most often miss", out)
            self.assertIn("an apology", out)


class SavePathTests(unittest.TestCase):
    def test_unique_path_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "reply-cafe-2026-10-12.md")
            self.assertEqual(rr.unique_path(path), path)
            open(path, "w").close()
            second = rr.unique_path(path)
            self.assertNotEqual(second, path)
            self.assertFalse(os.path.exists(second))
            open(second, "w").close()
            third = rr.unique_path(path)
            self.assertNotIn(third, (path, second))
            self.assertFalse(os.path.exists(third))


if __name__ == "__main__":
    unittest.main()
