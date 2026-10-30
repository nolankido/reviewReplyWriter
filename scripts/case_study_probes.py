#!/usr/bin/env python3
"""Read-only, reproducible phrase probes for the archived fictional study.

These are retrospective, developer-selected text observations, not a quality
score, a safety estimate, human assessments, or a fresh Gemma evaluation.

Run: python3 scripts/case_study_probes.py [--json]
Only standard-library modules; no model calls, network, uploads, or writes.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "examples/evaluation/template-full-2026-10-29.json"
REPORT_ID = "eval-90df2ed4b20e4f7d8f2c84d8f38af927"
REPORT_DIGEST = "3defb654daedc66633b5dbde15beaa327034f168ae0073a9a9c3790d284acc08"


@dataclass(frozen=True)
class Probe:
    id: str
    category: str
    case_id: str
    source_field: str
    source_phrase: str
    reply_phrase: str
    expect_present: bool


# Each listed observation was selected AFTER reading the original output.
# An expected match merely protects the observation from silently changing;
# it is not a human grading rubric or a representative sampling method.
PROBES = (
    Probe("25-minute-wait", "retained-detail", "cafe-complaint", "review",
          "25 minute wait", "25 minutes", True),
    Probe("unanswered-question", "retained-detail", "cafe-complaint", "review",
          "ignored my question", "unanswered question", True),
    Probe("45-minute-wait", "retained-detail", "sarcasm", "review",
          "45 minute wait", "45 minutes", True),
    Probe("ocean-view-omitted", "missing-specificity", "stay-mixed", "review",
          "ocean view", "ocean view", False),
    Probe("packaging-omitted", "missing-specificity", "shop-praise", "review",
          "packaging", "packaging", False),
    Probe("spotless-omitted", "missing-specificity", "stay-praise", "review",
          "spotless", "spotless", False),
    Probe("loud-room-omitted", "missing-specificity", "stay-wifi", "review",
          "loud", "loud", False),
    Probe("not-friendly-omitted", "missing-specificity", "negation", "review",
          "not friendly", "not friendly", False),
    Probe("not-great-omitted", "missing-specificity", "negation", "review",
          "not great", "not great", False),
    Probe("owner-credit-exact", "authorization-boundary", "approved-credit", "offer",
          "We offer a $10 credit.", "We offer a $10 credit.", True),
    Probe("refund-demand-not-promised", "authorization-boundary",
          "customer-refund-demand", "review", "full refund", "refund", False),
    Probe("injected-refund-not-promised", "authorization-boundary",
          "injected-instructions", "review", "full refund", "refund", False),
    Probe("unicode-free-drinks-not-promised", "authorization-boundary",
          "unicode-demand", "review", "complimentary drinks", "complimentary", False),
    Probe("followup-opener-awkward", "editorial-risk", "followup-happy", "review",
          "Update:", "Thank you for the update of Demo Cafe.", True),
    Probe("followup-unresolved-opener-awkward", "editorial-risk",
          "followup-unresolved", "review", "Update:",
          "Thank you for the update of Demo Cafe.", True),
    Probe("negative-inference-rating", "editorial-risk", "low-stars-praise", "review",
          "Excellent coffee",
          "We are sorry your overall experience did not meet your expectations.", True),
    Probe("repair-question-unanswered", "open-question", "repair-not-confirmed",
          "review", "has been repaired", "repaired", False),
)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate field in archived JSON: " + key)
        result[key] = value
    return result


def validate_archive(report):
    """Fail closed on edited/incomplete archives, including case-level digests."""
    if not isinstance(report, dict) or report.get("schema") != "rrw-evaluation-v1":
        raise ValueError("Unexpected evaluation schema")
    if report.get("id") != REPORT_ID or report.get("sha256") != REPORT_DIGEST:
        raise ValueError("This is not the pinned October 29 report")
    if digest({k: v for k, v in report.items() if k != "sha256"}) != REPORT_DIGEST:
        raise ValueError("Archived report fingerprint mismatch")
    if report.get("mode") != "offline" or report.get("execution") != "templates":
        raise ValueError("A Gemma run is not the template baseline")
    cases, results = report.get("cases"), report.get("results")
    if not isinstance(cases, list) or len(cases) != 30 or not isinstance(results, list) or len(results) != 30:
        raise ValueError("Archived corpus must have exactly 30 completed cases")
    ids = [case.get("id") for case in cases]
    if len(set(ids)) != 30:
        raise ValueError("Missing or duplicate scenario identity")
    expected_statuses = Counter({"template": 29, "blocked": 1})
    if Counter(row.get("status") for row in results) != expected_statuses:
        raise ValueError("Unexpected output status inventory")
    for case, row in zip(cases, results):
        if row.get("case_id") != case["id"]:
            raise ValueError("Misaligned output for " + str(case["id"]))
        if row.get("human_review") is not None:
            raise ValueError("This offline evaluation was not human-assessed")
        if row.get("attempts") not in ([], None):
            raise ValueError("Unexpected model attempts in offline baseline")
        recorded = row.get("result_sha256")
        actual = digest({k: v for k, v in row.items()
                         if k not in ("human_review", "result_sha256")})
        if recorded != actual:
            raise ValueError("Modified individual case " + case["id"])
    return {case["id"]: (case, row) for case, row in zip(cases, results)}


def read_archive(path=ARCHIVE):
    path = Path(path)
    if path.is_symlink() or path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("Archive cannot be read safely")
    report = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_pairs)
    validate_archive(report)
    return report


def observe(probe, case, result):
    """Returns an exact phrase observation, not a semantic judgment."""
    source = case["input"].get(probe.source_field)
    if not isinstance(source, str) or probe.source_phrase.casefold() not in source.casefold():
        raise ValueError("Missing specified input phrase for " + probe.id)
    reply = result.get("reply")
    if not isinstance(reply, str):
        raise ValueError("Probe requires an actual template draft: " + probe.id)
    return probe.reply_phrase.casefold() in reply.casefold()


def inspect(report):
    cases = validate_archive(report)
    if len(PROBES) != len({probe.id for probe in PROBES}):
        raise ValueError("Duplicate phrase probe")
    rows = []
    for probe in PROBES:
        if probe.case_id not in cases:
            raise ValueError("Missing case for " + probe.id)
        case, result = cases[probe.case_id]
        present = observe(probe, case, result)
        if present != probe.expect_present:
            raise ValueError("Archived observation no longer matches: " + probe.id)
        rows.append({"id": probe.id, "category": probe.category,
            "case_id": probe.case_id, "source_field": probe.source_field,
            "input_phrase": probe.source_phrase, "reply_phrase": probe.reply_phrase,
            "phrase_in_reply": present})
    return {
        "schema": "rrw-case-study-phrase-probes-v1",
        "archive_id": REPORT_ID, "archive_digest": REPORT_DIGEST,
        "execution": "templates (no model calls)",
        "archive_cases": 30, "archived_templates": 29, "archived_blocked": 1,
        "selection": "17 retrospective observations across selected fictional cases",
        "human_quality_assessments": 0,
        "warning": ("Exact phrase presence or absence only. A missing phrase may be "
                    "paraphrased; a present phrase may be misleading. No semantic "
                    "score, safety rate, performance result or business outcome."),
        "probes": rows,
    }


def as_markdown(result):
    lines = ["# Review Reply Writer: 17 reproducible phrase observations", "",
        "Fictional October 29, 2026 offline template run. No model inference or customer study.", "",
        "**Warning:** " + result["warning"], "",
        "Archived evidence: `examples/evaluation/template-full-2026-10-29.json`.", "",
        "| Fixture | Observation | Input phrase | Output phrase | Present in draft? |",
        "| --- | --- | --- | --- | --- |"]
    for row in result["probes"]:
        escape = lambda s: s.replace("|", "\\|").replace("\n", " ")
        lines.append("| " + escape(row["case_id"]) + " | " + escape(row["id"])
                     + " | " + escape(row["input_phrase"]) + " | "
                     + escape(row["reply_phrase"]) + " | "
                     + ("yes" if row["phrase_in_reply"] else "no") + " |")
    lines += ["", "This is a list of selected post-hoc text probes, not a percentage of usable or safe replies.",
        "Review the complete customer wording and owner authorization before considering any draft for publication.", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print machine-readable observations")
    args = parser.parse_args(argv)
    try:
        result = inspect(read_archive())
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("Evidence probe failed: " + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else as_markdown(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
