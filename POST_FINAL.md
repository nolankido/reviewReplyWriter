---
title: I Built a Review-Reply Writer That Never Phones Home
published: false
tags: devchallenge, hf26challenge
---

<!-- SUBMISSION CHECKLIST (delete before posting)
  [x] Examples + engine credits verified 2026-10-13 (all gemma3:4b;
      the glowing one after one format retry - see its war story)
  [x] 67/67 tests passing, --doctor output pasted below
  [x] Batch mode, owner profiles, and the mixed-review tier added
      2026-10-12 evening; sections below include them
  [x] Real-review paragraph added 2026-10-13 from an actual public
      Honolulu Coffee Google review run; see "Putting it on a real
      review" below. Nothing else is missing.
  [ ] Optional: add 1 screenshot of a run.
  [ ] Post inside Oct 12-18, 2026 via the DEV challenge template.
-->

Every small business owner knows they should reply to every review —
fast, gracefully, and like they mean it. In practice they do it at
11 p.m., tired, either a little too sharp or a little too grovelling.

The tools that fix the writing take something else in trade: every
review, every complaint, every customer name, read on someone else's
server, forever, for a monthly fee.

I built the other version. **Review Reply Writer** runs entirely on
the owner's own machine. Gemma 3 (4B, via Ollama) drafts the reply.
A validator checks the draft the way a good owner would before
anything gets posted. If it misses, the model gets one coached
retry. If it still misses, a template engine writes the reply
instead. No subscription, no API bill, nothing leaves the laptop.

```bash
ollama pull gemma3:4b

python3 review_reply.py "Cold coffee and a 25 minute wait. Disappointing." \
    --business "Moe's Coffee" --kind cafe --stars 2
```

## What "a good reply" actually is

The validator is the whole product, really. A draft only passes if it:

- opens with a genuine thank-you,
- names the business,
- answers a **specific detail from the review** — in the body, not
  smuggled into the signature,
- and, when the review is unhappy, apologises plainly and offers
  something concrete: a replacement, a refund, the next one on us,
- closes by inviting the customer back, stays inside the word range
  for the platform it's headed to, contains no bracketed
  placeholders,
- invents **no contact details** the owner never gave it,
- and invents **no people or facts** either — no staff names, dates,
  or amounts the customer never mentioned.

That last rule exists because the model earned it. Told to drop a
`[email address]` placeholder, its coached retry instead invented a
plausible owner email. A tool that fabricates how customers can
reach you is worse than no tool — so invented emails, phone-style
numbers, and websites are now rejected outright, with a regression
test.

Three more honest war stories from building it:

- **The signature cheat.** My first "generic reply" test passed its
  specifics check only because the sign-off ("– The Moe's Coffee
  team") contains the word *coffee*. Answering a complaint about the
  coffee is not the same as signing off from a coffee shop, so the
  checker now strips the sign-off before it looks for specifics.
- **Typography and idioms.** Gemma wrote *Moe's* with a curly
  apostrophe and the name check failed a reply that named the
  business three times — apostrophes are now straightened before
  comparing. And "that's on us" (our fault) kept tripping the offer
  detector, while "a complimentary upgrade" wasn't recognised as an
  offer at all. The check now looks for the treat, not the apology
  wearing its clothes.
- **The invented barista.** The first glowing-review reply Gemma
  wrote thanked our barista "Leo" — a man no customer had ever
  named. He read as warmth and would have posted as fiction. A fact
  guard now flags any name or number that traces to neither the
  review nor the owner; its first outing bullied the model into
  "[Barista's Name]" placeholders instead, so the prompt also
  teaches the compliant move — people the customer didn't name get
  referred to by role. The glowing reply above is the result.

## Live runs — Gemma wrote these

All three examples were generated locally by `gemma3:4b` via Ollama.
Two passed the validator first try; the glowing one arrived after
the fact guard below existed, and needed one coached retry to get
there. Each saved file in `examples/` carries its own engine credit
line.

**1. The glowing review (Moe's Coffee)**

> The oat milk latte was perfect and the barista remembered my name
> from last week. Cozy seats, quick service even during the morning
> rush — this is my new favorite spot in the neighborhood.

> Thank you so much for your wonderful review! We absolutely love
> hearing that our oat milk lattes are perfect – it truly makes our
> day. It was so lovely to see our barista remembered your name from
> last week; they really do take pride in getting to know our
> regulars. We’re thrilled you found the seats cozy and appreciated
> the quick service, especially during the morning rush. It’s
> feedback like yours that makes Moe’s Coffee such a special place
> in the neighborhood. We’re so happy you’ve declared us your new
> favorite spot! We hope you’ll stop by again soon. — The Moe’s
> Coffee Team

**2. The angry review (Moe's Coffee)**

> Cold coffee, a 25 minute wait, and nobody even looked up when I
> tried to ask about my order. Really disappointing for the price —
> I won't be back.

> Thank you so much for taking the time to leave your honest feedback
> about your recent visit to Moe's Coffee. We truly appreciate you
> sharing your experience. We're so sorry to hear about the cold
> coffee and the long 25-minute wait – that's certainly not the
> standard we aim for, especially regarding our handcrafted
> beverages. And we sincerely apologize that our team didn't make
> eye contact while you were trying to inquire about your order;
> that's completely unacceptable. To make things right, we'd love
> to offer you a complimentary replacement drink on your next visit.
> Please just mention this review when you return. We hope you'll
> stop by again soon. — The Moe's Coffee Team

**3. The mixed review (Kai Loft, a rental stay)**

> Beautiful room and a stunning ocean view, and the bed was
> incredibly comfortable. But check-in took forever, and the shower
> water pressure was weak both mornings.

> Thank you so much for taking the time to share your experience at
> Kai Loft. We truly appreciate your kind words regarding the
> beautiful room and the incredible ocean view – we strive to
> provide our guests with the most memorable stays possible. We
> sincerely apologise that the check-in process took longer than
> expected and that you experienced weak water pressure in the
> shower. We're addressing this immediately with our team to ensure
> a smoother arrival for all future guests. To compensate for the
> inconvenience, we'd like to offer you a complimentary breakfast
> during your next visit. We hope you'll stop by again soon and
> experience the full beauty of Kai Loft. — The Team

## Then it grew the parts a business actually needs

**Three pitches, not one.** Reviews are graded — negative, mixed,
positive — and answered at that pitch. The mixed grade is its own
honest middle: lead with what delighted them, own the one failure,
say what's being done. To grade the topics, the checker splits the
review into clauses, so "a stunning ocean view, but check-in took
forever" files the view under praise and the check-in under
complaints. (My first attempt used a fixed word-window around each
topic; a compact sentence broke it, and a test caught it.)

**Owner profiles.** One saved profile per business — name, tone,
sign-off, and a *standing offer* the validator then requires word
for word. I watched this work on the real model: Gemma's first draft
for the angry review offered a generic replacement drink, the
checker rejected it for missing the owner's offer, and the coached
retry landed "the next round is on us" verbatim, inside a better
reply than the first draft.

**Batch mode.** Owners don't have one review waiting, they have
twelve. `--batch reviews.csv` drafts every reply, saves each with
its credit line, and ends with a summary: each review's tier, which
engine wrote its reply, and the totals. Empty rows are reported as
skipped, never silently dropped.

**And the workflow around the drafts.** A triage mode walks the
saved drafts — approve, re-roll, set aside — with the state kept, so
"drafted" stops meaning "done." Voice profiles learn from replies
the owner actually sent (their opener, their sign-off, their pet
phrases) instead of stopping at settings. And every miss the model
makes is counted in a small ledger per business, so the next prompt
opens with "drafts here most often miss the standing offer" — a
tool that remembers what it keeps getting wrong.

**And the conversation after the reply.** Customers answer back, or
quietly edit a 2-star into a 4-star. A follow-up mode drafts the
*next* reply in the thread, with thread rules of its own: open by
acknowledging the update, never repeat an offer already made —
escalate instead — and treat the whole thread as the only source of
facts. When quality matters more than speed, `--choices 2` samples
two drafts and keeps the one covering more of the review's actual
specifics, credit line saying "best of 2". And `--tour` runs this
whole story end to end in one narrated pass.

## Putting it on a real review

For a real test I took an actual public Google review of Honolulu
Coffee in Waikiki — eleven words long and not happy: a soggy $6
croissant and a 45-minute wait for a cold coffee. Gemma's draft
passed the validator first try. It thanked the reviewer, named the
soggy croissant back to them, apologised plainly, and offered a
complimentary replacement croissant and coffee — the make-it-right
I would have offered myself. Two things I noticed on a human read:
it softened "45 min" into "the long wait," answering the complaint
but blurring its sharpest detail, and the sign-off ran on as a
sentence instead of sitting on its own line. My one edit before
sending would be putting the 45 minutes back in. That's the honest
shape of the tool today: the draft was sendable, and the last 10%
was still a human's job.

## What I'd sell, and to whom

The free tool as-is is a weekend build. The sellable version is the
same engine living where owners already work — a button on the
review dashboard that drafts in place. And the pitch is the part a
cloud tool can't copy without ceasing to be a cloud tool: for the
host whose reviews name guests, or the shop whose complaints mention
orders, a writer that runs entirely on their own laptop is the
feature.

## Verified, not vibes

```text
$ python3 review_reply.py --doctor
Review Reply Writer - doctor
  model:    OK    Ollama reachable, gemma3:4b found
  engine:   OK    template engine and validator sanity check
  verdict:  ready - Gemma will write the replies

$ python3 -m unittest
...................................................................
----------------------------------------------------------------------
Ran 67 tests in 0.11s

OK
```

67 tests: tier grading by stars and by words, clause-level topic
splitting, a fact guard that flags invented names and numbers,
per-platform word ranges, a gap ledger that learns which rules a
business's drafts keep missing (and emphasises them in the next
prompt), voice learning from the owner's past replies, a triage
queue with persisted state, follow-up replies graded against the
thread (including the no-repeat-offer rule), best-of-two draft
selection, a narrated tour, every validator rule failing on cue,
the template engine passing across kinds, tones, tiers, and seeds,
standing offers enforced word for word, profile save/load, batch
runs, the submission checker's own tests, and the model path with a
stand-in caller — first-try success, a coached retry that provably
runs cooler than the first attempt, and clean fallback when the
model misses twice or isn't there at all. A pre-flight checker
(`check_submission.py`) re-verifies this whole page against the code
before posting — gallery credits, test count, tags — so the claims
can't quietly go stale while the tool keeps improving.

## Honest limits

- Drafts still deserve a human read before posting — the validator
  checks form, not facts. If a reply says the espresso machine is
  fixed, that's the owner talking, not the tool knowing.
- Without a star rating, negative-review detection is a keyword
  heuristic; sarcasm will fool it, as it fools most of us.
- The examples were generated and verified in my development
  sandbox; on your machine it's the same code with your own Gemma.

The code is MIT licensed. If you run a small business: what would a
reply have to get right before you'd trust a machine to draft it?
