# 001 — rules-of-engagement-v2 — PHASE B

Date: 2026-08-30
HEAD at time of phase: `aa804d8`
Supersedes: nothing.
Committed: no. This task is the first to follow the new "Committing and pushing"
gate, so PHASE B ended at the report and the commit message was proposed rather
than applied. The commit hash is therefore not recorded in this file — see
"Consequence worth knowing" under the B9 findings below.

## Re-check of PHASE A's findings (the new B11 rule, applied to itself)

Before implementing, PHASE A's confirmed assumptions were re-verified:

    HEAD: aa804d8
    tree: (empty = clean)
    prompt_outputs: ABSENT
    RULES.md lines: 115

All unchanged from PHASE A. Proceeded.

## What was built

### RULES.md

Grew from 115 to 231 lines. `git diff --stat`:

    RULES.md | 140 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++------
    1 file changed, 128 insertions(+), 12 deletions(-)

Section order after the change. Three sections are new; no existing section was
reordered relative to another.

    ## The two-phase protocol          edited (B2, B11, B12)
    ## Saving prompt outputs           NEW (B5)
    ## When a phase goes wrong         NEW (B10)
    ## Regenerating the reference figures   unchanged
    ## Evidence standards              unchanged
    ## Report structure                edited (B1, D2) + NEW subsection (B13)
    ## Committing and pushing          NEW (B8)
    ## Running things                  edited (B15)
    ## What is irreversible            edited (D3)

The placement reasoning: `Saving prompt outputs` and `When a phase goes wrong`
sit immediately after the protocol because both describe how any phase operates
and how any phase ends. `Committing and pushing` sits immediately after
`Report structure` because it is the gate that follows a report. Inserting
rather than reordering keeps the diff readable.

### prompt_outputs/

Four files created:

    prompt_outputs/README.md                              55 lines
    prompt_outputs/INDEX.md                               12 lines
    prompt_outputs/001-rules-of-engagement-v2-phaseA.md   196 lines
    prompt_outputs/001-rules-of-engagement-v2-phaseB.md   this file

Confirmed trackable: `git check-ignore -v` exits 1 with no output for paths
under `prompt_outputs/`, so no `.gitignore` pattern matches and no `.gitignore`
change was needed. `git status --short` shows `?? prompt_outputs/`.

## The edits, verbatim

### B2 and B12 — the PHASE A definition

Before:

> **PHASE A — verification only.** Read files, list directories, run read-only
> commands. Create, edit, move and delete nothing. Install nothing. Check every
> assumption in the request against the actual data and report each as
> CONFIRMED / CONTRADICTED / UNKNOWN with the concrete evidence used — a count, a
> printed line, a min/max. Then list PROPOSED DEVIATIONS: anything the plan needs
> changed. Then stop and wait.

After:

> **PHASE A — verification only.** Read files, list directories, run read-only
> commands. Create, edit, move and delete nothing — with one exception: this
> phase's own output file under `prompt_outputs/`, which is the only thing
> PHASE A may write. Install nothing. Check every assumption in the request
> against the actual data and report each as CONFIRMED / CONTRADICTED / UNKNOWN
> with the concrete evidence used — a count, a printed line, a min/max. State
> explicitly what you could NOT check, and why: an unstated gap reads as a clean
> bill of health. Then list PROPOSED DEVIATIONS: anything the plan needs changed.
> Then stop and wait.

### B11 — the PHASE B definition

Before:

> **PHASE B — implementation.** Only after an explicit "PROCEED". Build exactly
> what was specified, nothing more.

After:

> **PHASE B — implementation.** Only after an explicit "PROCEED". Before
> implementing anything, re-check that the assumptions PHASE A confirmed still
> hold — approval may arrive hours or days later, and PHASE A's evidence has a
> shelf life; if anything has changed, stop and report rather than proceeding on
> stale verification. Then build exactly what was specified, nothing more.

### B1 — "Report structure" item 3

Before:

> 3. **What changed:** files, line counts, `git diff --stat`, commit hash.

After:

> 3. **What changed:** files, line counts, `git diff --stat` of the working tree.

### D2 — the closing paragraph of "Report structure"

Before:

> Do NOT paste full diffs. The project is under git — the commit hash and
> `git diff --stat` are enough, and the experimenter can run `git show` for the
> rest. Paste verbatim code only for a specific line under discussion.

After:

> Do NOT paste full diffs. The project is under git — `git diff --stat` is enough,
> and the experimenter can run `git show` for the rest. Paste verbatim code only
> for a specific line under discussion.

### D3 — the fourth bullet under "What is irreversible"

Added:

> - **`prompt_outputs/`** — the record of what was done and why. Different in kind
>   from the three above: those are outputs that do have a generating process, and
>   are irreplaceable only because running it destroys the baseline they serve as.
>   This one never had a generating process at all. The reasoning it holds existed
>   only in a conversation that no longer exists, so a deleted entry cannot be
>   recovered or rebuilt by any means. Append only.

### B15 — the line-endings note

Placed at the end of `## Running things` rather than in a section of its own.
Reasoning: it is knowledge about how this machine behaves when git touches a
file, which is the same category as "which interpreter to invoke", and a
six-line note did not justify a tenth top-level heading. It is findable by
searching for the bolded lead-in. Added:

> **Line endings** are governed by `core.autocrlf=true` at **system** scope, not
> by `.gitattributes`. `.gitattributes` pins exactly two things: `data/raw/**
> -text`, which is what keeps `provenance.json`'s SHA-256 hashes valid on a
> non-Windows clone, and `*.png binary`. Everything else, including every `.md`
> and `.py`, normalises to LF in the index via autocrlf and comes back as CRLF on
> a Windows checkout. Do not attribute a line-ending conversion to
> `.gitattributes` without running `git check-attr` first.

## New sections, verbatim

### ## Saving prompt outputs

> Every PHASE A and PHASE B output is written to `prompt_outputs/` as a markdown
> file, in full — not a summary of the report, the report.
>
> Naming:
>
>     NNN-short-slug-phaseA.md
>     NNN-short-slug-phaseB.md
>
> `NNN` is a zero-padded sequence that never resets. The slug names the task, not
> the date. Both phases of one task share a number.
>
> A read-only task that has no PHASE B — an audit, a verification, a check — uses
> `NNN-short-slug-audit.md` instead.
>
> **The file is written as part of the phase it records, BEFORE reporting in
> chat.** That order is the whole point: it guarantees the on-disk copy is never
> the summarised one. Write the record, then write the chat report from it.
>
> **The directory is TRACKED in git.** It is a decision record, in the same spirit
> as CLAUDE.md's rationale sections — the reasoning behind a change is worth as
> much as the change, and it exists nowhere else once the conversation ends.
>
> **APPEND-ONLY.** Never edit and never delete an existing file. A re-run of a
> task gets a new number, and its file states at the top which number it
> supersedes and why. A record that can be revised is not a record.
>
> `prompt_outputs/INDEX.md` gets one appended line per entry: number, slug, phases
> present, date, and one sentence on what the task did or found. It covers
> read-only work as well as changes — an audit that found nothing is a result, and
> the record should show it was run. `README.md` and `INDEX.md` are
> infrastructure, not entries, and carry no number of their own.

### ## When a phase goes wrong

> If PHASE B fails partway — a test goes red unexpectedly, a command errors, a
> file is not what PHASE A found it to be — **STOP.** Do not push through, do not
> work around it, do not clean up.
>
> - **Leave the working tree exactly as it is.** The half-finished state is
>   evidence, and the experimenter may want to see it.
> - **Write the `prompt_outputs/` file anyway,** with what was completed, what
>   failed, and the verbatim error. An abandoned phase still gets its record —
>   it needs one more than a successful phase does, not less.
> - **Report in chat:** what was done, what failed, the current state of the tree,
>   and what you propose. Then wait.
> - **Reverting is a decision, not a cleanup.** Ask.

### ### The chat report and the file are different documents

> The file in `prompt_outputs/` and the report in chat have different jobs. The
> file is the complete record: everything, verbatim, no summarising. The chat
> report is what the experimenter needs in order to decide the next step, and
> nothing else. When something long belongs in the record but not in the
> decision — a full file dump, an exhaustive heading list, complete tool output —
> put it in the file and give chat one line saying where it is.
>
> Chat report requirements:
>
> - **FIRST LINE is a status line:** phase, task slug, HEAD hash, and the number
>   of items needing a decision.
>
>       PHASE B - prompt-outputs - aa804d8 - 0 decisions needed
>
>   If that number is not zero, those items come first and nothing precedes them.
> - **LAST LINE is exactly** `--- END OF REPORT ---`. It exists so truncation in
>   transit is visible. If it is absent, the experimenter did not receive the
>   whole report.
> - **No box-drawing characters.** Plain markdown tables or plain text. They are
>   heavy and they mangle when pasted between tools.
> - **State each fact ONCE.** A line-count table and a `git diff --stat` say the
>   same thing; pick one.
> - **Reference code by heading or function name, never by line number.** Line
>   numbers go stale as soon as anything above them shifts, and a stale reference
>   is worse than none.
> - **Paste a file verbatim in chat only when that file IS the deliverable,** and
>   say so. Otherwise it goes in `prompt_outputs/` and chat gets the path.
> - **Never nest one verbatim block inside another.** Separate them with headings.

### ## Committing and pushing

> **PHASE B ENDS BEFORE THE COMMIT.** Do not commit as part of PHASE B. Report,
> then wait.
>
> 1. After the experimenter approves the PHASE B report, **propose** a commit
>    message. Do not commit yet.
> 2. Commit messages follow 50/72: subject 50 characters or fewer, imperative mood
>    ("Add", not "Added" or "Adds"), no trailing full stop; blank line; body
>    wrapped at 72 columns. The body explains WHY and what the change guarantees,
>    not what the diff already shows.
> 3. Once the message is approved, commit AND push, then report both in one turn:
>    hash, push output, `git status`. These are one gate, not two.
>
> **If any gate is not explicitly answered, wait. Silence is not approval.**

## B3 — correcting the record

In the report for commit `aa804d8` I wrote that the LF-to-CRLF warning was
expected because "the repo's `.gitattributes` normalises". **That was wrong.**

`.gitattributes` plays no part. It matches nothing named `*.md`:
`git check-attr -a RULES.md` returns no attributes at all, and `text` and `eol`
are both `unspecified`. Its only two active rules are `data/raw/** -text` and
`*.png binary`.

The mechanism is `core.autocrlf=true`, set at **system** scope in
`file:C:/Users/berke.santos/AppData/Local/Programs/Git/etc/gitconfig`. It is
unset at global and local scope, and `core.eol` is unset everywhere.

The distinction matters for exactly the reason the correction was asked for. The
`data/raw/** -text` rule is what holds `provenance.json`'s SHA-256 hashes valid
on a non-Windows clone. If a reader believed `.gitattributes` were governing all
text files, they would draw the wrong conclusion about what protects the raw
tree and might "simplify" the rule that is actually load-bearing.

A second correction of tense, beyond what was asked: no conversion had actually
occurred. The worktree `RULES.md` at `aa804d8` was 5717 bytes with CR=0 and
LF=115 — LF only — and `git cat-file -s HEAD:RULES.md` was also 5717 bytes, so
the stored blob was LF too. `autocrlf=true` normalises to LF on the way in,
which for a file written as LF is a no-op. The warning was a prediction about
the next checkout, which had not happened.

Not verified: that a future checkout does produce CRLF. Confirming it needs a
fresh clone, which was outside the read-only scope of the phase that established
the mechanism. The mechanism is observed; the outcome is inferred.

## B9 — sections contradicted by the new commit gate

Searched `RULES.md` for `commit|push|git show|revert`. Every hit reviewed.

**Nothing contradicts B8.** No section states or implies that PHASE B ends with
a commit, other than the two "commit hash" references in `Report structure` that
B1 and D2 had already removed. Three things are worth reporting anyway.

**Finding 1 — `git show` in the same corrected sentence is stale for the same
reason.** The closing paragraph of `Report structure` now reads "`git diff
--stat` is enough, and the experimenter can run `git show` for the rest". At the
moment a PHASE B report is written there is no commit, so `git show` has nothing
to show; the correct command at that point is `git diff`. D2 approved changing
the first half of the sentence and did not mention the second. Not fixed —
reported for a decision. Suggested wording: "the experimenter can run `git diff`
for the rest, or `git show` once it is committed."

**Finding 2 — `Regenerating the reference figures` step 4 is now the general
rule stated twice.** It reads "Never commit modified reference overlays without
an explicit request naming the reason." Under B8 *no* commit happens without an
explicit approved message, so the special restriction has become the default.
This is redundancy, not contradiction. Recommendation: leave it. Restating the
rule at the highest-stakes site is worth twelve words, and step 3 above it
carries the real content.

**Finding 3, a consequence worth knowing — a PHASE B record can never contain
its own commit hash.** The record is written before the report, and the report
precedes the commit gate, so the hash does not exist yet and append-only forbids
adding it later. The link from an entry to its commit therefore runs the other
way: the commit message is the place to name the entry. Nothing in the current
rules requires that. Flagging it rather than proposing a rule, since it may be
better solved when there is a second entry to see the shape of.

## Verification

Suite after the change:

    318 passed in 60.55s (0:01:00)

Constraint check — nothing outside the four intended files was touched:

    git --no-pager diff --stat -- CLAUDE.md src tests data figures
    (no output)

    git status --short
     M RULES.md
    ?? prompt_outputs/

No dependencies added; nothing was installed.

## Proposed commit message

Not applied. Awaiting approval per the new gate.

    Track prompt outputs and gate commits on review

    RULES.md now requires every PHASE A and PHASE B report to be written to
    prompt_outputs/ in full before it is summarised into chat, so the record
    on disk is never the abridged one. The directory is tracked and
    append-only: it holds the evidence and the argument behind a decision,
    which exists nowhere else once a conversation ends and which no process
    can regenerate. It is listed under "What is irreversible" for that
    reason.

    PHASE B now ends before the commit. Committing as part of implementation
    made the commit invisible to review, so the message and the change were
    approved together or not at all. Splitting them means a report can be
    rejected without anything having to be undone.

    Adds a rule for a phase that fails partway: stop, leave the tree as
    it is, record the failure, ask. A half-finished state is evidence,
    and cleaning it up destroys what the experimenter needs to judge it.

    Records that line endings here are governed by core.autocrlf=true at
    system scope, not by .gitattributes. A previous report attributed a
    conversion to .gitattributes; that was wrong. .gitattributes pins only
    data/raw/** -text, which is what keeps provenance.json's hashes valid on
    a non-Windows clone, and *.png binary.
