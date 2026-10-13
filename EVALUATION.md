# Review Reply Writer: repository import evaluation

Reviewed October 13, 2026. Scope: the supplied ZIP, executable local checks,
and the initial contents of `nolankido/reviewReplyWriter`.

## Verdict

A useful, unusually complete command-line prototype. It is suitable for
demonstration and supervised experimentation, but the current validator is
not sufficient to approve business replies for publication automatically.

The strongest parts are the standard-library-only Python implementation,
local Ollama integration, explicit fallback engine credits, batch mode,
owner profiles, persisted triage, and tests of coached retries. The application
does not contain a review-platform publishing integration: approval is a
local queue status, and the owner still copies and posts a reply.

The biggest product weakness is trust in the generated content, followed by
the terminal-only workflow. Adding more generation features would be less
valuable than making promises, factual claims, and review decisions reliable.

## Verification

| Check | Result |
| --- | --- |
| Supplied unit suite | 67 tests pass |
| Supplied submission pre-flight | Passes |
| Revised unit suite | 81 tests pass, including 14 new regression tests |
| Example replies | All three still pass the current validator |
| Offline generation | Exercised through the CLI, templates, and batch tests |
| Reroll persistence | Tested for platform, offer, signature, rating, voice metadata, and thread context |
| Failed draft replacement | Original file survives a simulated write failure |
| Live Gemma generation | Not verified: no running Ollama server in this environment |
| Challenge rules and eligibility | Not researched or independently verified in this code review |

The uploaded examples' model credits and the post's claimed firsthand runs
are inherited from the supplied archive. Passing the pre-flight validates
formatting, selected metadata, and test counts. It does not establish that
those runs happened or that the post's real-review account is accurate.

## Corrections included with the import

1. **Saved platform loss.** The legacy parser required a semicolon after
   every field, but the writer did not place one after `platform`. A saved
   Google draft reloaded as `generic`. The parser now handles the final field.
2. **Reroll context loss.** New drafts store structured metadata containing
   owner offers, signatures, ratings, voice, selection settings, and original
   review threads. Rerolls retain those inputs and use the follow-up generator
   when applicable. Legacy files still load; missing historical settings
   cannot be reconstructed.
3. **Ambiguous saved text.** JSON metadata preserves punctuation in business
   names and multiline reviews; quoted review lines cannot become reply
   section delimiters. Writes replace drafts atomically.
4. **Missing sign-off enforcement.** The validators now require a configured
   signature on the closing line, including follow-up replies.
5. **Malformed model response crashes.** Invalid JSON, unexpected response
   shapes, and non-text candidates now reach rejection or fallback paths.
6. **Ignored batch rating default.** The CLI now forwards `--stars` to batch
   defaults when a row has no rating.
7. **Repository maintenance.** Added GitHub Actions checks, common environment
   exclusions, regression tests, and clearer documentation of current limits.

## Remaining priorities

### 1. Require owner authorization for promises

`OFFERS` and `ESCALATION` can promise refunds, replacements, credits, or free
service even when the owner supplied no standing offer. Other template phrases
claim a team has already discussed or addressed a problem. The model prompts
also encourage compensation without distinguishing an approved policy from a
suggestion. These are material business commitments, not just tone choices.

Next change: make the default reply offer a neutral contact or review step;
require an explicit owner policy for monetary promises; avoid completed-action
claims without supplied evidence. Test first replies, follow-ups, and fallbacks
against the same policy.

### 2. Validate every output and expose unresolved gaps

Templates bypass the validator at the single, batch, and reroll output paths.
Their functions do not receive the selected platform. A reproduced case with
a 34-word standing offer, warm tone, and seed 0 produces 127 words for Google's
configured maximum of 120. The ordinary short negative-review probe passed
120 combinations of business kind, tone, and seed for each supported platform;
that is not a guarantee for arbitrary owner input.

Next change: centralize final validation for every engine, show remaining gaps
in triage, and prevent an invalid draft from being represented as ready. Treat
word ranges as application style targets, not official platform limits.

### 3. Strengthen semantic evaluation

Sentiment and topic extraction are substring/keyword heuristics. The name
guard ignores sentence-initial names; numbers are checked by substring rather
than exact numeric identity. An invented assertion such as a repaired machine
can pass without introducing a name or number. A four- or five-star rating
also overrides negative wording. The validators do not prove truthfulness,
understanding, or suitability for the customer situation.

Next change: add a representative, owner-reviewed evaluation set including
negation, sarcasm, mixed feedback, business kinds, long policies, and hostile
review instructions. Measure useful drafts and harmful promises, not only
whether drafts contain keywords.

### 4. Harden local state and input handling

Profile, ledger, and triage JSON writes are not atomic. Malformed profiles can
be silently treated as empty and overwritten. `profiles.json` is tracked and
is also the file used for personal profile edits and learned voice samples.
Generated replies and the gap ledger are ignored by Git, but profiles are not.
CSV headers, row ratings, empty single inputs, and conflicting CLI modes need
clearer validation. Manual draft edits do not invalidate an earlier approval.

Next change: separate shipped sample profiles from ignored personal state,
validate inputs, preserve corrupt files for recovery, and bind approvals to
the exact reply content.

### 5. Make the owner workflow accessible

The current product requires Python, terminal commands, and an optional local
model installation. A small local interface with policy setup, editable
drafts, visible review status, and a copy action would better serve a busy
business owner. Keep human approval central while improving the interface.

## Repository delivery

The first import commit preserves all 17 supplied files byte for byte.
The follow-up commit contains this evaluation and the focused fixes. The
existing `.gitattributes` is retained. The repository remains private.
Neither a public release nor a DEV submission was requested or performed.
