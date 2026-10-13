# Review Reply Writer

> Status: command-line prototype for human-reviewed drafts. See
> [EVALUATION.md](EVALUATION.md) for the import review, verified behavior,
> and remaining product risks. Nothing is posted automatically.

**Every customer review answered in minutes — on your own machine, with nothing sent anywhere.**

A café, an Etsy seller, a vacation-rental host: all of them are told to
reply to every review, fast and gracefully. The tools that help with
that charge a monthly subscription and read every review on someone
else's server — including the angry ones with customer names in them.
Review Reply Writer does the same job locally. Gemma 3 (via Ollama)
drafts the reply; a format validator checks selected wording and length rules; if the draft misses, the model gets
one coached retry; if it still misses, a template engine writes the
reply instead. No subscription, no API bill, no data leaving the
laptop.

Built for DEV Hacktoberfest Week 2 — "Side Hustle": the kind of thing
someone would actually pay for, except it runs free and private.

## What a good reply means here

The validator encodes what owners learn the hard way. Model replies are checked against the following rules. These checks
are heuristics, not a factual guarantee; template output currently bypasses
this final validation step. The intended rules are:

- opens with a genuine thank-you,
- names the business,
- answers a **specific detail from the review** — in the body, not just
  smuggled into the signature (the checker strips the sign-off before
  looking, because "– The Moe's Coffee team" mentioning coffee is not
  the same as answering a complaint about the coffee),
- and when the review is unhappy, **apologises plainly and offers
  something concrete** — a replacement, a refund, the next one on the
  house,
- closes by inviting the customer back, stays inside the word range
  for its platform (Google short, Airbnb longer — see `--platform`),
  and contains no bracketed placeholders,
- and invents **no contact details** — no email, phone-style number,
  or website the owner never gave it. Left alone, a model will
  cheerfully fabricate one ("reach me at owner@…"); the checker
  rejects it, and the retry gets told why,
- and passes a **heuristic name-and-number check** — a fact guard flags some names
  and numbers in the draft that traces to neither the review nor the
  owner. It exists because Gemma once thanked a barista named
  "Leo" whom no customer had ever mentioned.

Word-level honesty matters too: "that's on us" (our fault) must not
count as "this one's on us" (our treat), and "a complimentary upgrade"
must count as the offer it plainly is. The offer check looks for the
treat, not the apology wearing its clothes. Typography gets the same
respect: when Gemma types Moe's with a curly apostrophe, the name
check straightens apostrophes before comparing — a reply shouldn't
fail for its punctuation.

## Three pitches, not one

Reviews are graded before they're answered — **negative**, **mixed**,
or **positive** — and each pitch has its own rules. A negative review
gets the apology and the offer. A glowing one gets thanks and the
praise passed to the team, with no invented problems to apologise
for. And a mixed review — "loved the room, the shower was weak" —
gets its own honest middle: lead with what delighted them, own the
one failure plainly (the checker splits the review into clauses to
tell which topics were praised and which were panned), and say what's
being done about it. No grovelling, no pretending the complaint
wasn't there.

## Owner profiles

One command per business, forever, once it's saved:

```bash
python3 review_reply.py --file review.txt --business "Moe's Coffee" \
    --kind cafe --offer "the next round is on us" \
    --signoff "The Moe's Coffee team" --save-profile moes
python3 review_reply.py --file review.txt --profile moes
```

A profile carries the business, kind, tone, sign-off — and a
**standing offer**. Set one, and the validator requires it *word for
word* in negative and mixed replies: a generic make-it-right is not
the owner's promise. Profiles live in `profiles.json`; two samples
(`moes`, `kai`) ship with the project.

## Batch mode

Owners don't have one review waiting, they have twelve:

```bash
python3 review_reply.py --batch reviews.csv   # or --batch-dir folder/
```

The CSV takes `review,business,kind,tone,stars` per row (everything
but the review is optional; flags and profiles fill the gaps). Every
reply is drafted and saved, and the run ends with a summary — each
review's tier, which engine wrote its reply, and the totals. Empty
rows are reported as skipped, never silently dropped.
`examples/batch-sample.csv` is a runnable demo.

## Triage

Drafted is not the same as ready to post. `--triage` walks the
saved drafts in `replies/` one at a time — approve, re-roll (same
tone or a new one), or set aside. State persists in
`replies/triage.json`, so a half-finished session resumes where it
stopped, and approved drafts stay approved.

## Voice matching

Settings make a profile; samples make it *yours*:

```bash
python3 review_reply.py --learn-voice my-past-replies.txt --profile moes
```

Give it a few replies you've actually sent (separated by `---`
lines) and it learns how you open, how you sign off, how long you
write, and the phrases you reach for. The model is then briefed in
your voice, and your sign-off is enforced like any other rule.

## The gap ledger

Every time a draft misses, the miss is counted per business in
`gap_ledger.json`. Repeat offenders change the brief — "drafts for
this business most often miss the standing offer" becomes an
instruction in the next prompt — and `--doctor` reports the pattern.
Nothing grand; just a tool that remembers what it keeps getting
wrong.

## Follow-up replies

A review thread does not always end with the first reply. A customer
may come back, update their rating, or say the fix did not work:

```bash
python3 review_reply.py --followup --file update.txt \
    --original original-review.txt --previous my-first-reply.txt \
    --profile moes
```

Follow-ups have their own checker rules. The draft must acknowledge
the update in its opening, use the whole thread as its source of
facts, and never repeat a standing offer that was already made. If
the customer is still unhappy, it must escalate instead — for
example, to the owner personally or a refund.

## Better drafts and a guided tour

- `--choices 2` samples two passing drafts and keeps the one that
  covers more of the review's specifics. Its saved credit line says
  `best of 2`.
- `--tour` runs the whole workflow as a narrated demonstration:
  doctor, a profile draft, a sample batch, triage counts, and the
  gap ledger.

## Quick start

Use Python 3.10 or newer and [Ollama](https://ollama.com) for model-written
replies (without it, the template engine still works):

```bash
ollama pull gemma3:4b

python3 review_reply.py "Cold coffee and a 25 minute wait. Disappointing." \
    --business "Moe's Coffee" --kind cafe --stars 2

python3 review_reply.py --file review.txt --business "Kai Loft" \
    --kind stay --tone professional --save

python3 review_reply.py --file review.txt --profile moes
python3 review_reply.py --batch examples/batch-sample.csv
```

- `--kind` — `cafe`, `shop`, `stay`, or `service`; shapes the
  make-it-right offer.
- `--tone` — `warm` (default), `professional`, or `playful`.
- `--stars 1..5` — when known, helps grade the review's tier;
  without it, the writer reads the review's own words.
- `--profile NAME` — use a saved owner profile (see above);
  `--offer` and `--signoff` set those pieces for a single run.
- `--batch CSV` / `--batch-dir DIR` — draft a whole inbox at once.
- `--followup` with `--original` and `--previous` — draft the next
  reply in an ongoing review thread.
- `--choices 2` — sample two drafts and keep the one covering more
  of the review's specifics.
- `--tour` — run a narrated end-to-end demonstration.
- `--platform google|yelp|airbnb|etsy` — where the reply will be
  posted; sets the word range the checker enforces (saved in
  profiles too).
- `--save` — also writes the review and reply to `replies/` as
  Markdown, with a credit line saying which engine wrote it.
- `--offline` — skip the model; template engine only.
- `--doctor` — checks the setup and says, plainly, what will write
  your replies.

## What a run looks like

```text
$ python3 review_reply.py --doctor
Review Reply Writer - doctor
  model:    OK    Ollama reachable, gemma3:4b found
  engine:   OK    template engine and validator sanity check
  verdict:  ready - Gemma will write the replies
```

Three sample reviews live in `examples/`, with the replies Gemma
wrote for them — each file credits its engine honestly, including
when a coached retry was needed.

## Why local is the pitch

Review platforms and AI subscriptions both want the same thing: the
text of every complaint your business ever received, forever, on
their machines. For a lot of small owners that trade is fine. For the
ones it isn't — the host whose reviews name guests, the shop whose
complaints mention orders — a writer that runs entirely on their own
laptop is worth paying for. This one just happens to be free and
open source.

## Tests

```bash
python3 -m unittest
```

81 tests: tier grading by stars and by words, clause-level topic
splitting for mixed reviews, a fact guard against invented names
and numbers, per-platform word ranges, a gap ledger that learns
which rules a business's drafts keep missing, voice learning from
past replies, a triage queue with persisted state, follow-up replies
graded against their thread, best-of-two draft selection, a narrated
tour, every validator rule failing on cue, the template engine
passing the validator across review kinds, tones, tiers, and seeds,
standing offers enforced word for word, profile save/load, batch
runs that write files and skip empty rows, the submission checker's
own tests, and the model path with a stand-in caller — first-try
success, a coached retry that recovers and provably runs cooler
than the first attempt, and clean fallback when the model misses
twice or isn't there at all. A pre-flight checker
(`python3 check_submission.py`) re-verifies the gallery and the
submission post's claims against the code before posting.

## Honest limits

- Fallback templates can make unapproved refund, replacement, or repair
  promises. Review every draft against your actual business policy.
- Platform word ranges are application style targets. Templates currently
  bypass final validation and can exceed them when owner settings are long.
- New saved drafts preserve owner settings and follow-up threads during
  rerolls. Older files cannot recover settings they never stored.
- `profiles.json` is tracked and stores profile edits and learned voice data.
  Check it before committing personal profiles. Generated replies and the
  gap ledger are excluded from Git.
- The application calls Ollama on localhost. Privacy also depends on running
  a local model and on your Ollama configuration; the app does not audit that
  configuration or enforce local execution for arbitrary `--model` values.

- Drafts still deserve a human read before posting — the validator
  checks form, not facts. If a reply claims the shop fixed the
  espresso machine, that's the owner talking, not the tool knowing.
- The negative-review detection without stars is a keyword heuristic;
  sarcasm will fool it, as it fools most of us.
- Replies were generated and verified in the development sandbox;
  running it on your own machine is the same code with your own
  Gemma.

MIT licensed.
