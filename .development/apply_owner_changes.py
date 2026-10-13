"""Apply the locally tested owner-policy changes with exact source hashes."""
from pathlib import Path
import hashlib

CHANGES = [
    ('review_reply.py',
     '2997771b8ce6f8aeac888cb8ced9509de82ce5e8912147334592638b20c461a0',
     'b6221f1ae76b5b104653f430ccae772f5a29a21d5de7f78e62818aa1eeffd4c6',
     [
      (1, 2, r'''"""Local model drafts with owner-authorized statements and human approval.
'''),
      (3, 25, r'''All generation routes, including templates, validate their final output.
Checks are conservative heuristics, not a factual or legal guarantee.
'''),
      (36, 37, r'''from datetime import date, datetime, timezone
from reply_safety import (DraftBlocked, SAFETY_VERSION, MAX_REVIEW_CHARS,
                          policy_gaps, policy_instructions, require_valid,
                          validate_owner_statements, content_fingerprint)
'''),
      (82, 86, r''''''),
      (109, 109, r'''


def validate_input(review, stars=None, platform="generic", offer=None, approved_actions=None):
    if not isinstance(review, str) or not review.strip():
        raise ValueError("review must be non-empty text")
    if len(review) > MAX_REVIEW_CHARS:
        raise ValueError(f"review exceeds {MAX_REVIEW_CHARS} characters")
    if stars is not None and (type(stars) is not int or stars not in range(1, 6)):
        raise ValueError("star rating must be an integer from 1 to 5")
    if platform not in PLATFORMS:
        raise ValueError(f"unknown platform: {platform}")
    validate_owner_statements(offer, approved_actions)


def draft_findings(draft):
    """Recheck the current text and saved owner policy, not stale check labels."""
    common = dict(offer=draft.get("offer"), signoff=draft.get("signoff"),
                  platform=draft.get("platform", "generic"),
                  approved_actions=draft.get("approved_actions"))
    try:
        validate_input(draft.get("review"), draft.get("stars"),
                       common["platform"], common["offer"], common["approved_actions"])
        if draft.get("original") is not None and draft.get("previous") is not None:
            return followup_gaps(draft["reply"], draft["original"], draft["previous"],
                                 draft["review"], draft.get("business"), **common)
        return reply_gaps(draft["reply"], draft["review"], draft.get("business"),
                          draft.get("stars", _TIER_STARS.get(draft.get("tier"))), **common)
    except (ValueError, KeyError, TypeError) as exc:
        return [f"invalid saved draft: {exc}"]
'''),
      (142, 143, r'''    """True when the reply should acknowledge an unhappy experience."""
'''),
      (228, 229, r'''    for sentence in re.split(r"(?<=[.!?])\s+|\n+", reply):
'''),
      (239, 239, r'''    number_tokens = {n.lstrip("$").replace(",", "") for n in
                     re.findall(r"\$?\d[\d,]*(?:\.\d+)?", haystack)}
'''),
      (240, 241, r'''        if num.lstrip("$").replace(",", "") not in number_tokens:
'''),
      (247, 249, r'''               signoff=None, platform="generic", approved_actions=None):
    """Heuristic findings; an empty list still requires human review.
'''),
      (256, 256, r'''    try:
        validate_owner_statements(offer, approved_actions)
    except ValueError as exc:
        return [f"policy: {exc}"]
'''),
      (278, 280, r'''
'''),
      (295, 299, r'''    gaps.extend(policy_gaps(reply, offer, approved_actions))
    owner_context = "\n".join([offer or ""] + list(approved_actions or []))
    invented = invented_details(reply, review, business, signoff, owner_context)
'''),
      (309, 310, r'''                   signoff=None, platform="generic", approved_actions=None):
'''),
      (311, 312, r'''                          platform, approved_actions)
'''),
      (316, 317, r'''                 voice=None, approved_actions=None):
'''),
      (322, 326, r'''        guidance = ("- The review is unhappy: acknowledge the concern and "
                    "apologise plainly. Do not promise compensation or actions "
                    "unless the owner explicitly authorized the exact statement.\n")
'''),
      (329, 331, r'''                    "the problem plainly without claiming a fix or "
                    "inventing an operational action.\n")
'''),
      (333, 335, r'''                    "what delighted them. Do not promise to pass anything "
                    "to the team or invent a problem to apologise for.\n")
'''),
      (382, 383, r'''        "Write only the reply." + policy_instructions(offer, approved_actions))
'''),
      (411, 412, r'''                        choices=1, approved_actions=None):
'''),
      (420, 420, r'''    validate_input(review, stars, platform, offer, approved_actions)
'''),
      (427, 428, r'''                          voice=voice, approved_actions=approved_actions)
'''),
      (433, 434, r'''                      platform, approved_actions):
'''),
      (443, 444, r'''                                          platform, approved_actions):
'''),
      (450, 451, r'''                      platform, approved_actions)
'''),
      (462, 463, r'''                      platform, approved_actions):
'''),
      (467, 468, r'''                                         platform, approved_actions), ledger_path)
'''),
      (473, 544, r''''''),
      (545, 547, r'''    """Exact owner authorization on its own line, without invented conditions."""
    return offer.strip()
'''),
      (562, 567, r'''                   signoff=None, platform="generic", approved_actions=None):
    """Conservative fallback, checked with the same rules as model output."""
    validate_input(review, stars, platform, offer, approved_actions)
    spec = (specifics(review) or ["experience"])[0]
    who = business or "our business"
'''),
      (568, 582, r'''    opener = "Mahalo" if tone == "warm" else "Thank you"
    parts = [f"{opener} for sharing your feedback about {who}.",
             f"Your comments about the {spec} help us understand your experience."]
    if tier == "positive":
        parts.append("We appreciate hearing what you enjoyed and the time you "
                     "took to describe it. Your perspective is valuable to us.")
'''),
      (583, 586, r'''        parts.append("We are sorry that parts of your experience did not meet "
                     "your expectations. Thank you for explaining what mattered "
                     "to you in your own words.")
'''),
      (587, 588, r'''    statements = ([offer] if offer and tier != "positive" else []) + list(approved_actions or [])
    reply = "\n\n".join([body] + statements + [
        "We hope you'll visit again. Thank you for taking the time to share your perspective.",
        _signoff_line(business, signoff)])
    require_valid(reply_gaps(reply, review, business, stars, offer, signoff,
                             platform, approved_actions))
    return reply
'''),
      (596, 599, r''''''),
      (604, 605, r'''                  offer=None, signoff=None, platform="generic", approved_actions=None):
'''),
      (607, 608, r'''    The thread supplies context: quoted details may come from the original
'''),
      (609, 611, r'''    made must not be made again. An unhappy update does not authorize
    a refund or escalation. Explicit new owner authorization is required.
'''),
      (614, 614, r'''    try:
        validate_owner_statements(offer, approved_actions)
    except ValueError as exc:
        return [f"policy: {exc}"]
'''),
      (643, 646, r'''
'''),
      (650, 652, r'''
'''),
      (661, 665, r'''    gaps.extend(policy_gaps(reply, None if offer_spent else offer, approved_actions))
    owner_context = "\n".join([offer or ""] + list(approved_actions or []))
    invented = invented_details(reply, thread, business, signoff, owner_context)
'''),
      (675, 676, r'''                      offer=None, signoff=None, platform="generic", approved_actions=None):
'''),
      (677, 678, r'''                             business, offer, signoff, platform, approved_actions)
'''),
      (682, 683, r'''                          platform="generic", emphasis=None, voice=None, approved_actions=None):
'''),
      (688, 692, r'''        guidance = ("- The update is still unhappy: acknowledge the ongoing "
                    "concern and apologise. Never invent a stronger offer or "
                    "an escalation. A neutral acknowledgment is acceptable.\n")
'''),
      (694, 696, r'''                         "standing offer. Do NOT repeat it or invent an "
                         "escalation.\n")
'''),
      (745, 746, r'''        "Write only the follow-up reply." + policy_instructions(
            None if offer_spent else offer, approved_actions))
'''),
      (750, 751, r'''                      platform="generic", ledger_path=None, voice=None, approved_actions=None):
'''),
      (752, 752, r'''    validate_input(update, None, platform, offer, approved_actions)
'''),
      (759, 760, r'''                                   emphasis=emphasis, voice=voice, approved_actions=approved_actions)
'''),
      (765, 766, r'''                         offer, signoff, platform, approved_actions):
'''),
      (768, 769, r'''                         business, offer, signoff, platform, approved_actions)
'''),
      (780, 781, r'''                         offer, signoff, platform, approved_actions):
'''),
      (786, 787, r'''            signoff, platform, approved_actions), ledger_path)
'''),
      (790, 817, r''''''),
      (818, 820, r'''                      rng, offer=None, signoff=None, platform="generic",
                      approved_actions=None):
    """Never escalate or repeat an already used offer without authorization."""
    validate_input(update, None, platform, offer, approved_actions)
    spec = (specifics(update) or specifics(original) or ["experience"])[0]
'''),
      (821, 824, r'''    spent = bool(offer) and _norm(offer) in _norm(previous)
    parts = [f"Thank you for the update about your experience at {business or 'our business'}.",
             f"Your comments about the {spec} help us understand how things went this time."]
'''),
      (825, 828, r'''        parts.append("We appreciate hearing what you enjoyed and the time you took to explain it.")
'''),
      (829, 840, r'''        parts.append("We are sorry that you are still disappointed. Thank you for explaining "
                     "your concerns and what matters to you.")
    statements = ([offer] if offer and not spent and tier == "negative" else []) + list(approved_actions or [])
    reply = "\n\n".join([" ".join(parts)] + statements + [
        "We hope you'll visit again. Thank you for sharing your perspective.",
        _signoff_line(business, signoff)])
    require_valid(followup_gaps(reply, original, previous, update, business,
                                offer, signoff, platform, approved_actions))
    return reply
'''),
      (845, 846, r'''                             ".rrw", "profiles.json")



def atomic_json(path, data):
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory,
                                         delete=False) as fh:
            temp = fh.name
            json.dump(data, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp, path)
    finally:
        if temp and os.path.exists(temp):
            os.unlink(temp)
'''),
      (849, 850, r'''    """Load local owner profiles. Shipped samples are used only when none exist."""
    selected = path or PROFILES_PATH
    if path is None and not os.path.exists(selected):
        selected = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profiles.json")
'''),
      (851, 852, r'''        with open(selected, encoding="utf-8") as fh:
'''),
      (853, 855, r'''        if not isinstance(data, dict) or any(not isinstance(v, dict) for v in data.values()):
            raise ValueError("profile file must contain named JSON objects; restore from backup")
        return data
    except FileNotFoundError:
'''),
      (861, 864, r'''    atomic_json(path or PROFILES_PATH, profiles)
'''),
      (952, 954, r'''        if not isinstance(data, dict):
            raise ValueError("state file must contain a JSON object; restore from backup")
        return data
    except FileNotFoundError:
'''),
      (966, 969, r'''    atomic_json(path or LEDGER_PATH, ledger)
'''),
      (980, 987, r'''    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        fields = [name.strip().lower() for name in (reader.fieldnames or [])]
        if "review" not in fields or len(fields) != len(set(fields)):
            raise ValueError("CSV needs a unique review column and no duplicate headers")
        rows = []
        for row_no, raw in enumerate(reader, 2):
            if None in raw:
                raise ValueError(f"CSV row {row_no} has more values than its header")
            rows.append({k.strip().lower(): (v or "").strip() for k, v in raw.items()})
'''),
      (1021, 1021, r'''    metadata["safety_version"] = SAFETY_VERSION
    metadata["engine"] = engine
    metadata["validation_findings"] = draft_findings(dict(metadata, reply=reply))
    metadata["review_status"] = "blocked" if metadata["validation_findings"] else "needs_human_review"
'''),
      (1043, 1050, r'''def run_batch(rows, outdir, model, offline, seed=None, caller=None, defaults=None):
    """Each row is validated independently. Failed rows are reported, never saved as ready."""
'''),
      (1054, 1054, r'''        business = row.get("business") or defaults.get("business")
        base = {"n": idx, "business": business or "-", "tier": "-", "file": None}
'''),
      (1055, 1056, r''''''),
      (1057, 1060, r'''            results.append(dict(base, engine="skipped - empty review", status="skipped"))
'''),
      (1061, 1090, r'''        try:
            kind = row.get("kind") or defaults.get("kind") or "cafe"
            tone = row.get("tone") or defaults.get("tone") or "warm"
            if kind not in KINDS or tone not in TONES:
                raise ValueError("unknown business kind or tone")
            raw_stars = row.get("stars")
            stars = int(raw_stars) if raw_stars not in (None, "") else defaults.get("stars")
            # Never apply one business's policy to another business in a batch.
            same_business = _norm(business or "") == _norm(defaults.get("business") or "")
            owner = defaults if same_business else {}
            offer = row.get("offer") or owner.get("offer")
            signoff = row.get("signoff") or owner.get("signoff")
            actions = owner.get("approved_actions")
            platform = row.get("platform") or defaults.get("platform") or "generic"
            validate_input(review, stars, platform, offer, actions)
            reply, reason = None, "offline mode selected"
            if not offline:
                reply, reason = generate_with_model(
                    review, business, tone, stars, kind, model, caller=caller,
                    offer=offer, signoff=signoff, platform=platform,
                    ledger_path=defaults.get("ledger_path"), voice=owner.get("voice"),
                    choices=defaults.get("choices", 1), approved_actions=actions)
            engine = reason
'''),
      (1091, 1107, r'''                reply = template_reply(review, business, tone, stars, kind,
                    random.Random(seed + idx if seed is not None else None),
                    offer=offer, signoff=signoff, platform=platform, approved_actions=actions)
                engine = "template engine (offline)" if offline else f"template engine (fallback: {reason})"
            require_valid(reply_gaps(reply, review, business, stars, offer, signoff, platform, actions))
            tier = review_tier(review, stars)
            path = save_reply_file(outdir, business, review, reply, engine, tone, kind,
                                  tier, platform, stars=stars, offer=offer, signoff=signoff,
                                  voice=owner.get("voice"), choices=defaults.get("choices", 1),
                                  approved_actions=actions)
            results.append(dict(base, tier=tier, engine=engine,
                                file=os.path.basename(path), status="needs_human_review"))
        except (ValueError, TypeError, OSError) as exc:
            results.append(dict(base, engine=f"blocked: {exc}", status="blocked"))
'''),
      (1131, 1131, r'''    path = os.path.join(replies_dir, TRIAGE_NAME)
'''),
      (1132, 1137, r'''        with open(path, encoding="utf-8") as fh:
            state = json.load(fh)
    except FileNotFoundError:
'''),
      (1138, 1138, r'''    if not isinstance(state, dict) or any(not isinstance(v, dict) for v in state.values()):
        raise ValueError("invalid triage state; restore the file from backup")
    for name, entry in state.items():
        if os.path.basename(name) != name:
            raise ValueError("invalid draft name in triage state")
        if entry.get("status", "pending") not in ("pending", "approved", "aside"):
            raise ValueError("invalid draft status in triage state")
        if entry.get("status") == "approved":
            draft_path = os.path.join(replies_dir, name)
            if (entry.get("safety_version") != SAFETY_VERSION or
                    not os.path.isfile(draft_path) or
                    entry.get("content_sha256") != content_fingerprint(draft_path)):
                entry["status"] = "pending"
                entry["approval_invalidated"] = "draft content or safety policy changed"
    return state
'''),
      (1141, 1145, r'''    atomic_json(os.path.join(replies_dir, TRIAGE_NAME), state)
'''),
      (1198, 1198, r'''    approved_actions = draft.get("approved_actions")
'''),
      (1207, 1208, r'''                      voice=voice, approved_actions=approved_actions)
'''),
      (1223, 1224, r'''                signoff=signoff, platform=platform, approved_actions=approved_actions)
'''),
      (1227, 1228, r'''                                   signoff=signoff, platform=platform, approved_actions=approved_actions)
'''),
      (1233, 1234, r'''                "original", "previous", "approved_actions") if key in draft}
    require_valid(draft_findings(dict(draft, reply=reply, tone=tone)))
'''),
      (1256, 1256, r'''            reviewed_hash = content_fingerprint(path)
'''),
      (1257, 1257, r'''            if reviewed_hash != content_fingerprint(path):
                continue
'''),
      (1260, 1260, r'''            findings = draft_findings(draft)
            print_fn("Checks: " + ("; ".join(findings) if findings else
                     "passed heuristic checks; human review still required"))
'''),
      (1267, 1268, r'''                if reviewed_hash != content_fingerprint(path):
                    print_fn("Draft changed while being reviewed; review the current text again.")
                    continue
                findings = draft_findings(draft)
                if findings:
                    print_fn("Approval blocked: " + "; ".join(findings))
                    continue
                state[name] = {"status": "approved",
                               "content_sha256": reviewed_hash,
                               "safety_version": SAFETY_VERSION,
                               "approved_at": datetime.now(timezone.utc).isoformat()}
'''),
      (1328, 1329, r'''                               signoff=prof.get("signoff"), platform=prof.get("platform", "generic"))
'''),
      (1330, 1330, r'''    require_valid(reply_gaps(reply, review, prof.get("business"), 2,
                             prof.get("offer"), prof.get("signoff"),
                             prof.get("platform", "generic")))
'''),
      (1423, 1424, r'''def _main(argv=None):
'''),
      (1438, 1438, r'''    ap.add_argument("--approved-action", action="append", default=None,
                    help="exact owner-approved operational or contact statement; repeatable")
'''),
      (1485, 1485, r'''    exclusive_modes = (args.doctor, args.batch is not None, args.batch_dir is not None,
                       args.triage, args.tour, args.followup)
    if sum(bool(x) for x in exclusive_modes) > 1:
        ap.error("choose only one of doctor, batch, batch-dir, triage, tour, or followup")
    if args.review is not None and args.file is not None:
        ap.error("choose a positional review or --file, not both")
'''),
      (1495, 1495, r'''    if args.business and prof.get("business") and _norm(args.business) != _norm(prof["business"]):
        ap.error("the selected profile belongs to another business; create a separate owner profile")
'''),
      (1498, 1499, r'''    offer = args.offer if args.offer is not None else prof.get("offer")
    approved_actions = args.approved_action if args.approved_action is not None else prof.get("approved_actions")
    validate_owner_statements(offer, approved_actions)
'''),
      (1527, 1528, r'''                       "offer": offer, "approved_actions": approved_actions, "signoff": signoff,
'''),
      (1540, 1541, r'''                  "offer": offer, "approved_actions": approved_actions, "signoff": signoff,
'''),
      (1554, 1555, r'''                    "offer": offer, "approved_actions": approved_actions, "signoff": signoff,
'''),
      (1560, 1561, r'''        return 2 if any(r.get("status") == "blocked" for r in results) else 0
'''),
      (1579, 1579, r'''    validate_input(review, args.stars, platform, offer, approved_actions)

'''),
      (1592, 1593, r'''                platform=platform, ledger_path=LEDGER_PATH, voice=voice, approved_actions=approved_actions)
'''),
      (1600, 1602, r'''                                      offer=offer, signoff=signoff, platform=platform, approved_actions=approved_actions)
            engine = "template engine (offline)" if args.offline else "template engine (fallback)"
        require_valid(followup_gaps(reply, original, previous, review, business,
                                     offer, signoff, platform, approved_actions))
'''),
      (1603, 1604, r'''        print(f"\n[{engine}; checks passed; human review required]", file=sys.stderr)
'''),
      (1610, 1611, r'''                                   original=original, previous=previous, approved_actions=approved_actions)
'''),
      (1619, 1620, r'''            ledger_path=LEDGER_PATH, voice=voice, choices=choices, approved_actions=approved_actions)
'''),
      (1626, 1628, r'''                               rng, offer=offer, signoff=signoff, platform=platform, approved_actions=approved_actions)
        engine = "template engine (offline)" if args.offline else "template engine (fallback)"
'''),
      (1629, 1629, r'''    require_valid(reply_gaps(reply, review, business, args.stars, offer,
                             signoff, platform, approved_actions))
'''),
      (1630, 1631, r'''    print(f"\n[{engine}; checks passed; human review required]", file=sys.stderr)
'''),
      (1638, 1639, r'''                               signoff=signoff, voice=voice, choices=choices, approved_actions=approved_actions)
'''),
      (1643, 1643, r'''def main(argv=None):
    try:
        return _main(argv)
    except (ValueError, OSError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


'''),
     ]),
    ('test_review_reply.py',
     '61865b47aa7f6f927e2e0bf5c8f4803a79a2a7eaabe20ef4943b896101a934c5',
     '7d7c46fcc74e56f8d850c7b6f8422edb39b5fa2c1fc7ecb8df6d261a903f835f',
     [
      (23, 26, r'''    "You mentioned the coffee and the wait, and those details matter. "
    "We are genuinely sorry; that's on us. Your explanation tells us "
    "what did not meet your expectations. We hope you'll stop by "
'''),
      (27, 27, r'''
'''),
      (65, 71, r'''    def test_negative_without_offer_is_valid(self):
        self.assertEqual(rr.reply_gaps(GOOD_NEGATIVE_REPLY, ANGRY, "Moe's Coffee", 2), [])
        fabricated = GOOD_NEGATIVE_REPLY + "\nWe have repaired the coffee machine."
        self.assertTrue(any("policy:" in g for g in rr.reply_gaps(
            fabricated, ANGRY, "Moe's Coffee", 2)))
'''),
      (84, 93, r'''    def test_complimentary_offer_requires_authorization(self):
        offer = "a complimentary upgrade on your next visit"
        reply = GOOD_NEGATIVE_REPLY + "\n\n" + offer
        self.assertFalse(rr.validate_reply(reply, ANGRY, "Moe's Coffee", 2))
        self.assertTrue(rr.validate_reply(reply, ANGRY, "Moe's Coffee", 2, offer=offer))
'''),
      (329, 332, r'''        invented = GOOD_NEGATIVE_REPLY + " A $50 credit toward your next visit."
'''),
      (540, 548, r'''        previous = GOOD_NEGATIVE_REPLY + "\n\n" + STANDING_OFFER
        reply = "Thank you for the update. We are sorry the coffee was still cold. " \
                "We hope you'll visit again.\n\n" + STANDING_OFFER + "\n- The Moe's Coffee team"
        gaps = rr.followup_gaps(reply, ANGRY, previous, UPDATE_STILL_BAD,
                               "Moe's Coffee", offer=STANDING_OFFER)
'''),
      (549, 550, r'''        self.assertTrue(any("unauthorized compensation" in g for g in gaps))
        # An unhappy follow-up must NOT be forced to invent an escalation.
        safe = rr.template_followup(ANGRY, previous, UPDATE_STILL_BAD,
            "Moe's Coffee", "warm", "cafe", random.Random(1), offer=STANDING_OFFER)
        self.assertNotIn("refund", safe)
        self.assertNotIn(STANDING_OFFER, safe)
'''),
      (593, 594, r'''            ANGRY, GOOD_NEGATIVE_REPLY + "\n" + STANDING_OFFER, UPDATE_STILL_BAD,
'''),
     ]),
    ('test_import_reliability.py',
     '6d4f0012a74d36a15b63c0a0eb779c1d9dff6f9d5b2dac8fba408e86fb2bbf7e',
     'fc9d41a43b4001aee1c35771f6ddb2d1ab7178b4edb3b55417ccb8b6edae5ae4',
     [
      (66, 67, r'''                previous=GOOD_NEGATIVE_REPLY + "\n" + offer, offer=offer)
'''),
      (70, 71, r'''            self.assertEqual(draft["previous"], GOOD_NEGATIVE_REPLY + "\n" + offer)
'''),
      (73, 74, r'''                draft["reply"], ANGRY, GOOD_NEGATIVE_REPLY + "\n" + offer,
'''),
     ]),
    ('EVALUATION.md',
     'a38592cdc2779ea298e1997f5319f02685e65d9787ed821cd43a36f40374f425',
     'd5bdb3ad4cb5eed7d095e6c308ef4bf14ae85385aab2f1b106b1286e813acf93',
     [
      (130, 130, r'''
## Follow-up: owner-policy development pass

This document above describes the import baseline. The subsequent implementation
addresses its first two priorities and part of its state/input priority. See
[docs/SAFETY_PASS.md](docs/SAFETY_PASS.md) for the current design and executable
evidence. The original unsafe gallery is historical, not the active test gallery.
'''),
     ]),
]

for name, before, after, edits in CHANGES:
    path = Path(name)
    original = path.read_bytes()
    if hashlib.sha256(original).hexdigest() != before:
        raise SystemExit(f"Source changed: {name}; refusing to overwrite")
    rows = original.decode("utf-8").splitlines(keepends=True)
    for start, end, text in reversed(edits):
        rows[start:end] = [text]
    updated = "".join(rows).encode("utf-8")
    if hashlib.sha256(updated).hexdigest() != after:
        raise SystemExit(f"Result hash mismatch: {name}")
    path.write_bytes(updated)
    print(f"Verified update: {name} {after}")
