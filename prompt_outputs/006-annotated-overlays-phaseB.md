# 006 — annotated-overlays — PHASE B

Supersedes nothing. Implements the design scoped in
`prompt_outputs/005-annotated-overlays-phaseA.md`, under the experimenter's
answers to that entry's D1 and D2.

Date: 2026-09-01
HEAD at time of writing: `42557f4`
Phase completed. Nothing committed; PHASE B ends before the commit.

---

## 1. Blockers and decisions needed

**None.** Every step completed. STEP 0's stop conditions did not fire, STEP 5's
stop condition did not fire, and the suite is green.

---

## 2. PROPOSED DEVIATIONS

Three things were done that the request did not spell out. None changes the
specified behaviour; all three are disclosed here because they were judgement
calls made inside the specified scope, and a later reader should not have to
infer them from the diff.

**PD1 — the STEP 4d test went into a new module, `tests/test_annotate_cli.py`
(91 lines).** The request said "synthetic experiment in `tmp_path`, as the suite
does" but did not name a module, and no existing module fits. `test_cli_output.py`
states in its own docstring that it "only ever runs `inspect`, which writes
nothing, so `figures/` is never touched", and reaches `main.py` by subprocess,
which cannot have its roots redirected; putting a `plot` test there would
contradict a stated contract. `test_output_filenames.py` is about filename
collisions, not error paths. `test_plotting.py` is about figure construction,
not the CLI. The new module has one responsibility — the `--annotate` gate in
`main.py` — which is what `CLAUDE.md` asks of a module. **If the experimenter
would rather it lived elsewhere, moving it is a one-file change.**

**PD2 — `_annotate_band_centres` raises `ValueError` when the label rows would
fill the whole panel.** The top-limit extension solves
`new_range = old_range / (1 - reserved/panel_height)`, which is undefined at
`reserved >= panel_height` and negative beyond it. Some behaviour had to be
chosen for that case. The alternative — clamping — would silently produce a
figure whose labels sit on top of the data while claiming to be annotated, and
`CLAUDE.md` says to fail loudly and never substitute a default. The message
names the window, both pixel counts, the band count and the row count.
Unreachable on this dataset: the worst panel here uses 2 rows out of a possible
~5. **No new constant was introduced for it**, which is why it is a raise rather
than a threshold.

**PD3 — `BandSpec` is imported into `plotting.py` under `if TYPE_CHECKING:`,
not at runtime.** The request said to use the actual type `load_bands_config`
returns, and that type lives in `report.py`. A runtime import would make
`import ramsess.plotting` pull `report.py` in, which works but undoes half the
point of `report.py` importing `plotting` lazily — that lazy import exists so the
`inspect` path never has the process backend fixed on its behalf.
`from __future__ import annotations` is already at the top of `plotting.py`, so
the annotation is a string and the guarded import costs nothing at runtime. The
type in the signature is exactly `dict[str, BandSpec] | None`; nothing was
reshaped, and no new type was invented.

---

## 3. Self-correction against entry 005

**Entry 005's B3 said "six" literal 3-tuple indices across four tests. There are
seven.** Counted in the file while making the change:

    all_runs[(False, False, False)]      test_log_and_linear_overlays_are_separate_files
    all_runs[(False, False, True)]       same test
    all_runs[(True, False, False)]       test_log_and_linear_baseline_overlays_are_separate_files
    all_runs[(True, False, True)]        same test
    producers == [(False, False, False)] test_the_raw_filename_is_produced_only_by_the_raw_combination
    all_runs[(False, True, False)]       test_logy_is_a_no_op_for_the_diagnostic_figure
    all_runs[(False, True, True)]        same test

2 + 2 + 1 + 2 = 7. The count of *tests* affected (four) was right; the count of
*literals* was one low. All seven were updated. Entry 005 is frozen and is not
amended; this is the correction, per `RULES.md`'s append-only boundary.

Nothing else in entry 005 was contradicted by the build. Its four structural
findings were re-checked at STEP 0 and all held.

---

## 4. STEP 0 — the re-check, before anything was touched

**0a. Full suite, before any edit:**

    318 passed in 68.28s (0:01:08)

`tests/test_raw_plot_reference.py` on its own:

    51 passed in 7.78s

So the premise entry 005 could not verify — that the six reference overlays are
byte-correct now — **holds**. Nothing was regenerated.

Also recorded for STEP 4a's before/after: `tests/test_output_filenames.py` alone
was `9 passed in 16.34s`.

**0b.** HEAD `42557f4` (`42557f49509387cde68c9ae50b31b3e1092f81ab`). Working tree
clean apart from entries 004 and 005 and their `INDEX.md` lines, all written
earlier in this session and already reported.

**0c. The four structural findings, re-read from the current source:**

    def build_sample_overlay(
        spectra: list[Spectrum],
        logy: bool = False,
        baseline_params: dict[str, dict[str, float | int]] | None = None,
    ) -> plt.Figure:
    ...
        return figure

    scale_suffix = LOG_SCALE_SUFFIX if logy else ""

    COMBINATIONS = list(itertools.product([False, True], repeat=3))  # baseline, diagnostic, logy

    def load_bands_config(
        experiment_folder: Path, window_ranges: Mapping[str, tuple[float, float]]
    ) -> tuple[str, dict[str, BandSpec], dict[str, tuple[float, float]]]:

All four unchanged. Proceeded.

---

## 5. What changed

    main.py                        |  24 +++++
    src/ramsess/plotting.py        | 199 ++++++++++++++++++++++++++++++++++++++++-
    src/ramsess/report.py          |  41 +++++++--
    tests/test_output_filenames.py | 129 +++++++++++++++++++++-----

plus `tests/test_annotate_cli.py`, new, 91 lines, untracked.
(`prompt_outputs/INDEX.md` also shows in the diff; that is entries 004 and 005
from earlier in this session, plus this entry's line.)

### `plotting.py`

New module-level constants, each with a one-line comment, beside the existing
`FIGURE_SIZE` and `LINE_WIDTH`: `ANNOTATION_FONT_SIZE` (8),
`ANNOTATION_RULE_WIDTH` (0.6), `ANNOTATION_RULE_ALPHA` (0.45),
`ANNOTATION_COLOR` ("0.35"), `ANNOTATION_ZORDER` (0.5), `ANNOTATION_ROW_GAP`
(0.35), `ANNOTATION_TOP_PAD` (0.35), `ANNOTATION_MIN_CLEARANCE` (1.15).

The last three are **dimensionless multipliers of measured quantities**, not
distances: the two gaps multiply the label line height as the renderer reports
it, and the clearance multiplies the two labels' measured half-extents. No
number of cm-1 and no number of points appears anywhere in the placement.

New private helper `_annotate_band_centres(figure, panel, window, bands, logy)`,
returning the band names placed as one list per row. It:

- selects only bands whose `spec.window` equals the panel's window label, sorted
  by centre;
- measures each label by drawing a probe `Text` with exactly the parameters the
  real label will use, reading `get_window_extent(renderer=...)`, and removing
  the probe — so both the horizontal footprint (the line height, since the label
  is rotated upright) and the vertical footprint (the name's length) come from
  the renderer;
- assigns rows top-down: a label goes in the topmost row where it clears that
  row's rightmost label by `ANNOTATION_MIN_CLEARANCE * (last_half + this_half)`
  in display pixels, and opens a new row when no row has space;
- computes `reserved = ANNOTATION_TOP_PAD * line_height + sum(row_heights) +
  gap * len(rows)` and raises if that reaches the panel's pixel height (PD2);
- draws one `axvline` per band at its configured centre, at
  `ANNOTATION_ZORDER = 0.5`, below the data traces whose default zorder is 2;
- raises the top limit so the reserved band is empty —
  `bottom + (top - bottom) / (1 - fraction)` on a linear axis, the same in
  log10 space on a log one — **leaving `bottom` untouched**, which is what keeps
  a corrected panel's negative floor where it is;
- places the labels in a blended transform, x in data units so each tracks its
  centre, y in axes fractions so each tracks the top of the panel.

`build_sample_overlay` gains `bands: dict[str, BandSpec] | None = None` and one
gated call at the end of the per-panel loop, after the existing negative-clamp
and after the legend:

    # Last, so the labels are measured against the panel's final limits and
    # the reserved band is added on top of the clamp above, not before it.
    if bands is not None:
        _annotate_band_centres(figure, panel, window, bands, logy)

`plot_sample_overlay` passes `bands` straight through.

**No band centre, band name, sample name or wavenumber from this dataset was
added.** Verified by grepping the finished module for `ech[0-9]`, `glycine`,
`silicon`, `si_5`, `522`, `893`, `979`, `1328`, `1412`, `2975`, `3012`, `3146`.
One hit, and it is the pre-existing `ech6` comment entry 005 B9 already
recorded:

    475:            # whose baseline sits well above it - ech6's low window spans

### `report.py`

New constant beside `LOG_SCALE_SUFFIX`:

    # Appended to the figures carrying band labels, before the scale suffix, so an
    # annotated run cannot land on an unannotated run's filename. The diagnostic
    # figure is never annotated, so it carries no suffix here either.
    ANNOTATED_SUFFIX = "_annotated"

`write_sample_overlays` gains `annotate: bool = False` and
`bands: dict[str, BandSpec] | None = None`, rejects `annotate` without `bands`
in the same style as the existing baseline check, and composes both suffixes at
the one place the existing comment designates. That comment was extended to say
so:

    # ... Two flags need encoding: `logy` and `annotate`, both of
    # which change the two overlay figures. The diagnostic figure takes neither,
    # so it carries no suffix at all. The content flag goes before the scale
    # suffix, keeping `_log` last as it already was. ...
    scale_suffix = LOG_SCALE_SUFFIX if logy else ""
    annotated_suffix = ANNOTATED_SUFFIX if annotate else ""
    # An annotated run replaces the unannotated figure rather than joining it,
    # so the six reference overlays can only ever come from a run with neither
    # flag set.
    overlay_bands = bands if annotate else None

The two overlay write sites became
`f"{name}_overlay{annotated_suffix}{scale_suffix}.png"` and
`f"{name}_overlay_baseline{annotated_suffix}{scale_suffix}.png"`. The diagnostic
write site is untouched, so it takes neither suffix.

### `main.py`

One `add_argument` in the shape of the existing flags:

    plot.add_argument(
        "--annotate",
        action="store_true",
        help="label each panel with the bands configured in bands.json",
    )

and the gated load, before the `write_sample_overlays` call:

    # Only --annotate reads bands.json. Plain plot touches no configuration file
    # at all and must keep working in an experiment that has none.
    bands = None
    if args.annotate:
        try:
            _, bands, _ = load_bands_config(
                RAW_ROOT / args.experiment, common_window_ranges(spectra)
            )
        except FileNotFoundError as exc:
            print(f"error: --annotate needs a band configuration: {exc}", file=sys.stderr)
            return 1
        except (ValueError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

`common_window_ranges` and `load_bands_config` were added to the existing
`ramsess.report` import block.

### The eight output paths `plot` can now produce

| combination | overlay path |
|---|---|
| — | `{sample}_overlay.png` |
| `--logy` | `{sample}_overlay_log.png` |
| `--annotate` | `{sample}_overlay_annotated.png` |
| `--annotate --logy` | `{sample}_overlay_annotated_log.png` |
| `--baseline` | `{sample}_overlay_baseline.png` |
| `--baseline --logy` | `{sample}_overlay_baseline_log.png` |
| `--baseline --annotate` | `{sample}_overlay_baseline_annotated.png` |
| `--baseline --annotate --logy` | `{sample}_overlay_baseline_annotated_log.png` |

`{sample}_{window}_baseline_check.png` remains the diagnostic path and takes
neither suffix.

---

## 6. Test result

**Full suite after the change: `327 passed in 80.15s (0:01:20)`. Zero
warnings** — pytest printed no warnings summary, and a second confirming run gave
`327 passed in 79.82s`.

Before the change it was 318. The nine new tests are six in
`test_output_filenames.py` (four of them one parametrised test) and three in
`test_annotate_cli.py`.

**Per-module counts that changed:**

| module | before | after |
|---|---|---|
| `tests/test_output_filenames.py` | 9 passed in 16.34s | 15 passed in 30.25s |
| `tests/test_annotate_cli.py` | — | 3 passed in 2.18s |
| `tests/test_raw_plot_reference.py` | 51 passed in 7.78s | unchanged, untouched |

**STEP 4a's runtime question:** the filenames module went from 16.34s to 30.25s,
a factor of 1.85 for a factor of 2 in rendered combinations. That is the honest
cost of the fourth boolean and it lands where entry 005 predicted, in the
`all_runs` fixture.

### The new tests

**4a** — `COMBINATIONS` is now
`list(itertools.product([False, True], repeat=4))` with the flag order in a
comment above it; `run()` takes `annotate` and passes `bands=BANDS if annotate
else None`; the `all_runs` comprehension keys and `out_` directory names carry
four digits; `test_a_baseline_run_never_writes_the_raw_figure` unpacks four and
skips the all-false case; all seven literal tuples are 4-tuples. The module
gained a `BANDS` fixture of five `BandSpec`s — the real type — two of them
placed close enough together to exercise the row-stacking path rather than only
the easy case.

**4b** — `test_annotating_changes_the_figure_and_its_name`, parametrised over
all four overlay flag pairs. It asserts both halves: the annotated run writes
exactly the annotated name, and its bytes differ from the unannotated run's.
The second half is the one that matters — a rename with no drawing would pass
every other test in the module.

**4c** — `test_an_annotated_run_never_writes_an_unannotated_overlay`, over all
sixteen combinations: any run carrying `--annotate` must produce none of the
four unannotated overlay names.

Also added, because it is the same guarantee from the other side:
`test_annotation_does_not_reach_the_diagnostic_figure`, asserting the check
figures are byte-identical with and without `--annotate`.

**4d** — `tests/test_annotate_cli.py`, three tests against `main.main()` with
`main.RAW_ROOT` and `main.FIGURES_ROOT` monkeypatched to `tmp_path`: plain
`plot` still succeeds and writes `s_overlay.png` in an experiment with no
`bands.json`; `--annotate` there exits 1, names both `--annotate` and the full
expected path on stderr, and leaves no `figures/` tree at all; and `--annotate`
with a valid `bands.json` writes `s_overlay_annotated.png` and nothing else.
The first of those is STEP 3's explicit "verify that" requirement.

---

## 7. STEP 4e — the demonstration that 4b guards what it claims

`_annotate_band_centres` was temporarily made a no-op by inserting a single
line immediately after its docstring:

    return []  # TEMPORARY no-op for STEP 4e; reverted immediately after.

With the call still in place and the filenames still changing, the annotation
draws nothing. Running 4b against it — actual output, tail:

    >       assert annotated[annotated_name] != plain[plain_name], (
                f"{annotated_name} holds the same pixels as {plain_name}: --annotate "
                f"changed the filename but drew no labels"
            )
    E       AssertionError: s_overlay_baseline_annotated_log.png holds the same pixels as s_overlay_baseline_log.png: --annotate changed the filename but drew no labels
    E       assert b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x08\xa1\x00\x00\x04;\x08\x06\x00\x00\x00] /\xc5\x00\x00\x00:tEXtSoftware...0\x00\x80\xba\tB\x01\x00\x00\x00\x00\x00\x00\x00 \xd5\xeb\xff\x01\x1e\x8e0\xf1O\x8c\xd0Q\x00\x00\x00\x00IEND\xaeB`\x82' != b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x08\xa1\x00\x00\x04;\x08\x06\x00\x00\x00] /\xc5\x00\x00\x00:tEXtSoftware...0\x00\x80\xba\tB\x01\x00\x00\x00\x00\x00\x00\x00 \xd5\xeb\xff\x01\x1e\x8e0\xf1O\x8c\xd0Q\x00\x00\x00\x00IEND\xaeB`\x82'

    tests\test_output_filenames.py:230: AssertionError
    =========================== short test summary info ===========================
    FAILED tests/test_output_filenames.py::test_annotating_changes_the_figure_and_its_name[False-False-s_overlay.png-s_overlay_annotated.png]
    FAILED tests/test_output_filenames.py::test_annotating_changes_the_figure_and_its_name[False-True-s_overlay_log.png-s_overlay_annotated_log.png]
    FAILED tests/test_output_filenames.py::test_annotating_changes_the_figure_and_its_name[True-False-s_overlay_baseline.png-s_overlay_baseline_annotated.png]
    FAILED tests/test_output_filenames.py::test_annotating_changes_the_figure_and_its_name[True-True-s_overlay_baseline_log.png-s_overlay_baseline_annotated_log.png]
    4 failed, 11 deselected in 15.85s

**All four parametrised cases failed**, each with the intended message. Note
that every *other* test in the module still passed under the no-op — including
every filename test — which is precisely why 4b was needed.

The line was then removed. Confirmed clean by grepping the module for
`TEMPORARY` (no hits) and re-running:

    15 passed in 30.57s

---

## 8. STEP 5 — the real run

Eight invocations, all successful. Paths written:

    figures\irradiation_sara\ech2_overlay_annotated.png                    175878 bytes
    figures\irradiation_sara\ech2_overlay_annotated_log.png                247247
    figures\irradiation_sara\ech2_overlay_baseline_annotated.png           170359
    figures\irradiation_sara\ech2_overlay_baseline_annotated_log.png       247475
    figures\irradiation_sara\ech4_overlay_annotated.png                    286640
    figures\irradiation_sara\ech4_overlay_annotated_log.png                358972
    figures\irradiation_sara\ech4_overlay_baseline_annotated.png           211913
    figures\irradiation_sara\ech4_overlay_baseline_annotated_log.png       282970

The four `--baseline` runs printed the resolved parameters as they always do —
low `lam` 1e6, high `lam` 1e8 from `windows.high`, `p` 0.01, `n_iter` 10, every
one sourced from `baseline.json`, none from a built-in default.

**The six reference overlays are UNMODIFIED:**

    $ git status --short figures/
    (no output)

STEP 5's stop condition did not fire.

### Layout, measured from the rendered figures

Each figure was rebuilt in memory exactly as the CLI built it, drawn, and
measured through the renderer. Results are identical across all four flag
combinations for a given sample, and identical between ech2 and ech4, because
label placement now depends only on the configured centres, the panel geometry
and the font — not on the data. **That is D1's answer working as intended.**

**Low panel — 5 labels in 1 row:**

    row 0: si_522, glycine_893, glycine_979, glycine_1328, glycine_1412

**High panel — 3 labels in 2 rows:**

    row 0: glycine_2975, glycine_3146
    row 1: glycine_3012

**The pair pushed to a second row is `glycine_2975` → `glycine_3012`** — entry
005 B8's worst case, 37 cm-1 apart, 7.3 pt on the drawn figure. `glycine_3146`
then fits back into row 0, because it clears `glycine_2975` by 33.8 pt. So the
mechanism does the non-trivial thing: it drops one label and returns to the top
row for the next, rather than cascading everything downward.

The low window needs only one row because rotating the labels changes the
relevant extent from the string width (48–53 pt) to the line height (~10 pt).
Entry 005 B8's two low-window collisions — `glycine_893`/`glycine_979` at 17.0
pt and `glycine_1328`/`glycine_1412` at 16.6 pt — both clear the ~11.5 pt a
rotated pair needs.

**No label overlaps another**, in any panel, in any of the eight figures —
checked by pairwise `Bbox.overlaps` on every label pair.

**No label overlaps a trace.** Clearance between the lowest label's bottom edge
and the tallest drawn data point, in display pixels:

| figure | low panel | high panel |
|---|---|---|
| ech2 plain | +20.2 | +16.1 |
| ech2 logy | +19.7 | +16.2 |
| ech2 baseline | +20.5 | +17.0 |
| ech2 baseline+logy | +19.7 | +16.1 |
| ech4 plain | +19.7 | +16.1 |
| ech4 logy | +19.7 | +16.2 |
| ech4 baseline | +20.6 | +17.0 |
| ech4 baseline+logy | +19.7 | +16.1 |

All positive, so the reserved band is doing its job on both scales and on both
raw and corrected data.

### The legends — reported, not fixed

Entry 005 B1 flagged that the per-panel legends use `loc="best"`, so adding
artists can move them. **They do move.** In seven of the eight figures they
settle at axes-fraction y≈0.57, inside the reserved label band, at x≈0.78 (low)
and x≈0.69 (high), overlapping nothing.

**In one figure they collide.** `ech4 --annotate --baseline --logy`, low panel:
the legend lands at x=0.01, y=0.57 and **overlaps the `si_522` label**. It is
the only overlap of any kind across all eight figures and all sixteen panels.

Confirmed that annotation is what moved it, by building the same sample and
flags with and without:

    unannotated  low   legend axes-fraction x=0.40 y=0.02
    unannotated  high  legend axes-fraction x=0.35 y=0.02
    annotated    low   legend axes-fraction x=0.01 y=0.57
    annotated    high  legend axes-fraction x=0.69 y=0.57

The cause is that matplotlib's "best" placement scores candidate positions
against the *data*, and `Text` artists are not data. The reserved band at the
top of the panel is empty of data by construction, so it reads to matplotlib as
the emptiest region on the figure and the legend moves into it — exactly where
the labels are.

**Not fixed, as instructed.** It is one panel of sixteen, and the fix is a
design decision — pin the legend, exclude the reserved band from its search, or
leave it — that belongs to the experimenter.

---

## 9. Everything measured or validated, with the numbers

| what | result |
|---|---|
| suite before any edit | 318 passed in 68.28s |
| `test_raw_plot_reference.py` before, alone | 51 passed in 7.78s |
| `test_output_filenames.py` before | 9 passed in 16.34s |
| `test_output_filenames.py` after | 15 passed in 30.25s (×1.85 for ×2 combinations) |
| `test_annotate_cli.py` | 3 passed in 2.18s |
| suite after | 327 passed in 80.15s, 0 warnings (confirmed 79.82s on a second run) |
| net new tests | +9 |
| 4e: 4b against a no-op annotation | 4 failed, 11 deselected in 15.85s |
| 4e: other tests in the module under the no-op | all passed — which is why 4b exists |
| 4e: after revert | 15 passed in 30.57s; grep for `TEMPORARY` finds nothing |
| literal 3-tuples in the filenames module | 7, not 6 as entry 005 said |
| combinations rendered | 8 → 16 |
| overlay output paths | 4 → 8 |
| annotated figures written | 8, sizes 170,359–358,972 bytes |
| `git status --short figures/` after the real run | empty |
| low panel layout | 5 labels, 1 row, every flag combination, both samples |
| high panel layout | 3 labels, 2 rows, every flag combination, both samples |
| label pushed to row 1 | `glycine_3012`, behind `glycine_2975` (7.3 pt apart) |
| `glycine_3146` | returns to row 0, clearing `glycine_2975` by 33.8 pt |
| label-label overlaps | 0, across 8 figures / 16 panels |
| label-trace clearance | +16.1 to +20.6 px, always positive |
| legend/label overlaps | 1 of 16 panels: ech4 baseline+logy, low, `si_522` |
| legend movement caused by annotation | y 0.02 → 0.57; low-panel x 0.40 → 0.01 |
| new dataset literals in `plotting.py` | 0 (the one hit is the pre-existing `ech6` comment) |
| ylim bottom changed by annotation | never — verified 0.0 and 1683.86 both preserved |
| xlim changed by annotation | never — `axvline` does not autoscale inside current bounds |

---

## 10. Matters next

- **The `ech4 --annotate --baseline --logy` legend/label collision** is the one
  cosmetic defect in the output. It needs a decision, not a patch made on my
  own judgement: pin the legend location, tell `loc="best"` to avoid the
  reserved band, or accept it.
- **PD1 is reversible cheaply.** If `tests/test_annotate_cli.py` should live
  elsewhere, say where.
- **The reserved band costs real panel height** — one row in the low window,
  two in the high. Nothing measured suggests that is a problem for these eight
  figures, but a future experiment configuring more closely-spaced bands will
  use more rows, and PD2's raise is what stands between that and a silently
  unreadable figure. It has never fired.
- **`--annotate` is not offered on the diagnostic figure**, by decision. The
  diagnostic path is untouched and its bytes are asserted identical with and
  without the flag.
- **Entry 005's B8 predicted the high-window collision and it happened exactly
  as measured.** The low-window collisions it predicted did not, because
  rotation changes which extent matters — which was the point of the design.

---

## 11. Files touched by this phase

Modified: `main.py`, `src/ramsess/plotting.py`, `src/ramsess/report.py`,
`tests/test_output_filenames.py`.
Added: `tests/test_annotate_cli.py`, this file, one `INDEX.md` line.
Generated: eight annotated PNGs under `figures/irradiation_sara/`, all
gitignored build output.

Untouched: `data/raw/`, `data/derived/`, the six
`figures/irradiation_sara/{sample}_overlay.png` reference files,
`tests/test_raw_plot_reference.py`, `tests/fixtures/`,
`src/ramsess/analysis.py`, `src/ramsess/bands.py`, `src/ramsess/io.py`.

Nothing was committed. PHASE B ends here.
