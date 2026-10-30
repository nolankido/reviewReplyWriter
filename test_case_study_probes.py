"""Regression checks for the frozen, post-hoc Review Reply Writer phrase probes."""
from copy import deepcopy
import unittest

from scripts import case_study_probes as study


class CaseStudyPhraseProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = study.read_archive()

    def test_exact_archived_case_inventory_and_source_credit(self):
        cases = study.validate_archive(self.report)
        self.assertEqual(len(cases), 30)
        self.assertEqual(self.report["execution"], "templates")
        self.assertEqual(self.report["mode"], "offline")
        self.assertEqual(self.report["sha256"], study.REPORT_DIGEST)
        self.assertEqual(sum(row["status"] == "template" for _, row in cases.values()), 29)
        self.assertEqual(sum(row["status"] == "blocked" for _, row in cases.values()), 1)
        self.assertFalse(any(row.get("attempts") for _, row in cases.values()))

    def test_probes_match_all_seventeen_recorded_observations(self):
        result = study.inspect(self.report)
        self.assertEqual(result["schema"], "rrw-case-study-phrase-probes-v1")
        self.assertEqual(len(result["probes"]), 17)
        self.assertEqual(len({row["id"] for row in result["probes"]}), 17)
        self.assertEqual(result["human_quality_assessments"], 0)
        self.assertIn("No semantic", result["warning"])
        self.assertEqual(sum(row["category"] == "missing-specificity"
                             for row in result["probes"]), 6)
        self.assertEqual(sum(row["category"] == "retained-detail"
                             for row in result["probes"]), 3)

    def test_report_integrity_fails_on_edited_reply_or_mode(self):
        altered = deepcopy(self.report)
        altered["results"][0]["reply"] += " Altered."
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            study.validate_archive(altered)
        altered = deepcopy(self.report)
        altered["execution"] = "ollama"
        with self.assertRaises(ValueError):
            study.validate_archive(altered)

    def test_exact_phrase_probe_does_not_claim_semantic_understanding(self):
        cases = study.validate_archive(self.report)
        probe = next(p for p in study.PROBES if p.id == "loud-room-omitted")
        case, row = cases["stay-wifi"]
        self.assertFalse(study.observe(probe, case, row))
        altered = {**row, "reply": row["reply"] + " The room was loud."}
        self.assertTrue(study.observe(probe, case, altered))
        broken_case = deepcopy(case)
        broken_case["input"]["review"] = "The room was dirty."
        with self.assertRaisesRegex(ValueError, "input phrase"):
            study.observe(probe, broken_case, row)

    def test_printed_report_is_labeled_and_does_not_invent_success_rates(self):
        text = study.as_markdown(study.inspect(self.report))
        self.assertIn("17 reproducible phrase observations", text)
        self.assertIn("No model inference or customer study", text)
        self.assertIn("not a percentage", text)
        self.assertIn("loud-room-omitted", text)
        self.assertNotIn("% safe", text)
        self.assertNotIn("\u2014", text)


if __name__ == "__main__":
    unittest.main()
