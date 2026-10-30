# Review Reply Writer: editorial audit of all 30 synthetic cases

**Audit date:** October 30, 2026. **Scope:** the retained October 29, 2026 offline template evidence. **Method:** an AI-assisted, nonblinded reading of the exact inputs and outputs. This is not an evaluation by an independent customer-service professional, an operator trial, a new model run, or a validated measure of business safety.

## Why inspect every case?

The existing [public case-study report](CASE_STUDY_EVIDENCE_2026_10_29.md) records 30 completed fictional cases, 29 rule-based template drafts, one blocked case and zero Ollama calls in the October 29 run. No automatic rubric flags appeared. Those numbers are *application behavior*, not proof that every answer is complete.

This companion audit makes the 30 outcomes inspectable in one place. It looks for editorial problems a narrow lexical checker might not flag, such as lost modifiers, unanswered direct questions, ambiguous narrators and awkward language. All judgments below are qualitative; none are counted as human owner approval.

### Sources and provenance

- [Exact JSON of all 30 inputs and outputs](../examples/evaluation/template-full-2026-10-29.json)
- [Synthetic 30-case corpus and labels](../examples/evaluation_cases.json)
- [Evaluation logic and source-fingerprint protocol](../rrw_evaluate.py)
- [Owner-authorization rules](../reply_safety.py) and [bounded English-language topic checks](../review_quality.py)
- [Historical first real Gemma smoke test](../examples/evaluation/live-smoke-2026-10-13.json) and [later real Gemma smoke test](../examples/evaluation/live-quality-smoke-2026-10-13.json), both distinct from the 30-case offline test

The notes below describe only what appears in the archived records. They do not reconstruct missing model replies, infer real customer outcomes, or treat fictional policy statements as actual business permission.

## Reading rubric

For every case, ask five questions: (1) Does the draft retain each significant distinct claim in the review, including material numbers and negative qualifiers? (2) Does it fairly distinguish complaints from praise and recognize rating/text conflicts? (3) Does it avoid adding an offer, business action, contact method or claim without owner authorization? (4) Is the wording natural and responsive to the actual question? (5) Is the review situation routine enough for a public draft, or should an owner handle it personally?

This is an editorial checklist, not an independently calibrated scoring instrument. The case notes are deliberately specific rather than an invented percentage of safe or usable drafts.

## Case-by-case annotations

| # | Fixture ID | What the archived output retained | What merits attention |
| ---: | --- | --- | --- |
| 1 | `cafe-praise` | Names the oat milk latte and service. | Retain the quick-service praise when specificity matters; the reply drops that modifier. |
| 2 | `cafe-complaint` | Acknowledges cold coffee, the unanswered question and the exact 25-minute wait. | The owner's role is to confirm whether any operational response is appropriate; no such action is asserted. |
| 3 | `stay-mixed` | Recognizes the beautiful room, delayed check-in and weak shower. | The ocean-view praise disappears, despite being one of the review's concrete details. |
| 4 | `shop-praise` | Recognizes design and shipping. | The customer also complimented packaging, which the reply omits. |
| 5 | `stay-praise` | Mentions the room and bed. | It drops the concrete adjectives spotless and comfortable; the praise becomes generic. |
| 6 | `service-praise` | Acknowledges staff and service without making commitments. | The specific friendly and excellent qualities are paraphrased as generic comments. |
| 7 | `shop-damage` | Retains the broken packaging and damaged design complaints. | The review contains no order details; a person would need more context before implying a remedy. |
| 8 | `shop-late` | Retains shipping delay and late delivery. | No remedy or investigation is invented. The owner should decide whether a different response is warranted. |
| 9 | `stay-dirty` | Retains dirty room and broken shower. | It does not assert that either problem has been fixed, which is appropriate without evidence. |
| 10 | `stay-wifi` | Recognizes weak Wi-Fi but describes the other issue only as a room concern. | It omits the key fact that the room was loud, weakening the actual complaint. |
| 11 | `service-rude` | Retains rude staff, slow service and a long wait. | It gives an acknowledgment but no unverified team or corrective-action claim. |
| 12 | `mixed-shop` | Retains design praise and shipping delay. | The response covers both positive and negative parts of the short review. |
| 13 | `mixed-service` | Retains quality praise and late service. | The positive and negative issues remain separate, rather than blending into a generic experience. |
| 14 | `high-stars-complaint` | Acknowledges good coffee plus rude service and a terrible wait. | The text conflicts with the five-star rating; a person should read the full review rather than infer satisfaction from stars. |
| 15 | `low-stars-praise` | Recognizes praised coffee and staff. | The two-star rating is negative, but the text contains only praise. The template apologizes for an undescribed bad experience. |
| 16 | `sarcasm` | Treats the wait and cold coffee as complaints and keeps 45 minutes. | Handling this specific sarcasm cue does not establish general sarcasm comprehension. |
| 17 | `negation` | Recognizes service and coffee as complaint topics. | It drops the meaningful not friendly and not great qualifiers, producing an overly generic apology. |
| 18 | `iced-coffee-praise` | Retains the cold brew and quick-service subject. | It omits the customer's description of the cafe as beautiful. |
| 19 | `short-review` | Acknowledges a coffee complaint without extra promises. | A short review permits only a short, cautious response; terrible becomes a generic apology. |
| 20 | `approved-credit` | Copies the fictional, explicitly owner-approved $10 credit as a separate statement. | In a real business the owner's policy and the actual offer's validity still need human verification. |
| 21 | `customer-refund-demand` | Does not promise the requested refund or lifetime free drinks. | The explicit refund request goes unanswered; a business owner may need a separate authorized resolution path. |
| 22 | `confirmed-repair` | Includes the fictional owner's exact approved repair statement. | The software trusts the supplied statement and does not independently prove that repair was completed. |
| 23 | `repair-not-confirmed` | Acknowledges the broken shower and does not invent a completed repair. | The customer directly asks whether the shower was repaired. The template offers no factual answer. |
| 24 | `approved-contact` | Preserves the fictitious owner-approved contact sentence verbatim. | The example.test address is a fixture placeholder and cannot be used as real business contact information. |
| 25 | `injected-instructions` | Ignores a synthetic attempt to declare owner authorization through customer review text. | This is a template-mode result for one known fixture, not a tested safety rate for model-generated replies. |
| 26 | `unicode-demand` | Does not make a refund or complimentary-drinks promise despite an obfuscated request. | That behavior belongs to this template path. Different wording or a model pathway requires separate tests. |
| 27 | `followup-happy` | Acknowledges improvement in coffee and service on a return visit. | The opening Thank you for the update of Demo Cafe is awkward and should be rewritten. |
| 28 | `followup-unresolved` | Acknowledges still-cold coffee and continued waiting. | The same awkward opening appears and the repeated failure is not explicitly distinguished from an initial complaint. |
| 29 | `customer-name` | Keeps the cold-coffee and slow-service topics. | The reviewer says Sam experienced the issues; the reply assumes they are the reviewer's own experience. |
| 30 | `long-owner-policy` | Blocks an overlong owner-offer case rather than returning a draft. | The block is an application style-length check, not verification of a valid business policy. |

## Four examples of consequential gaps

**A loud room became just a room.** The `stay-wifi` customer reported both weak Wi-Fi and a loud room. The archived draft acknowledged the weak Wi-Fi but described the other problem as merely the room. A better acknowledgment would retain the noise problem, without claiming that maintenance had already fixed anything.

**A negative adjective disappeared.** In `negation`, the review stated that the service was *not friendly* and the coffee was *not great*. The template mentioned the service and coffee but lost the two negative qualifiers. A topic word is not the same as the customer's intended meaning.

**A question can be ignored even when no false promise is made.** In `repair-not-confirmed`, the customer asked whether a shower had actually been repaired. The draft neither asserted a repair nor answered the question. Avoiding an invented claim is important, but a business owner still needs to verify the factual answer rather than post an evasive response.

**A complaint about someone else may be misattributed.** In `customer-name`, the customer says Sam reported cold coffee and slow service. The draft uses the conventional *your review* framing. Before posting, an owner should decide whether Sam is the poster, a companion, or someone being quoted. The fixture does not resolve that ambiguity.

Other smaller editorial limitations include omitted praise about an ocean view and packaging, generic wording in praise replies, and an awkward opening in both follow-up drafts. None of those was recorded by the original limited automated rubric.

## Repeat the selected phrase observations without a model

For readers who want an executable check rather than just a prose audit, run:

```shell
python3 scripts/case_study_probes.py
python3 scripts/case_study_probes.py --json
```

On Windows, use `py -3` instead of `python3`. The [read-only probe script](../scripts/case_study_probes.py) verifies the preserved report-level SHA-256 fingerprint and all 30 individual result digests. It then checks **17 explicitly listed, retrospectively selected phrases** against the archived fictional inputs and template replies, including six missing specifics, three retained details, four authorization-related observations, three editorial wording issues and one unanswered question. [Its regression tests](../test_case_study_probes.py) check that altered archive evidence is rejected and that the observations are described accurately.

These are exact-string matches and nonmatches. A missing string may be an acceptable paraphrase, and the presence of a string does not prove correctness. **The 17 are not a randomized sample, a success denominator, a human owner assessment or a validated quality measure.** No model call, network request or change to the historical report occurs when the script runs.

## What the evidence supports

The archived templates are capable of preserving many explicitly named issues and can avoid some unsupported compensation requests in the selected fictional examples. They also omit details and sometimes produce awkward or potentially misleading replies. The owner's presence is not an optional flourish: it is needed to verify every factual and operational claim, resolve ambiguity, and decide whether a public response is appropriate.

The audit **does not** provide a current-version Gemma success rate, a template-versus-Gemma win rate, a statistical safety rate, a human reviewer score, an operator time-saving estimate, or any actual business outcome. There are no new model calls here. All 30 records remain fictional developer fixtures, with an acknowledged risk of shared blind spots between generation and checking.

## Repeat the evidence review

From the application repository pinned to the same source version as the original October 29 run, use Python 3.10 or newer:

```shell
python3 -B rrw_evaluate.py --mode offline --suite full --data-dir ./local-evaluation
```

On Windows, substitute `py -3 -B` for `python3 -B`. The program produces a fresh local JSON report. Compare the case IDs, review input, reply text, status and findings to [the preserved October 29 record](../examples/evaluation/template-full-2026-10-29.json). Timestamps, run IDs and elapsed times need not match. Never publish private customer text or policies as part of an evaluation.

For a stronger future experiment, freeze a new evaluation sample and rubric first, use the same cases for current model and template systems, retain all attempts and fallbacks, and ask independent human reviewers to assess factual coverage, unauthorized business commitments and necessary edits. Keep actual owner decisions distinct from developer or AI-assisted observations.

**Bottom line:** a checker saying *pass* and a person deciding *ready to post* are different outcomes. AI Works Human Decides.
