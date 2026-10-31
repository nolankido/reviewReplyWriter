# Preserve fractional wait durations

October 14, 2026. The owner's direct continuation started from verified main
`4cf29b835e105ee8beb9af27a983360ca45a4930`, full tree
`3f88b63943cf81d77e11a5f0835f95c46c9b3026`, matching clean local source.
No AGENTS.md, new competing work or Actions workflows were present. The
overnight automation stays paused; this is direct owner-authorized follow-up.

## Reproduction and result

On that source, the fictional review “Cold coffee and a 1.5 hour wait” produced
a five-hour duration. The template then rejected its own reply as an invented
number. The same defect interpreted 2.25 hours as 25 hours and 10.5 minutes as
five minutes. These were executed reproductions, not operator feedback.

Shared duration parsing now preserves the entire decimal spelling. Templates,
model prompts, detail validation and source-linked checks agree on 1.5 hours,
2.25 hours and 10.5 minutes. Trailing zeros and leading-dot notation remain
unchanged, so 1.50 and .5 do not get rounded or rewritten. Fractional keys use
JSON-safe strings; ordinary integer keys retain their existing integer type.
Units are normalized to minute/hour, but never converted into another unit.

The bounded grammar accepts at most four digits before the decimal point and
six after it, with a minute/hour label. It does not start again at the tail of
an unsupported number, exponent, signed number or comma-grouped number.
Numeric comma groups stay together during clause splitting so 1,500 cannot
be mistaken for 500. Unsupported forms are not extracted as duration facts;
they still need full human review. Written fractions and arbitrary units are
outside this grammar. These remain conservative English lexical checks.

The quality version is `review-detail-v4-fractional-durations`; approval version
is `owner-policy-v8-fractional-durations`. Older approvals require fresh review
and explicit approval. Reading them does not rewrite private files. Current
follow-ups use current update durations without inheriting the original wait.
Review durations never authorize business promises or owner policy.

## Actual verification

All 555 Python tests passed, including eight new regressions; 116 focused
quality/evidence/workspace tests passed. The final actual local verifier passed
the development checker, both real Python launcher HTTP workflows and all nine
Node state scripts with unchanged inventoried source. Compilation and whitespace
checks passed. Real loopback HTTP generation, approval and approved copy retain
1.5 hours; editing it to five hours saves a blocked draft and rejects approval
and approved copy. A controlled model stand-in with the wrong duration receives
a coached retry. Decimal source offsets and JSON spelling are checked.

The unchanged 30-case fictional Quality Lab set completed with 29 templates,
one expected oversized-policy block, zero errors/rubric flags and zero model
calls/human assessments. This is regression evidence, not a blind quality test.
Historical Gemma receipts are preserved and stale for current source. Real
Windows, browser/mobile/screen-reader behavior, fresh Gemma and real operator
feedback remain unexecuted. No Actions job, installation, paid inference,
posting, upload or contest submission occurred. Exact candidate/tree and merge
outcome are recorded in the PR. The next evidence priority remains current
target-computer verification, actual local Gemma and consenting owner use.

### Later source version

This report records the earlier `review-detail-v4-fractional-durations` and `owner-policy-v8-fractional-durations` release. A subsequent [case-study-driven correction](CASE_STUDY_CORRECTION_2026_10_30.md) advances current detail checks to `review-detail-v5-room-noise` and saved approval checks to `owner-policy-v9-room-noise`. This note preserves the historical release and does not claim new model or operator evidence.

A further [negated-detail correction](CASE_STUDY_NEGATION_CORRECTION_2026_10_30.md) introduced `review-detail-v6-negated-qualifiers` and `owner-policy-v10-negated-qualifiers`. Earlier version labels above are historical records. New source and approval revisions must be checked separately; the October 29 template and old Gemma data were not rerun or rewritten.
