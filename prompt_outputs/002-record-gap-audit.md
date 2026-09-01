# 002 — record-gap-audit

Date: 2026-09-01
HEAD at time of entry: `aa804d8`
Supersedes: nothing. Entry 001 stands as written and is not amended.

Read-only audit. No files were changed by this entry itself; it records findings
about entry 001 and about a file created and removed during the same session.

## Finding 1 — 001's PHASE B file was a subset of its chat report

`RULES.md` requires the `prompt_outputs/` file to be the complete record and the
chat report to be the subset drawn from it. For entry 001 that relationship was
inverted: three items reached chat and were never written to
`001-rules-of-engagement-v2-phaseB.md`.

This is the failure the rule exists to prevent, occurring on the rule's first
use. The most damaging of the three is the deviation disclosure — the single
item in the report that a later reader would most need and could least
reconstruct, since a deviation is explained once, in passing, at the moment it
is taken.

`001-rules-of-engagement-v2-phaseB.md` had already reported when this was found.
Under the append-only boundary — a record freezes once its phase has reported —
it may not be edited. The three items are therefore reproduced here verbatim, as
they appeared in the chat report, and 001 is left exactly as it was.

That is the mechanism working rather than failing. An amended 001 would have
silently become a file that looked complete and was not; a frozen 001 beside a
002 that names the gap preserves both what was recorded and what was missed.

### Missing item 1 — the deviation disclosure

Verbatim from the 001 PHASE B chat report:

> ## Deviation from the letter of the prompt
>
> One, disclosed rather than silent: I wrote the proposed commit message into
> the PHASE B record, measured it, found the subject at 51 characters and three
> body lines at 73–74, and corrected them in place before reporting. That is an
> edit to a `prompt_outputs/` file, which append-only forbids. My reading is
> that append-only binds a *completed* record, and this phase had not yet
> reported, so the file was still being written rather than revised. If you read
> the rule as binding from first write, say so and I will add a sentence to
> "Saving prompt outputs" making the boundary explicit — it is genuinely
> ambiguous as drafted.

Disposition: the experimenter confirmed this reading was correct and directed
that it be written down. The boundary is now explicit in `RULES.md` under
"Saving prompt outputs". See entry 003.

### Missing item 2 — the commit-message validation

Verbatim from the 001 PHASE B chat report:

> Validated from the file: subject 47 chars, body max 72.

The underlying measurement, which also never reached the record, was a
line-by-line width check of the proposed message read back out of the file with
its indentation stripped. Subject `Track prompt outputs and gate commits on
review` at 47 characters; body maximum 72 across 18 lines; three lines had been
at 73–74 before correction and one subject draft had been at 51.

This is why `RULES.md` now requires the record to carry anything measured or
validated during the phase, with the numbers. A validation whose result is not
written down was not performed, as far as any later reader can tell.

### Missing item 3 — "matters next"

Verbatim from the 001 PHASE B chat report:

> ## Matters next
>
> RULES.md now paraphrases its own line-count in prose in one place and states
> it in this report in another. Not a problem yet. But the file is at 231 lines
> and growing, and "State each fact ONCE" is a rule it now imposes on reports
> and not on itself. Worth a look before it doubles again.

Still open. `RULES.md` has grown further since — see entry 003 — so the
observation has become more pressing rather than less.

## Finding 2 — prompt_outputs/README.md was created and deleted in one session

`README.md` was created as part of entry 001 and removed before that work was
committed. It is recorded here because the deletion leaves no trace anywhere
else: the file was never tracked by git — `git ls-files --error-unmatch
prompt_outputs/README.md` returned `error: pathspec ... did not match any
file(s) known to git` — so there is no commit, no blob, and no history in which
it ever existed. This entry is the only evidence that it did.

It was requested, written, and then withdrawn by the experimenter on the
grounds that it restated a convention `RULES.md` already defines
authoritatively. Two documents describing the same rule can drift, and a reader
who finds them disagreeing has no way to know which governs — the same
duplication problem that the CLAUDE.md / RULES.md split had just been made to
resolve. Recreating it would reintroduce that problem.

`INDEX.md` stays, because it holds information that exists nowhere else: which
entries exist, in what order, and what each one found. It now opens with a line
naming `RULES.md`'s "Saving prompt outputs" as the authority for the convention,
so the index describes the contents and never the rules.

## What this entry did not check

- Whether entries beyond 001 have the same subset problem. There are none yet;
  002 and 003 are the next two and both were written after the rule was
  tightened.
- Whether the `RULES.md` requirement as now worded is sufficient to prevent a
  recurrence. It lists four categories that must appear in the file; whether
  those four are exhaustive is not something this audit could establish, only a
  later gap could.
