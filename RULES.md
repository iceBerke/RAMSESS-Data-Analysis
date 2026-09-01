# RAMSESS analysis — rules of engagement

How we work. `CLAUDE.md` is about the project; this file is about the process,
and where the two disagree, this file wins.

## The two-phase protocol

Every task runs in two phases. Do not start PHASE B until the user replies
"PROCEED".

**PHASE A — verification only.** Read files, list directories, run read-only
commands. Create, edit, move and delete nothing — with one exception: this
phase's own output file under `prompt_outputs/`, which is the only thing
PHASE A may write. Install nothing. Check every assumption in the request
against the actual data and report each as CONFIRMED / CONTRADICTED / UNKNOWN
with the concrete evidence used — a count, a printed line, a min/max. State
explicitly what you could NOT check, and why: an unstated gap reads as a clean
bill of health. Then list PROPOSED DEVIATIONS: anything the plan needs changed.
Then stop and wait.

**PHASE B — implementation.** Only after an explicit "PROCEED". Before
implementing anything, re-check that the assumptions PHASE A confirmed still
hold — approval may arrive hours or days later, and PHASE A's evidence has a
shelf life; if anything has changed, stop and report rather than proceeding on
stale verification. Then build exactly what was specified, nothing more.

**NO SILENT CHANGES.** If you want to do anything not written in the request —
rename something, add a helper, install a package, restructure a path, "improve"
an API — do not do it. Stop, list it under PROPOSED DEVIATIONS, wait. This
applies even when the change seems trivially correct or obviously beneficial:
"obviously beneficial" is exactly the judgement that is not yours to make alone.
If an assumption turns out false, do not work around it — report and wait.

## Saving prompt outputs

Every PHASE A and PHASE B output is written to `prompt_outputs/` as a markdown
file, in full — not a summary of the report, the report.

Naming:

    NNN-short-slug-phaseA.md
    NNN-short-slug-phaseB.md

`NNN` is a zero-padded sequence that never resets. The slug names the task, not
the date. Both phases of one task share a number.

A read-only task that has no PHASE B — an audit, a verification, a check — uses
`NNN-short-slug-audit.md` instead.

**The file is written as part of the phase it records, BEFORE reporting in
chat.** That order is the whole point: it guarantees the on-disk copy is never
the summarised one. Write the record, then write the chat report from it.

**The directory is TRACKED in git.** It is a decision record, in the same spirit
as CLAUDE.md's rationale sections — the reasoning behind a change is worth as
much as the change, and it exists nowhere else once the conversation ends.

**APPEND-ONLY.** Never edit and never delete an existing file. A re-run of a
task gets a new number, and its file states at the top which number it
supersedes and why. A record that can be revised is not a record.

**Append-only binds a record once its phase has reported.** Until then the file
is still being written and may be revised freely — drafting something, measuring
it, and correcting it before it is delivered is writing, not revising. After the
report it is frozen. A correction to a frozen entry is a new numbered entry that
names what it supersedes, never an edit.

### What the file must contain that chat may omit

**The file is a superset of the chat report, never a subset.** Chat may leave
out anything the record holds. The record may leave out nothing chat said. A
fact that appears in chat and not in the record is a failure of the record.

Beyond the report itself, the file must carry:

- **Any deviation from the prompt, and the reasoning for it.** This is the most
  important thing in the record and the easiest to lose, because a deviation is
  typically explained once, in passing, at the moment it is taken.
- **Any self-correction** — something previously claimed that turned out to be
  wrong, what the correct statement is, and how it was established.
- **"Matters next."**
- **Anything measured or validated during the phase, with the numbers.** A
  validation whose result is not written down was not performed, as far as any
  later reader can tell.

`prompt_outputs/INDEX.md` gets one appended line per entry: number, slug, phases
present, date, and one sentence on what the task did or found. It covers
read-only work as well as changes — an audit that found nothing is a result, and
the record should show it was run. `INDEX.md` is infrastructure, not an entry,
and carries no number of its own.

## When a phase goes wrong

If PHASE B fails partway — a test goes red unexpectedly, a command errors, a
file is not what PHASE A found it to be — **STOP.** Do not push through, do not
work around it, do not clean up.

- **Leave the working tree exactly as it is.** The half-finished state is
  evidence, and the experimenter may want to see it.
- **Write the `prompt_outputs/` file anyway,** with what was completed, what
  failed, and the verbatim error. An abandoned phase still gets its record —
  it needs one more than a successful phase does, not less.
- **Report in chat:** what was done, what failed, the current state of the tree,
  and what you propose. Then wait.
- **Reverting is a decision, not a cleanup.** Ask.

## Regenerating the reference figures

The six `figures/irradiation_sara/{sample}_overlay.png` files are the reference
output of the raw plot path. Regenerating them is not a routine refresh. The
procedure:

1. **Run the suite BEFORE regenerating.** If `test_raw_plot_reference` passes,
   regeneration is a no-op: the bytes will not change, so there is nothing to
   gain by running it.
2. **If it FAILS, do not regenerate.** A failing reference test means the
   plotting path produces different pixels than the baseline. Regenerating at
   that point overwrites the baseline with whatever the code does today, which
   makes the comparison self-fulfilling and the test worthless. The failure is
   the finding. Report it.
3. **After any regeneration, run `git status --short figures/`.** Clean means
   nothing changed and all is well. Modified means the plotting path changed —
   STOP and report `git diff --stat` plus the test output. Do not commit and do
   not revert: that is a finding for the experimenter to judge, and reverting
   destroys the evidence just as surely as committing buries it.
4. **Never commit modified reference overlays** without an explicit request
   naming the reason.

Why this care is warranted: the committed PNG **is** the baseline. There is no
second copy to compare against, no golden hash held elsewhere — the file in git
is the entire definition of "correct" for that code path. Git makes an
accidental overwrite detectable and reversible, but it does not prevent it. The
judgement is the safeguard, not the tooling.

## Evidence standards

- **Prove it, don't assert it.** A claim that a test guards X must be shown by
  running it against the unfixed code and pasting the actual failure. A test
  that has only ever been seen passing has not been shown to guard anything.
- **Scope your claims precisely.** "The only instance in this function" and "the
  only instance in this module" are different claims, and so is "in the
  repository". Say which one you actually checked.
- **Say UNCERTAIN rather than guessing.** A false "this is unused" is worse than
  an honest gap: the gap gets checked, the false claim gets acted on.
- **Distinguish what you verified from what the experimenter told you.**
  Attribute the latter to him explicitly. Both are usable; they are not the same
  kind of fact and must not be reported as though they were.
- **Quote the actual current code** for anything about to be modified, not a
  description of it and not what you remember it saying.

## Report structure

Order matters, because long reports arrive truncated. Front-load what cannot be
worked without:

1. **Blockers and questions needing a decision.**
2. **PROPOSED DEVIATIONS.**
3. **What changed:** files, line counts, `git diff --stat` of the working tree.
4. **Test result:** the summary line, and per-file counts only if they changed.
   NOT the full dot matrix.
5. **Demonstrations:** pre-fix failure output, real-run output.
6. **"Matters next."**

Do NOT paste full diffs. The project is under git — `git diff --stat` is enough,
and the experimenter can run `git diff` for the rest, or `git show` once it is
committed. Paste verbatim code only for a specific line under discussion.

### The chat report and the file are different documents

The file in `prompt_outputs/` and the report in chat have different jobs. The
file is the complete record: everything, verbatim, no summarising. The chat
report is what the experimenter needs in order to decide the next step, and
nothing else. When something long belongs in the record but not in the
decision — a full file dump, an exhaustive heading list, complete tool output —
put it in the file and give chat one line saying where it is.

Chat report requirements:

- **FIRST LINE is a status line:** phase, task slug, HEAD hash, and the number
  of items needing a decision.

      PHASE B - prompt-outputs - aa804d8 - 0 decisions needed

  If that number is not zero, those items come first and nothing precedes them.
- **LAST LINE is exactly** `--- END OF REPORT ---`. It exists so truncation in
  transit is visible. If it is absent, the experimenter did not receive the
  whole report.
- **No box-drawing characters.** Plain markdown tables or plain text. They are
  heavy and they mangle when pasted between tools.
- **State each fact ONCE.** A line-count table and a `git diff --stat` say the
  same thing; pick one.
- **Reference code by heading or function name, never by line number.** Line
  numbers go stale as soon as anything above them shifts, and a stale reference
  is worse than none.
- **Paste a file verbatim in chat only when that file IS the deliverable,** and
  say so. Otherwise it goes in `prompt_outputs/` and chat gets the path.
- **Never nest one verbatim block inside another.** Separate them with headings.

## Committing and pushing

**PHASE B ENDS BEFORE THE COMMIT.** Do not commit as part of PHASE B. Report,
then wait.

**The PHASE B report must NOT contain a proposed commit message.** A message
drafted before the report is approved describes a change that may still be
rejected, and it pulls the reader toward accepting. Proposing one early is
itself a deviation.

1. After the experimenter approves the PHASE B report, **propose** a commit
   message. Do not commit yet.
2. Commit messages follow 50/72: subject 50 characters or fewer, imperative mood
   ("Add", not "Added" or "Adds"), no trailing full stop; blank line; body
   wrapped at 72 columns. The body explains WHY and what the change guarantees,
   not what the diff already shows.
3. The body ends with a `Record:` line naming the `prompt_outputs/` entry the
   commit corresponds to:

       Record: prompt_outputs/001-rules-of-engagement-v2-phaseB.md

   When one commit covers several entries, there is one `Record:` line per
   entry, each on its own line. Every entry the commit covers gets a line;
   none is left unlinked.

       Record: prompt_outputs/001-rules-of-engagement-v2-phaseB.md
       Record: prompt_outputs/002-record-gap-audit.md
       Record: prompt_outputs/003-rules-corrections-phaseB.md

   The record cannot hold the hash — it is written before the commit exists and
   frozen once the phase has reported — so the hash must hold the record.
   Without these lines the two halves of the history have no link at all.
4. Once the message is approved, commit AND push, then report both in one turn:
   hash, push output, `git status`. These are one gate, not two.

**If any gate is not explicitly answered, wait. Silence is not approval.**

## Running things

Always `.venv\Scripts\python.exe`. Never bare `python`, never the system
interpreter, and never install into it.

    .venv\Scripts\python.exe -m pytest
    .venv\Scripts\python.exe main.py <subcommand>

**The suite must pass before any change is considered complete.** Regenerate the
golden fixture `tests/fixtures/inspect_irradiation_sara.txt` only when the
output is deliberately changed — never to make a failing test pass.

**Line endings** are governed by `core.autocrlf=true` at **system** scope, not
by `.gitattributes`. `.gitattributes` pins exactly two things: `data/raw/**
-text`, which is what keeps `provenance.json`'s SHA-256 hashes valid on a
non-Windows clone, and `*.png binary`. Everything else, including every `.md`
and `.py`, normalises to LF in the index via autocrlf and comes back as CRLF on
a Windows checkout. Do not attribute a line-ending conversion to
`.gitattributes` without running `git check-attr` first.

## What is irreversible

Everything in this project is reproducible from raw plus config, **except** the
following. None of these may be touched without an explicit request:

- **`data/raw/`** — the experiment itself. It cannot be regenerated by anything,
  at all, ever. Nothing writes here.
- **The six `figures/irradiation_sara/{sample}_overlay.png` reference
  overlays** — regenerable as bytes, but not as a *baseline*: regenerate them
  and the thing they were being compared against is gone. See above.
- **The golden fixture `tests/fixtures/inspect_irradiation_sara.txt`** — same
  reasoning. It is a record of intended output, not a cache of current output.
- **`prompt_outputs/`** — the record of what was done and why. Different in kind
  from the three above: those are outputs that do have a generating process, and
  are irreplaceable only because running it destroys the baseline they serve as.
  This one never had a generating process at all. The reasoning it holds existed
  only in a conversation that no longer exists, so a deleted entry cannot be
  recovered or rebuilt by any means. Append only.

Derived data and every other figure are build output. Delete them freely; they
come back.
