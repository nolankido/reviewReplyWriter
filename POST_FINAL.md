---
title: The Model Writes the Review Reply. The Owner Keeps the Promises.
published: false
tags: devchallenge, hf26challenge
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 2: Side Hustle](https://dev.to/challenges/hacktoberfest-week2-2026-10-12).*

<!-- RRW:NOTICE:START -->
> TODO before publication: confirm the original development window and judge
> access, add the watched and access-checked demo link, review current-source
> Gemma results, and verify the claims below. This is an unpublished draft.
<!-- RRW:NOTICE:END -->

## What I Built

“The coffee was excellent, but I was charged twice. The waiter ignored my
question about the bill.”

That fictional review has three things worth answering. Thanking the customer
for the coffee is easy. Acknowledging the double charge and unanswered question
takes more care. Promising a refund introduces a different decision: does the
person writing the reply have permission to offer one?

I built Review Reply Writer for independent cafe and small hospitality
operators. Gemma drafts the language locally. The owner supplies the business
policy, reads the result, and approves the exact text before copying it for
manual posting.

The Side Hustle hypothesis is paid installation, policy setup and support for
an operator who wants local control without configuring a model. The application
code stays free. Demand, willingness to pay and time saved remain unproven.

## Demo

<!-- RRW:DEMO:START -->
TODO: Add the reviewed, judge-accessible video or deployed-demo URL.
The recording must show the current interface and distinguish actual Gemma
output from template preview or fallback. No current recording is claimed here.
<!-- RRW:DEMO:END -->

The focused walkthrough uses the fictional **Duplicate billing** example with
no compensation authorized:

1. Generate a draft and show its actual source label.
2. Compare the reply with **Details to keep** and the customer's quoted wording.
3. Add “We will give you a full refund.” Choose **Save & recheck** and show
   blocked approval.
4. Remove that added promise, save, read the reply, then approve and copy it.

Any other corrections should remain visible. An edited reply is not untouched
Gemma output. Demonstration approval clicks are not operator feedback.

## Code

Repository: https://github.com/nolankido/reviewReplyWriter

The application is MIT licensed; Gemma's model terms are separate. Judge access
still needs confirmation.

Run `py -3 rrw_setup.py --launch` on Windows or
`python3 rrw_setup.py --launch` on macOS/Linux. The application uses Python's
standard library and local browser assets. Model-written drafts require Ollama
and downloaded `gemma3:4b` weights. Clearly labelled template preview works
without either.

## How I Built It

### Keep the customer's concern visible

The editor places the saved review beside the reply. **Details to keep** links
recognized concerns to exact excerpts of the original text. Prompts, fallbacks
and checks share a bounded interpretation, so “charged twice” does not quietly
become a generic billing apology.

An unanswered question also matters. A reply can mention the coffee and still
leave the customer's main frustration untouched. Unsaved edits mark the checks
stale until the owner saves and rechecks.

The interface says **Mention detected** because a phrase match cannot establish
understanding. The owner still reads the whole review and reply.

### Customer wording cannot authorize a business promise

The first version required a make-it-right offer in negative replies. That was
a bad default: it encouraged commitments without permission.

Now authorization is separate from customer text, earlier replies and voice
examples. Exact owner statements can permit an offer or action. Detected
unauthorized promises block approval, whether introduced by the model, a
fallback or an edit. An authorized credit cannot silently become a larger
credit plus a refund.

Approval is tied to the saved text and check version. Changing the reply
requires a new review. Serious allegations are conservatively referred for
personal handling before routine generation.

### Preserve the work around the words

A lost response should not mean a lost draft. Saved generation receipts let the
owner check an interrupted request without automatically running it again.
Pending edits, private recovery copies and checked backups support recovery.
Recovery leaves authorization unchecked and does not resurrect old approval.

The recurring workflow includes saved profiles and a one-business CSV inbox.
Each reply still needs individual review. Nothing posts automatically.

### Keep evidence separate from confidence

On October 14, the local release check ran 569 passing Python tests. Linux
launcher HTTP workflows and Node state checks also have executed evidence.
These checks do not establish current Windows, browser/mobile or model behavior.

Two historical three-case Gemma smoke runs remain in the repository. The later
run produced three model drafts on first attempts, but both runs predate current
drafting-source changes and have no recorded human assessments. They do not
validate this version's reply quality.

A historical false rejection of “should have addressed” and an accepted reply
that softened an exact wait duration helped expose limits in the checks.
Quality Lab preserves attempts, rejection reasons, retries, fallbacks and
available model receipts so those failures remain inspectable.

AI coding assistance helped implement and test the project.

## Why Does Open Innovation Matter?

Downloaded Gemma weights support inference on the owner's machine without a
hosted-model charge for each draft. Hardware, electricity and setup still cost
money. Local execution gives the owner control over the customer context sent
to the model and the runtime processing it.

Open application code makes the policy boundary inspectable: what entered the
prompt, why a candidate was rejected, and which fallback was used. The browser
uses local assets without external fonts, scripts or analytics.

The initial model download needs internet access. Privacy still depends on the
computer and Ollama configuration; a loopback URL alone does not prove a private
model runtime.

## What I Still Need to Prove

The English pattern checks can miss unfamiliar topics, sarcasm and subtle
claims. They cannot establish whether an owner-supplied fact is true.

Current-source Gemma results need genuine human assessment. Setup usability,
operator preferences, comparative task times and willingness to pay need real
observation. No operator trial, customer adoption or revenue is claimed.

## Prize Categories

**Best Use of Gemma.** Gemma 3 generates the AI drafts through Ollama. Template
previews and fallbacks are separately labelled and are not counted as Gemma output.
