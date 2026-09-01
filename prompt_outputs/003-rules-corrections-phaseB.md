# 003 — rules-corrections — PHASE B

Date: 2026-09-01
HEAD at time of phase: `aa804d8`
Supersedes: nothing. Amends the `RULES.md` that entry 001 established; 001's
record of what was done at that time stands unchanged and remains accurate.
Committed: no. Nothing in 001, 002 or 003 has been committed; all of it is in
the working tree awaiting the commit gate.

## Deviation: this entry was not requested

**Disclosed rather than silent.** The experimenter directed six corrections
(C1–C6) and named exactly one new file to be written for them,
`002-record-gap-audit.md`, specified as a short read-only entry. But C1, C2, C3,
C5 and C6 are changes to `RULES.md` and a file deletion — not read-only work,
and not something a read-only audit entry can honestly hold.

That left the changes with no record at all. Under the rule being written in
this very session — a fact that appears in chat and not in the record is a
failure of the record — writing six rule changes and recording none of them
would have violated the newest rule at the moment of its creation. And under the
append-only boundary confirmed in C2, `001-rules-of-engagement-v2-phaseB.md` is
frozen and cannot absorb them.

So this entry exists. If the preference is to fold it into 002 instead, say so
and 003 can be superseded by a combined entry; the append-only mechanism handles
that correctly and nothing here is lost.

A second, smaller judgement: no PHASE A ran for this work. The corrections were
dictated with no ambiguity requiring verification, and they arrived inside an
open PHASE B gate rather than as a new task. The only verification performed was
the re-check below.

## Re-check before implementing

    HEAD: aa804d8
    tree: M RULES.md, ?? prompt_outputs/  (as left by entry 001)
    RULES.md lines: 231

Unchanged from where entry 001 left it. Proceeded.

## What changed

`RULES.md` grew from 231 to 276 lines — 268 after C1–C6, then 276 after C7.

    RULES.md | 183 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++----
    1 file changed, 172 insertions(+), 11 deletions(-)

That stat is cumulative against `HEAD` (`aa804d8`) and therefore includes entry
001's changes as well as this entry's, because none of it has been committed
yet. There is no way to show this entry's changes alone as a diff stat without
an intervening commit; the section-by-section list below is the substitute.

    prompt_outputs/README.md                 DELETED (55 lines, never tracked)
    prompt_outputs/INDEX.md                  edited — authority line, 3 entries
    prompt_outputs/002-record-gap-audit.md   NEW
    prompt_outputs/003-rules-corrections-phaseB.md   NEW (this file)

## C1 — "Report structure", closing paragraph

The `git show` half of the sentence D2 had corrected was stale for the same
reason the "commit hash" half was: at the moment a PHASE B report is written,
there is no commit for `git show` to show.

Before:

> Do NOT paste full diffs. The project is under git — `git diff --stat` is enough,
> and the experimenter can run `git show` for the rest. Paste verbatim code only
> for a specific line under discussion.

After:

> Do NOT paste full diffs. The project is under git — `git diff --stat` is enough,
> and the experimenter can run `git diff` for the rest, or `git show` once it is
> committed. Paste verbatim code only for a specific line under discussion.

## C2 — the append-only boundary

Added after the APPEND-ONLY paragraph under "Saving prompt outputs":

> **Append-only binds a record once its phase has reported.** Until then the file
> is still being written and may be revised freely — drafting something, measuring
> it, and correcting it before it is delivered is writing, not revising. After the
> report it is frozen. A correction to a frozen entry is a new numbered entry that
> names what it supersedes, never an edit.

This resolves the ambiguity flagged as a deviation in 001 and reproduced in 002.
It is also the rule that forced 002 to exist rather than 001 being amended, and
that forced this entry to exist rather than 001 absorbing the corrections — the
first two things it did were both to prevent an edit.

## C3 — the commit message names its record

Added as step 3 of "Committing and pushing", renumbering the old step 3 to 4:

> 3. The body's final line, on its own, names the `prompt_outputs/` entry the
>    commit corresponds to:
>
>        Record: prompt_outputs/001-rules-of-engagement-v2-phaseB.md
>
>    The record cannot hold the hash — it is written before the commit exists and
>    frozen once the phase has reported — so the hash must hold the record.
>    Without that line the two halves of the history have no link at all.

This closes finding 3 from entry 001's B9 review, which had proposed waiting for
a second entry before deciding the shape. The experimenter overrode that: with
no link in either direction the two halves of the history are simply
disconnected, and waiting would have left every commit made in the interim
unlinked.

## C4 — the file is a superset of chat

Added as a subsection of "Saving prompt outputs":

> ### What the file must contain that chat may omit
>
> **The file is a superset of the chat report, never a subset.** Chat may leave
> out anything the record holds. The record may leave out nothing chat said. A
> fact that appears in chat and not in the record is a failure of the record.
>
> Beyond the report itself, the file must carry:
>
> - **Any deviation from the prompt, and the reasoning for it.** This is the most
>   important thing in the record and the easiest to lose, because a deviation is
>   typically explained once, in passing, at the moment it is taken.
> - **Any self-correction** — something previously claimed that turned out to be
>   wrong, what the correct statement is, and how it was established.
> - **"Matters next."**
> - **Anything measured or validated during the phase, with the numbers.** A
>   validation whose result is not written down was not performed, as far as any
>   later reader can tell.

## C5 — no commit message in the PHASE B report

Added immediately under the "PHASE B ENDS BEFORE THE COMMIT" paragraph:

> **The PHASE B report must NOT contain a proposed commit message.** A message
> drafted before the report is approved describes a change that may still be
> rejected, and it pulls the reader toward accepting. Proposing one early is
> itself a deviation.

Entry 001's PHASE B report proposed a commit message, which contradicted the
"Committing and pushing" section written in that same phase. The experimenter
attributed the fault to their own REPORT instruction, which had asked for one.
The rule stands as originally written and is now explicit, because it was
ambiguous enough to be tripped over on first use.

## C6 — README.md deleted

`prompt_outputs/README.md` was removed. It restated a convention `RULES.md`
already defines authoritatively, and two documents describing one rule can
drift with no way for a reader to tell which governs.

Verified untracked before deleting, so this is a plain file removal and not a
`git rm`:

    git ls-files --error-unmatch prompt_outputs/README.md
    error: pathspec 'prompt_outputs/README.md' did not match any file(s) known to git

Consequence recorded in entry 002: because the file was never committed, its
deletion leaves no trace in git at all, and 002 is the only evidence it existed.

Two follow-on edits this forced, neither separately requested:

- The closing paragraph of "Saving prompt outputs" read "`README.md` and
  `INDEX.md` are infrastructure, not entries, and carry no number of their own."
  It now reads "`INDEX.md` is infrastructure, not an entry, and carries no
  number of its own." Leaving it would have named a file that no longer exists.
- `INDEX.md` gained an opening line naming `RULES.md`'s "Saving prompt outputs"
  as the authority for the convention, per C6.

## C7 — one commit, several entries

Added after this session produced three entries destined for a single commit,
which the `Record:` rule as first written could not express: it named "the
body's final line, on its own". Step 3 of "Committing and pushing" now reads:

> 3. The body ends with a `Record:` line naming the `prompt_outputs/` entry the
>    commit corresponds to:
>
>        Record: prompt_outputs/001-rules-of-engagement-v2-phaseB.md
>
>    When one commit covers several entries, there is one `Record:` line per
>    entry, each on its own line. Every entry the commit covers gets a line;
>    none is left unlinked.
>
>        Record: prompt_outputs/001-rules-of-engagement-v2-phaseB.md
>        Record: prompt_outputs/002-record-gap-audit.md
>        Record: prompt_outputs/003-rules-corrections-phaseB.md
>
>    The record cannot hold the hash — it is written before the commit exists and
>    frozen once the phase has reported — so the hash must hold the record.
>    Without these lines the two halves of the history have no link at all.

This closes the second matters-next item carried below from the previous
version of this entry. It is answered rather than deferred: one commit covers
all three entries (C8), and all three are named.

`001-rules-of-engagement-v2-phaseA.md` gets no line of its own. Both phases of
one task share a number, so entry 001 is the pair, and naming its phaseB file
names the entry. Flagged because the rule says "every entry the commit covers
gets a line" and a reader counting files rather than entries would expect four.

## Deviation: editing this entry after its phase reported

**Disclosed rather than silent, and it needs a ruling.**

This entry's PHASE B reported in chat before C7 arrived. C2, as now written in
`RULES.md`, says append-only binds "once its phase has reported" and that after
the report the file "is frozen". Taken literally, this entry froze at that
point and C7 belonged in a new entry 004.

The experimenter directed otherwise, on the reading that 003 "has not yet
reported to a commit and is therefore still being written, not revised". That is
a coherent freeze point and arguably the better one — a record whose work is not
yet committed is still in flight — but it is not what the rule says. The rule
says "reported"; the ruling says "committed". Those are different moments, and
this entry sits between them.

C7 was applied here as directed. The wording of C2 was **not** changed, because
that was not requested and choosing between the two freeze points is a decision,
not a cleanup. Until it is settled, C2 and the practice it governs disagree —
which is precisely the CLAUDE.md/RULES.md failure mode this session began by
resolving, reappearing inside RULES.md itself.

### Resolved: C2 stands, and these edits are an authorised exception

The experimenter settled it. **C2 stands exactly as written: a record freezes
when its phase reports, not when it is committed.** The commit-time reading was
introduced in an instruction rather than in the file, and a rule that means one
thing in `RULES.md` and another when spoken is worse than a rule that is
occasionally inconvenient. `RULES.md` was not changed.

The consequence, stated plainly rather than fudged: this entry reported before
C7 arrived, so under C2 it was already frozen. The C7 additions above, and the
later additions of the final suite result and the file-size table, are all
**edits to a frozen record.** They were authorised explicitly and individually,
as a one-time exception, on the grounds that this entry has not been committed
and the alternative was an entry 004 existing solely to append five numbers to
a file no one had yet read.

Three things follow, and none of them is that the rule bent:

- The exception was **authorised**, not assumed. It came from the experimenter
  after the conflict was surfaced, not from a reading of the rule that made it
  permissible.
- **The rule was not amended to allow it.** C2 forbids exactly what happened
  here and still forbids it.
- **From entry 004 onward the correct handling is a new entry**, whatever the
  size of the addition and whether or not the work has been committed. Appending
  five numbers to a frozen record is a new entry's worth of ceremony for very
  little content, and that is the cost of the guarantee.

An exception that is written down is not the same as a rule that is ignored.
This paragraph is the difference between them.

## Validation of the proposed commit message

Measured from the file, per C4. First draft, then corrected, then re-measured:

| Property | Limit | First draft | Final |
|---|---|---|---|
| Subject length | ≤ 50 | 47 | 47 |
| Subject trailing full stop | none | none | none |
| Subject mood | imperative | "Track" | "Track" |
| Line 2 blank | yes | yes | yes |
| Body max width | ≤ 72 | 73 | 72 |
| Body lines over 72 | 0 | 2 | 0 |
| Body line count | — | 35 | 35 |
| Lines beginning `Record:` | 3 | 4 | 3 |

Two body lines were at 73 in the first draft and were rewrapped.

The `Record:` count of 4 in the first draft was a real defect, not a counting
artefact: the prose read "and the `Record:` lines below, which link a commit to
the entries it covers", and the wrap put `Record:` at the start of a line. A
line beginning with the trailer token that is not a trailer would be
miscounted by anything parsing the message, and misread by a person skimming
it. Reworded to "the trailer lines below". The count is now 3, matching the
three entries the commit covers, and all three were confirmed present on disk.

## Verification

Suite, run twice — once after C1–C6, and again after C7:

    318 passed in 74.36s (0:01:14)    state after C1-C6
    318 passed in 89.29s (0:01:29)    state after C7, the state being committed

The second is the one that verifies what is committed. For one turn this entry
carried only the first, which made it assert a suite result measured before the
change it describes — not an omission but a wrong number. Corrected under the
authorised exception recorded above.

File sizes at the state being committed:

| File | Lines |
|---|---|
| `RULES.md` | 276, from 231 after C1–C6, from 115 at session start |
| `001-rules-of-engagement-v2-phaseA.md` | 196 |
| `001-rules-of-engagement-v2-phaseB.md` | 360 |
| `002-record-gap-audit.md` | 111 |
| `003-rules-corrections-phaseB.md` | this file |
| `INDEX.md` | 18 |

Section order in `RULES.md` after the change. Two subsections are new; no
top-level section moved relative to another.

    ## The two-phase protocol
    ## Saving prompt outputs
    ### What the file must contain that chat may omit      NEW (C4)
    ## When a phase goes wrong
    ## Regenerating the reference figures
    ## Evidence standards
    ## Report structure
    ### The chat report and the file are different documents
    ## Committing and pushing
    ## Running things
    ## What is irreversible

Constraint check — nothing outside `RULES.md` and `prompt_outputs/` was touched:

    git --no-pager diff --stat -- CLAUDE.md src tests data figures
    (no output)

    git status --short
     M RULES.md
    ?? prompt_outputs/

No dependencies added; nothing installed.

## The proposed commit message

Per C5, no message appeared in this entry's PHASE B report. The report was
approved, and one commit was directed for all three entries (C8). The message
proposed after that approval, verbatim:

    Track prompt outputs and gate commits on review

    RULES.md now requires every PHASE A and PHASE B report to be written to
    prompt_outputs/ in full before it is summarised into chat, so the copy
    on disk is never the abridged one. The directory is tracked and
    append-only: it holds the evidence and the argument behind a decision,
    which exists nowhere else once a conversation ends and which no process
    regenerates. It is listed under "What is irreversible" for that reason.

    PHASE B now ends before the commit. Committing as part of implementation
    made the commit invisible to review, so the message and the change were
    approved together or not at all. Splitting them lets a report be
    rejected without anything having to be undone. A phase that fails
    partway stops and leaves the tree as it is, because a half-finished
    state is evidence and cleaning it up destroys what there is to judge.

    The mechanism was tested immediately. Entry 001's own record turned out
    to be a subset of its chat report, missing the deviation disclosure most
    of all. Append-only forbade amending it, so entry 002 records the gap
    and reproduces what was missing, and 001 stands wrong but honest beside
    it. That is the intended behaviour, not a workaround.

    Entry 003 carries the corrections that followed: the append-only freeze
    point, the requirement that a record be a superset of its chat report,
    the ban on proposing a commit message inside a PHASE B report, and the
    trailer lines below, which link a commit to the entries it covers
    because the entries cannot hold the hash.

    Also records that line endings here are governed by core.autocrlf=true
    at system scope, not by .gitattributes. An earlier report attributed a
    conversion to .gitattributes; that was wrong. .gitattributes pins only
    data/raw/** -text, which keeps provenance.json's hashes valid on a
    non-Windows clone, and *.png binary.

    Record: prompt_outputs/001-rules-of-engagement-v2-phaseB.md
    Record: prompt_outputs/002-record-gap-audit.md
    Record: prompt_outputs/003-rules-corrections-phaseB.md

Not committed at the time of writing. Awaiting approval of the message.

## Matters next

- **DEFERRED BY DECISION, NOT FORGOTTEN — a consolidation pass on `RULES.md`,
  after the EANA presentation.** The file is at 276 lines, up from 115 at the
  start of the session. It states the append-only rule in two places and
  record-completeness in two more, while imposing "State each fact ONCE" on
  reports. The experimenter has seen this and ruled that it waits until after
  EANA. Recorded here so it is not lost: this is the item to pick up when
  process work resumes.
- **The C2 freeze point is settled** — freeze at report, not at commit, and
  `RULES.md` is unchanged. Closed, not deferred. See the resolution under
  "Deviation: editing this entry after its phase reported" above, including the
  one-time exception that covers the edits made to this entry after it reported.
- **`002-record-gap-audit.md` uses the `-audit` suffix for an entry that
  reports on the project's own process** rather than on its data or code. The
  naming rule permits it — an audit is a read-only task with no PHASE B — but
  every previous use of the word "audit" in this project meant a code audit.
  Not a problem, just an overload worth noticing before it confuses someone.
