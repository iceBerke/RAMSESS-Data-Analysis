# RAMSESS analysis — rules of engagement

How we work. `CLAUDE.md` is about the project; this file is about the process,
and where the two disagree, this file wins.

## The two-phase protocol

Every task runs in two phases. Do not start PHASE B until the user replies
"PROCEED".

**PHASE A — verification only.** Read files, list directories, run read-only
commands. Create, edit, move and delete nothing. Install nothing. Check every
assumption in the request against the actual data and report each as
CONFIRMED / CONTRADICTED / UNKNOWN with the concrete evidence used — a count, a
printed line, a min/max. Then list PROPOSED DEVIATIONS: anything the plan needs
changed. Then stop and wait.

**PHASE B — implementation.** Only after an explicit "PROCEED". Build exactly
what was specified, nothing more.

**NO SILENT CHANGES.** If you want to do anything not written in the request —
rename something, add a helper, install a package, restructure a path, "improve"
an API — do not do it. Stop, list it under PROPOSED DEVIATIONS, wait. This
applies even when the change seems trivially correct or obviously beneficial:
"obviously beneficial" is exactly the judgement that is not yours to make alone.
If an assumption turns out false, do not work around it — report and wait.

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
3. **What changed:** files, line counts, `git diff --stat`, commit hash.
4. **Test result:** the summary line, and per-file counts only if they changed.
   NOT the full dot matrix.
5. **Demonstrations:** pre-fix failure output, real-run output.
6. **"Matters next."**

Do NOT paste full diffs. The project is under git — the commit hash and
`git diff --stat` are enough, and the experimenter can run `git show` for the
rest. Paste verbatim code only for a specific line under discussion.

## Running things

Always `.venv\Scripts\python.exe`. Never bare `python`, never the system
interpreter, and never install into it.

    .venv\Scripts\python.exe -m pytest
    .venv\Scripts\python.exe main.py <subcommand>

**The suite must pass before any change is considered complete.** Regenerate the
golden fixture `tests/fixtures/inspect_irradiation_sara.txt` only when the
output is deliberately changed — never to make a failing test pass.

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

Derived data and every other figure are build output. Delete them freely; they
come back.
