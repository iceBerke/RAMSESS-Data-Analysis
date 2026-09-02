# 013 — per-sample-subfolders — PHASE B

Supersedes nothing. Implements **Change 2** from
`prompt_outputs/010-scale-exclusion-and-layout-phaseA.md`, under the
experimenter's decisions recorded there. Change 1 landed at `73daf33`.

Date: 2026-09-02
HEAD: `73daf33`. Nothing was committed.

**This phase moved tracked files.** The evidence it rests on is the OID table in
section 4.

---

## 1. Blockers and decisions needed

**None.** All six steps completed; no stop condition fired. The six reference
overlays are byte-identical, still tracked, and no longer at risk of being
ignored.

---

## 2. PROPOSED DEVIATIONS

**PD1 — I ran `plot --logy` in STEP 5, which was not asked for.** STEP 5 said
"run `plot` and `quantify`". Deleting the orphaned build files in STEP 2 removed
the six `{sample}_overlay_log.png` figures, and
`test_no_log_scaled_figure_occupies_a_reference_filename` **skips** when none is
on disk — so the reference module went from `51 passed` to `50 passed, 1
skipped`. Regenerating them restores that check, which is a live guard against
a log figure landing on a reference filename and is exactly the sort of coverage
this phase should not quietly drop. They are gitignored build output either way.

**PD2 — I deleted 36 orphaned build files, not the 28 entry 010 counted.** The
count moved because entry 012 added eight `_refexcluded` figures after entry 010
measured. All 36 were verified untracked before deletion.

---

## 3. A correction to entry 010's D8

**D8 listed `tests/test_output_filenames.py` as depth-agnostic and needing no
change. That is wrong for one assertion.** Every test in that module reads
filenames off the paths `write_sample_overlays` returns — except
`test_a_baseline_run_never_writes_the_raw_figure`, which reconstructs the path
by hand:

    survivor = (shared / "exp" / "s_overlay.png").read_bytes()

It was the only failure in the first full-suite run of this phase:

    FAILED tests/test_output_filenames.py::test_a_baseline_run_never_writes_the_raw_figure
    E  FileNotFoundError: ...\shared\exp\s_overlay.png
    1 failed, 368 passed in 120.79s

Fixed to `shared / "exp" / "s" / "s_overlay.png"` with a comment saying why it
is the exception. Entry 010 is frozen; this is the correction.

---

## 4. STEP 0 and STEP 2 — the OID table

This is the evidence the phase rests on. Captured with `git rev-parse HEAD:<old>`
before anything moved, and `git rev-parse :<new>` from the index immediately
after `git mv`.

| sample | OID before | OID after | |
|---|---|---|---|
| ech1 | `c21e76a58fa0c1fad2ec8583fbfe8f7b9ff995c2` | `c21e76a58fa0c1fad2ec8583fbfe8f7b9ff995c2` | IDENTICAL |
| ech2 | `2a24c48ef69b54472f1307394cc17b8e5602fb28` | `2a24c48ef69b54472f1307394cc17b8e5602fb28` | IDENTICAL |
| ech3 | `64e542a37a7b2555e5c91d660c868aed9cddb494` | `64e542a37a7b2555e5c91d660c868aed9cddb494` | IDENTICAL |
| ech4 | `7380469c0ce5d32914351f60e0f7054d14f68694` | `7380469c0ce5d32914351f60e0f7054d14f68694` | IDENTICAL |
| ech5 | `72d5f430a549b8558009fcd4ff6c6771a05dedcf` | `72d5f430a549b8558009fcd4ff6c6771a05dedcf` | IDENTICAL |
| ech6 | `127fdd7827f143035fce08d29df7ebffc49924fa` | `127fdd7827f143035fce08d29df7ebffc49924fa` | IDENTICAL |

All six unchanged. A blob OID is the hash of the content, so identical OID *is*
identical bytes — nothing rewrote a file. These are also the same six OIDs entry
010's D11 recorded, so they have not drifted since that phase measured them.

`git status` records all six as renames, not as delete-plus-add:

    R  figures/irradiation_sara/ech1_overlay.png -> figures/irradiation_sara/ech1/ech1_overlay.png
    R  figures/irradiation_sara/ech2_overlay.png -> figures/irradiation_sara/ech2/ech2_overlay.png
    R  figures/irradiation_sara/ech3_overlay.png -> figures/irradiation_sara/ech3/ech3_overlay.png
    R  figures/irradiation_sara/ech4_overlay.png -> figures/irradiation_sara/ech4/ech4_overlay.png
    R  figures/irradiation_sara/ech5_overlay.png -> figures/irradiation_sara/ech5/ech5_overlay.png
    R  figures/irradiation_sara/ech6_overlay.png -> figures/irradiation_sara/ech6/ech6_overlay.png

**STEP 0's other checks.** Suite `369 passed in 120.78s`. HEAD `73daf33`,
working tree clean. `git diff 583414a..HEAD -- .gitignore` is empty, so the
`figures/` rules had not drifted since entry 010 measured them.

---

## 5. STEP 1 — the ignore rules, applied and proved before the move

The rules were changed **first**, and proved at the new depth **before**
anything moved, so nothing was ever placed on top of untested rules.

The replacement, appended to the existing level-by-level construction:

    figures/*
    !figures/*/
    figures/*/*
    !figures/*/*/
    figures/*/*/*
    !figures/*/*/*_overlay.png

with a comment recording why it is three levels and what went wrong at two.

**A methodological note that mattered.** My first check used
`git check-ignore -v` and read its exit code as "is ignored". It is not:
`check-ignore` exits 0 when **any rule matched, including a negation**, so a
correctly-exempted file also exits 0. Read that way the first probe appeared to
say the reference path was ignored, which would have been a stop condition. The
`-v` output shows which rule won — `!figures/*/*/*_overlay.png`, a negation, so
not excluded. Re-run with plain `git check-ignore -q`, where exit 0 genuinely
means excluded:

    figures/irradiation_sara/ech2/ech2_overlay.png            NOT excluded  <-- tracked-able
    figures/irradiation_sara/ech2/ech2_overlay_log.png        EXCLUDED
    figures/irradiation_sara/ech2/ech2_overlay_baseline.png   EXCLUDED
    figures/irradiation_sara/ech2/ech2_bands.png              EXCLUDED
    figures/irradiation_sara/ech2/ech2_low_baseline_check.png EXCLUDED
    figures/irradiation_sara/ech2/ech2_overlay_annotated.png  EXCLUDED
    figures/irradiation_sara/bands_all_samples.png            EXCLUDED
    figures/irradiation_sara/ech2_overlay.png                 EXCLUDED

All three STEP 1 requirements met: the new reference path is exempt, new build
paths are ignored, and the experiment-level `bands_all_samples.png` stays
ignored. The last line is a bonus check — the *old* two-level reference path is
now excluded, which is right, because nothing should live there any more.

Confirmed against the real tree afterwards: `git ls-files -s figures/` lists
exactly the six overlays, and `git status --porcelain --ignored figures/` marks
`bands_all_samples.png` and all twelve per-sample build figures `!!`.

---

## 6. STEP 2 — the orphaned build files

36 files sat at the old experiment level after the move. Every one was verified
untracked before deletion — a loop over `git ls-files --error-unmatch` produced
no output — and all 36 were deleted deliberately. They are build output and were
regenerated in STEP 5.

The count is 36 rather than entry 010's 28 because entry 012 added eight
`_refexcluded` figures in between (PD2).

---

## 7. STEP 3 — the code

**3a. `write_sample_overlays`.** The experiment directory is now computed once
and the sample directory inside the loop:

    experiment_directory = figures_root / experiment
    ...
    for name in wanted:
        group = by_sample[name]
        # One directory per sample. Every figure this function writes belongs to
        # exactly one sample, including the per-window diagnostic, so all of them
        # go inside it.
        output_directory = experiment_directory / name

The three write sites are unchanged below that; the diagnostic figure moves with
its sample because it uses the same `output_directory`.

**3b. `quantify_experiment`.** The per-sample trend figure moves in; the
all-samples figure stays a level up, with the reason recorded:

    experiment_directory = guard_not_under_raw(figures_root / experiment, raw_root)
    for name in sorted({str(r["sample"]) for r in rows}):
        path = plot_sample_band_trends(
            rows, name, reference,
            guard_not_under_raw(
                experiment_directory / name / f"{name}_bands.png", raw_root
            ),
            MIN_SIGNAL_TO_NOISE,
        )
        print(f"wrote {path}")
    # The one figure with no sample to live under: it overlays every sample at
    # once, so it belongs to the experiment rather than to any one of them and
    # stays a level up. The tree is mixed-depth on purpose.

**3c. `_save` needed no change — verified, not assumed.** It reads:

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=DPI, bbox_inches="tight")

and was exercised three levels into a directory that did not exist:

    target parent exists beforehand: False
    written: True  size 7552

**3d. `guard_not_under_raw`.** Satisfied by construction: it raises only when the
resolved path is `raw_root` or has it among its parents, and
`figures/<experiment>/<sample>/` is not under `data/raw/` at any depth. The
guard's three figure call sites in `quantify_experiment` were updated to wrap
the new paths and still pass.

**The `plot` write sites still lack the guard**, exactly as entry 010's D8
found: `guard_not_under_raw` appears seven times in `report.py`, none of them in
`write_sample_overlays`. **Not added here**, per the instruction — it is
pre-existing and independent, and closing it is its own change.

---

## 8. STEP 4 — the tests

**`tests/test_raw_plot_reference.py`** — two path constructions:

- `reference_png()` now returns `FIGURES_DIR / sample / f"{sample}_overlay.png"`,
  with a docstring line saying why;
- the log-figure guard's two references become
  `FIGURES_DIR / sample / f"{sample}_overlay_log.png"`.

`FIGURES_DIR` itself is unchanged — it is still the experiment directory.

**`tests/test_quantify_experiment.py`** — five assertions:

- the figure-set check now uses `rglob("*.png")` rather than `iterdir()`, with a
  comment that the tree is one-per-sample plus one a level up;
- the loop over written figures likewise;
- the stdout assertion becomes `figures / name / f'{name}_bands.png'`;
- `"sa_bands.png"` becomes `"sa" / "sa_bands.png"` in two places;
- the `--sample` filter test gained two positive assertions pinning *where* each
  figure landed, not just that the names are right.

**`tests/test_band_trend_figures.py`** — one: the per-sample target gains
`/ sample`. The `bands_all_samples.png` target is deliberately left at the
experiment level.

**`tests/test_annotate_cli.py`** — one: its `figures()` helper globs recursively.

**`tests/test_output_filenames.py`** — one, the correction in section 3.

### The verification

    tests/test_raw_plot_reference.py:  50 passed, 1 skipped in 7.54s

The pixel comparison passes against the moved files. **STEP 4's stop condition
did not fire.** The single skip was
`test_no_log_scaled_figure_occupies_a_reference_filename`, skipping because the
log figures had just been deleted — which is what PD1 addresses. After STEP 5
regenerated them the module runs 51 passed with no skip.

---

## 9. STEP 5 — the real run

`plot`, `plot --logy` and `quantify`, whole experiment. The resulting tree:

    figures/irradiation_sara/bands_all_samples.png
    figures/irradiation_sara/ech1/ech1_bands.png
    figures/irradiation_sara/ech1/ech1_overlay.png
    figures/irradiation_sara/ech1/ech1_overlay_log.png
    figures/irradiation_sara/ech2/ech2_bands.png
    figures/irradiation_sara/ech2/ech2_overlay.png
    figures/irradiation_sara/ech2/ech2_overlay_log.png
    ... the same three for ech3, ech4, ech5, ech6

Nineteen files: six samples × three, plus the one experiment-level figure. The
mixed depth is visible and is the decision.

**`git status --short figures/` shows the six renames and nothing else.** No
figure shows as modified — which is a second, independent confirmation of the
OID table, because `plot` had just rewritten all six overlays from scratch and
git sees the bytes as unchanged.

---

## 10. STEP 6 — full suite

    369 passed in 118.47s (0:01:58)

**Zero warnings.** Same count as before the phase: no test was added or removed,
eleven assertions across six modules were repointed.

**`tests/fixtures/inspect_irradiation_sara.txt` is unaffected.**
`git status --short tests/fixtures/` is empty and `tests/test_cli_output.py`
passes on its own (15 passed). The reason is structural: that fixture captures
`inspect` output, and `inspect` writes no figures and prints no figure paths —
it inventories the `.txt` spectra and prints groups and warnings. Nothing in it
can see the figure tree. No fixture was regenerated.

---

## 11. Everything measured, with the numbers

| what | result |
|---|---|
| suite before | 369 passed in 120.78s |
| suite after | **369 passed in 118.47s, 0 warnings** |
| HEAD | `73daf33`, clean at start |
| six blob OIDs, before vs after | **all six IDENTICAL** |
| `git status figures/` | six renames, zero modifications |
| `.gitignore` drift since entry 010 | none |
| new ignore rules | 6 patterns, 3 levels; all three STEP 1 checks pass |
| `check-ignore -v` exit code | 0 on a matched **negation** too — not a "is ignored" test |
| orphaned build files deleted | 36 (entry 010 counted 28; entry 012 added 8) |
| tracked files under `figures/` | 6, all exempt from the new rules |
| ignored files under `figures/` | 13 after the real run |
| `_save` at three levels into a missing tree | writes, 7552 bytes |
| `guard_not_under_raw` sites in `report.py` | 7, still none in `write_sample_overlays` |
| test assertions repointed | 11, across 6 modules |
| `test_raw_plot_reference.py` after the move | 50 passed, 1 skipped → 51 passed once log figures regenerated |
| figures after the real run | 19: 6 samples × 3, plus `bands_all_samples.png` |
| golden fixture | unaffected; `test_cli_output.py` 15 passed |

---

## 12. Self-corrections during this phase

**Two.**

1. **I misread `git check-ignore -v`'s exit code** as "is this ignored", when it
   means "did any rule match" — a negation matches too. Read that way the first
   STEP 1 probe appeared to fail. Re-run with plain `git check-ignore -q`, which
   is unambiguous. Section 5 records both, because the wrong reading would have
   triggered a false stop.
2. **Entry 010's D8 said `test_output_filenames.py` needed no change.** One
   assertion in it reconstructs a figure path by hand and did need changing;
   it was the only failure in the first full-suite run. Section 3.

Neither changed the outcome, and both are recorded because a later reader
repeating this work would hit the same two things.

---

## 13. Files touched by this phase

Modified: `.gitignore`, `src/ramsess/report.py`,
`tests/test_raw_plot_reference.py`, `tests/test_quantify_experiment.py`,
`tests/test_band_trend_figures.py`, `tests/test_annotate_cli.py`,
`tests/test_output_filenames.py`.
Moved: the six `figures/irradiation_sara/{sample}_overlay.png` reference
overlays, into per-sample directories, bytes unchanged.
Deleted: 36 orphaned gitignored build figures.
Added: this file, one `INDEX.md` line.
Regenerated: 19 figures under `figures/irradiation_sara/`.

**Not touched:** `data/raw/`, `main.py`, `src/ramsess/plotting.py`,
`src/ramsess/analysis.py`, `src/ramsess/bands.py`, `src/ramsess/io.py`,
`CLAUDE.md`, `tests/fixtures/`, and the `plot` path's missing write guard.

**The `.gitignore` change and the `git mv` are both in the working tree and must
go in one commit**, per the decision and entry 010's D-A: a commit with the
files moved but the rules unchanged leaves the reference overlays
tracked-but-ignored, which is the state entry 010 proved is unrecoverable by
`git add`.

Nothing was committed. PHASE B ends here.
