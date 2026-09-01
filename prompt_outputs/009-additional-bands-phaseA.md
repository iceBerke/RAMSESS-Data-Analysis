# 009 — additional-bands — PHASE A

Supersedes nothing. Measures where four unconfigured glycine peaks actually sit
and what adding them to `bands.json` would cost.

Date: 2026-09-01
HEAD at time of writing: `583414a`, working tree clean, 342 tests green.

**Scope of this phase.** Read-only. Nothing created, edited, moved or deleted
except this file and its `INDEX.md` line. **`data/raw/irradiation_sara/bands.json`
was not touched** — not read-modify-written, not copied over. `quantify` and
`plot` were not run. Candidate configurations were validated by writing them to
a **scratchpad** directory outside the project and pointing `load_bands_config`
at that, which is why section 5's snippet is known to be accepted rather than
merely believed to be.

**Method.** Spectra loaded with `load_experiment`, corrected in memory with
`correct_baseline` using the parameters `resolve_baseline_config` returns from
`baseline.json` — low `lam` 1e6, `p` 0.01, `n_iter` 10, all three sourced from
`baseline.json`, none from a built-in default. Local maxima located with
`scipy.signal.find_peaks`, widths with `peak_widths` at half prominence.
Figures built in memory and closed; nothing saved.

---

## 1. Blockers and decisions needed

**Two decisions. The first is the substantive finding of this phase.**

**D1 — the 1440–1455 target is a DOUBLET, not one peak, and the two members
swap dominance between ech2 and ech4.** Measured at every step of both samples:
two resolved local maxima, one at 1441.8–1444.3 and one at 1457.0–1459.5,
separated by 12.7–17.8 cm-1 (mean 14.9 in ech2, 15.6 in ech4). Which one is
taller is **not** consistent:

- **ech4: the lower member is taller in all 7 steps** (e.g. step 0: 18,822 vs
  16,691).
- **ech2: the upper member is taller in 6 of 7 steps** (step 2 is the exception:
  2,873 vs 2,586), and at step 5 they are within 0.8% of each other (2,569 vs
  2,590).

A single band centred between them with any half_width wide enough to hold both
would locate whichever happens to be taller, so **the same band name would
measure a different vibrational mode in ech2 than in ech4**, and in ech2 would
flip between steps. That is exactly the failure the overlap check in
`load_bands_config` exists to prevent, arriving by a different route. Decide:
configure **two** bands (making it five new bands, not four), or **one** band
and accept that the identity is sample-dependent, or one band deliberately
narrowed onto a single member.

**D2 — splitting the doublet forces `half_width` 7 on both members, and that is
the only value that works.** Measured across all 23 low-window files:

    centre 1443, half_width 6:  4 points  -> below MIN_POINTS (5), measure_band raises
    centre 1443, half_width 7:  6 points  -> ok
    centre 1458, half_width 6:  4 points  -> below MIN_POINTS
    centre 1458, half_width 7:  6 points  -> ok
    half_width 8 on both:       REJECTED by load_bands_config -
      "search windows for 'glycine_1443' [1435.000, 1451.000] and
       'glycine_1458' [1450.000, 1466.000] overlap in window 'low'"

So the viable window is a single integer wide. It works, and it leaves a 1 cm-1
gap between the two search windows — the tightest thing in the whole config.
Moving either centre by 1 cm-1 breaks it. The experimenter should know the
configuration is that tightly constrained before adopting it.

Everything else is measured and unambiguous.

---

## 2. What I could NOT check, and why

- **Whether these peaks are the modes the reference table names.** I measured
  where maxima sit; assigning `1038.02` to a C–N stretch is chemistry and is the
  experimenter's call. Note the measured positions run consistently **+3 to +4
  cm-1 above** the reference table (1034→1038.0, 1565–1570→1571.6, 1670→1673.1).
  That offset is systematic across all four targets, which is suggestive of a
  calibration offset or a different sample form, but I did not investigate it
  and it is not this phase's question.
- **ech1, ech3, ech5, ech6.** The prompt scoped C1 to ech2 and ech4. A band
  configured in `bands.json` is measured in **every** sample, so
  `quantify` would apply these centres to the other four as well, and I have not
  checked that the peaks are present or that the search windows behave there.
  ech3 in particular is documented as collapsing after irr3.
- **How the added labels look.** C5's row counts and reserved fractions are
  renderer geometry from figures built in memory; no figure was saved or opened.
- **The `at_edge` and drift flags under the recommended config**, because that
  would mean running the measurement with the new bands and reporting numbers
  the experimenter might read as results. I checked only that the observed peak
  positions sit inside the proposed windows with margin (section 5), which is
  what determines whether those flags fire.
- **Whether `noise_regions` should now be configured.** Adding bands does not
  change that the signal-to-noise column is empty; it just makes more rows
  empty. Out of scope here, noted in section 6.

---

## 3. PROPOSED DEVIATIONS

**None to the phase's instructions.** Three disclosures about method:

- **Candidate configurations were validated by writing `bands.json` files into a
  scratchpad directory** outside the project and calling `load_bands_config` on
  that folder. `load_bands_config` reads only `<folder>/bands.json` and takes
  the window ranges as an argument, so this exercises the real validator without
  going near `data/raw/`. Nothing was written inside the project.
- **C1 was measured with a prominence floor of 0.5% of the panel maximum**, and
  that floor initially hid two real peaks in ech2. Re-run with no floor, ech2's
  1038 and 1673 maxima are present at **every** step (section 4, C1). The floor
  was a measurement artefact of mine, not a property of the data, and the
  corrected reading is the one reported.
- **C5 measures two scenarios**, four new bands and five, because D1 makes the
  band count itself an open question and reporting only one would have presumed
  the answer.

---

## 4. Findings

### C1 — where the four targets actually sit

Baseline-corrected, low window, all seven steps of each sample. The wave axis
carries **269 points between 1000 and 1700 cm-1, mean spacing 2.606 cm-1**, so
located positions quantise to that grid — a "spread" of 2.5 cm-1 is one grid
step, not a drifting peak.

#### Target ~1034 (C–N stretch) — ONE PEAK, at 1038.0

| | ech2 | ech4 |
|---|---|---|
| positions across 7 steps | 1035.176 / 1038.022 | **1038.022** (1038.020 at step 0) |
| spread | 2.846 cm-1 (one grid step) | **0.002 cm-1** |
| corrected height | 1,620 – 1,957 | 10,595 – 12,114 |
| FWHM | 9.6 – 10.5 | 12.2 – 13.0 |

One resolved maximum in the 1005–1065 span at every step of both samples. In
ech4 it is rock solid on one grid point. In ech2 it alternates between two
adjacent grid points, which is quantisation, not movement.

**Correction to my own first measurement:** with a 0.5%-of-maximum prominence
floor, ech2 showed "NO local max" at four steps. With no floor it is a genuine
local maximum at **all seven**, prominence 476–877:

    step 0: 1035.176 h=1859.7 prom=877.2      step 4: 1038.022 h=1956.9 prom=680.8
    step 1: 1035.176 h=1779.3 prom=717.8      step 5: 1038.022 h=1899.2 prom=730.7
    step 2: 1038.022 h=1783.3 prom=708.7      step 6: 1035.176 h=1715.8 prom=537.4
    step 3: 1038.022 h=1620.1 prom=476.1

ech2's glycine is roughly a sixth of ech4's here, which is why it fell under a
floor scaled to the panel maximum — a maximum dominated by silicon.

#### Target ~1440–1455 (CH2 deformation) — **CLUSTER: TWO PEAKS**

This is D1. Two resolved maxima in the 1415–1495 span, at **every step of both
samples** (one exception: ech2 step 3, where the lower member falls under the
prominence floor).

| member | positions observed | FWHM (ech4) |
|---|---|---|
| lower | 1441.760 or 1444.303 | ~9.1 |
| upper | 1456.993 or 1459.526 | ~7.4 |

Separation: ech2 12.69–15.23 (mean 14.87), ech4 15.22–17.77 (mean 15.59) cm-1.

**Which is tallest, per step:**

| step | ech2 lower | ech2 upper | taller | ech4 lower | ech4 upper | taller |
|---|---|---|---|---|---|---|
| 0 | 2,150.3 | 2,814.5 | upper | 18,822.0 | 16,690.8 | **lower** |
| 1 | 2,163.2 | 3,022.1 | upper | 18,000.5 | 15,965.9 | **lower** |
| 2 | 2,872.6 | 2,586.0 | **lower** | 18,986.3 | 16,589.7 | **lower** |
| 3 | (under floor) | 2,599.6 | upper | 20,701.2 | 17,669.6 | **lower** |
| 4 | 2,536.7 | 2,724.6 | upper | 18,949.1 | 18,624.5 | **lower** |
| 5 | 2,569.2 | 2,590.4 | upper (by 0.8%) | 24,646.1 | 21,608.6 | **lower** |
| 6 | 2,336.4 | 2,769.8 | upper | 19,440.7 | 15,658.9 | **lower** |

**ech4: lower taller 7/7. ech2: upper taller 6/7.** The two samples disagree,
and ech2 nearly ties at step 5.

Note also that the plain argmax over the 1415–1495 span is **1416.221 at every
step of both samples** — the tail of the existing 1412 band, not either member
of the doublet. Any search window that reaches down to 1416 will report the 1412
peak under a new name. This is why the members must be located as local maxima,
not as a span maximum.

#### Target ~1565–1570 (COO-/NH3) — ONE PEAK, at 1571.6

| | ech2 | ech4 |
|---|---|---|
| positions | 1569.165 / 1571.617 | **1571.617** (1571.620 at step 0) |
| spread | 2.452 cm-1 (one grid step) | **0.003 cm-1** |
| height | 1,574 – 1,956 | 13,147 – 18,766 |
| FWHM | 14.1 – 16.3 | 13.6 – 14.4 |

One maximum, every step, both samples, no ambiguity. The broadest of the four.

#### Target ~1670 (COO-/NH3) — ONE PEAK, at 1673.1

| | ech2 | ech4 |
|---|---|---|
| positions | 1670.719 / 1673.103 | **1673.103** (1673.100 at step 0) |
| spread | 2.384 cm-1 (one grid step) | **0.003 cm-1** |
| height | 1,098 – 1,294 | 8,625 – 11,487 |
| FWHM | 13.9 (measured at step 1 only; the other six steps fell under the first run's prominence floor, so no width was taken there) | 12.2 – 13.5 |

Same correction as 1038: ech2's maximum is real at all seven steps, prominence
450–848, and only looked absent under my prominence floor.

Scope: ech2 and ech4, low window, all seven steps each, from the real
`data/raw/` files.

### C2 — does `centre ± half_width` fit inside the low window?

The measured common low-window range, from `common_window_ranges` over all 23
low files, is **201.912354 – 1824.880**. `measure_band` requires the whole
search window inside it, so the usable centre range is
**[201.912 + half_width, 1824.880 − half_width]**.

Every proposed band fits, with very large margins:

| band | half_width | search window | margin below | margin above |
|---|---|---|---|---|
| 1038 | 10 | 1028 – 1048 | 826.09 | 776.88 |
| 1443 | 7 | 1436 – 1450 | 1234.09 | 374.88 |
| 1458 | 7 | 1451 – 1465 | 1249.09 | 359.88 |
| 1571 | 15 | 1556 – 1586 | 1354.09 | 238.88 |
| 1673 | 15 | 1658 – 1688 | 1456.09 | 136.88 |

The tightest is 1673's upper margin at 136.88 cm-1 — over nine half-widths of
slack. **None of these is anywhere near the window edge.** CONFIRMED.

### C3 — would any proposed window overlap an existing one?

Existing low-window search windows: `si_522` [507, 537], `glycine_893`
[878, 908], `glycine_979` [964, 994], `glycine_1328` [1313, 1343],
`glycine_1412` [1397, 1427].

**No proposed window overlaps any existing one.** Gaps to the nearest neighbour:

| proposed | window | nearest neighbour | gap |
|---|---|---|---|
| 1038 ± 10 | 1028 – 1048 | `glycine_979` ends 994 | **34.0** |
| 1443 ± 7 | 1436 – 1450 | `glycine_1412` ends 1427 | **9.0** |
| 1458 ± 7 | 1451 – 1465 | 1443's window ends 1450 | **1.0** |
| 1571 ± 15 | 1556 – 1586 | 1458's window ends 1465 | **91.0** |
| 1673 ± 15 | 1658 – 1688 | 1571's window ends 1586 | **72.0** |

The 1 cm-1 gap between the two doublet members is D2 and is the binding
constraint. Note the validator rejects **touching** windows, not only
intersecting ones — the test is `first.centre + first.half_width >=
second.centre - second.half_width`, so a gap of exactly 0 is also refused.

**A warning about the obvious alternative:** `half_width` 15 on a single band at
1443 gives [1428, 1458], which does *not* overlap `glycine_1412` [1397, 1427] —
it clears by 1 cm-1 and would be accepted — but the window **contains the upper
doublet member at 1456.99**. It would validate cleanly and then measure the
wrong peak, sample-dependently. The overlap check cannot catch this because the
competing peak is not a configured band.

### C4 — is `half_width` 15 appropriate?

Measured FWHM, and the point count each candidate half_width yields across all
23 low files:

| band | FWHM | half_width 15 appropriate? | recommended | points (min across 23 files) |
|---|---|---|---|---|
| 1038 | 9.6 – 13.0 | Workable but generous — [1023, 1053] is ~2.4 FWHM and holds no competing peak | **10** | 7 |
| 1443 | ~9.1 | **NO.** [1428, 1458] swallows the upper doublet member | **7** (forced, D2) | 6 |
| 1458 | ~7.4 | **NO.** [1443, 1473] swallows the lower member | **7** (forced, D2) | 6 |
| 1571 | 13.6 – 16.3 | **Yes** — the broadest of the four; ±15 is about one FWHM either side | **15** | 12 |
| 1673 | 12.2 – 13.5 | **Yes** — isolated, nothing within 70 cm-1 | **15** | 13 |

So `half_width` 15 is right for the two broad isolated bands, generous but
harmless for 1038, and **wrong for both doublet members** — for the specific
reason that the neighbouring peak is inside the window, not because of width.

`MIN_POINTS` is 5 and the local spacing is ~2.6 cm-1, so 7 is also close to the
floor of what is measurable: half_width 6 gives 4 points and `measure_band`
would raise. The recommended values all give 6 or more, on every one of the 23
files, so the count does not depend on which file is being measured.

### C5 — the label cost

Measured on real figures at `ANNOTATION_FONT_SIZE` 12, the shipped value.
Identical for ech2 and ech4 in every scenario, as expected — entry 008
established that placement depends only on centres, panel geometry and font.

| scenario | low-window bands | rows | reserved band |
|---|---|---|---|
| **current** | 5 | 1 | **13.1%** |
| **A — four new bands** (doublet as one) | 9 | **2** | **28.7%** |
| **B — five new bands** (doublet split) | 10 | **3** | **40.5%** |

Row membership, both scenarios, both samples:

    Scenario A   row 0: 522, 893, 979, 1328, 1412, 1571.6, 1673.1
                 row 1: 1038, 1443

    Scenario B   row 0: 522, 893, 979, 1328, 1412, 1571.6, 1673.1
                 row 1: 1038, 1443
                 row 2: 1458

**The pairs pushed down are exactly the two the prompt predicted**, plus one
more in scenario B:

- **979 → 1038**, 59 cm-1 apart, which at the low panel's 5.057 cm-1 per point
  is about 16 px against the ~19.6 px two 12-point rotated labels need. `1038`
  drops to row 1.
- **1412 → 1443**, 31 cm-1, about 8.5 px. `1443` drops to row 1, where it clears
  `1038` comfortably.
- **1443 → 1458** (scenario B only), 15 cm-1, about 4.1 px — far too tight for
  row 1, so `1458` opens row 2.

`1571.6` and `1673.1` both stay in row 0: they are 106 and 101 cm-1 from their
left neighbours, which clears easily.

**Cost in context.** Scenario B's 40.5% is the largest reserved band this
project has produced, but it is still below the 58.1% that entry 007 measured
for the *high* window at font 12 with full band names — the configuration that
prompted the switch to numeric labels. Entry 008's font-size table applies
unchanged if 40.5% is too much: dropping `ANNOTATION_FONT_SIZE` to 10 would
shrink it, at the cost of legibility, and would not change the row count, since
rows are decided by line height and every pair here is far outside the
threshold.

### C6 — what re-running `quantify` would change

**The eight existing bands' `height` values would be bit-identical. Proven, not
only traced.**

**The trace.** In `measure_all_bands`, the correction runs per spectrum before
any band is considered:

    for spectrum in spectra:
        values, _ = correct_baseline(spectrum, **baseline_params[spectrum.window])
        corrected[(spectrum.sample, spectrum.window, spectrum.step)] = (spectrum, values)

Nothing in that loop mentions `bands`. Noise likewise comes from
`noise_regions`, not from the band set. Each band is then measured
independently:

    measurement = measure_band(
        spectrum.wave, values, spec.centre, spec.half_width,
        noise=noise[(sample, window, step)],
    )

and `measure_band` in `bands.py` is a pure function of `(wave, intensity,
centre, half_width, noise)` — it holds no state, accumulates nothing, and never
sees another band. The only cross-band coupling in the whole path is
`height_norm` and `area_norm`, which divide by the reference band's values via
`by_sample_step`; the reference stays `si_522`, so those are unchanged too.

The iteration order does change — `[reference] + sorted(others)` reorders when
names are added — but order affects only which row is appended first, not any
computed value.

**The proof.** `measure_all_bands` was run twice in memory, once with the
current 8 bands and once with 13, and every one of the 184 existing rows
compared across `height`, `area`, `position`, `position_drift`, `n_points`,
`at_edge`, `height_norm`, `area_norm`, `cross_window` and `centre`:

    rows: current 184  augmented 299
    existing-band rows compared: 184
    columns differing on any existing row: NONE - bit-identical

**So the heights quoted in the presentation material are safe.** What *would*
change:

- **`bands.csv` is not byte-identical.** It gains 115 rows, and since it is
  sorted by `(sample, step, band)` the new names interleave alphabetically, so
  existing rows move position within the file. Their values do not.
- **`provenance.json` gets a new `generated_utc`.** The baseline parameters,
  their sources, and all 46 input hashes would be identical.
- **The 46 derived `*_corrected.txt` files** are written from spectra and
  baseline parameters only, with no band involvement, so their contents would be
  identical — mtimes aside.
- **Figures** `{sample}_bands.png` and `bands_all_samples.png` gain series, and
  the all-samples figure gains panels.
- **`print_band_summary`'s stdout** gains rows and columns.
- **A bad config costs nothing.** `load_bands_config` runs before any write, and
  `quantify_experiment` measures before it writes, so a rejected or failing
  configuration leaves no derived tree at all.

### C7 — `provenance.json` records no hash of `bands.json`. CONFIRMED

Read from the file on disk:

    top-level keys:            ['baseline_parameters', 'experiment', 'generated_utc', 'source_files']
    source_files entry keys:   ['n_points', 'name', 'sample', 'sha256', 'step', 'window']
    'bands.json' appears anywhere in the file:  False
    any band name or centre recorded:           False

`write_provenance` builds exactly those four keys, and `source_files` is
constructed from `spectra` — the `.txt` files — so no band configuration reaches
it by any path.

**What that means.** Given a `bands.csv` found later, you can prove which *raw
files* and which *baseline parameters* produced it, but **not which band set**,
except by inference from the file's own contents. In practice the CSV is
partly self-describing: it carries one row per band with that band's `name`,
`centre` and `window`, so the band names and centres are recoverable from the
CSV itself. **`half_width` is not** — it appears in no column — so two runs
differing only in a `half_width` produce CSVs that are indistinguishable as to
configuration, while genuinely holding different measurements. That gap is
exactly what this change would widen, since it introduces two bands whose
`half_width` of 7 is load-bearing and unusual.

This restates entry 004's section 2 finding and confirms it is still true at
`583414a`.

---

## 5. The JSON snippet

**Not written to any file.** This is text for the experimenter to paste into
`data/raw/irradiation_sara/bands.json` if he chooses to. It is the **scenario B**
configuration — the doublet split — and it was **validated by the real
`load_bands_config` against the measured window ranges**, from a scratchpad
copy: `RECOMMENDED CONFIG VALIDATES: reference si_522 - 13 bands`.

```json
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
```

The five existing entries and the three high-window ones are unchanged from the
current file; only the five `glycine_1038` / `1443` / `1458` / `1571` / `1673`
lines are new.

**One line of justification each, from C1 and C4:**

- **`glycine_1038`, half_width 10** — a single peak at 1038.022 in ech4 with a
  spread of 0.002 cm-1 across seven steps, FWHM 9.6–13.0; half_width 10 covers
  both grid positions ech2 visits with ~4 cm-1 to spare and yields 7 points on
  every file, while 15 would be twice the FWHM for no gain.
- **`glycine_1443`, half_width 7** — the lower doublet member, observed only at
  1441.760 and 1444.303, FWHM ~9.1; 7 is forced from both sides (6 gives 4
  points, below `MIN_POINTS`; 8 overlaps its partner) and still leaves ~5.7 cm-1
  between the observed positions and either edge.
- **`glycine_1458`, half_width 7** — the upper doublet member, observed only at
  1456.993 and 1459.526, FWHM ~7.4; same forced half_width, and separating it
  from 1443 is what stops one band reporting the lower peak in ech4 and the
  upper in ech2.
- **`glycine_1571`, half_width 15** — a single broad peak at 1571.617 in ech4
  with a spread of 0.003 cm-1, FWHM 13.6–16.3, the broadest of the four;
  half_width 15 is about one FWHM either side and there is no other peak within
  70 cm-1.
- **`glycine_1673`, half_width 15** — a single peak at 1673.103 in ech4, spread
  0.003 cm-1, FWHM 12.2–13.5, isolated with 72 cm-1 of clear space below and
  137 cm-1 above; nothing constrains the window, so the project's default width
  applies.

**If D1 is answered the other way** — one band for the doublet instead of two —
the merged alternative also validates (`MERGED-DOUBLET ALTERNATIVE VALIDATES:
12 bands`): replace the two `1443`/`1458` entries with
`"glycine_1450": {"centre": 1450, "half_width": 12, "window": "low"}`. It costs
one fewer label row (scenario A, 2 rows / 28.7% instead of 3 / 40.5%) and buys
that with a band whose located peak is the lower member in ech4 and the upper in
ech2. I do not recommend it, for the reason in D1, but it is a legitimate choice
if the doublet is not the point of the analysis.

---

## 6. Matters next

- **D1 and D2 gate everything.** Nothing should be pasted into `bands.json`
  until the doublet question is settled.
- **The other four samples are unchecked.** `quantify` measures every sample, so
  ech1, ech3, ech5 and ech6 would get these bands too. Worth a look before the
  run, particularly ech3, which is documented as collapsing after irr3.
- **`half_width` is invisible in `bands.csv` and unrecorded in
  `provenance.json`** (C7). This change makes that matter more than it did,
  because two of the five new bands carry an unusual `half_width` of 7 that is
  load-bearing. Recording the band configuration in `provenance.json` would
  close it; that is a code change and out of scope here.
- **Entry 004's A6 gap report can be updated once this lands** — four of the
  five entries it listed as "in range but not configured" would become
  configured, and the ~1440–1455 entry turns out to be two bands rather than one.
- **The systematic +3 to +4 cm-1 offset** between the reference table and the
  measured positions holds for all four targets. Not investigated; worth knowing
  before the numbers go into a talk.
- **Adding bands does not populate `signal_to_noise`.** No `noise_regions` is
  configured, so all 299 rows would carry an empty noise column, and the
  weak-band flagging would remain inert. ech2's new bands are the weakest
  measurements in the experiment (heights of 1,100–2,000 against a silicon peak
  of 150,000), which is precisely where an SNR flag would earn its keep.

---

## 7. Self-corrections during this phase

**One, and it changed a reported result.** My first C1 measurement used a
prominence floor of 0.5% of the panel maximum and reported "NO local max" for
ech2 at four of seven steps at 1038, and six of seven at 1673. That was wrong —
an artefact of a floor scaled to a panel maximum that silicon dominates. Re-run
with no floor, **both peaks are genuine local maxima at all seven steps of
ech2**, with prominences of 476–877 (1038) and 450–848 (1673). The corrected
reading is what section 4 reports; the flawed one is recorded here so the
correction is not invisible.

Nothing else measured during this phase was later found wrong.

---

## 8. Everything measured, with the numbers

| what | result |
|---|---|
| HEAD | `583414a`, tree clean |
| baseline parameters used | low `lam` 1e6, `p` 0.01, `n_iter` 10, all from `baseline.json` |
| common low-window range | 201.912354 – 1824.880 |
| wave spacing 1000–1700 | mean 2.606 cm-1, 269 points |
| ~1034 → measured | **1038.02**, one peak, FWHM 9.6–13.0 |
| ech4 1038 spread / height | 0.002 cm-1 / 10,595 – 12,114 |
| ech2 1038 spread / height | 2.846 cm-1 / 1,620 – 1,957 |
| ~1440–1455 → measured | **DOUBLET**: 1441.8–1444.3 and 1457.0–1459.5 |
| doublet separation | ech2 12.69–15.23 (mean 14.87); ech4 15.22–17.77 (mean 15.59) |
| doublet dominance | ech4 lower 7/7; ech2 upper 6/7, near-tie at step 5 |
| argmax over 1415–1495 | 1416.221 every step — the 1412 band's tail, not either member |
| ~1565–1570 → measured | **1571.62**, one peak, FWHM 13.6–16.3 |
| ech4 1571 spread / height | 0.003 cm-1 / 13,147 – 18,766 |
| ~1670 → measured | **1673.10**, one peak, FWHM 12.2–13.5 |
| ech4 1673 spread / height | 0.003 cm-1 / 8,625 – 11,487 |
| reference-table offset | measured positions +3 to +4 cm-1, all four targets |
| all proposed windows inside low range | yes; tightest margin 136.88 cm-1 |
| overlaps with existing bands | none; tightest gap 9.0 cm-1 (1412 → 1443) |
| tightest gap in proposed config | 1.0 cm-1, between 1443 and 1458 |
| half_width 6 on doublet members | 4 points — below `MIN_POINTS` 5, would raise |
| half_width 7 on doublet members | 6 points on all 23 low files |
| half_width 8 on both | rejected: windows [1435,1451] and [1450,1466] overlap |
| rows / reserved, current | 1 row / 13.1% |
| rows / reserved, +4 bands | 2 rows / 28.7% |
| rows / reserved, +5 bands | 3 rows / 40.5% |
| pairs pushed down | 979→1038, 1412→1443, and 1443→1458 in scenario B |
| existing 184 rows after adding bands | **bit-identical** across 10 compared columns |
| row count, current → augmented | 184 → 299 |
| `provenance.json` top-level keys | `baseline_parameters`, `experiment`, `generated_utc`, `source_files` |
| `bands.json` referenced in provenance | no |
| recommended config validates | yes — 13 bands, reference `si_522` |
| merged-doublet alternative validates | yes — 12 bands |

---

## 9. Files touched by this phase

`prompt_outputs/009-additional-bands-phaseA.md` (this file) and one appended
line in `prompt_outputs/INDEX.md`. Nothing else.
**`data/raw/irradiation_sara/bands.json` is unchanged**, as are `data/derived/`,
`figures/`, `src/`, `tests/` and `main.py`.

PHASE A ends here. Awaiting answers to D1 and D2 and an explicit "PROCEED".
