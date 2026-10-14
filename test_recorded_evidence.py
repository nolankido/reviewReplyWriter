"""Verify the historical smoke artifact, not fresh inference on each test run."""
from pathlib import Path
import unittest
import rrw_evaluate as ev


class RecordedEvidenceTests(unittest.TestCase):
    def test_historical_live_record_is_intact_and_unreviewed(self):
        report = ev.load_report(Path(__file__).parent / 'examples/evaluation/live-smoke-2026-10-13.json')
        summary = ev.summarize(report)
        self.assertEqual(report['execution'], 'ollama')
        self.assertEqual((summary['model'], summary['fallback'], summary['completed_api_responses']), (2, 1, 5))
        self.assertEqual(summary['human_reviewed'], 0)
        self.assertTrue(any('Human assessment' in s for s in ev.live_evidence_blockers(report)))


if __name__ == '__main__':
    unittest.main()
