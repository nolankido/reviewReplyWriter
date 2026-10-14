---
title: A Local Review-Reply Writer That Knows When It Cannot Promise a Refund
published: false
tags: devchallenge, hf26challenge
---

> TODO: This is an unpublished working draft. A hosted CPU Gemma smoke run is
> recorded, but owner-device testing, human assessments, the public demo, contest
> development-window confirmation and judge access still need review.

## What I Built

Review Reply Writer drafts replies to customer reviews using a local Ollama
model. Its central design question is not whether AI can sound polite. It is
whether a draft promises something the owner never authorized.

The application combines a local model, conservative policy and format checks,
one coached retry, a checked template fallback, and a human approval queue.
It does not post to review platforms. Its default response to an unhappy
customer is an acknowledgment and apology, not an automatic refund.

The local browser workspace puts that pipeline behind a single Python launch:
review input, business settings, an editable draft, visible findings, explicit
approval, and copy/export controls. Edited replies lose their approval, and a
stale tab cannot copy an earlier version. No review-platform credentials or
publishing integration are involved.

## Demo

TODO: Add a public video showing real local Gemma generation, a rejected
unauthorized promise, the retry or labelled fallback, and human approval.
The deterministic examples in `examples/safety/` are template outputs, not
new Gemma results. They demonstrate the safety checks without claiming model
performance.

## Code

Repository: https://github.com/nolankido/reviewReplyWriter

The code is MIT licensed. Repository visibility and judge access still need
owner confirmation. The license does not replace Gemma's model terms.

## How I Built It

The first prototype required concrete make-it-right offers and trusted its own
fallback templates. Code review exposed the flaw: a refund or a claim that a
machine has been repaired is a business commitment, even when a deterministic
template says it.

The revised pipeline treats customer text and earlier replies as untrusted
data, not permission. An owner can configure an exact offer or confirmed action.
A larger amount, extra refund, invented contact instruction or operational
claim is checked separately. Approved text must stand alone and cannot be
silently expanded. These are conservative English-language heuristics, not a
proof that every possible promise or false statement will be caught.

All generation routes validate their final output. If a fallback cannot meet
policy and length constraints, it blocks instead of being presented as ready.
The approval queue checks the current text again. Approval is tied to the saved
file's fingerprint and policy version, so an edit requires another review.

Tests exercise unauthorized compensation, exact authorization, coached retry,
fallback failures, per-business policy isolation, follow-up conversations,
input errors and approval invalidation. Test callers simulate model responses;
they must not be presented as live Gemma evaluations. A separate real Gemma
smoke run is now retained in the repository; operator usability remains untested.

## Testing the Difference Between a Demo and Evidence

Quality Lab runs a separate, developer-written set of fictional reviews. It
records raw attempts, checked fallbacks, blocked outputs, model metadata and
source fingerprints. Model timings exclude template-only cases, and a passed
wording check never becomes a claim of customer satisfaction.

There are three smoke scenarios and 30 stress scenarios. The latter deliberately
includes rating/text conflicts, negation, sarcasm, prompt injection, authorized
and unauthorized promises, and follow-up threads. These fixtures are not an
unbiased benchmark or real-customer validation. The initial template run exposed
sentiment and topic-selection weaknesses; those observations remain visible.

A human can assess each exact result and preserve corrections beside the original.
The exported evidence keeps these judgments separate from generated output and
from posting approval. A recorded evaluation file is now needed for the project's
release check; toggling a checkbox alone is no longer enough to claim a fresh run.
The first real three-case Gemma smoke run on a GitHub-hosted CPU runner produced two
model-written drafts and one template fallback, with five completed API responses.
The complaint retry exposed a false positive: "should have addressed" was matched
as a completed action. The mixed-review fallback was still repetitive. The next code pass addressed these observed failures: a match-level retrospective
exception, multi-complaint coverage, preserved durations, and shorter fallbacks.
A separate retained comparison uses the unchanged 30-case template set. The four
original diagnostic warnings became zero while the oversized policy still blocked.
These cases informed development, so this is not an unbiased quality score.

The [original measurement report](https://github.com/nolankido/reviewReplyWriter/blob/main/docs/QUALITY_RESULTS.md) and complete JSON preserve those
results. No human assessments were manufactured. Operator feedback, user-device
testing and a public demo still need to be supplied and reviewed before publication.

## Why Open Innovation Matters

An owner can inspect and change the rules as well as the prompts. The local model
can be tested against the same saved reviews after a change without per-request
API fees. Hardware, electricity, setup and human editing still have costs. The
intended model configuration uses downloaded Gemma weights through Ollama,
so the owner can run inference on their own machine rather than make a paid
API call for every draft. The Python policy and workflow code are inspectable
and modifiable. Local operation depends on the selected model and Ollama's
configuration, which the application does not fully audit.

## Side Hustle Direction

The narrow customer is an independent cafe, shop or accommodation operator who
already answers reviews but wants consistent drafts
without sending additional review and policy context to a hosted writing tool.
The local browser interface is now implemented, but remains a supervised
prototype rather than a market-ready service. Real operator feedback and
measured model quality are the next product steps. A paid version could package local setup, business-specific policy onboarding and
support, but willingness to pay has not been measured. No paying customer,
time-saving measurement or adoption result is claimed here. The next validation
step is five operator-selected reviews with editing effort and rejected drafts
recorded, not a testimonial written in advance.

## Development Assistance

AI coding assistance was used during implementation, testing, and this write-up.
The repository records the changes and repeatable checks. Automated tests and
AI-assisted analysis are not represented as customer feedback.

## Prize Categories

Intended category: Best Use of Gemma. Confirm eligibility and supply a fresh
Gemma demonstration before submitting this entry.
