# 008 — annotation-legibility — PHASE B

Supersedes nothing. Fixes F1, F2 and F3 as scoped in
`prompt_outputs/007-annotation-legibility-phaseA.md`, under the experimenter's
decisions recorded there.

Date: 2026-09-01
HEAD at time of writing: `42557f4`
Entries 006 and 008 are both in the working tree, **uncommitted**, and are to be
committed together once both are approved.

---

## 1. Blockers and decisions needed

**None.** All six steps completed. STEP 0's stop condition did not fire, STEP 5's
did not fire, and the suite is green.

---

## 2. PROPOSED DEVIATIONS

Two, both disclosed rather than silent, and one of them is the substantive
finding of this phase.

**PD1 — the F3 test as literally specified did NOT guard F3, so it gained a
second assertion.** STEP 4c asked for "no legend overlaps any label, over every
flag combination". I wrote exactly that, and then ran the STEP 4 proof: **with
the F3 fix reverted, the test still passed, all four combinations.** The reason
is that whether a legend inside the reserved band happens to land on a label
depends on where it sits *horizontally*, which is luck — in the synthetic
figure the legend went to y0=0.77, well inside the band, but missed the labels
because they sit at particular x positions. Asserting only the symptom would
have shipped a test that passes whenever the luck holds.

I added a second assertion to the same test: **the legend's top must not rise
above the lowest label's foot** — that is, it must stay out of the reserved
band, which is what `set_bbox_to_anchor` actually guarantees and what the defect
actually is. That assertion fails on the reverted code in all four combinations
(output in section 7). The specified label-overlap assertion is kept, first, and
unchanged.

I could have instead engineered the synthetic data so the legend lands on a
label — I tried, with a dense zigzag spectrum, and it still missed (measured:
legend at y0frac 0.77 in the low panel, `hits=none`, in all four combinations).
Chasing that would have made the test depend on a coincidence of geometry rather
than on the invariant.

**PD2 — the new tests went into a new module, `tests/test_annotation_layout.py`
(239 lines).** STEP 4 said "in `tests/` as the suite does" without naming a
module. `test_output_filenames.py` is about filenames and bytes,
`test_annotate_cli.py` (added by entry 006) about the CLI gate, and
`test_plotting.py`'s own docstring scopes it to "the tripwire, the panel layout,
and display settings" — none of which is the annotation's drawn geometry. This
is the same judgement, and the same disclosure, as entry 006's PD1. Moving it is
a one-file change.

**Not a deviation, but worth stating:** STEP 1 says each rule stops below the
foot of its own label, "which differs by row". It is implemented **per label**,
not per row, which is strictly what "its own label" requires — within one row
`522` and `1328` have different rendered heights, so their feet differ. Measured
in the low panel: rule tops of 0.8985 for the three-character labels and 0.8725
for the four-character ones, in the same row.

---

## 3. STEP 0 — the re-check

    full suite:                     327 passed in 82.38s (0:01:22)
    tests/test_raw_plot_reference:  51 passed in 8.18s
    git status --short figures/:    (empty)
    HEAD:                           42557f4

`git status --short` showed entry 006's five modified files and its two new
untracked files still present and uncommitted, exactly as entry 006 left them.
Nothing differed. Proceeded.

---

## 4. What changed

    main.py                        |  24 +++++      (entry 006, unchanged here)
    prompt_outputs/INDEX.md        |   4 +
    src/ramsess/plotting.py        | 234 ++++++++++++++++++++++++++++++++++++++++-
    src/ramsess/report.py          |  41 ++++++--    (entry 006, unchanged here)
    tests/test_output_filenames.py | 129 +++++++++++++++++++----  (entry 006, unchanged here)

plus `tests/test_annotation_layout.py`, new, 239 lines, untracked.

The diff is cumulative over entries 006 and 008 because neither is committed.
**This phase touched exactly two files:** `src/ramsess/plotting.py` and the new
test module. `main.py`, `report.py` and `test_output_filenames.py` are entry
006's work and were not reopened.

### F1 — the rule through its own label

The standalone rule loop is gone. Rules are now drawn inside the label-placement
loop, where the row's `y` and the label's own measured height are both in scope:

    # Labels and rules are placed together, because a rule has to stop below the
    # foot of its own label and where that foot sits depends on the label's row.
    # ymin/ymax are axes fractions, so this needs no unit conversion and behaves
    # the same on a log axis. The top stays inside the reserved band, and so
    # above every trace, because the clearance is smaller than the row gap.
    cursor = ANNOTATION_TOP_PAD * line_height
    for row, indices in enumerate(rows):
        y = 1.0 - cursor / panel_height
        for index in indices:
            spec = selected[index]
            label(spec, y)
            foot = y - (heights[index] + ANNOTATION_RULE_CLEARANCE * line_height) / panel_height
            panel.axvline(
                spec.centre,
                ymax=foot,
                color=ANNOTATION_RULE_COLOR,
                linewidth=ANNOTATION_RULE_WIDTH,
                alpha=ANNOTATION_RULE_ALPHA,
                zorder=ANNOTATION_ZORDER,
            )
        cursor += row_heights[row] + gap

The new constant, dimensionless as required:

    # Gap between the foot of a label and the top of its own rule, in the same units
    # as the two above. Below ANNOTATION_ROW_GAP, which is what keeps every rule top
    # inside the reserved band and so strictly above the traces.
    ANNOTATION_RULE_CLEARANCE = 0.25

Being below `ANNOTATION_ROW_GAP` (0.35) is not decoration: it is what makes
`ymax > 1 - fraction > 0` provable for every row, so no rule can be given a
negative extent and every rule top lands inside the reserved band.

### F2 — label text and legibility

    ANNOTATION_FONT_SIZE = 12          # was 8

    # Near-black for the label, so it carries to the back of a room. Not black: the
    # control step is drawn in black and a label should not read as a trace.
    ANNOTATION_TEXT_COLOR = "0.15"
    # The rule stays grey, and keeps its own alpha on top. Separate from the text
    # colour so the label can be darkened without the rule following it.
    ANNOTATION_RULE_COLOR = "0.35"

`ANNOTATION_COLOR` is gone; a repository grep over `src/`, `tests/` and
`main.py` finds no remaining reference. The rule's appearance is unchanged —
same grey, same `ANNOTATION_RULE_ALPHA`, same width.

The label text, with the reasoning kept at the call site:

    def label(spec: BandSpec, y: float):
        # The label is the configured centre, not the band name. A rotated
        # label's height is the length of its text, and that height is what the
        # reserved band is made of, so a short label buys back panel height that
        # a smaller font cannot. The centre comes from the caller's spec; no
        # position is written here. `:g` drops the point from a whole number.
        return panel.text(
            spec.centre,
            y,
            f"{spec.centre:g}",
            ...

`:g` is the formatter the codebase already uses for this
(`_params_label` in this module, the noise-region print in `report.py`).
**No band centre appears as a literal**: grepping the finished module for
`ech[0-9]`, `glycine`, `silicon`, `si_5`, `522`, `893`, `2975` gives one hit,
the pre-existing `ech6` comment entry 005 B9 already recorded.

The helper's return value still carries **band names**, not label text — it is
documented as "the band names placed" and nothing was changed about it.

### F3 — the legend

Inside `_annotate_band_centres`, after `fraction` is computed and the top limit
raised:

    # Keep the legend out of the band just reserved. Its placement is still
    # chosen by loc="best", but searched only over the data region: "best"
    # scores candidates against the data, and the reserved band is empty of data
    # by construction, so without this it reads as the emptiest part of the
    # panel and the legend lands on top of the labels. Guarded because nothing
    # in this function's contract says the caller made a legend.
    legend = panel.get_legend()
    if legend is not None:
        legend.set_bbox_to_anchor(
            (0.0, 0.0, 1.0, 1.0 - fraction), transform=panel.transAxes
        )

`panel.legend(...)` in `build_sample_overlay` is **untouched** — not reordered,
not parameterised — as decided. The whole of F3 sits behind the
`bands is not None` gate, so it cannot reach the six reference figures by
construction.

The docstring of `_annotate_band_centres` was updated to state the new label
text, the rule stopping below its own foot, and the legend confinement.

---

## 5. STEP 2's measurement — what a different font size would cost

Rows and reserved band with the new short labels, measured on real figures in
memory. **This is the table to look at if 12 costs too much panel height: one
constant, `ANNOTATION_FONT_SIZE`, moves it.**

**Rows per panel — unchanged at every size tested:**

| panel | fs 10 | fs 11 | fs 12 | fs 14 |
|---|---|---|---|---|
| ech2 low | 1 | 1 | 1 | 1 |
| ech2 high | 2 | 2 | 2 | 2 |
| ech4 low | 1 | 1 | 1 | 1 |
| ech4 high | 2 | 2 | 2 | 2 |

**Reserved band as a fraction of panel height:**

| panel | fs 10 | fs 11 | fs 12 (shipped) | fs 14 |
|---|---|---|---|---|
| ech2 low | 10.8% | 12.0% | **13.1%** | 14.5% |
| ech2 high | 20.4% | 22.7% | **24.9%** | 27.5% |
| ech4 low | 10.8% | 12.0% | **13.1%** | 14.5% |
| ech4 high | 20.4% | 22.7% | **24.9%** | 27.5% |

**The decision's premise is confirmed, and the win is larger than the font
change alone.** Against entry 007's measurements with full band names:

| panel | old: names @ fs 8 | old: names @ fs 12 | new: centres @ fs 12 |
|---|---|---|---|
| low | 19.5% | 29.7% | **13.1%** |
| high | 37.9% | 58.1% | **24.9%** |

So the figures now carry text half again as large as before *and* give up **less
than two-thirds** of the panel height the original size-8 version did. Shortening
the label was worth more than shrinking the font, exactly as entry 007's A3
predicted, because the reserved band is made of string length and the row count
is made of line height.

At fs 14 the high window is still only 27.5% — below the 37.9% the old size-8
names cost — so there is headroom above 12 if the experimenter wants it. Row
counts do not move at any size tested.

---

## 6. Test result

**Full suite: `342 passed in 102.76s (0:01:42)`. Zero warnings** — pytest
printed no warnings summary.

327 before, so **+15**, all in the new module. No existing test changed, and
none needed to: entry 007's "matters next" was right that the existing suite
would pass unchanged, which is why these were written.

| module | result |
|---|---|
| `tests/test_annotation_layout.py` (new) | 15 passed in 4.40s |
| `tests/test_raw_plot_reference.py` | 51 passed, untouched |
| `tests/test_output_filenames.py` | 15 passed, untouched |
| `tests/test_annotate_cli.py` | 3 passed, untouched |

### What the new module asserts

- **F1** — `test_every_rule_stops_below_its_own_label`, parametrised over all
  four flag combinations: every rule is paired to its label by x, and the rule's
  top (axes fraction, from `axvline`'s ydata) must be strictly below that
  label's foot (axes fraction, from the renderer). It also asserts every label
  has exactly one rule and that all five configured bands were checked.
- **F1 guard** — `test_more_than_one_row_is_actually_exercised`: if the fixture
  ever degenerates to a single row, the per-label extent proves little, so the
  test fails and says to move the centres closer together.
- **F2** — `test_labels_are_the_configured_centre_not_the_band_name`,
  parametrised over the same four, asserting the drawn text set equals the
  centre set and is disjoint from the band names. The fixture's band names
  (`alpha`, `beta`, …) are deliberately unlike its centres so the two can be
  told apart.
- **F2** — `test_a_whole_number_centre_carries_no_decimal_point`.
- **F3** — `test_no_legend_overlaps_a_label`, parametrised over the same four,
  with the two assertions described in PD1.
- **Regression guard** — `test_annotation_leaves_the_unannotated_figure_alone`:
  a figure built without bands has no texts, no annotation rules, and a legend
  still anchored to the whole panel.

---

## 7. STEP 4's demonstrations — each fix reverted in turn

Each revert was made alone, with the other two fixes in place.

### F1 — `ymax=foot` removed from the `axvline` call

    E   AssertionError: the rule at 230 reaches 1.0000 but its label's foot is at 0.9083: the rule runs through its own label
    E   assert 1.0 < np.float64(0.9083038173947265)

    tests\test_annotation_layout.py:125: AssertionError
    =========================== short test summary info ===========================
    FAILED tests/test_annotation_layout.py::test_every_rule_stops_below_its_own_label[False-False]
    FAILED tests/test_annotation_layout.py::test_every_rule_stops_below_its_own_label[False-True]
    FAILED tests/test_annotation_layout.py::test_every_rule_stops_below_its_own_label[True-False]
    FAILED tests/test_annotation_layout.py::test_every_rule_stops_below_its_own_label[True-True]
    4 failed, 11 deselected in 2.53s

The rule reaching exactly 1.0000 is `axvline`'s default `ymax` — the defect
itself, reproduced.

### F2 — label text put back to `spec.name`

    E   AssertionError: assert {'alpha', 'be...lon', 'gamma'} == {'230', '234'...'2470', '290'}
    E     Extra items in the left set:
    E     'gamma'
    E     'alpha'
    E     'beta'
    E     'epsilon'
    E     'delta'...

    tests\test_annotation_layout.py:166: AssertionError
    =========================== short test summary info ===========================
    FAILED tests/test_annotation_layout.py::test_labels_are_the_configured_centre_not_the_band_name[False-False]
    FAILED tests/test_annotation_layout.py::test_labels_are_the_configured_centre_not_the_band_name[False-True]
    FAILED tests/test_annotation_layout.py::test_labels_are_the_configured_centre_not_the_band_name[True-False]
    FAILED tests/test_annotation_layout.py::test_labels_are_the_configured_centre_not_the_band_name[True-True]
    4 failed, 1 passed, 10 deselected in 1.69s

(`test_a_whole_number_centre_carries_no_decimal_point` is the one that still
passed: `alpha` contains no decimal point either. It is a formatting test, not a
"which string" test, and the test above is what covers that.)

### F3 — first attempt, and why the specified test was not enough

With `set_bbox_to_anchor` disabled:

    4 passed, 11 deselected in 2.49s

**The test passed with the fix removed.** This is PD1. Diagnosis, measured on
the reverted code with a dense zigzag spectrum built to try to force the
collision:

    baseline=False logy=False low: legend y0frac=0.77 hits=none
    baseline=False logy=False high: legend y0frac=0.39 hits=none
    baseline=False logy=True low: legend y0frac=0.77 hits=none
    ... (all eight panels: hits=none)

The legend does move into the reserved band (y0frac 0.77 against a band starting
around 0.87) but misses the labels horizontally. After adding the second
assertion:

    E   AssertionError: the legend reaches 0.9836 but the lowest label's foot is at 0.8166: the legend has entered the reserved band
    E   assert np.float64(0.983602256329529) <= np.float64(0.8166076347894531)

    tests\test_annotation_layout.py:219: AssertionError
    =========================== short test summary info ===========================
    FAILED tests/test_annotation_layout.py::test_no_legend_overlaps_a_label[False-False]
    FAILED tests/test_annotation_layout.py::test_no_legend_overlaps_a_label[False-True]
    FAILED tests/test_annotation_layout.py::test_no_legend_overlaps_a_label[True-False]
    FAILED tests/test_annotation_layout.py::test_no_legend_overlaps_a_label[True-True]
    4 failed, 11 deselected in 2.68s

### Restoration

All three reverts removed. Confirmed by grepping the module for `TEMPORARY`,
`and False` and `spec.name,` — no hits — and by `ymax=foot` being present. The
module then ran `15 passed in 4.40s`.

---

## 8. STEP 5 — the real run

Eight figures regenerated, all successful:

    figures\irradiation_sara\ech2_overlay_annotated.png                    175789 bytes
    figures\irradiation_sara\ech2_overlay_annotated_log.png                268312
    figures\irradiation_sara\ech2_overlay_baseline_annotated.png           175180
    figures\irradiation_sara\ech2_overlay_baseline_annotated_log.png       249647
    figures\irradiation_sara\ech4_overlay_annotated.png                    293438
    figures\irradiation_sara\ech4_overlay_annotated_log.png                385790
    figures\irradiation_sara\ech4_overlay_baseline_annotated.png           214398
    figures\irradiation_sara\ech4_overlay_baseline_annotated_log.png       288172

**The six reference overlays are UNMODIFIED:**

    $ git status --short figures/
    (no output)

STEP 5's stop condition did not fire.

### Measured from the rendered figures

**Rows and reserved band**, identical for both samples:

| panel | rows | reserved | membership |
|---|---|---|---|
| low | 1 | 13.1% | 522, 893, 979, 1328, 1412 |
| high | 2 | 24.9% | row 0: 2975, 3146 — row 1: 3012 |

**F1 — rule below its own label.** Tightest margin **+0.0098 of panel height**
(about 4.1 px of 423.5), in every one of the sixteen panels. Positive
everywhere, so no rule touches its own label anywhere. The margin is uniform
because it is `ANNOTATION_RULE_CLEARANCE × line_height`, and line height is the
same for every label at one font size.

**Label-label overlaps: none**, in all sixteen panels.

**Label-trace clearance: +20.3 to +23.5 px**, positive in all sixteen panels —
and *better* than entry 006's +16.1 to +20.6 px, because the shorter labels
leave more of the reserved band empty below them.

**F3 — legend.** **Label hits: none, in all sixteen panels** (entry 006: 1 of
16). Legend positions collapse to three cases: y0frac **0.44** on the six low
panels outside `baseline+logy`, **0.32** on the six high panels outside
`baseline+logy`, and **0.02** on all four `baseline+logy` panels — sixteen in
total.

**Entry 007 predicted 5 panels and 30 trace-touches. The prediction was checked,
not assumed, and it is beaten:**

| | entry 007, before the anchor | entry 007's prediction | measured now |
|---|---|---|---|
| panels with a legend over traces | 1 of 16 | 5 of 16 | **3 of 16** |
| trace-touches | 7 | 30 | **18** |

The three are `ech2 baseline+logy low` (7/7), `ech4 baseline+logy low` (7/7) and
`ech4 logy high` (4/7). The prediction was made with the old reserved-band
fractions of 19.5% and 37.9%; shrinking them to 13.1% and 24.9% gave `loc="best"`
more room below the band, and two of the five predicted panels no longer need to
sit on the traces. That is F2 improving F3 as a side effect — worth recording
because it was not the reason for either change.

---

## 9. Everything measured, with the numbers

| what | result |
|---|---|
| suite before | 327 passed in 82.38s |
| suite after | **342 passed in 102.76s, 0 warnings** |
| net new tests | +15, all in the new module |
| `test_annotation_layout.py` | 239 lines, 15 passed in 4.40s |
| reference test, before and after | 51 passed, untouched |
| `ANNOTATION_FONT_SIZE` | 8 → 12 |
| `ANNOTATION_COLOR` | split into `ANNOTATION_TEXT_COLOR` "0.15" and `ANNOTATION_RULE_COLOR` "0.35" |
| stale `ANNOTATION_COLOR` references | 0 |
| new constant | `ANNOTATION_RULE_CLEARANCE = 0.25`, dimensionless, below `ANNOTATION_ROW_GAP` 0.35 |
| label text | configured centre via `:g` — `522`, `893`, `979`, `1328`, `1412`, `2975`, `3012`, `3146` |
| reserved band, low: names@8 → names@12 → centres@12 | 19.5% → 29.7% → **13.1%** |
| reserved band, high: names@8 → names@12 → centres@12 | 37.9% → 58.1% → **24.9%** |
| rows, low / high | 1 / 2, at fs 10, 11, 12 and 14 |
| rule-below-label margin | +0.0098 of panel height, all 16 panels |
| rule tops within one row | 0.8985 and 0.8725 — per label, not per row |
| label-label overlaps | 0, all 16 panels |
| label-trace clearance | +20.3 to +23.5 px (entry 006: +16.1 to +20.6) |
| legend/label overlaps | **0 of 16** (entry 006: 1 of 16) |
| legend over traces | **3 of 16 panels, 18 trace-touches** (predicted 5 and 30) |
| F1 revert → test | 4 failed, 11 deselected |
| F2 revert → test | 4 failed, 1 passed, 10 deselected |
| F3 revert → test as specified | **4 passed — did not guard** |
| F3 revert → test with the added assertion | 4 failed, 11 deselected |
| dataset literals in `plotting.py` | 0 (one pre-existing `ech6` comment) |
| `git status --short figures/` | empty, before and after |

---

## 10. Matters next

- **PD1 is the thing to read before approving.** A test written exactly as
  specified passed against the broken code, and only the added assertion caught
  it. If the experimenter disagrees with that assertion, F3 has no working test.
- **`ANNOTATION_FONT_SIZE` is now a genuinely cheap dial.** Section 5's table
  gives the cost of 10, 11, 12 and 14 with the shipped labels; nothing else has
  to change to move it, and the row counts do not shift.
- **Three panels still put the legend over traces**, all involving `--logy`.
  That is the accepted cost of the F3 decision and is better than predicted, but
  it has not been eliminated and will not be by any font choice.
- **PD2 is reversible cheaply** if the new test module should live elsewhere.
- **The rule now stops below its label but still spans everything beneath it**,
  including the traces, at `ANNOTATION_RULE_ALPHA` 0.45. That was not part of
  F1 and was not changed. If a rule crossing a peak reads badly on the
  projector, that is a separate decision.
- **Entry 006's PD2 guard — the raise when labels would fill a panel — still has
  never fired**, and is now further from firing than ever, since the reserved
  band roughly halved.

---

## 11. Files touched by this phase

Modified: `src/ramsess/plotting.py`.
Added: `tests/test_annotation_layout.py`, this file, one `INDEX.md` line.
Regenerated: the eight annotated PNGs under `figures/irradiation_sara/`, all
gitignored build output.

Untouched by this phase: `main.py`, `src/ramsess/report.py`,
`tests/test_output_filenames.py` and `tests/test_annotate_cli.py` (all entry
006's), `data/raw/`, `data/derived/`, the six
`figures/irradiation_sara/{sample}_overlay.png` reference files,
`tests/test_raw_plot_reference.py`, `tests/fixtures/`,
`src/ramsess/analysis.py`, `src/ramsess/bands.py`, `src/ramsess/io.py`.

Nothing was committed. PHASE B ends here.
