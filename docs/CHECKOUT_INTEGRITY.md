# Source fingerprints and Windows checkouts

The first Submission Desk Windows CI run found that Git's platform-default
line endings changed the bytes of otherwise unchanged Python and JSON files.
The recorded Gemma evidence uses exact byte hashes, so the evidence check
correctly refused to call that checkout identical to the measured source.
Ubuntu and the browser workflow passed; the Windows failure was not ignored.

`.gitattributes` now specifies LF for detected text files on all platforms.
The Windows batch launcher has an explicit CRLF exception and is not among
model-input source fingerprints. The engine and recorded reports themselves
were not changed, nor were integrity comparisons weakened or replaced with
normalized hashes. The existing cross-platform tests check the retained report
against the actual checked-out source and exercise checked packet export.

This controls new Git checkouts. An older working directory or an editor that
rewrites files with CRLF can still differ from the retained report. Preserve
any local work and use a fresh checkout for byte-identical reproduction, or
perform a new measured evaluation of the actual source you are running.
Do not force-reset or overwrite local edits merely to make an evidence badge
green. A source mismatch is useful information, not an application crash.
