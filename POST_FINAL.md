---
title: The Model Writes the Review Reply. The Owner Keeps the Promises.
published: false
tags: devchallenge, hf26challenge
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 2: Side Hustle](https://dev.to/challenges/hacktoberfest-week2-2026-10-12).*

<!-- RRW:NOTICE:START -->
> TODO before publication: add a judge-accessible demo link, confirm code access
> and the original development window, review fresh current-code Gemma evidence,
> and remove this notice. This is an unpublished draft.
<!-- RRW:NOTICE:END -->

## What I Built

A customer writes: “The coffee was excellent, but I was charged twice.”

A useful reply needs to acknowledge both parts. A fluent reply can still fail:
it might thank the customer for the coffee, apologize vaguely about billing,
and promise a refund that the owner never authorized.

Review Reply Writer is a local browser app for independent cafe and small
hospitality operators. Gemma drafts the language. The business owner decides
what the business can promise and what gets posted.

The workflow is deliberately small:

1. Add the customer review and any exact owner-authorized statements.
2. Generate a draft with local Gemma, or try a clearly labelled template preview.
3. Compare the reply with the customer's words, edit it, and save for rechecking.
4. Approve the exact saved text, then copy it for manual posting.

Saved profiles, first replies, follow-ups and a searchable draft library make
this a repeatable task. Nothing is posted to a review platform automatically.

For a recurring queue, the browser also accepts a CSV for one business. A preview
shows duplicate rows, invalid inputs and items requiring personal handling.
The saved inbox drafts one review per click and resumes after reopening the app.
It does not import refund policies or bulk-approve the resulting replies.

The Side Hustle hypothesis is paid installation, policy setup and support for
an operator who values local control but does not want to configure a model.
The application code stays free. I have not established demand, revenue or
measured time savings. The next test is an observed session with a real operator,
including whether setup is worth paying for.

## Demo

<!-- RRW:DEMO:START -->
TODO: Add the reviewed, publicly accessible video or deployed-demo URL.
Record the actual current interface and distinguish live Gemma output from
no-AI template preview. A local recording is not a hosted link.
<!-- RRW:DEMO:END -->

The best short demonstration uses the fictional **Duplicate billing** example.
Show the source wording under **Details to keep**, then edit the reply to remove
the double-charge detail. Save and watch the check identify the omission. Add an
unauthorized refund and show why approval remains blocked. Restore the details,
review the reply, then approve and copy it.

This sequence demonstrates the product's main decision in one case: help with
the words, preserve the customer's concern, and keep business authority with
its owner. A template demonstration proves the workflow; it does not prove
Gemma inference.

## Code

Repository: https://github.com/nolankido/reviewReplyWriter

The application is MIT licensed. Gemma's model terms are separate. Judges need
access to the repository before submission.

Run `py rrw_web.py` on Windows, or `python3 rrw_web.py` on macOS/Linux. The app
uses Python's standard library and local UI assets. For model-written drafts,
install Ollama and download `gemma3:4b`; template preview needs neither.

## How I Built It

### Fluent language is not permission

The first version required a make-it-right offer in negative replies. That was
a bad default: it encouraged business promises even when the owner supplied
none, and the fallback templates were trusted too readily.

Now customer reviews, earlier replies and voice examples cannot authorize
compensation or business actions. Owner statements are checked separately. An
approved credit cannot silently become a larger credit plus a refund, and a
repair claim must be explicitly authorized.

Model output, one coached retry and template fallbacks go through final checks.
Approval is tied to the saved content fingerprint and policy version. Editing
invalidates it; a stale tab cannot export a changed reply using an old approval.
Potentially serious allegations are routed to personal handling before routine
AI or template generation.

Personal handling has its own screen and private inbox notes. Marking an item
handled records the owner's work; it does not turn the allegation into an AI
draft, an authorized business promise or a publication approval.

### An apology should preserve the actual complaint

“I was charged twice” is more useful than a generic billing topic. The current
interpretation retains that reported duplicate charge, unanswered questions and
explicit wait durations. Prompts, detail checks and fallbacks use the same
bounded review analysis.

The editor shows exact excerpts from the original review beside the detected
details. Each excerpt includes offsets into the untouched source text. That
helps an owner inspect the interpretation instead of trusting an unexplained
checkmark. Unsaved edits mark the displayed coverage stale until rechecking.

A detail being mentioned does not prove that the reply handles it correctly.
That is why the interface says **Mention detected**, and the owner still reads
the complete review and response.

The same owner control applies to style. A short complete reply does not need
filler, and a return invitation is optional. Removing those stock requirements
reduced median template length from 35 to 25 words on the unchanged 30-case
fictional diagnostic set. That is a measured writing change, not a customer
preference study or a time-saving claim.

### Keep the failed experiments

A previous live Gemma test rejected “should have addressed” as if it claimed
a completed business action. Another accepted draft reduced a 25-minute wait
to an “extended wait.” Those failures led to narrower action checks and exact
reported-duration checks.

The repository retains two three-case hosted Gemma smoke runs. The later run
produced three model-written drafts on their first attempts, taking about
18 to 20 seconds each on the recorded GitHub-hosted CPU machine. Those are
historical results from an earlier engine version, not measurements of this
new pass or predictions for a customer's laptop.

Quality Lab retains raw attempts, rejection reasons, retries, final engine
labels and available timing receipts. Templates, real model output and human
assessments remain separate. Deterministic regressions also test source excerpts,
negation, duplicate billing, unanswered questions and the approval boundary.

AI coding assistance helped implement and test the project. The code and
retained evidence make the changes inspectable.

## Why Does Open Innovation Matter?

Downloaded Gemma weights let the owner run the model on their machine, without
a hosted-model bill for each draft. Hardware, electricity and setup still cost
money. The practical advantage is control over inference and customer context.

Open application code makes policy handling inspectable too: what entered the
prompt, why a candidate was rejected, and which fallback was used. The false
positive around “should have addressed” was a bug I could inspect and fix.

The UI uses no external fonts, scripts or analytics. Local privacy depends on
the machine and Ollama configuration, and the initial model download requires
internet access. A loopback address alone does not prove local inference.

## What I Still Need to Prove

These English pattern checks can miss unfamiliar topics, sarcasm and subtle
claims. They trust owner-supplied facts; they cannot prove a repair happened.
Fresh Gemma tests on the current code, real operator task times, comparative
reply preferences and willingness to pay remain work to do. Test counts are
engineering evidence, not customer validation.

## Prize Categories

**Best Use of Gemma.** Gemma 3 generates the AI drafts through Ollama. Template
previews and fallbacks are separately labelled and are not counted as Gemma output.
