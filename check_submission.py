#!/usr/bin/env python3
"""Development checks and a separate, fail-closed release checklist.

python check_submission.py            # tests and current safety examples
python check_submission.py --release  # also require explicit submission evidence

Development success is NOT confirmation of eligibility or a submitted entry.
Release evidence contains owner attestations, not independently verified facts.
"""
import argparse
import io
import json
import os
import re
import sys
import unittest
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import review_reply as rr

POST_PATH = os.path.join(HERE, "POST_FINAL.md")
EXAMPLES = os.path.join(HERE, "examples", "safety")
EVIDENCE_PATH = os.path.join(HERE, "docs", "submission_evidence.json")
GALLERY = [("01-glowing-cafe", "Moe's Coffee", 5),
           ("02-angry-cafe", "Moe's Coffee", 2),
           ("03-mixed-stay", "Kai Loft", 3)]


def parse_saved_reply(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    credit = re.search(r"Drafted [^>]*? by ([^;]+);", text)
    engine = credit.group(1).strip() if credit else None
    draft = rr.parse_draft(path)
    return engine, draft.get("platform", "generic"), draft["reply"]


def discover_suite():
    return unittest.TestLoader().discover(HERE, pattern="test_*.py")


def suite_state():
    suite = discover_suite()
    count = suite.countTestCases()
    # Tests sometimes exercise CLIs; their output is not submission evidence.
    from contextlib import redirect_stdout, redirect_stderr
    with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
        result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    return count, result.wasSuccessful()


def gallery_blockers():
    blockers = []
    for stem, business, stars in GALLERY:
        path = os.path.join(EXAMPLES, f"{stem}-reply.md")
        try:
            engine, platform, reply = parse_saved_reply(path)
            draft = rr.parse_draft(path)
            if not engine:
                blockers.append(f"{stem}: missing engine credit")
            if draft.get("business") != business or draft.get("stars") != stars:
                blockers.append(f"{stem}: incorrect example context")
            gaps = rr.draft_findings(draft)
            if gaps:
                blockers.append(f"{stem}: " + "; ".join(gaps))
        except (OSError, ValueError, TypeError, KeyError) as exc:
            blockers.append(f"{stem}: {exc}")
    return blockers


def post_findings(post_text, actual_count, suite_green):
    blockers, todos = [], []
    for claimed in re.findall(r"Ran (\d+) tests", post_text):
        if int(claimed) != actual_count:
            blockers.append(f"POST_FINAL claims {claimed} tests; the suite has {actual_count}")
    if not suite_green:
        blockers.append("the test suite is not green right now")
    for tag in ("devchallenge", "hf26challenge"):
        if tag not in post_text:
            blockers.append(f"POST_FINAL is missing the #{tag} tag")
    if "[REAL REVIEW TEST" in post_text:
        todos.append("replace the [REAL REVIEW TEST] placeholder with verified evidence")
    return blockers, todos


def release_blockers(evidence, post_text):
    """Require explicit evidence, while not claiming to verify external facts."""
    if not isinstance(evidence, dict):
        return ["release evidence must be a JSON object"]
    blockers = []
    for key in ("repository_url", "demo_url"):
        value = evidence.get(key)
        parsed = urlparse(value) if isinstance(value, str) else None
        if not parsed or parsed.scheme != "https" or not parsed.netloc or \
                parsed.hostname in ("example.com", "example.org", "localhost"):
            blockers.append(f"missing real HTTPS {key}")
        elif value not in post_text:
            blockers.append(f"{key} must appear in the DEV post")
    for key in ("repository_accessible_to_judges", "development_window_confirmed",
                "fresh_gemma_run_recorded", "firsthand_claims_reviewed"):
        if evidence.get(key) is not True:
            blockers.append(f"owner evidence not confirmed: {key}")
    for heading in ("## Demo", "## Code", "## How I Built It",
                    "## Why Open Innovation Matters", "## Prize Categories"):
        if heading not in post_text:
            blockers.append(f"missing submission section: {heading}")
    if "Best Use of Gemma" not in post_text:
        blockers.append("prize category is not identified")
    if re.search(r"\b(?:TODO|UNVERIFIED|REPLACE_ME)\b", post_text):
        blockers.append("unresolved publication markers remain in the post")
    return blockers



def evaluation_blockers(path):
    """Require a checked run artifact; a checkbox alone is not model evidence."""
    if not path:
        return ["missing evaluation report: pass --evaluation FILE from Quality Lab"]
    from rrw_evaluate import load_report, live_evidence_blockers
    try:
        return live_evidence_blockers(load_report(path))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        return ["invalid evaluation evidence: " + str(exc)]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--release", action="store_true")
    ap.add_argument("--evaluation", help="JSON report exported by Quality Lab, for release checks")
    args = ap.parse_args(argv)
    count, green = suite_state()
    try:
        with open(POST_PATH, encoding="utf-8") as fh:
            post = fh.read()
        blockers = gallery_blockers()
        findings, todos = post_findings(post, count, green)
        blockers.extend(findings)
        if args.release:
            with open(EVIDENCE_PATH, encoding="utf-8") as fh:
                evidence = json.load(fh)
            blockers.extend(release_blockers(evidence, post))
            report_path = args.evaluation or evidence.get("evaluation_report")
            if report_path and not os.path.isabs(report_path):
                report_path = os.path.join(HERE, report_path)
            blockers.extend(evaluation_blockers(report_path))
    except (OSError, ValueError) as exc:
        blockers, todos = [str(exc)], []
    print(f"Review Reply Writer - {'release' if args.release else 'development'} checks")
    print(f"  suite: {count} tests, {'green' if green else 'FAILING'}")
    for finding in blockers:
        print(f"  BLOCKED: {finding}")
    for todo in todos:
        print(f"  TODO: {todo}")
    if not blockers:
        print("  Checks passed. Human review is still required.")
    if not args.release:
        print("  This is not contest readiness. Run --release to check submission evidence.")
    else:
        print("  External accessibility, eligibility and firsthand claims require owner verification.")
    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
