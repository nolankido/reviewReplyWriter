---
title: A Local Review-Reply Writer That Knows When It Cannot Promise a Refund
published: false
tags: devchallenge, hf26challenge
---

> TODO: This is an unpublished working draft. Record fresh local Gemma runs,
> add the demo, verify the contest's development window and public code access,
> and review all firsthand claims before publishing.

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
they must not be presented as live Gemma evaluations. Fresh model runs and a
business-owner usability test are still outstanding.

## Why Open Innovation Matters

The intended model configuration uses downloaded Gemma weights through Ollama,
so the owner can run inference on their own machine rather than make a paid
API call for every draft. The Python policy and workflow code are inspectable
and modifiable. Local operation depends on the selected model and Ollama's
configuration, which the application does not fully audit.

## Side Hustle Direction

The proposed customer is a small-business operator who wants consistent drafts
without sending additional review and policy context to a hosted writing tool.
The local browser interface is now implemented, but remains a supervised
prototype rather than a market-ready service. Real operator feedback and
measured model quality are the next product steps. No paying customer, time-saving measurement or adoption result is
claimed here.

## Prize Categories

Intended category: Best Use of Gemma. Confirm eligibility and supply a fresh
Gemma demonstration before submitting this entry.
