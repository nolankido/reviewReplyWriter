#!/usr/bin/env python3
"""Pre-flight checker for the DEV Week 2 submission.

    python3 check_submission.py

Verifies the claims the submission makes, while they can still be
fixed: every gallery reply still passes the current validator (the
fact guard included), each saved file's engine credit parses, the
test suite is green and POST_FINAL.md's test count matches it, and
the DEV front matter carries both challenge tags. What only the
owner can do (the real-review paragraph) is reported as a TODO,
never as a blocker. Exit 0 means nothing is blocking.
"""
import io
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import review_reply as rr  # noqa: E402

POST_PATH = os.path.join(HERE, "POST_FINAL.md")
EXAMPLES = os.path.join(HERE, "examples")

# stem, business, stars - the gallery the post quotes.
GALLERY = [
    ("01-glowing-cafe", "Moe's Coffee", 5),
    ("02-angry-cafe", "Moe's Coffee", 2),
    ("03-mixed-stay", "Kai Loft", 3),
]


def parse_saved_reply(path):
    """(engine credit, reply text) from a saved reply file."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    credit = re.search(r"Drafted [^>]*? by ([^;]+);", text)
    engine = credit.group(1).strip() if credit else None
    platform_m = re.search(r"platform=(\w+)", text)
    platform = platform_m.group(1) if platform_m else "generic"
    reply = text.split("## The reply", 1)[-1].strip()
    return engine, platform, reply


def discover_suite():
    loader = unittest.TestLoader()
    return loader.discover(HERE, pattern="test_*.py")


def suite_state():
    """(test count, green?) across every test file in the project."""
    suite = discover_suite()
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=0).run(
        suite)
    return suite.countTestCases(), result.wasSuccessful()


def gallery_blockers():
    blockers = []
    for stem, business, stars in GALLERY:
        review_path = os.path.join(EXAMPLES, f"{stem}.txt")
        reply_path = os.path.join(EXAMPLES, f"{stem}-reply.md")
        if not os.path.exists(reply_path):
            blockers.append(f"{stem}: saved reply file is missing")
            continue
        with open(review_path, encoding="utf-8") as fh:
            review = fh.read().strip()
        engine, platform, reply = parse_saved_reply(reply_path)
        if not engine:
            blockers.append(f"{stem}: no engine credit line found")
            continue
        gaps = rr.reply_gaps(reply, review, business, stars,
                             platform=platform)
        if gaps:
            blockers.append(
                f"{stem}: gallery reply no longer passes the checker "
                f"({'; '.join(gaps)}) - regenerate it before posting")
    return blockers


def post_findings(post_text, actual_count, suite_green):
    """(blockers, todos) for POST_FINAL.md against the real numbers."""
    blockers, todos = [], []
    for claimed in re.findall(r"Ran (\d+) tests", post_text):
        if int(claimed) != actual_count:
            blockers.append(
                f"POST_FINAL claims {claimed} tests; the suite has "
                f"{actual_count} - fix the number or the post is "
                "wrong on arrival")
    if not suite_green:
        blockers.append("the test suite is not green right now")
    for tag in ("devchallenge", "hf26challenge"):
        if tag not in post_text:
            blockers.append(f"POST_FINAL front matter is missing "
                            f"the #{tag} tag")
    if "[REAL REVIEW TEST" in post_text:
        todos.append("replace the [REAL REVIEW TEST] paragraph with "
                     "the real run's story (owner only)")
    return blockers, todos


def main():
    count, green = suite_state()
    with open(POST_PATH, encoding="utf-8") as fh:
        post_text = fh.read()
    blockers = gallery_blockers()
    post_blockers, todos = post_findings(post_text, count, green)
    blockers += post_blockers

    print("Review Reply Writer - submission pre-flight")
    print(f"  suite:    {count} tests, {'green' if green else 'FAILING'}")
    for stem, business, stars in GALLERY:
        reply_path = os.path.join(EXAMPLES, f"{stem}-reply.md")
        if os.path.exists(reply_path):
            engine, platform, _ = parse_saved_reply(reply_path)
            print(f"  {stem}: engine = {engine} (platform {platform})")
    if blockers:
        print("\n  BLOCKING:")
        for b in blockers:
            print(f"   - {b}")
    if todos:
        print("\n  Owner TODOs:")
        for t in todos:
            print(f"   - {t}")
    if not blockers:
        print(f"\n  Nothing blocking - {len(todos)} owner TODO(s) left.")
    return 1 if blockers else 0


if __name__ == "__main__":
    sys.exit(main())
