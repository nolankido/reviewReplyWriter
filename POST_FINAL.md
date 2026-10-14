---
title: A Local Review Writer That Does Not Invent Your Refund Policy
published: false
tags: devchallenge, hf26challenge
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 2: Side Hustle](https://dev.to/challenges/hacktoberfest-week2-2026-10-12).*

> TODO before publication: insert a judge-accessible video URL, check repository
> access and the original development window, review the final live evidence,
> and remove this notice. This file is a draft, not a submitted entry.

## What I Built

A customer says their coffee was cold and they waited 25 minutes. A model can
write a polite apology. It can also offer a full refund, invent an email address,
or announce that the shop has retrained its staff.

Those are not merely writing mistakes. They are decisions the owner never made.

Review Reply Writer is a local browser app for small-business owners who want
help drafting replies without handing the model authority to set their policies.
It uses Gemma 3 through Ollama, checks the proposed response, allows one coached
retry, and uses a clearly labelled template when the model cannot produce an
acceptable draft. A person still edits, reviews and approves the final text.
Nothing is posted automatically.

The proposed buyer is an independent shop, cafe or accommodation operator with
a recurring review queue. The product offers a saved business voice, exact
owner-authorized statements, first replies and follow-ups, and a searchable
local draft library. A possible business model is paid installation, policy
setup and support around the free code. That is a commercial hypothesis, not a
claim that someone has paid or that a time-saving target has been validated.

## Demo

TODO: Replace this paragraph with the actual hosted video link after reviewing
it. The recording script captures the running application, a fictional review,
real engine labels, a deliberately unsafe edit, and approval/export controls.
A template-only recording is explicitly marked as no AI. Demonstration clicks
are not real customer approval or a first-user testimonial.

The application starts with `py rrw_web.py` or the Windows launcher. Its browser
interface requires no additional Python runtime packages. Ollama and downloaded
Gemma weights are needed for model-written drafts, not for template preview.

## Code

Repository: https://github.com/nolankido/reviewReplyWriter

The application code is MIT licensed. Gemma's model terms are separate. The
repository must be accessible to judges before this article is submitted.

## How I Built It

The first version made a tempting mistake: it required a concrete make-it-right
offer in negative replies and trusted its own templates. A fallback could then
promise a refund even when no owner had authorized one.

I changed that boundary. Review text, earlier replies and voice examples are
untrusted context, not permission. An owner can authorize an exact offer or
operational statement. The checker looks separately for compensation, actions
and customer instructions. An authorized credit does not authorize a larger
credit, a refund on top, or invented instructions for redeeming it.

The same final checks apply to model output, retries and templates. A fallback
that fails is blocked rather than treated as safe because it is deterministic.
The approval queue rechecks the saved text. Approval belongs to a content
fingerprint and policy version, so editing the text or using a stale tab cannot
silently carry forward an old approval.

These are conservative English-language checks, not a proof of truthfulness.
The software trusts owner-authorized statements; it cannot know whether a repair
actually happened. That is why the human decision is part of the workflow.

### A useful failure in the checker itself

A real hosted Gemma test produced the phrase "should have addressed" about a
barista's missed response. The checker matched "have addressed" and rejected
it as a claim that an action had already happened.

That was our false positive, not a safety success. A later quality pass added a
narrow exception for past-modal wording while continuing to scan for actual
commitments elsewhere in the sentence. It does not exempt a refund or an
explicit future deadline just because the word "should" appears nearby.

The same test showed another problem: the accepted retry turned a 25-minute
wait into an "extended wait." The reply sounded smoother but lost useful detail.
The current prompt now includes a complaint checklist, and output checks retain
explicit reported wait durations. Mixed reviews must cover detected complaint
topics and acknowledge a detected positive point, not answer only the praise.

### Evidence instead of a polished anecdote

Quality Lab runs fictional regression reviews without touching the customer's
drafts, profiles or publication approvals. It preserves the original attempts,
rejection reasons, retries, final engine and available model timing receipts.
Human assessments and edited versions stay beside the unchanged original.

The earlier three-case hosted Gemma smoke produced two model-written final
replies and one labelled template fallback from five completed API responses.
It is retained as historical evidence, not presented as a universal success rate
or a prediction of performance on a customer's laptop.

After the quality changes, a fresh run of the same three fictional scenarios
produced three model-written drafts on the first attempt. The complaint kept the
25-minute wait, and the mixed reply covered both check-in and the weak shower.
Those cases took about 18 to 20 seconds each on a GitHub-hosted CPU runner.
The raw outputs are retained in the repository. Three selected stochastic cases
do not establish a general success rate, and none has been labelled as a real
business owner's assessment.

For the quality pass, I reran the unchanged 30-case template set. Both runs
retained 29 drafts, one blocked oversized owner policy and no execution errors.
Cases flagged by the existing limited rubric fell from four to zero. Median
reply length fell from 64 to 38 words. The fixes target known cases, so this is
not a blind benchmark or evidence that every reply is good. No human assessments
or customer endorsements were manufactured.

The deterministic suite now contains 247 tests, including targeted counterexamples
for authorization, omitted details, negation and rating conflicts. Browser tests
exercise editing, stale tabs, clipboard copying and evidence export. Controlled
model responses in unit tests are kept distinct from actual inference records.

AI coding assistance helped implement and test this project. The repository
history and retained reports are inspectable evidence of the engineering work;
they are not a claim that every implementation step was handwritten.

## Why Does Open Innovation Matter?

Downloaded Gemma weights let this workflow use the owner's machine for inference
instead of requiring a paid hosted model request for every draft. That does not
make computing literally free: hardware, electricity and setup still have costs.
The benefit is control over the model and how the application handles context.

The open application code also makes the important behavior inspectable: what
counts as an owner statement, why a reply was rejected, and when a fallback was
used. The check that rejected "should have addressed" was a bug I could inspect,
change and protect with a regression test.

The UI loads no external fonts, scripts or analytics. Local privacy still depends
on the machine and Ollama configuration, and the initial model download requires
internet access. A localhost address is not an independent network audit. Copying
a reply intentionally moves it into the operating system clipboard, whose own
history or synchronization settings are outside this app.

## What Is Still Missing

This is a supervised prototype. Complex sarcasm, unfamiliar topics, subtle factual
claims and creative paraphrases can defeat lexical checks. The generated text
still needs a person who understands the business. Real operator testing and
willingness to pay have not been established. Those are the next product tests,
not numbers to invent for a competition entry.

## Prize Categories

**Best Use of Gemma.** Gemma 3 is the model that generates the AI drafts through
Ollama. Templates are separately identified and are not counted as Gemma output.
