# 011 — additional-bands — PHASE B

Supersedes nothing. Implements the band additions scoped in
`prompt_outputs/009-additional-bands-phaseA.md`, under the experimenter's
answers to that entry's D1 and D2.

Date: 2026-09-01
HEAD: `583414a`. Nothing was committed; entries 009, 010 and this one are all in
the working tree.

---

## 1. Blockers and decisions needed

**None.** Every step completed. STEP 0's stop condition did not fire, STEP 2's
did not fire, STEP 4's did not fire, STEP 6's did not fire.

---

## 2. PROPOSED DEVIATIONS

**None.** The phase did exactly what was specified. Two things are worth stating
explicitly rather than leaving to inference:

- **`data/raw/irradiation_sara/bands.json` was never written by this phase.** It
  was read three times — once verbatim for STEP 0c, once through
  `load_bands_config` for STEP 0d, and once by `quantify`. Its mtime is
  **23:44:40**, the experimenter's own edit; `bands.csv` was written at
  **23:48:01**, over three minutes later. Nothing in this phase reformatted or
  corrected it, and `git diff --stat data/raw/` shows the single `+5` the
  experimenter made.
- **The before-state `bands.csv` was copied to the session scratchpad** before
  `quantify` overwrote it, because STEP 2's comparison needs it and `quantify`
  rewrites the file in place. That copy is outside the project.

---

## 3. STEP 0 — verification before anything

**0a. Full suite:**

    342 passed in 82.82s (0:01:22)

**0b.** HEAD `583414a`. Working tree:

     M data/raw/irradiation_sara/bands.json
     M prompt_outputs/INDEX.md
    ?? prompt_outputs/009-additional-bands-phaseA.md
    ?? prompt_outputs/010-scale-exclusion-and-layout-phaseA.md

`bands.json` is modified, as expected — `git diff --stat` gives
`1 file changed, 5 insertions(+)`, the five new bands and nothing else.

**0c. `bands.json` verbatim, as the experimenter left it:**

    {
      "reference": "si_522",
      "bands": {
        "si_522":       {"centre": 522,  "half_width": 15, "window": "low"},
        "glycine_893":  {"centre": 893,  "half_width": 15, "window": "low"},
        "glycine_979":  {"centre": 979,  "half_width": 15, "window": "low"},
        "glycine_1038": {"centre": 1038, "half_width": 10, "window": "low"},
        "glycine_1328": {"centre": 1328, "half_width": 15, "window": "low"},
        "glycine_1412": {"centre": 1412, "half_width": 15, "window": "low"},
        "glycine_1443": {"centre": 1443, "half_width": 7,  "window": "low"},
        "glycine_1458": {"centre": 1458, "half_width": 7,  "window": "low"},
        "glycine_1571": {"centre": 1571, "half_width": 15, "window": "low"},
        "glycine_1673": {"centre": 1673, "half_width": 15, "window": "low"},
        "glycine_2975": {"centre": 2975, "half_width": 15, "window": "high"},
        "glycine_3012": {"centre": 3012, "half_width": 15, "window": "high"},
        "glycine_3146": {"centre": 3146, "half_width": 15, "window": "high"}
      }
    }

Checked field by field against entry 009 section 5's recommended config —
thirteen `(centre, half_width, window)` triples plus the reference and the
top-level key set:

    reference == 'si_522'   band count 13
    top-level keys ['bands', 'reference']
    matches entry 009 section 5 exactly: True

No differences. **STEP 0's stop condition did not fire.**

**0d.** Loaded through the real `load_bands_config` against
`common_window_ranges`:

    VALIDATES - reference si_522 - 13 bands; noise_regions {} (none)

**0e. The before state, on the record:**

    data/derived/irradiation_sara/bands.csv
      bytes    27809
      rows     184
      SHA-256  665ce77abb02ca4325287ab55f3884e0aac0fefe0bd3d1de4d61477366dae922
      mtime    2026-08-29 21:52:17.120164

---

## 4. STEP 1 — `quantify` for the whole experiment

Run as the CLI does, no `--sample`. Full stdout is long; the parts the phase
asked for, verbatim:

    baseline parameters:
      low:
        lam = 1000000.0   from baseline.json
        p = 0.01   from baseline.json
        n_iter = 10   from baseline.json
      high:
        lam = 100000000.0   from baseline.json windows.high
        p = 0.01   from baseline.json
        n_iter = 10   from baseline.json
      no noise_regions configured in bands.json; signal-to-noise will not be computed
    wrote 46 corrected spectra to ...\data\derived\irradiation_sara
      worst reconstruction residual on read-back: 1.45519e-11
    wrote ...\data\derived\irradiation_sara\provenance.json
    wrote ...\data\derived\irradiation_sara\bands.csv   299 measurement(s)
    wrote ...\figures\irradiation_sara\ech1_bands.png
    wrote ...\figures\irradiation_sara\ech2_bands.png
    wrote ...\figures\irradiation_sara\ech3_bands.png
    wrote ...\figures\irradiation_sara\ech4_bands.png
    wrote ...\figures\irradiation_sara\ech5_bands.png
    wrote ...\figures\irradiation_sara\ech6_bands.png
    wrote ...\figures\irradiation_sara\bands_all_samples.png

Every baseline parameter is sourced from `baseline.json`; none fell back to a
built-in default. The noise-region notice fired as expected — no
`noise_regions` is configured, so the whole `signal_to_noise` column stays empty
across all 299 rows.

Resulting state:

    bands.csv   45874 bytes, 299 rows
                SHA-256 e48bf8e41779147e255883575d7927b8e73360dc1701d3aa48922d376ae52f3d
    provenance.json   generated_utc 2026-09-01T21:48:01.521075+00:00
                      46 source files recorded

The full `== reference band ==`, `== normalised band heights ==` and
`== flags ==` blocks were printed and are summarised in section 6; the flag
lists are reproduced there in full, and completely, which the stdout summary is
not — `print_band_summary` truncates the edge listing at 12 and reported
"peaks on a search-window edge: 16".

---

## 5. STEP 2 — the existing numbers did not move

Entry 009's C6 predicted this from a code trace and an in-memory run. It is now
tested against real written output.

The new `bands.csv` was compared against the preserved before-state copy,
restricted to the eight original band names, **as raw CSV text** rather than as
parsed floats — so this catches a formatting change as well as a numerical one.

    header identical: True
    rows: before 184  after 299
    before rows (all 8 original bands): 184   after rows for those bands: 184
    same key set: True

Per column, over all 184 rows:

| column | result | column | result |
|---|---|---|---|
| sample | IDENTICAL | at_edge | IDENTICAL |
| window | IDENTICAL | noise | IDENTICAL |
| step | IDENTICAL | signal_to_noise | IDENTICAL |
| band | IDENTICAL | height_norm | IDENTICAL |
| centre | IDENTICAL | area_norm | IDENTICAL |
| position | IDENTICAL | cross_window | IDENTICAL |
| position_drift | IDENTICAL | | |
| **height** | **IDENTICAL** | | |
| area | IDENTICAL | | |
| n_points | IDENTICAL | | |

**ALL 184 ROWS × 16 COLUMNS BIT-IDENTICAL.** 115 rows were added; nothing was
changed. **STEP 2's stop condition did not fire, and entry 004's heights in the
presentation material are unaffected.**

Note this holds for `height_norm` too, which is the column that *could* have
moved: it divides by `si_522`, and `si_522` is unchanged, so it does not.

---

## 6. STEP 3 — the new measurements

### ech2, the five new bands

| band | step 0 | 1 | 2 | 3 | 4 | 5 | 6 | net 0→6 | max step-to-step |
|---|---|---|---|---|---|---|---|---|---|
| glycine_1038 | 1859.7 | 1779.3 | 1783.3 | 1620.1 | 1956.9 | 1899.2 | 1715.8 | **−7.74%** | **+20.79%** (3→4) |
| glycine_1443 | 2150.3 | 2163.2 | 2872.6 | 2234.4 | 2536.7 | 2569.2 | 2336.4 | **+8.65%** | **+32.80%** (1→2) |
| glycine_1458 | 2814.5 | 3022.1 | 2586.0 | 2599.6 | 2724.6 | 2590.4 | 2769.8 | **−1.59%** | **−14.43%** (1→2) |
| glycine_1571 | 1844.3 | 1801.6 | 1574.0 | 1687.4 | 1955.5 | 1800.8 | 1750.7 | **−5.07%** | **+15.89%** (3→4) |
| glycine_1673 | 1162.8 | 1294.0 | 1097.7 | 1223.9 | 1222.9 | 1174.7 | 1283.9 | **+10.42%** | **−15.17%** (1→2) |

Positions and flags: `glycine_1038` alternates 1035.176 / 1038.022 (drift −2.824
to +0.022); `glycine_1443` 1441.760 / 1444.303 (−1.240 to +1.303);
`glycine_1458` 1456.993 / 1459.526 (−1.007 to +1.526); `glycine_1571`
1569.165 / 1571.617 (−1.835 to +0.617); `glycine_1673` 1670.719 / 1673.103
(−2.281 to +0.103). **`at_edge` is False for all 35 measurements.**

### ech4, the five new bands

| band | step 0 | 1 | 2 | 3 | 4 | 5 | 6 | net 0→6 | max step-to-step |
|---|---|---|---|---|---|---|---|---|---|
| glycine_1038 | 11087.5 | 11252.9 | 11264.4 | 11329.7 | 12113.9 | 12039.4 | 10594.6 | **−4.45%** | **−12.00%** (5→6) |
| glycine_1443 | 18822.0 | 18000.5 | 18986.3 | 20701.2 | 18949.1 | 24646.1 | 19440.7 | **+3.29%** | **+30.06%** (4→5) |
| glycine_1458 | 16690.8 | 15965.9 | 16589.7 | 17669.6 | 18624.5 | 21608.6 | 15658.9 | **−6.18%** | **−27.53%** (5→6) |
| glycine_1571 | 14003.0 | 13302.5 | 13147.2 | 14586.0 | 14829.5 | 18765.9 | 13335.5 | **−4.77%** | **−28.94%** (5→6) |
| glycine_1673 | 9470.6 | 8625.4 | 8682.8 | 9915.2 | 9676.9 | 11486.5 | 8903.7 | **−5.99%** | **−22.49%** (5→6) |

Positions: `glycine_1038` fixed at 1038.022 (drift +0.022 throughout);
`glycine_1443` 1441.760 / 1444.303; `glycine_1458` 1456.990 / 1459.526;
`glycine_1571` fixed at 1571.617; `glycine_1673` fixed at 1673.103.
**`at_edge` is False for all 35 measurements.**

**The net and the step-to-step are reported side by side because they disagree
in every case.** In ech4 all five nets sit between −6.18% and +3.29% while four
of the five maxima exceed 22%, and all four of those are the same step 5→6
transition. In ech2 the nets run −7.74% to +10.42% against maxima of 14–33%. No
interpretation offered.

### Flags across all six samples

**`at_edge`: 16 measurements**, of which 12 are on the new bands.

    ech1  glycine_1038   step 0   position 1029.478  drift  -8.522  [NEW]
    ech3  glycine_1038   step 4   position 1029.478  drift  -8.522  [NEW]
    ech3  glycine_1038   step 5   position 1029.478  drift  -8.522  [NEW]
    ech3  glycine_1038   step 6   position 1029.478  drift  -8.522  [NEW]
    ech3  glycine_1443   step 4   position 1449.385  drift  +6.385  [NEW]
    ech3  glycine_1443   step 5   position 1449.385  drift  +6.385  [NEW]
    ech3  glycine_1443   step 6   position 1449.385  drift  +6.385  [NEW]
    ech3  glycine_1571   step 5   position 1583.852  drift +12.852  [NEW]
    ech3  glycine_1571   step 6   position 1583.852  drift +12.852  [NEW]
    ech3  glycine_893    step 5   position  878.319  drift -14.681
    ech5  glycine_1038   step 0   position 1029.478  drift  -8.522  [NEW]
    ech6  glycine_1443   step 0   position 1449.385  drift  +6.385  [NEW]
    ech6  glycine_3012   step 0   position 2998.132  drift -13.868
    ech6  glycine_3146   step 0   position 3131.202  drift -14.798
    ech6  glycine_979    step 0   position  966.238  drift -12.762
    ech6  si_522         step 0   position  509.283  drift -12.717

**Drift beyond `MAX_POSITION_DRIFT` = 5 cm-1: 29 measurements**, of which 12
are on the new bands. The complete list, which the stdout summary groups rather
than enumerates:

    ech1  glycine_1038  step 0   -8.522  [NEW]
    ech2  glycine_979   step 2   -6.970
    ech3  glycine_1038  steps 4,5,6   -8.522 each  [NEW]
    ech3  glycine_1328  step 5   +5.220 ; step 6  -5.295
    ech3  glycine_1443  steps 4,5,6   +6.385 each  [NEW]
    ech3  glycine_1571  steps 5,6     +12.852 each [NEW]
    ech3  glycine_1673  steps 4,5     -9.440 each  [NEW]
    ech3  glycine_2975  step 6  -10.278
    ech3  glycine_3012  step 4   -6.069 ; step 6  -9.965
    ech3  glycine_3146  step 4   +9.132
    ech3  glycine_893   step 5  -14.681 ; step 6  -5.801
    ech3  glycine_979   step 3   -6.970
    ech5  glycine_1038  step 0   -8.522  [NEW]
    ech5  glycine_3146  step 0   -9.254
    ech6  glycine_1443  step 0   +6.385  [NEW]
    ech6  glycine_2975  step 0  -10.278
    ech6  glycine_3012  step 0  -13.868
    ech6  glycine_3146  step 0  -14.798
    ech6  glycine_979   step 0  -12.762
    ech6  si_522        step 0  -12.717

**Per sample, new bands only:**

| sample | new-band measurements | at_edge | drifted |
|---|---|---|---|
| ech1 | 5 | 1 | 1 |
| **ech2** | **35** | **0** | **0** |
| ech3 | 30 | 8 | 10 |
| **ech4** | **35** | **0** | **0** |
| ech5 | 5 | 1 | 1 |
| ech6 | 5 | 1 | 1 |

Entry 009 flagged that ech1, ech3, ech5 and ech6 were unchecked. Reporting what
the new bands do there, without interpreting it: ech2 and ech4 are entirely
clean on the new bands. `glycine_1038` fires `at_edge` at step 0 in ech1 and
ech5 and at steps 4–6 in ech3, always at the same position 1029.478, the lower
edge of its [1028, 1048] window. `glycine_1443` fires at 1449.385, the upper
edge of [1436, 1450], in ech3 steps 4–6 and ech6 step 0. `glycine_1571` reaches
1583.852 in ech3 steps 5 and 6, 12.852 cm-1 from its centre. Eight of ech3's ten
new-band drifts fall at steps 4 and later; `CLAUDE.md` records ech3 as
collapsing after irr3. ech6's step 0 already drifted on four of the original
eight bands before this change, including the reference itself at −12.717.

---

## 7. STEP 4 — the annotated figures

Eight regenerated, all successful:

    ech2_overlay_annotated.png              ech4_overlay_annotated.png
    ech2_overlay_annotated_log.png          ech4_overlay_annotated_log.png
    ech2_overlay_baseline_annotated.png     ech4_overlay_baseline_annotated.png
    ech2_overlay_baseline_annotated_log.png ech4_overlay_baseline_annotated_log.png

**The six reference overlays are UNMODIFIED:**

    $ git status --short figures/
    (no output)

STEP 4's stop condition did not fire.

### Entry 009 C5's prediction, checked

Predicted: **3 rows and 40.5%**. Measured on the rendered figures, identical for
ech2 and ech4:

    low panel:  3 row(s), reserved 36.7%
        row 0: 522, 893, 979, 1328, 1412, 1571, 1673
        row 1: 1038, 1443
        row 2: 1458
    high panel: 2 row(s), reserved 24.9%   (unchanged)

**The row count and the row membership are exactly as predicted. The fraction is
36.7%, not 40.5% — 3.8 points better.**

The difference was checked rather than explained away. Entry 009's C5 measured
with the *measured* centres `1571.6` and `1673.1`; the shipped config uses the
whole numbers `1571` and `1673`. A rotated label's height is the length of its
text, and that height is what the reserved band is made of, so two six-character
labels cost more than two four-character ones. Re-measured both ways on the same
figure:

    shipped config (1571, 1673):            3 rows, reserved 36.7%
      labels: 1038 1328 1412 1443 1458 1571 1673 522 893 979
    entry 009 C5 config (1571.6, 1673.1):   3 rows, reserved 40.5%
      labels: 1038 1328 1412 1443 1458 1571.6 1673.1 522 893 979

Entry 009's 40.5% reproduces exactly under its own assumption, so the prediction
was right about what it measured; the shipped config is simply cheaper.

**Overlap check across all sixteen panels of the eight figures: 0 label-label
overlaps and 0 legend-label overlaps.** The entry 008 layout absorbs five extra
low-window labels without a collision.

---

## 8. STEP 5 — CLAUDE.md

Three paragraphs added to the "Band quantification" section, immediately after
the existing paragraph on band names and validation. Nothing was restructured;
no existing line was changed. They record, citing entry 009:

- that `glycine_1443` and `glycine_1458` carry `half_width` 7 and that the value
  is **forced** — 6 gives 4 points, below `MIN_POINTS`, and `measure_band`
  raises; 8 makes the windows [1435, 1451] and [1450, 1466] and
  `load_bands_config` rejects them as overlapping;
- that the result leaves **1 cm-1** between the two search windows, so moving
  either centre by one breaks the configuration;
- that the doublet was split **deliberately**, because a merged band locates the
  lower member in ech4 at every step and the upper in six of ech2's seven, so
  one name would mean two different vibrational modes depending on the sample,
  with the measured positions 1441.8–1444.3 and 1457.0–1459.5;
- that **`half_width` appears in neither `bands.csv` nor `provenance.json`**, so
  two runs differing only in a width produce indistinguishable derived trees
  holding genuinely different measurements — which matters most for exactly
  these two bands.

---

## 9. STEP 6 — full suite

    342 passed in 84.46s (0:01:24)

**Zero warnings** — pytest printed no warnings summary. Same count as before the
change: no test was added, removed or modified in this phase.

**`tests/fixtures/inspect_irradiation_sara.txt` is NOT affected.**
`git status --short tests/fixtures/` is empty, and `tests/test_cli_output.py`
passes on its own (`15 passed in 9.52s`). The reason is structural rather than
lucky: that fixture captures `inspect` output, and `inspect` reads no
configuration at all — it inventories the `.txt` spectra and prints groups and
warnings. `bands.json` is read only by `quantify`, and by `plot` under
`--annotate`. **No fixture was regenerated.**

---

## 10. Everything measured, with the numbers

| what | result |
|---|---|
| suite before | 342 passed in 82.82s |
| suite after | **342 passed in 84.46s, 0 warnings** |
| tests added or changed | none |
| golden fixture | untouched; `test_cli_output.py` 15 passed |
| HEAD | `583414a`, nothing committed |
| `bands.json` match to entry 009 §5 | **exact**, 13 bands, reference `si_522` |
| `bands.json` mtime vs `bands.csv` mtime | 23:44:40 vs 23:48:01 — not written by this phase |
| `load_bands_config` | validates, 13 bands, no noise regions |
| bands.csv before | 27,809 bytes, 184 rows, SHA-256 `665ce77a…` |
| bands.csv after | 45,874 bytes, 299 rows, SHA-256 `e48bf8e4…` |
| rows added | 115 |
| **original 8 bands, 184 rows × 16 columns** | **bit-identical** |
| worst reconstruction residual | 1.45519e-11 |
| baseline sources | all six values from `baseline.json`; none defaulted |
| provenance `generated_utc` | 2026-09-01T21:48:01.521075+00:00 |
| ech2 new bands, net 0→6 | −7.74%, +8.65%, −1.59%, −5.07%, +10.42% |
| ech2 new bands, max step-to-step | +20.79%, +32.80%, −14.43%, +15.89%, −15.17% |
| ech4 new bands, net 0→6 | −4.45%, +3.29%, −6.18%, −4.77%, −5.99% |
| ech4 new bands, max step-to-step | −12.00%, +30.06%, −27.53%, −28.94%, −22.49% |
| ech2 / ech4 new-band flags | **0 at_edge, 0 drifted**, 35 measurements each |
| ech3 new-band flags | 8 at_edge, 10 drifted of 30 |
| ech1 / ech5 / ech6 new-band flags | 1 at_edge, 1 drifted each, of 5 |
| total at_edge / drifted, all bands | 16 / 29 |
| low panel rows, predicted → measured | 3 → **3** |
| low panel reserved, predicted → measured | 40.5% → **36.7%** |
| cause of the difference | `1571`/`1673` are four characters, `1571.6`/`1673.1` six |
| high panel | 2 rows, 24.9%, unchanged |
| label-label and legend-label overlaps | **0 of 16 panels** |
| `git status --short figures/` | empty |

---

## 11. Matters next

- **`glycine_1038` sits on its lower window edge at 1029.478 in ech1, ech3 and
  ech5.** That is the [1028, 1048] boundary, and `at_edge` means the real
  maximum is probably outside the window. Entry 009 chose `half_width` 10 from
  ech2 and ech4, where the peak is at 1035–1038; these three samples put it
  lower. Widening to 15 would still clear `glycine_979` by 29 cm-1, and nothing
  else constrains it. Not changed here — the config is the experimenter's file
  and the phase specified no change to it.
- **`glycine_1443` hits its upper edge at 1449.385** in ech3 steps 4–6 and ech6
  step 0. Unlike 1038 this one cannot simply be widened: `half_width` 7 is
  forced by the doublet, as CLAUDE.md now records. If those samples matter, the
  doublet may need different centres there rather than a wider window.
- **The signal-to-noise column is now empty across 299 rows rather than 184.**
  No `noise_regions` is configured. ech2's five new bands, at heights of
  1,100–3,000 against a silicon peak near 150,000, are the weakest measurements
  in the experiment and are exactly where an SNR flag would be worth having.
- **Entry 004's A6 gap report is now partly stale.** Four of its five
  "in range but not configured" entries are configured, and the ~1440–1455 entry
  turned out to be two bands.
- **Entries 009, 010 and 011 are all uncommitted**, along with entry 008's
  figures. The working tree now carries a `data/raw/` change (the experimenter's
  own), a `CLAUDE.md` change, and three prompt-output entries.

---

## 12. Self-corrections during this phase

None. No claim made during this phase was later found wrong. Entry 009's C6
prediction was confirmed exactly; its C5 row-count prediction was confirmed and
its fraction differed for a reason that was measured rather than assumed
(section 7).

---

## 13. Files touched by this phase

Modified: `CLAUDE.md` (three paragraphs added to one section).
Added: this file, one `INDEX.md` line.
Regenerated: `data/derived/irradiation_sara/` in full — 46 corrected spectra,
`provenance.json`, `bands.csv` — and 15 figures under
`figures/irradiation_sara/` (7 from `quantify`, 8 annotated overlays). All of
that is gitignored build output.

**Not touched:** `data/raw/` in any way, including `bands.json`;
`src/`, `tests/`, `main.py`; the six
`figures/irradiation_sara/{sample}_overlay.png` reference files;
`tests/fixtures/inspect_irradiation_sara.txt`.

Nothing was committed. PHASE B ends here.
