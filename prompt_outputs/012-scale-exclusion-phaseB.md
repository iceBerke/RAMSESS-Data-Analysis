# 012 — scale-exclusion — PHASE B

Supersedes nothing. Implements **Change 1 only** from
`prompt_outputs/010-scale-exclusion-and-layout-phaseA.md`, under the
experimenter's decision recorded there. **Change 2, the per-sample subfolders,
was not started.**

Date: 2026-09-02
HEAD: `1964b62`. Nothing was committed.

---

## 1. Blockers and decisions needed

**None.** All six steps completed; no stop condition fired.

But two things below are findings rather than routine, and both concern tests
that did not guard what they claimed. They are in section 2 and section 7.

---

## 2. PROPOSED DEVIATIONS

**PD1 — the new parameter on `build_sample_overlay` defaults to `None`, not
`False`.** STEP 1 said "a new keyword parameter, defaulting to False, carrying
the exclusion", and also that "the function must be told WHICH band to exclude
by its caller". Those pull in opposite directions: a boolean cannot carry which
band. I implemented one parameter,
`exclude_from_scale: BandSpec | None = None`, matching the shape `bands` and
`baseline_params` already use in this function. The behavioural requirement is
met exactly — the default is falsy, no code path is taken, and nothing changes
— but the literal word "False" is not what is in the signature. A separate
boolean *plus* a spec would be two parameters that can contradict each other.
**The CLI flag is a boolean, as decided; only the internal parameter differs.**

**PD2 — I added a guard that raises, and a test for it, neither of which was
specified.** While proving the tests I found two real defects in my own first
implementation, both reachable and both silent:

- on a log panel, if the data left after masking is non-positive, `log10`
  produces NaN and matplotlib raised `Axis limits cannot be NaN or Inf` from
  deep inside `set_ylim`;
- on a linear panel, if the masked data sits entirely below the panel's clamped
  floor, the computed top is *below* the bottom and matplotlib **silently draws
  an inverted axis**. Observed: `ylim low (0.0, -4.706)`.

Both happen when the excluded band held all the signal there was — which a
corrected spectrum with a single peak produces, and which my first
`test_output_filenames` fixture produced by accident. I added one guard covering
all three failure modes (inverted, non-positive, NaN) that raises naming the
band and the numbers, in the style of entry 006's PD2, plus
`test_excluding_the_only_signal_refuses_rather_than_inverting_the_axis`.
Drawing an inverted panel would be worse than refusing because it still looks
like a figure.

**PD3 — the new geometric tests went into a new module,
`tests/test_scale_exclusion.py` (254 lines).** Same judgement and disclosure as
entry 006's PD1 and entry 008's PD2: `test_output_filenames.py` is about
filenames and bytes, and cannot see a limit. STEP 4c and 4d are limit
assertions.

**PD4 — I changed the synthetic fixture in `test_output_filenames.py`.** Its
`peaked` helper made spectra with a single peak, and no configured band
contained that peak — so excluding any band would have changed nothing and all
32 exclusion runs would have been silent no-ops. `peaked` now takes a mapping of
sample index to peak height, the low window gets a second peak at index 32
(wave 290.750, inside band `c`), and a new band `ref` sits on the first peak at
257.75 and is the reference. Verified by computing the wave grid rather than
assuming it.

---

## 3. The design question STEP 3 asked: does the flag require `--annotate`?

**No, and they are not inseparable — so I made the flag imply the config load
rather than rejecting the combination.**

The two flags want different parts of the same file: `--annotate` wants the band
list, `--exclude-reference-from-scale` wants the `reference` name. Loading it is
one call over data `plot` already holds, and `main.py` already had that call
under `--annotate`; making either flag trigger it is a change of condition, not
of structure.

Requiring `--annotate` would be worse than merely unnecessary. The supervisor
asked for a *linear figure scaled to the glycine bands*; forcing `--annotate`
would put ten labels and a 36.7% reserved band on it as well, which is a
different figure and a different decision. Two flags that each need `bands.json`
for their own reasons should each be able to ask for it.

So `main.py` now collects which flags want the file, loads it once, and names
all of them if it is missing:

    needs_bands = [
        flag
        for flag, wanted in (
            ("--annotate", args.annotate),
            ("--exclude-reference-from-scale", args.exclude_reference_from_scale),
        )
        if wanted
    ]

The rejection style STEP 3 mentioned is therefore not used here; it remains in
place for the `--baseline-lam` family, which genuinely does depend on another
flag. Plain `plot` still reads no configuration at all —
`tests/test_annotate_cli.py::test_plain_plot_still_works_without_a_bands_config`
covers that and still passes.

---

## 4. The filename suffix, proposed

    REFERENCE_EXCLUDED_SUFFIX = "_refexcluded"

composed at the one designated place, content flag before the scale suffix so
`_log` stays last:

    {name}_overlay{annotated}{refexcluded}{scale}.png
    {name}_overlay_baseline{annotated}{refexcluded}{scale}.png

Its comment records why it names no band:

    # Appended to the figures whose upper limit was computed with the reference
    # band's window left out. It names no band on purpose: the flag is keyed to
    # whichever band bands.json calls the reference, so one experiment's figures
    # can only ever mean one thing by it, and no unvalidated band name reaches a
    # path. The band is named in the title instead, where a path's rules do not
    # apply.

Real paths produced: `ech2_overlay_refexcluded.png`,
`ech2_overlay_refexcluded_log.png`, `ech2_overlay_baseline_refexcluded.png`,
`ech2_overlay_annotated_refexcluded.png`, and the ech4 equivalents.

---

## 5. STEP 0 — the re-check

**0a.** `342 passed in 84.94s`. **0b.** HEAD `1964b62`, working tree clean.

**0c/0d. Entry 010's D3, re-measured against the current thirteen-band state.**
The reference is `si_522`, window `low`, search window [507, 537], read from
`bands.json` rather than assumed.

**ech2 low, RAW — limit 165,644.1 → 13,851.5, a factor of 11.96**

| band | % now | % excluded | | band | % now | % excluded |
|---|---|---|---|---|---|---|
| si_522 | 95.3% | 1263.9% | | glycine_1412 | 4.4% | **46.3%** |
| glycine_893 | 6.2% | **71.0%** | | glycine_1443 | 3.5% | **34.9%** |
| glycine_979 | 5.9% | **67.1%** | | glycine_1458 | 3.8% | **38.5%** |
| glycine_1038 | 3.2% | **31.4%** | | glycine_1571 | 3.3% | **32.0%** |
| glycine_1328 | 8.0% | **95.5%** | | glycine_1673 | 3.1% | **29.8%** |

**ech2 low, CORRECTED — 160,910.1 → 11,635.6, a factor of 13.83.** The nine
glycine bands move from 0.8–6.9% to 11.1–95.0%.

**ech4 low** — factor 1.16 raw, 1.34 corrected; its `glycine_1328` was already
82% of the panel, so silicon was never the constraint there.

**The change still meets the supervisor's request**, and by a wider margin than
entry 010 measured: with thirteen bands the crowding at the floor is worse
before and the spread after is the same. **0c's stop condition did not fire.**

**0d.** All four high panels come out **IDENTICAL** with and without the
exclusion, in raw and corrected, for both samples — as D3 found.

Note the 0c table recomputed both bounds; the implementation moves **only the
top**, so the bottom stays as the clamp left it. That makes the implemented
percentages slightly different from the table above and is the behaviour tested
by `test_the_lower_limit_never_moves`.

---

## 6. What changed

    main.py                        |  32 ++++--
    src/ramsess/plotting.py        | 113 +++++++++++++++++++++-
    src/ramsess/report.py          |  49 +++++++---
    tests/test_output_filenames.py | 158 ++++++++++++++++++++++++++-------

plus `tests/test_scale_exclusion.py`, new, 254 lines, untracked.

**`plotting.py`** gains `_raise_top_excluding_band`, which masks the band's
search window out of the values already drawn, applies
`plt.rcParams["axes.ymargin"]` — in log space on a log panel — and sets only the
upper limit. `build_sample_overlay` gains `exclude_from_scale` and collects
`panel_values` as it draws. The call sits after the scale and the clamp:

    # After the scale and the clamp, so it composes with both: set_yscale
    # re-autoscales and would undo a limit set before it. Before the legend
    # and the labels, because loc="best" and the reserved band are both
    # measured against the panel this leaves behind.
    if exclude_from_scale is not None and window == exclude_from_scale.window:
        _raise_top_excluding_band(panel, panel_values, exclude_from_scale, logy)

Placing it after `set_yscale` rather than before is not cosmetic: `set_yscale`
re-autoscales the axis and would have discarded a limit set before it. Entry
010's D6 ordering requirement — exclusion before the legend and before the
reserved band — is met.

**No band name, centre or width appears in `plotting.py`.** Grepped the finished
module for `ech[0-9]`, `glycine`, `silicon`, `si_5`, `522`: one hit, the
pre-existing `ech6` comment.

**The title (STEP 2):**

    ech2 - irradiation_sara - y-SCALE EXCLUDES si_522 (low panel; its peak runs off the top)

**`report.py`** gains `REFERENCE_EXCLUDED_SUFFIX`, the `reference` and
`exclude_reference` parameters, two validation checks in the style of the
existing ones, and the suffix composition. **`main.py`** gains the flag and the
shared config load described in section 3.

---

## 7. STEP 4e — the demonstrations, and what they exposed

### 4d and the benefit test: they guard. Proven.

With the rescale made a no-op (`if False and ...`), leaving the rename and the
title in place:

    E  AssertionError: the excluded band peaks at 40002.0 but the panel's limit is 41952.1: it was not excluded from the scale
    E  AssertionError: the excluded band peaks at 40002.0 but the panel's limit is 48104.5: it was not excluded from the scale
    E  AssertionError: the excluded band peaks at 38988.8 but the panel's limit is 40938.9: it was not excluded from the scale
    E  AssertionError: the excluded band peaks at 38988.8 but the panel's limit is 45241.4: it was not excluded from the scale
    E  AssertionError: the other band occupies 7.2% of the panel before and 7.2% after: the exclusion bought almost nothing
    E  AssertionError: the other band occupies 4.6% of the panel before and 4.6% after: the exclusion bought almost nothing
    ...
    9 failed, 12 passed in 3.43s

### 4b does NOT guard the rescaling, and this is the finding

Against the same no-op:

    4 passed, 17 deselected in 31.55s

**All four parametrisations of the byte-difference test passed against a build
that rescaled nothing.** The reason is that STEP 2's title also changes, so the
bytes differ whether or not the limit moved. The test as specified proves the
flag produces *a different figure under its own name*; it cannot distinguish
"rescaled" from "retitled".

This is entry 008's PD1 repeating in a new place, and it is why STEP 4e exists.
Rather than delete the test — it does guard something real, that the flag is not
a pure rename — I corrected its docstring to say what it does and does not
prove, and to name the test that covers the gap:

    This does NOT prove the panel was rescaled: the title also changes, and a
    build that renamed the file and retitled it while rescaling nothing passes
    here. Verified by making the rescale a no-op - every assertion below still
    held. ``tests/test_scale_exclusion.py`` carries the test that fails in that
    case, by checking the excluded band ends up above the panel's limit.

### 4c is a negative guard and needed a different mutation

A test asserting the high panel must **not** change cannot fail against a no-op,
so a second mutation was used: the window check was dropped, applying the
exclusion to every panel.

    E  assert excluded.axes[1].get_ylim() == plain.axes[1].get_ylim()
    E    At index 1 diff: np.float64(21437.719980623824) != np.float64(21437.71998062386)
    ...
    FAILED tests/test_scale_exclusion.py::test_the_panel_without_the_reference_band_is_untouched[False-True]
    FAILED tests/test_scale_exclusion.py::test_the_panel_without_the_reference_band_is_untouched[True-True]

It fails — but only on the two **log** parametrisations. On the linear ones,
recomputing the limit with nothing masked reproduces matplotlib's own autoscale
to the last bit, so the panel is genuinely unchanged and there is nothing to
catch. That is a good sign for the formula's fidelity and a real limit on 4c's
sensitivity; both are worth knowing.

### Restoration

Both mutations removed. `grep` for `TEMPORARY` and `if False` in
`plotting.py` returns nothing, and the two modules run `42 passed in 66.11s`.

---

## 8. STEP 4a — the arity change

    COMBINATIONS = list(itertools.product([False, True], repeat=5))
    # baseline, diagnostic, logy, annotate, exclude_reference

Changed: the enumeration and its comment, `run()`'s signature and its
`write_sample_overlays` call, the `all_runs` keys and `out_` directory name, the
unpacking and skip condition in the last test, and **all eleven literal tuples**
across six tests — four more than the seven entry 006 counted, because entry 008
added `test_annotating_changes_the_figure_and_its_name` and
`test_annotation_does_not_reach_the_diagnostic_figure` since.

| | before | after |
|---|---|---|
| combinations rendered | 16 | **32** |
| tests | 15 | **21** |
| runtime | 31.57s | **64.20s** |

A factor of 2.03 for a factor of 2 in combinations. The two core guarantee tests
needed no change; they iterate generically.

---

## 9. STEP 5 — the real run

Eight figures, all successful:

    ech2_overlay_refexcluded.png            ech4_overlay_refexcluded.png
    ech2_overlay_refexcluded_log.png        ech4_overlay_refexcluded_log.png
    ech2_overlay_baseline_refexcluded.png   ech4_overlay_baseline_refexcluded.png
    ech2_overlay_annotated_refexcluded.png  ech4_overlay_annotated_refexcluded.png

**The six reference overlays are UNMODIFIED:**

    $ git status --short figures/
    (no output)

The fourth combination of each pair was chosen to exercise `--annotate` and the
exclusion together, which is the composition section 3 argued should be
available and which produces `_annotated_refexcluded` — the suffix order
working as designed.

---

## 10. STEP 6 — full suite

    369 passed in 118.89s (0:01:58)

**Zero warnings** (grep for "warning" over the output: 0).

342 before, so **+27**: six new in `test_output_filenames.py` and 21 in
`tests/test_scale_exclusion.py`.

---

## 11. Everything measured, with the numbers

| what | result |
|---|---|
| suite before | 342 passed in 84.94s |
| suite after | **369 passed in 118.89s, 0 warnings** |
| net new tests | +27 |
| `test_output_filenames.py` | 15 → 21 tests, 31.57s → 64.20s, 16 → 32 combinations |
| `tests/test_scale_exclusion.py` | 254 lines, 21 passed in 2.67s |
| literal tuples updated | 11, across 6 tests |
| ech2 low RAW limit | 165,644.1 → 13,851.5 (÷11.96) |
| ech2 low CORRECTED limit | 160,910.1 → 11,635.6 (÷13.83) |
| ech4 low RAW / CORRECTED | ÷1.16 / ÷1.34 |
| ech2 low glycine bands, raw | 3.1–8.0% → **29.8–95.5%** |
| ech2 low glycine bands, corrected | 0.8–6.9% → **11.1–95.0%** |
| high panels, all four | **IDENTICAL** with and without |
| new suffix | `_refexcluded`, before the scale suffix |
| 4d against a no-op rescale | 9 failed, 12 passed |
| **4b against a no-op rescale** | **4 passed — does not guard the rescaling** |
| 4c against an over-broad exclusion | 2 of 4 failed (log only) |
| defects found while proving | NaN limit on log; **inverted axis** `(0.0, -4.706)` on linear |
| dataset literals in `plotting.py` | 0 (one pre-existing `ech6` comment) |
| `git status --short figures/` | empty |
| Change 2 | **not started** |

---

## 12. Self-corrections during this phase

**Two, both caught by the STEP 4e proofs rather than by the tests passing.**

1. **My first implementation produced a NaN limit on log panels and an inverted
   axis on linear ones** when the excluded band held all the signal. The linear
   case was the worse of the two because matplotlib accepted it silently and
   drew a figure. Fixed by the guard in PD2; the observed inverted limit was
   `(0.0, -4.706)`.
2. **My first `test_output_filenames` fixture could not exercise the exclusion
   at all** — no configured band contained the synthetic peak, so every
   exclusion run was a no-op. Found by computing the wave grid, not by a failing
   test. Fixed in PD4.

Neither would have been visible from a green suite, which is the argument for
STEP 4e.

---

## 13. Files touched by this phase

Modified: `main.py`, `src/ramsess/plotting.py`, `src/ramsess/report.py`,
`tests/test_output_filenames.py`.
Added: `tests/test_scale_exclusion.py`, this file, one `INDEX.md` line.
Generated: eight PNGs under `figures/irradiation_sara/`, gitignored build output.

**Not touched:** `data/raw/`, `data/derived/`, the six reference overlays,
`tests/test_raw_plot_reference.py`, `tests/fixtures/`, `CLAUDE.md`,
`src/ramsess/analysis.py`, `src/ramsess/bands.py`, `src/ramsess/io.py`.
**Change 2 was not started:** no path construction was altered, `.gitignore` is
unchanged, and nothing was moved.

Nothing was committed. PHASE B ends here.
