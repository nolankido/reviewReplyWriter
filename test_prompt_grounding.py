"""Keep illustrative numbers out of prompts for unrelated reviews."""
import unittest
import rrw_quality as quality


class PromptGroundingTests(unittest.TestCase):
    def test_quantity_free_review_has_no_unrelated_numeric_example(self):
        prompt = quality.detail_instructions(
            "Beautiful room and ocean view, but check-in took forever and the shower was weak.", 3)
        self.assertNotRegex(prompt, r"\d")
        self.assertIn("not permission to guess", prompt)

    def test_quantity_checklist_uses_actual_review_not_example_duration(self):
        prompt = quality.detail_instructions("Cold coffee and a 45 minute wait.", 2)
        self.assertIn("45-minute", prompt)
        self.assertNotIn("25", prompt)
        self.assertIn("current review", prompt)


if __name__ == "__main__":
    unittest.main()
