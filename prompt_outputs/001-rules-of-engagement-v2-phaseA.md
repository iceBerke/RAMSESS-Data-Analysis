# 001 — rules-of-engagement-v2 — PHASE A

Date: 2026-08-30
HEAD at time of phase: `aa804d8`
Supersedes: nothing. This is the first entry.

## Note on how this file came to exist

**This file was written during PHASE B, not during PHASE A.** That is a
bootstrap, not a violation, and it is the only entry to which it applies.

When PHASE A of this task ran, `prompt_outputs/` did not exist, the rule
requiring a phase to write its output here did not exist, and the PHASE A
definition in `RULES.md` still read "Create, edit, move and delete nothing" with
no carve-out. PHASE A could not write its own record without breaking the rule
it was about to amend. The gap was raised in the PHASE A report as deviation D1
and the experimenter confirmed the handling: write the file during PHASE B,
verbatim as delivered, with this note explaining why.

The body below is the PHASE A report exactly as it was delivered in chat. It has
not been edited, tidied, or corrected with hindsight. From entry 002 onward the
rule operates as written and each phase writes its own file before reporting.

---

## The report as delivered

PHASE A - rules-of-engagement-v2 - aa804d8 - 3 decisions needed

### Decisions needed

**D1. This task's own PHASE A file cannot be written during PHASE A.**
B7 requires `001-*-phaseA.md`, but `prompt_outputs/` does not exist, the rule
does not exist, and the B2 carve-out that would permit PHASE A to write does not
exist. PHASE A as currently written forbids creating anything. Proposed: this
PHASE A report is written to disk during PHASE B, verbatim as delivered in this
chat message, with a note in the file recording that it was written
retroactively and why. From task 002 onward the rule operates as written.
Confirm or specify otherwise.

**D2. B1 does not go far enough — "commit hash" appears twice in "Report
structure".** B1 names item 3. The closing paragraph also says it. Verbatim:

> Do NOT paste full diffs. The project is under git — the commit hash and
> `git diff --stat` are enough, and the experimenter can run `git show` for the
> rest. Paste verbatim code only for a specific line under discussion.

Under B8 there is no commit when the report is written, so this sentence is
stale in exactly the way B1 corrects. Proposed: change "the commit hash and
`git diff --stat` are enough" to "`git diff --stat` is enough". Not literally
specified, so I am not doing it without approval.

**D3. B5 creates a fourth irreversible thing, and "What is irreversible" will be
wrong without it.** That section opens "Everything in this project is
reproducible from raw plus config, **except** the following" and lists three. An
append-only record of process transcripts is not reproducible from raw plus
config by any means. Proposed: add `prompt_outputs/` as a fourth bullet. Not
specified, so it waits.

### Assumptions I will proceed on unless you say otherwise

- INDEX.md dates in ISO 8601 from the session date, `2026-08-30`. B5 says the
  slug names the task not the date, which does not conflict — the date lives in
  INDEX.md's date column only.
- INDEX.md lists only `NNN-*` entry files. `README.md` and `INDEX.md` are
  infrastructure, not entries.
- This PHASE A report already uses the B13 format (status first line,
  `--- END OF REPORT ---` last, no box-drawing). Flagging rather than doing it
  silently: the rule is not live yet, but demonstrating it costs nothing.

### Verification

**A1 — CONFIRMED, all three.** `git status --short` → empty.
`git rev-parse --short HEAD` → `aa804d8`.
`.venv\Scripts\python.exe -m pytest -q` → `318 passed in 77.40s (0:01:17)`.

**A2 — CONFIRMED absent, and CONFIRMED not ignored.** `Test-Path prompt_outputs`
→ false. `git check-ignore -v prompt_outputs/README.md` and
`git check-ignore -v prompt_outputs/001-x-phaseA.md` both exit 1 with no output,
meaning no pattern matches. The ignore file's patterns are `__pycache__/`,
`*.pyc`, `.pytest_cache/`, `.venv/`, `venv/`, `.vscode/`, `desktop.ini`,
`data/derived/`, and the four-line `figures/` ladder. None can match a top-level
`prompt_outputs/`. The directory will track with no `.gitignore` change.

**A3 — "## Report structure" verbatim:**

> Order matters, because long reports arrive truncated. Front-load what cannot be
> worked without:
>
> 1. **Blockers and questions needing a decision.**
> 2. **PROPOSED DEVIATIONS.**
> 3. **What changed:** files, line counts, `git diff --stat`, commit hash.
> 4. **Test result:** the summary line, and per-file counts only if they changed.
>    NOT the full dot matrix.
> 5. **Demonstrations:** pre-fix failure output, real-run output.
> 6. **"Matters next."**
>
> Do NOT paste full diffs. The project is under git — the commit hash and
> `git diff --stat` are enough, and the experimenter can run `git show` for the
> rest. Paste verbatim code only for a specific line under discussion.

**A4 — the PHASE A paragraph verbatim:**

> **PHASE A — verification only.** Read files, list directories, run read-only
> commands. Create, edit, move and delete nothing. Install nothing. Check every
> assumption in the request against the actual data and report each as
> CONFIRMED / CONTRADICTED / UNKNOWN with the concrete evidence used — a count, a
> printed line, a min/max. Then list PROPOSED DEVIATIONS: anything the plan needs
> changed. Then stop and wait.

**A5 — settled, and my earlier attribution was wrong.**

`core.autocrlf`, all scopes:

| Scope | Value | Origin |
|---|---|---|
| system | `true` | `file:C:/Users/berke.santos/AppData/Local/Programs/Git/etc/gitconfig` |
| global | unset | — |
| local | unset | — |

`core.eol` is unset. `git check-attr -a RULES.md` returns no attributes; `text`
and `eol` are both `unspecified`. `.gitattributes` contains exactly three
rules — `data/raw/** -text`, `*.png binary`, and a comment block explaining that
`tests/fixtures/inspect_irradiation_sara.txt` is deliberately *not* pinned.
**Nothing in it matches `*.md`.**

So the mechanism is `core.autocrlf=true` from the system gitconfig, not
`.gitattributes`. Detail worth having, because it changes the tense of the
claim: `RULES.md` in the worktree is currently **LF-only** — 5717 bytes, CR=0,
LF=115 — and `git cat-file -s HEAD:RULES.md` is also 5717 bytes, so the stored
blob is LF too. No conversion has happened yet. `autocrlf=true` normalises to LF
on the way in, which for a file I wrote as LF was a no-op; the warning was a
prediction about the next checkout, which has not occurred.

**A6 — no conflict.** Nothing in either file restricts adding a tracked
top-level directory. The nearest thing is CLAUDE.md's "Hard rules": "never add
top-level scripts alongside it" — scoped to executable entry points competing
with `main.py`, not to documentation. `.gitignore`'s header comment ("What is
tracked in this repository, and why") establishes that tracking decisions get
written rationale; `prompt_outputs/README.md` satisfies that in place, and no
`.gitignore` edit is needed since nothing matches. The one real interaction is
D3 above, which is an omission the new rule creates rather than a conflict with
an existing one.

**A7 — CONFIRMED, nothing.** RULES.md has no rule about a phase failing partway.
I read all 115 lines. The closest text is step 3 of "Regenerating the reference
figures" — "STOP and report `git diff --stat` plus the test output. Do not
commit and do not revert" — which is the same instinct but scoped to one
specific artifact, not to phases generally. There is no general rule. B10 is new
ground, and B10's shape matches that existing step 3, which is a point in its
favour.

### What I could NOT check

- **That a future checkout will actually produce CRLF for `RULES.md`.**
  Confirming it requires a fresh clone or checkout, which writes, and PHASE A
  does not write. The mechanism is established from config and attributes; the
  outcome is inferred, not observed.
- **Whether anything outside this repository consumes `RULES.md`** — same class
  of gap as the `__init__.py` re-exports noted in CLAUDE.md. Not checkable from
  here.
- **Whether `318` remains the right number after PHASE B.** Nothing in this task
  touches `tests/`, so it should hold, but I verified the pre-state only.

### Matters next

B9 is a PHASE B item and I will do it properly then, but the read-only part is
already visible: the only text in RULES.md implying a commit at report time is
the two "commit hash" mentions in "Report structure" (D2 covers the second).
"Regenerating the reference figures" steps 3 and 4 already say "do not commit",
which reinforces B8 rather than conflicting with it. I expect B9's finding to be
short.

STOPPING. Awaiting PROCEED.

--- END OF REPORT ---

---

## Disposition

The experimenter replied PROCEED and answered all three decisions:

- **D1 — confirmed as proposed.** Write the PHASE A file during PHASE B,
  verbatim, with a note recording why. "This is the correct handling of a
  bootstrap, not a violation."
- **D2 — approved.** Fixing the named occurrence and leaving the other "would
  have left the file self-contradicting, which is the exact failure this task
  exists to prevent."
- **D3 — approved,** with the wording direction that the fourth bullet must
  distinguish itself from the other three: those are outputs that happen to be
  baselines, this is a record that never had a generating process at all.

All three stated assumptions were accepted. One addition was made — B15,
recording the line-ending mechanism in `RULES.md` so a future reader does not
repeat the wrong attribution. See `001-rules-of-engagement-v2-phaseB.md`.
