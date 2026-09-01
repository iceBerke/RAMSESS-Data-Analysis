# Index of prompt outputs

**The convention this directory follows is defined in `RULES.md`, under "Saving
prompt outputs".** That section is the authority; this file only lists what is
here.

One line per entry, in order. Number, slug, phases present, date, and what the
task did or found. Read-only work is listed too: an audit that found nothing is
a result, and the record should show it was run.

Append a line for every new entry. Never rewrite an existing one — if a task is
re-run, the new entry says which number it supersedes.

| NNN | Slug | Phases | Date | What it did or found |
|-----|------|--------|------|----------------------|
| 001 | rules-of-engagement-v2 | A, B | 2026-08-30 | Introduced this directory and its conventions; added the prompt-output, commit-gate and phase-failure sections to `RULES.md`, moved the commit out of PHASE B, and corrected a wrong attribution of line-ending conversion to `.gitattributes` — the mechanism is `core.autocrlf=true` at system scope. |
| 002 | record-gap-audit | audit | 2026-09-01 | Found that 001's PHASE B file was a subset of its chat report, missing the deviation disclosure, the commit-message validation and "matters next"; reproduced all three verbatim rather than amending 001, which the append-only boundary forbids. Also records that `prompt_outputs/README.md` was created and deleted in one session, leaving no trace in git. |
| 003 | rules-corrections | B | 2026-09-01 | Applied six corrections to `RULES.md`: the stale `git show` reference, the append-only boundary, the `Record:` line linking a commit to its entry, the file-is-a-superset-of-chat requirement, the ban on proposing a commit message inside a PHASE B report, and the deletion of `README.md`. Written as its own entry because 001 was frozen and 002 is read-only. Then extended by C7, allowing one `Record:` line per entry when a single commit covers several. |
