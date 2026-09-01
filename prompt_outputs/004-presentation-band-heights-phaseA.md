# 004 — presentation-band-heights — PHASE A

Supersedes nothing.

Date: 2026-09-01
HEAD at time of writing: `42557f4`
Working tree at start and end of this phase: clean apart from this file and the
`INDEX.md` line it adds.

**Goal being verified.** A table of absolute, baseline-corrected peak heights
for ech2 and ech4 only, comparable between those two samples, within a single
spectral window. The experimenter believes
`data/derived/irradiation_sara/bands.csv` already contains this.

**Scope of this phase.** Read-only. Nothing was created, edited, moved or
deleted except this file and the `INDEX.md` line. `quantify` and `plot` were not
run. Nothing was written under `data/derived/` or `figures/`. Everything
executed ran through `.venv\Scripts\python.exe`.

**How the numbers below were produced.** One throwaway read-only script at
`…\scratchpad\verify.py` (session scratchpad, outside the project tree). It
imports `ramsess.report.BANDS_CSV_COLUMNS` and `ramsess.io.load_experiment`,
reads `bands.csv` and `provenance.json`, re-hashes the raw files, and prints. It
opens no file for writing. It is not part of the repository and is not proposed
to become part of it.

---

## 1. Blockers and decisions needed

**One decision, and it is the substantive finding of this phase.**

**D1 — the window constraint conflicts with the sample-comparison goal, and the
experimenter must choose which one gives.** The goal asks for heights
"comparable between those two samples, within a single spectral window". Both
halves are satisfiable individually and the CSV already holds the numbers for
either. What is not established is that a height in ech2 and a height in ech4
are on the same scale at all — see A9. The single-window constraint removes one
comparability hazard (low and high are separate sweeps) but not the one that
actually threatens an ech2-vs-ech4 comparison, which is acquisition conditions
between two different samples. Concretely, at step 0 in the low window,
`glycine_893` is 6,343.5 in ech2 and 43,634.2 in ech4 — a factor of 6.9. Nothing
in `data/raw/irradiation_sara/` says whether that factor is chemistry or laser
power. Decide: present the comparison with the caveat stated on the table, or
restrict deliverable 2 to within-sample trends.

Everything else in the request checks out and needs no decision.

---

## 2. What I could NOT check, and why

- **Whether ech2 and ech4 were acquired under the same laser power, integration
  time, objective, slit width and detector gain.** There is no acquisition
  metadata in the repository at all (A9). This cannot be established from the
  data, from the code, or from anything in git. Only the experimenter or the
  instrument's own logs can answer it. Marked UNKNOWN FROM THE DATA ALONE, not
  assumed either way.
- **Whether `bands.json` has changed since `bands.csv` was written.**
  `provenance.json` records the baseline parameters and the hashes of the raw
  `.txt` files, but it records no hash of `bands.json` and no copy of the band
  definitions. I worked around this indirectly rather than leaving it open: the
  CSV carries a `centre` and a `window` per band, and all eight match the current
  `bands.json` exactly (table in A5). That proves centres and windows are
  unchanged. It does **not** prove `half_width` is unchanged, because
  `half_width` is not written to the CSV. A change to `half_width` alone since
  the run would be undetectable from the artefacts on disk. Corroborating but
  not conclusive: `bands.json` has mtime 2026-08-28 16:44, older than the CSV's
  2026-08-29 21:52.
- **Whether the `signal_to_noise` path produces correct values on real data.**
  It has never run on real data — no `noise_regions` is configured, so the whole
  column is empty (A5, A7). This matches what `CLAUDE.md` already records under
  "Audited and deliberately not acted on". I did not test it; I only confirmed
  it is inactive.
- **That no code outside `src/` and `main.py` produces an absolute-height
  comparison.** A10's grep covered `src/**/*.py` and `main.py`. It did not cover
  `tests/`. Scoped accordingly in A10.

---

## 3. PROPOSED DEVIATIONS

**None to the phase's instructions.** Two reporting refinements, disclosed
because they are departures from the literal wording of the request:

- **A6 needed a fourth and a fifth category.** The request specified three:
  CONFIGURED, IN RANGE BUT NOT CONFIGURED, OUTSIDE THE ACQUIRED RANGE. Four of
  the sixteen entries are broad envelopes (~2850–3000, ~3000–3100, ~3200–3550)
  or otherwise do not fall cleanly into one bucket: a 30 cm-1 search window
  configured inside a 150 cm-1 envelope is neither "configured" nor "not
  configured" honestly. I used PARTIALLY CONFIGURED and PARTIALLY IN RANGE for
  those, and said in each case exactly what is and is not covered. Forcing them
  into three buckets would have lost the distinction that matters.
- **A9 reports one observation that is not acquisition metadata but is worth
  recording:** `desktop.ini` names two files that do not exist on disk. Detail
  in A9. It is not metadata and does not bear on comparability; it is recorded
  because a later reader finding it should not have to re-derive what it is.

---

## 4. Findings

### A1 — does `bands.csv` exist? CONFIRMED

    data/derived/irradiation_sara/bands.csv
    size  = 27809 bytes
    mtime = 2026-08-29 21:52:17.120163900 +0200
    lines = 185   (1 header + 184 data rows)

Confirmed by `stat` and by `csv.reader`, which counted 184 data rows
independently of the line count.

It is **not tracked in git** — `git ls-files --error-unmatch` errors, and
`git check-ignore -v` gives:

    .gitignore:21:data/derived/	data/derived/irradiation_sara/bands.csv

That is correct and expected: derived data is build output. It means the file
exists only in this working tree and a fresh clone has none.

Scope: the file, and the repository's git state.

### A2 — is the header exactly `BANDS_CSV_COLUMNS`? CONFIRMED

Actual first line read from the file:

    sample,window,step,band,centre,position,position_drift,height,area,n_points,at_edge,noise,signal_to_noise,height_norm,area_norm,cross_window

`BANDS_CSV_COLUMNS` imported live from `ramsess.report` and joined the same way:

    sample,window,step,band,centre,position,position_drift,height,area,n_points,at_edge,noise,signal_to_noise,height_norm,area_norm,cross_window

List-equality of the parsed header against the imported constant: `True`.

Scope: this file against this constant, compared as lists, not as strings.

### A3 — is `height` the corrected intensity at the located maximum? CONFIRMED

Traced the real call path. Four hops, each quoted from the current source.

**Hop 1 — `quantify_experiment` calls `measure_all_bands` before any write.**
In `report.py`, inside `quantify_experiment`:

    rows = measure_all_bands(wanted, bands, reference, noise_regions, baseline_params)

    written, worst = write_derived_spectra(…)

**Hop 2 — `measure_all_bands` corrects every spectrum first.** In `report.py`,
inside `measure_all_bands`:

    from ramsess.analysis import correct_baseline
    …
    corrected: dict[tuple[str, str, int], tuple[Spectrum, np.ndarray]] = {}
    for spectrum in spectra:
        values, _ = correct_baseline(spectrum, **baseline_params[spectrum.window])
        corrected[(spectrum.sample, spectrum.window, spectrum.step)] = (spectrum, values)

`values` is the corrected array. The fitted baseline is discarded here (`_`).

**Hop 3 — `correct_baseline` is a pure subtraction.** In `analysis.py`:

    baseline = fit_baseline(spectrum.intensity, lam=lam, p=p, n_iter=n_iter)
    corrected = np.asarray(spectrum.intensity, dtype=np.float64) - baseline
    return corrected, baseline

Subtraction only. No scaling, no division, no normalisation.

**Hop 4 — `measure_band` receives the corrected array, not the raw one.** In
`report.py`, inside `measure_all_bands`:

    measurement = measure_band(
        spectrum.wave,
        values,
        spec.centre,
        spec.half_width,
        noise=noise[(sample, window, step)],
    )

The second positional argument is `values` — the corrected array from hop 2 —
and `measure_band`'s second parameter is `intensity`. So the measurement runs on
baseline-subtracted data.

**Where `height` is assigned.** In `bands.py`, inside `measure_band`:

    window_wave = wave[mask]
    window_intensity = intensity[mask]
    peak = int(np.argmax(window_intensity))

    return BandMeasurement(
        …
        position=float(window_wave[peak]),
        height=float(window_intensity[peak]),

`peak` is the index of the maximum **inside the search window**, and `position`
and `height` are read at that same index. So `height` is the corrected intensity
at the located maximum, not at the configured centre. The docstring agrees:
`height` is documented as "Corrected intensity at ``position``."

**Does anything transform `height` between measurement and the CSV write?
No.** The full set of writes and reads of the key `"height"` in `report.py`:

    1157:                "height": measurement.height,            # row assignment
    1167:                    "height": measurement.height,        # reference anchor, separate dict
    1174:        height = anchor["height"] if anchor else None    # read only
    1176:        row["height_norm"] = (                           # writes a DIFFERENT key
    1177:            row["height"] / height if height not in (None, 0.0) else None

Line 1157 is the only assignment to `row["height"]`. The division at 1176–1177
writes `height_norm`, a separate column; `row["height"]` is read, never
rebound. And `write_bands_csv` copies without touching values:

    for row in sorted(rows, key=lambda r: (r["sample"], r["step"], r["band"])):
        writer.writerow({key: row.get(key) for key in BANDS_CSV_COLUMNS})

**Conclusion:** `height` in `bands.csv` is baseline-corrected, absolute, in raw
instrument counts, measured at the located maximum, with no normalisation and no
scaling of any kind applied to it.

Scope: `quantify_experiment`, `measure_all_bands` and `write_bands_csv` in
`report.py`; `correct_baseline` and `fit_baseline` in `analysis.py`;
`measure_band` in `bands.py`. The grep for `"height"` was over `src/**/*.py` and
`main.py`.

### A4 — was the CSV produced with the current baseline parameters? CONFIRMED — the file is CURRENT, not stale

`provenance.json` records:

    generated_utc: 2026-08-29T19:52:17.112903+00:00

Baseline parameters as recorded, with their sources:

| window | lam | source | p | source | n_iter | source |
|--------|-----|--------|---|--------|--------|--------|
| low | 1000000.0 | `baseline.json` | 0.01 | `baseline.json` | 10 | `baseline.json` |
| high | 100000000.0 | `baseline.json windows.high` | 0.01 | `baseline.json` | 10 | `baseline.json` |

Current `data/raw/irradiation_sara/baseline.json`, verbatim:

    {
      "lam": 1e6,
      "p": 0.01,
      "n_iter": 10,
      "windows": { "high": { "lam": 1e8 } }
    }

These agree exactly: top-level `lam` 1e6 = 1000000.0 for low, `windows.high.lam`
1e8 = 100000000.0 for high, `p` and `n_iter` from the top level for both. Every
source string names `baseline.json`; none says "built-in default", so no
parameter fell back.

**Input hashes.** `content_hash` in `report.py` is
`hashlib.sha256(path.read_bytes()).hexdigest()` — raw bytes. Re-hashed all 46
recorded files against the current `data/raw/irradiation_sara/*.txt`:

    recorded files: 46   matching: 46   mismatched: 0   missing: 0
    raw *.txt on disk: 46
    untracked-by-provenance raw files: []
    provenance files no longer on disk: []

Every recorded hash still matches, no raw file has appeared or disappeared, and
the set is exactly the 46 files. Note `.gitattributes` pins `data/raw/** -text`,
which is what keeps these byte hashes valid across platforms.

**Verdict: the `bands.csv` on disk is current.** It was produced with the
baseline parameters now in `baseline.json`, from the raw files now on disk,
unmodified. See section 2 for the one residual gap — `half_width` is not
recoverable from either the CSV or `provenance.json`.

Scope: `provenance.json`, `baseline.json`, and all 46 raw `.txt` files.

### A5 — the band configuration

`data/raw/irradiation_sara/bands.json`, verbatim:

    {
      "reference": "si_522",
      "bands": {
        "si_522":       {"centre": 522,  "half_width": 15, "window": "low"},
        "glycine_893":  {"centre": 893,  "half_width": 15, "window": "low"},
        "glycine_979":  {"centre": 979,  "half_width": 15, "window": "low"},
        "glycine_1328": {"centre": 1328, "half_width": 15, "window": "low"},
        "glycine_1412": {"centre": 1412, "half_width": 15, "window": "low"},
        "glycine_2975": {"centre": 2975, "half_width": 15, "window": "high"},
        "glycine_3012": {"centre": 3012, "half_width": 15, "window": "high"},
        "glycine_3146": {"centre": 3146, "half_width": 15, "window": "high"}
      }
    }

Eight bands. Every `half_width` is 15, so every search window is 30 cm-1 wide.

| band | centre | half_width | window | search window |
|------|--------|------------|--------|---------------|
| si_522 | 522 | 15 | low | 507–537 |
| glycine_893 | 893 | 15 | low | 878–908 |
| glycine_979 | 979 | 15 | low | 964–994 |
| glycine_1328 | 1328 | 15 | low | 1313–1343 |
| glycine_1412 | 1412 | 15 | low | 1397–1427 |
| glycine_2975 | 2975 | 15 | high | 2960–2990 |
| glycine_3012 | 3012 | 15 | high | 2997–3027 |
| glycine_3146 | 3146 | 15 | high | 3131–3161 |

**`reference` is `si_522`.**

**`noise_regions`: ABSENT.** The key does not exist in the file —
`'noise_regions' in cfg` is `False`, and the config's top-level keys are exactly
`['bands', 'reference']`. Note this differs from the example in `CLAUDE.md`,
which shows a `noise_regions` block; that is an illustration of the schema, not
a description of this file. Consequences, both confirmed in the CSV: the `noise`
column is empty for all 184 rows (the set of distinct values is `{''}`), and
`signal_to_noise` is empty throughout. `quantify` would have printed
"no noise_regions configured … signal-to-noise will not be computed".

**Cross-check of the CSV against the current config** (the workaround described
in section 2):

    band            csv_centre  cfg_centre  csv_window cfg_window  match
    glycine_1328        1328.0        1328        low        low   True
    glycine_1412        1412.0        1412        low        low   True
    glycine_2975        2975.0        2975       high       high   True
    glycine_3012        3012.0        3012       high       high   True
    glycine_3146        3146.0        3146       high       high   True
    glycine_893          893.0         893        low        low   True
    glycine_979          979.0         979        low        low   True
    si_522               522.0         522        low        low   True
    bands in csv not in config: []

Scope: `bands.json` and `bands.csv`.

### A6 — gap report: configured bands vs the shifts of interest

**First, the window bounds were verified against the data rather than trusted.**
Loaded all 46 spectra through `ramsess.io.load_experiment` and took per-file
min and max:

    low : 23 files   min of mins = 201.912   max of mins = 201.912
                     min of maxs = 1824.880  max of maxs = 1824.880
    high: 23 files   min of mins = 2372.977  max of mins = 2372.980
                     min of maxs = 3503.140  max of maxs = 3503.141

The stated bounds — low 201.912–1824.880, high 2372.977–3503.141 — are
**CONFIRMED**. The high window varies by 0.003 cm-1 across files, which is the
documented low-precision export (`ech4_high_0.txt` and `ech4_low_0.txt`, the two
headerless files, see A9), well under the 0.01 threshold and not an axis
mismatch. The unacquired gap between the windows is 1824.880–2372.977.

One constraint that matters for any future band: `measure_band` raises if
`centre ± half_width` is not entirely inside the data range. With
`half_width` 15 the usable centres are 216.912–1809.880 in low and
2387.977–3488.141 in high — narrower than the acquired range at each end.

| shift | assignment | detail |
|-------|-----------|--------|
| ~470–480 amorphous Si, broad | IN RANGE BUT NOT CONFIGURED (low) | Inside low 201.912–1824.880. Nearest configured band is `si_522` at 507–537, which does not reach 480. |
| ~520–521 crystalline Si, Si–Si optical phonon | **CONFIGURED** — `si_522` | Search window 507–537 contains it. Measured position is 522.251 in every ech2 and ech4 step. |
| ~893 glycine C–C stretch | **CONFIGURED** — `glycine_893` | Search window 878–908. |
| ~1034 glycine C–N stretch | IN RANGE BUT NOT CONFIGURED (low) | Inside low. Falls between `glycine_979` (964–994) and `glycine_1328` (1313–1343); neither reaches it. |
| ~1324–1325 glycine CH2 twisting | **CONFIGURED** — `glycine_1328` | Search window 1313–1343 contains both ends. |
| ~1410 glycine COO- symmetric stretch | **CONFIGURED** — `glycine_1412` | Search window 1397–1427. |
| ~1440–1455 glycine CH2 deformation | IN RANGE BUT NOT CONFIGURED (low) | Inside low. `glycine_1412` stops at 1427, short of 1440. |
| ~1565–1570 glycine COO- / NH3-related | IN RANGE BUT NOT CONFIGURED (low) | Inside low (max 1824.880). No configured band above 1427 in low. |
| ~1670 glycine COO- / NH3-related | IN RANGE BUT NOT CONFIGURED (low) | Inside low. Same gap. |
| ~2850–3000 sp3 C–H stretching | PARTIALLY CONFIGURED (high) | Whole span is inside high 2372.977–3503.141. `glycine_2975` covers only 2960–2990 of it; 2850–2960 and 2990–3000 are unconfigured. A 30 cm-1 window does not measure a 150 cm-1 envelope. |
| ~2970 glycine CH2 symmetric stretch | **CONFIGURED** — `glycine_2975` | Search window 2960–2990. Measured position is 2974.594 or 2976.563 in ech2 and ech4. |
| ~3000–3010 glycine CH2 asymmetric stretch | **CONFIGURED** — `glycine_3012` | Search window 2997–3027 contains both ends. |
| ~3000–3100 sp2 C–H stretching | PARTIALLY CONFIGURED (high) | Whole span inside high. `glycine_3012` covers 2997–3027; 3027–3100 is unconfigured. `glycine_3146` (3131–3161) lies above the span entirely. |
| ~3300 sp C–H stretching | IN RANGE BUT NOT CONFIGURED (high) | Inside high (max 3503.141). Nearest configured band is `glycine_3146`, topping out at 3161. |
| ~3200–3550 hydrogen-bonded O–H, broad | PARTIALLY IN RANGE (high), NOT CONFIGURED | 3200–3503.141 is acquired; 3503.141–3550 is beyond the high window's upper bound. Nothing is configured anywhere in the span. With `half_width` 15 the highest usable centre is 3488.141. |
| ~3600–3700 free O–H, sharper | **OUTSIDE THE ACQUIRED RANGE** | Entirely above the high window's upper bound of 3503.141. Not measurable from this data at all. |

None of the sixteen falls in the unacquired 1824.880–2372.977 gap.

Summary: 6 of 16 are directly configured; 3 are partially configured; 5 are in
range and unconfigured; 1 is partially in range and unconfigured; 1 is outside
the acquired range entirely. `bands.json` was not changed.

Scope: `bands.json`, and window bounds computed from all 46 raw files.

### A7 — ech2 and ech4 extraction

Both samples have **steps 0, 1, 2, 3, 4, 5, 6** present — control plus irr1
through irr6, no gaps — and 56 rows each (8 bands × 7 steps). `at_edge` is
`False` for every row shown. `signal_to_noise` is empty for every row, because
no `noise_regions` is configured (A5); it is written as `None` below to make the
absence explicit.

Grouped so heights read across steps for a given band. `drift` is the CSV's
`position_drift` column (`position - centre`).

**ech2 — low window**

    band si_522 (window low)
    step         height   position    drift at_edge    snr
       0       148947.9    522.251    0.251   False   None
       1       153224.6    522.251    0.251   False   None
       2       151623.7    522.251    0.251   False   None
       3       150955.6    522.251    0.251   False   None
       4       144449.3    522.251    0.251   False   None
       5       147047.4    522.251    0.251   False   None
       6       148032.6    522.251    0.251   False   None

    band glycine_893 (window low)
    step         height   position    drift at_edge    snr
       0         6343.5    893.108    0.108   False   None
       1         6589.9    893.108    0.108   False   None
       2         6064.7    893.108    0.108   False   None
       3         5990.8    893.108    0.108   False   None
       4         6142.5    896.060    3.060   False   None
       5         6423.3    896.060    3.060   False   None
       6         6228.8    893.108    0.108   False   None

    band glycine_979 (window low)
    step         height   position    drift at_edge    snr
       0         5841.1    977.813   -1.187   False   None
       1         6081.9    977.813   -1.187   False   None
       2         6055.6    972.030   -6.970   False   None
       3         6027.6    980.702    1.702   False   None
       4         6067.5    977.813   -1.187   False   None
       5         5999.6    977.813   -1.187   False   None
       6         5971.5    977.813   -1.187   False   None

    band glycine_1328 (window low)
    step         height   position    drift at_edge    snr
       0        10255.4   1327.966   -0.034   False   None
       1         9248.9   1327.966   -0.034   False   None
       2         9453.8   1327.966   -0.034   False   None
       3         8408.8   1327.966   -0.034   False   None
       4        11058.5   1327.966   -0.034   False   None
       5         9646.9   1327.966   -0.034   False   None
       6         8838.7   1327.966   -0.034   False   None

    band glycine_1412 (window low)
    step         height   position    drift at_edge    snr
       0         4141.3   1413.657    1.657   False   None
       1         3902.0   1411.091   -0.909   False   None
       2         4082.7   1411.091   -0.909   False   None
       3         3709.7   1411.091   -0.909   False   None
       4         4622.2   1413.657    1.657   False   None
       5         4005.8   1416.221    4.221   False   None
       6         3811.1   1411.091   -0.909   False   None

**ech2 — high window**

    band glycine_2975 (window high)
    step         height   position    drift at_edge    snr
       0        27581.0   2976.563    1.563   False   None
       1        28489.7   2976.563    1.563   False   None
       2        23248.6   2976.563    1.563   False   None
       3        22317.7   2974.594   -0.406   False   None
       4        26343.8   2976.563    1.563   False   None
       5        23301.1   2976.563    1.563   False   None
       6        27682.9   2974.594   -0.406   False   None

    band glycine_3012 (window high)
    step         height   position    drift at_edge    snr
       0        15976.2   3011.764   -0.236   False   None
       1        16356.3   3011.764   -0.236   False   None
       2        12821.2   3011.764   -0.236   False   None
       3        11812.7   3009.821   -2.179   False   None
       4        14690.7   3011.764   -0.236   False   None
       5        12319.2   3011.764   -0.236   False   None
       6        14787.5   3011.764   -0.236   False   None

    band glycine_3146 (window high)
    step         height   position    drift at_edge    snr
       0         3505.7   3144.117   -1.883   False   None
       1         3538.6   3145.957   -0.043   False   None
       2         2841.6   3144.117   -1.883   False   None
       3         2762.8   3144.117   -1.883   False   None
       4         3167.0   3149.631    3.631   False   None
       5         2920.7   3144.117   -1.883   False   None
       6         3472.4   3147.795    1.795   False   None

**ech4 — low window**

    band si_522 (window low)
    step         height   position    drift at_edge    snr
       0        99122.6    522.251    0.251   False   None
       1       100352.1    522.251    0.251   False   None
       2       104163.2    522.251    0.251   False   None
       3        95686.7    522.251    0.251   False   None
       4       101852.4    522.251    0.251   False   None
       5        92022.6    522.251    0.251   False   None
       6        86602.3    522.251    0.251   False   None

    band glycine_893 (window low)
    step         height   position    drift at_edge    snr
       0        43634.2    893.108    0.108   False   None
       1        42994.2    893.108    0.108   False   None
       2        43662.5    893.108    0.108   False   None
       3        45659.6    893.108    0.108   False   None
       4        45906.7    896.060    3.060   False   None
       5        47930.1    896.060    3.060   False   None
       6        43363.4    896.060    3.060   False   None

    band glycine_979 (window low)
    step         height   position    drift at_edge    snr
       0         3495.3    977.813   -1.187   False   None
       1         3548.1    980.702    1.702   False   None
       2         3737.9    977.813   -1.187   False   None
       3         3614.0    977.813   -1.187   False   None
       4         3789.4    983.588    4.588   False   None
       5         3511.3    983.588    4.588   False   None
       6         3187.7    977.813   -1.187   False   None

    band glycine_1328 (window low)
    step         height   position    drift at_edge    snr
       0        71394.3   1327.970   -0.030   False   None
       1        69587.8   1327.966   -0.034   False   None
       2        71183.1   1327.966   -0.034   False   None
       3        72215.2   1327.966   -0.034   False   None
       4        77780.0   1327.966   -0.034   False   None
       5        76731.0   1327.966   -0.034   False   None
       6        69505.2   1327.966   -0.034   False   None

    band glycine_1412 (window low)
    step         height   position    drift at_edge    snr
       0        28046.6   1413.660    1.660   False   None
       1        27461.7   1411.091   -0.909   False   None
       2        28249.5   1411.091   -0.909   False   None
       3        29491.9   1411.091   -0.909   False   None
       4        29977.0   1413.657    1.657   False   None
       5        32263.5   1416.221    4.221   False   None
       6        27590.0   1416.221    4.221   False   None

**ech4 — high window**

    band glycine_2975 (window high)
    step         height   position    drift at_edge    snr
       0       170146.4   2974.590   -0.410   False   None
       1       161746.7   2974.594   -0.406   False   None
       2       178767.2   2974.594   -0.406   False   None
       3       182803.9   2974.594   -0.406   False   None
       4       186714.7   2976.563    1.563   False   None
       5       205714.8   2976.563    1.563   False   None
       6       182920.8   2976.563    1.563   False   None

    band glycine_3012 (window high)
    step         height   position    drift at_edge    snr
       0        96342.8   3011.760   -0.240   False   None
       1        91653.0   3011.764   -0.236   False   None
       2       100457.7   3011.764   -0.236   False   None
       3       103751.4   3009.821   -2.179   False   None
       4       107596.2   3011.764   -0.236   False   None
       5       118483.6   3011.764   -0.236   False   None
       6       104530.4   3011.764   -0.236   False   None

    band glycine_3146 (window high)
    step         height   position    drift at_edge    snr
       0        23566.0   3144.120   -1.880   False   None
       1        21650.9   3144.117   -1.883   False   None
       2        23951.2   3144.117   -1.883   False   None
       3        26002.6   3144.117   -1.883   False   None
       4        25254.3   3147.795    1.795   False   None
       5        30308.1   3147.795    1.795   False   None
       6        25652.1   3144.117   -1.883   False   None

**Observations on the extracted values, stated as observations and not as
conclusions:**

- **No `at_edge` flag fires** in either sample, on any band, at any step.
- **Position drift beyond 5 cm-1** — the `MAX_POSITION_DRIFT` threshold the code
  flags on — occurs twice: ech2 `glycine_979` at step 2 (-6.970) and ech4
  `glycine_979` at step 4 (+4.588, below threshold) — so strictly, once. The
  ech2 step-2 case means the maximum inside 964–994 was found at 972.030, over
  half the search window away from the configured 979.
- **`si_522` behaviour differs sharply between the two samples.** In ech2 it
  moves from 148,947.9 to 148,032.6, a change of -0.6% across seven steps. In
  ech4 it moves from 99,122.6 to 86,602.3, -12.6%, non-monotonically (it rises
  to 104,163.2 at step 2 first). This reproduces exactly what `CLAUDE.md`
  records under "Analysis approach and what was tried".
- **The ech2-vs-ech4 scale difference is large and consistent across bands**, at
  step 0: `glycine_893` 6,343.5 vs 43,634.2 (×6.9), `glycine_1328` 10,255.4 vs
  71,394.3 (×7.0), `glycine_1412` 4,141.3 vs 28,046.6 (×6.8), `glycine_2975`
  27,581.0 vs 170,146.4 (×6.2). But `si_522` goes the other way: 148,947.9 vs
  99,122.6 (×0.67), and `glycine_979` also inverts: 5,841.1 vs 3,495.3 (×0.60).
  A uniform acquisition-gain difference would scale every band in a spectrum by
  the same factor; these do not. That does not resolve A9 — it means the
  difference is not a single global gain factor, which is a different statement
  from "the acquisitions were comparable".

Scope: the 112 rows of `bands.csv` whose sample is ech2 or ech4. No new data
file was written; this table exists only here and in stdout.

### A8 — does each band sit in exactly one window? CONFIRMED

From `bands.json`, each band declares exactly one `window` string, and the
schema has no way to express more than one. The split:

- **low (5 bands):** `si_522`, `glycine_893`, `glycine_979`, `glycine_1328`,
  `glycine_1412`
- **high (3 bands):** `glycine_2975`, `glycine_3012`, `glycine_3146`

Confirmed in the CSV as well: every row's `window` matches its band's configured
window (table in A5), and the set of distinct `window` values per band is a
single value in all eight cases. In `measure_all_bands` the loop skips any
spectrum whose window differs:

    for (sample, window, step), (spectrum, values) in sorted(corrected.items()):
        if window != spec.window:
            continue

So a band is only ever measured in spectra carrying its own window label, and no
single `height` value can mix windows.

Note for the deliverable: the single-window constraint in the goal is therefore
satisfied by band selection alone. The low-window set gives ech2-vs-ech4 across
five bands; the high-window set gives three.

Scope: `bands.json`, `bands.csv`, and `measure_all_bands` in `report.py`.

### A9 — acquisition metadata. NONE EXISTS. Inter-sample comparability UNKNOWN FROM THE DATA ALONE

Exhaustive scan of `data/raw/irradiation_sara/`.

**File headers.** Read the first line of all 46 `.txt` files as bytes:

    44 x b'#Wave\t\t#Intensity\r\n'
     1 x b'2372.98\t18221.4\r\n'
     1 x b'201.912\t16626\r\n'

Forty-four carry the documented two-column header and nothing else. Two carry no
header at all and begin with data — `ech4_high_0.txt` and `ech4_low_0.txt`,
identified by scanning for a first byte that is not `#`. These are the two
low-precision Jul 16 exports; they are the documented legacy files. No file
carries a laser power, an integration time, an objective, a slit width, a
detector gain, a date, or an instrument identifier.

**Comment lines beyond line 1.** Scanned every line of every file for a leading
`#`. Result: `files with comment lines other than a single line 1: []`. No file
has a comment block, a trailer, or an embedded metadata section.

**Sidecar and non-`.txt` files.** The directory holds exactly three:

    ['bands.json', 'baseline.json', 'desktop.ini']

`bands.json` and `baseline.json` are analysis configuration written by the
experimenter — band positions and baseline smoothness. Neither says anything
about acquisition conditions. `desktop.ini` is a Windows shell file with a
single `[LocalizedFileNames]` section mapping each filename to itself; it holds
no instrument data.

**The `desktop.ini` observation** (see PROPOSED DEVIATIONS). It lists
`ech3_low_irr2.txt` and `ech3_high_irr5.txt`, and neither exists in the
directory. That is consistent with — and is the same two gaps as — ech3's
documented missing steps. It means the Windows shell recorded those names at
some point; it is not evidence about acquisition and does not bear on
comparability. Recorded so a later reader does not have to re-derive it.

**Wider search.** Grepped `README.md`, `CLAUDE.md` and everything under
`data/raw/` (case-insensitive) for `laser`, `integration time`, `objective`,
`slit`, `detector gain`, `grating`, `power`. The only three hits are the phrase
"different grating settings" in `README.md` twice and `CLAUDE.md` once, used
hypothetically to explain that the measured window bounds are not invariants.
No actual setting is recorded anywhere.

**Verdict.** There is **no acquisition metadata in this repository at all**. The
assumption that ech2 and ech4 shared laser power, integration time, objective,
slit width and detector gain is therefore **UNKNOWN FROM THE DATA ALONE**. It is
not assumed to hold and it is not assumed to fail. It can only be answered by
the experimenter or by the instrument's own records, which are not here.

The observation at the end of A7 — that the ech2/ech4 ratio is roughly ×6.8 for
four bands but ×0.67 and ×0.60 for two others — narrows what the difference
cannot be (a single global gain), but does not establish comparability.

Scope: every file in `data/raw/irradiation_sara/` (46 `.txt` plus 3 others),
read as bytes; plus a keyword grep over `README.md`, `CLAUDE.md` and
`data/raw/`.

### A10 — does anything produce an absolute-height comparison between samples? CONFIRMED, with one qualification

**The two plotting functions plot `height_norm`, not `height`.** Quoting the
lines that select the column.

`build_sample_band_trends` in `plotting.py`:

    steps = [int(r["step"]) for r in series]
    values = [r["height_norm"] for r in series]

and its y-axis label confirms the intent:

    axes.set_ylabel(f"band height / {reference}")

`build_all_sample_band_trends` in `plotting.py`:

    axes.plot(
        [int(r["step"]) for r in series],
        [r["height_norm"] for r in series],

Both **CONFIRMED**: they plot `height_norm`. Neither reads `height`. A
repository grep for `height` over `src/**/*.py` and `main.py` finds exactly two
occurrences in `plotting.py`, both shown above, both `height_norm`.

**The qualification, which contradicts the claim as literally stated.** The
claim "nothing in the repository currently produces an absolute-height
comparison between samples" is **not quite true for stdout**.
`print_band_summary` in `report.py` prints absolute heights for the reference
band across every sample:

    print("\n== reference band ==")
    print(f"  {reference}: absolute height and area per sample and step")
    print(f"    {'sample':8s} {'step':>5s} {'height':>14s} {'area':>16s} {'position':>10s}")
    for row in sorted(
        (r for r in rows if r["band"] == reference), key=lambda r: (r["sample"], r["step"])
    ):
        …
        print(
            f"    {row['sample']:8s} {label:>5s} {row['height']:14.1f} "

Sorted by sample, so every sample's absolute `si_522` heights appear in one
block — that is an absolute-height comparison between samples. But it covers
**only the reference band**, it goes to stdout and no file, and it is not a
figure. The other absolute-height print is inside the weak-band listing, which
never fires here because no `noise_regions` is configured.

So: **no figure and no derived file** presents an absolute-height comparison
between samples for any band other than `si_522`; the second half of
`print_band_summary` is the normalised table, using `height_norm`.

Scope: `src/**/*.py` and `main.py`, searched for `height_norm` and for `height`
as a dict key. **`tests/` was not searched** — a test could read `height`, and
that would not change the conclusion about what the tool produces, but the claim
is scoped to the source tree, not to the repository.

---

## 5. Is deliverable 2 extraction, or does it need code?

**Extraction and presentation, against the existing CSV. No code is needed.**
`data/derived/irradiation_sara/bands.csv` already holds every number the
deliverable asks for: `height` is absolute, baseline-corrected, at the located
maximum, with no normalisation applied to it (A3, traced through four call
sites); the file on disk is current against both `baseline.json` and all 46 raw
inputs (A4, 46 of 46 hashes matching); ech2 and ech4 each have all seven steps
present with no gaps and no `at_edge` flags (A7); and each band sits in exactly
one window, five in low and three in high, so restricting to a single window is
a matter of filtering rows rather than of measuring anything (A8). The full A7
table above was produced by reading the CSV alone. What the repository does not
have is a *presenter* — `build_sample_band_trends` and
`build_all_sample_band_trends` both plot `height_norm`, and the only absolute
heights that reach a human are the `si_522` block `print_band_summary` writes to
stdout (A10). So if the deliverable is a table, it is extraction; if it must be
a figure or a committed artefact, the minimum is a presentation-only addition —
one function that filters `bands.csv` rows by sample and window and renders
`height`, plus its `main.py` subcommand if it needs a CLI. It must not touch
`measure_all_bands`, `bands.py`, `analysis.py` or the existing trend builders,
and it should not re-run `quantify`: the CSV is current, so regenerating it
would change nothing except the `generated_utc` stamp and would rewrite 46
derived spectra for no gain. The real cost of deliverable 2 is not code, it is
D1 — deciding what caveat the table must carry, given that inter-sample
comparability is unestablished.

---

## 6. Matters next

- **D1 is the gate.** Nothing should be built until the experimenter says
  whether an ech2-vs-ech4 absolute comparison is to be presented at all, and
  with what caveat.
- **Acquisition conditions are worth recording somewhere, once, from the
  experimenter's memory or lab notebook.** They cannot be recovered from the
  files and every future inter-sample question will hit the same wall. This is
  an observation, not a proposal to create a file — `data/raw/` is the
  experimenter's and nothing may be written there.
- **`provenance.json` does not record `bands.json`.** A change to a band's
  `half_width` since the last `quantify` run would be undetectable from the
  artefacts on disk (section 2). Centres and windows happen to be recoverable
  from the CSV; `half_width` is not. Not raised as a deviation because it is
  outside this task's scope, but it is a real gap in the provenance guarantee.
- **The `signal_to_noise` column is empty and will stay empty** until a
  `noise_regions` block is added to `bands.json`. Any table built for
  deliverable 2 must show that as "not computed", never as a blank that could
  read as zero or as a passing value.
- **`bands.csv` is gitignored and exists only in this working tree.** A fresh
  clone has none, and any deliverable that quotes these numbers should say which
  run they came from — `generated_utc` 2026-08-29T19:52:17.112903+00:00.

---

## 7. Self-corrections during this phase

None. No claim made during this phase was later found wrong.

---

## 8. Everything measured or validated, with the numbers

Collected here so a later reader does not have to hunt for them.

| what | result |
|------|--------|
| `bands.csv` size | 27,809 bytes |
| `bands.csv` mtime | 2026-08-29 21:52:17.120163900 +0200 |
| `bands.csv` lines / data rows | 185 / 184 |
| header == `BANDS_CSV_COLUMNS` (list equality) | True |
| samples in CSV | ech1, ech2, ech3, ech4, ech5, ech6 |
| bands in CSV | 8, matching `bands.json` exactly |
| distinct `noise` values in CSV | `{''}` — empty for all 184 rows |
| `cross_window` values present | False and True |
| provenance `generated_utc` | 2026-08-29T19:52:17.112903+00:00 |
| raw hashes re-verified | 46 recorded, 46 matching, 0 mismatched, 0 missing |
| raw `.txt` on disk | 46; set identical to provenance's |
| baseline params recorded vs `baseline.json` | identical; every source names `baseline.json`, none is a built-in default |
| low window bounds from data | min 201.912 (all 23 files), max 1824.880 (all 23 files) |
| high window bounds from data | min 2372.977–2372.980, max 3503.140–3503.141 (23 files) |
| unacquired gap | 1824.880–2372.977 |
| usable centres with half_width 15 | low 216.912–1809.880; high 2387.977–3488.141 |
| raw first-line variants | 44 × `#Wave\t\t#Intensity`, 2 headerless (`ech4_high_0.txt`, `ech4_low_0.txt`) |
| files with comments beyond line 1 | 0 |
| non-`.txt` in raw dir | `bands.json`, `baseline.json`, `desktop.ini` |
| ech2 steps / rows | 0–6, no gaps / 56 |
| ech4 steps / rows | 0–6, no gaps / 56 |
| `at_edge` True in ech2 or ech4 | 0 |
| drift beyond 5 cm-1 in ech2 or ech4 | 1 — ech2 `glycine_979` step 2, -6.970 |
| ech2 `si_522` step 0 → 6 | 148,947.9 → 148,032.6 (-0.6%) |
| ech4 `si_522` step 0 → 6 | 99,122.6 → 86,602.3 (-12.6%, non-monotonic, peaks 104,163.2 at step 2) |
| ech2 `glycine_893` step 0 → 6 | 6,343.5 → 6,228.8 |
| ech4 `glycine_893` step 0 → 6 | 43,634.2 → 43,363.4 (peaks 47,930.1 at step 5) |
| ech4/ech2 height ratio at step 0 | glycine_893 ×6.9, glycine_1328 ×7.0, glycine_1412 ×6.8, glycine_2975 ×6.2, si_522 ×0.67, glycine_979 ×0.60 |
| A6 tally | 6 configured, 3 partially configured, 5 in range unconfigured, 1 partially in range, 1 outside range |
| `height_norm` occurrences in `plotting.py` | 2, both plotting selections |
| `height` (non-norm) occurrences in `plotting.py` | 0 |

---

## 9. Files touched by this phase

`prompt_outputs/004-presentation-band-heights-phaseA.md` (this file) and one
appended line in `prompt_outputs/INDEX.md`. Nothing else. `data/raw/`,
`data/derived/`, `figures/`, `src/`, `tests/` and `main.py` are untouched.

PHASE A ends here. Awaiting a decision on D1 and an explicit "PROCEED".
