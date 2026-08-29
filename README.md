# RAMSESS analysis

Python tooling to load and inspect `.txt` Raman spectra from a RAMSESS in-situ
system. Each file holds one spectrum: one sample, one spectral window, one
irradiation step. Samples are irradiated cumulatively. Experiments are discovered
at runtime; nothing about the dataset is hardcoded.

## Data layout

    data/raw/<experiment>/*.txt     read-only input, never modified
    data/raw/<experiment>/*.json    hand-written configuration
    data/derived/<experiment>/      generated data, gitignored
    figures/<experiment>/           generated output, gitignored

Nothing in the code writes under `data/raw/` — a guard raises if any code path
tries. Raw data is the only thing here that cannot be regenerated; everything
under `data/derived/` and `figures/` is reproducible from raw plus config.

## Filenames

    <sample>_<window>_0.txt        control, step 0
    <sample>_<window>_irr<N>.txt   irradiation step N

`<window>` is exactly `low` or `high`, lowercase. `N` is a positive integer with
no upper bound. The sample part may contain underscores, so the name is split from
the right. Filenames that do not match are rejected, never skipped.

## File format

One header line, `#Wave` and `#Intensity` separated by two tabs, then two
whitespace-separated float columns of wave and intensity. Line endings are CRLF.
A few legacy files have no header and begin directly with data, so the header is
skipped only when the first line starts with `#`.

The numbers below are **measured for the `irradiation_sara` experiment**, not
constants — another experiment on different grating settings will differ, and the
code assumes none of them. 575 points per spectrum; the low window spans
201.912–1824.880 and the high window 2372.977–3503.141, disjoint with a gap of
about 548 cm-1. Wave spacing is not uniform (low mean 2.83, high mean 1.97) and
strictly increasing. Some samples have only a control, and step sequences may
contain gaps.

## Setup

    python -m venv .venv
    .venv\Scripts\python.exe -m pip install --upgrade pip
    .venv\Scripts\python.exe -m pip install -r requirements.txt

## Development

Install the dev dependencies first, then run the suite:

    .venv\Scripts\python.exe -m pip install -r requirements-dev.txt
    .venv\Scripts\python.exe -m pytest

## Usage

`main.py` is the single entry point. Omitting `--experiment` lists the
experiments available and exits non-zero.

    .venv\Scripts\python.exe main.py inspect --experiment irradiation_sara [--strict]

Prints one line per spectrum, a per-(sample, window) summary of the steps present
and whether the wave axes agree, and a warnings section. Writes no files and
draws no plots. `--strict` exits non-zero if any HARD check fired; without it
inspect always exits zero.

    .venv\Scripts\python.exe main.py plot --experiment irradiation_sara [--sample ech2] [--logy] [--force]

Writes `figures/<experiment>/<sample>_overlay.png` at 200 dpi, one per sample:
every step overlaid on a broken x-axis with the low window left and the high
window right, panel widths proportional to each window's span and y axes scaled
independently. Raw counts, no smoothing or baseline correction.

It prints one line per figure, with the peak intensity of each window and their
ratio, so you can see which samples are low-dominant without opening the PNGs:

    wrote ...\figures\irradiation_sara\ech2_overlay.png   low_max=157853.5 high_max=34439.7 low/high=4.58 low-dominant
    wrote ...\figures\irradiation_sara\ech6_overlay.png   low_max=37168.3 high_max=226450.2 low/high=0.16 high-dominant

Drawing details: the control is black dashed; irradiation steps take their colour
from viridis positioned by the actual step number, so the same step is the same
colour across samples even where the sequence has gaps. Each panel carries its
own legend listing only the steps drawn in it. On a linear scale the y lower
bound is clamped to zero only when autoscale would otherwise go negative, since
counts cannot be negative; under `--logy` both bounds are left alone.

Before returning each figure the code asserts that every drawn line still equals
the raw file contents exactly, and raises if not.

### Figure filenames

Each flag combination writes to its own path, so no run can overwrite another's
output:

    {sample}_overlay.png                    plot
    {sample}_overlay_log.png                plot --logy
    {sample}_overlay_baseline.png           plot --baseline
    {sample}_overlay_baseline_log.png       plot --baseline --logy
    {sample}_{window}_baseline_check.png    plot --baseline-diagnostic

The six `{sample}_overlay.png` files are the reference output and only plain
`plot` writes them. **`--logy` has no effect on the diagnostic figure** — it is
accepted and ignored there, so `--baseline-diagnostic` produces the same file
with or without it.

## HARD and SOFT checks

Every check is one or the other, and both always print under `== warnings ==`.

**HARD** means a file is not what its name says, which silently corrupts any
figure drawn from it: two files with identical content hashes, a file whose wave
range does not match the modal range for its window label, two window labels
whose ranges overlap, files in one group whose wave axes have different lengths
or differ by more than 0.01 cm-1.

**SOFT** means a true, accepted fact about the data: step gaps, a sample with no
control, a sample in only one window, a file with no header line, wave axes
differing by less than 0.01 cm-1, or a window label with too few files to derive
a trustworthy range.

`plot` runs the HARD checks before drawing. If any fire it prints them, draws
nothing and exits non-zero. **`--force` overrides that refusal** — it prints a
loud banner naming every overridden check, then draws anyway. SOFT findings
never affect an exit code and never block plotting.

Window ranges are derived per experiment from the files themselves, so a future
experiment recorded on different grating settings needs no code change.

## Quantifying bands

    .venv\Scripts\python.exe main.py quantify --experiment irradiation_sara [--sample ech2] [--force]

Exports every baseline-corrected spectrum to
`data/derived/<experiment>/<sample>_<window>_<step>_corrected.txt` as three
tab-separated columns — wave, corrected intensity, fitted baseline — so the raw
data is recoverable by summing columns 2 and 3. Each run also writes
`provenance.json` (parameters used, where each came from, input file hashes, UTC
timestamp) and `bands.csv` (one row per sample, window, step and band), and
draws `<sample>_bands.png` plus `bands_all_samples.png`.

Bands are configured in `data/raw/<experiment>/bands.json`:

    {
      "reference": "si_522",
      "bands": {
        "si_522":      {"centre": 522, "half_width": 15, "window": "low"},
        "glycine_893": {"centre": 893, "half_width": 15, "window": "low"}
      },
      "noise_regions": {"low": [1162, 1282], "high": [3273, 3393]}
    }

Band names are arbitrary. Each band's peak is located as the maximum within
`centre ± half_width` rather than assumed to sit at `centre`, because bands
shift. `reference` names the band all others are normalised against.
`noise_regions` is optional — a featureless stretch per window, used to estimate
local noise and hence signal-to-noise; without it that column is skipped rather
than guessed.

`quantify` has no baseline flags on purpose: derived data must be reproducible
from raw plus config alone.

The `height_norm`, `area_norm` and `cross_window` columns belong to the
secondary si_522-normalisation path. The primary measurement is the absolute
`height` column; see "Analysis approach and what was tried" in `CLAUDE.md` for
why, and for what `cross_window` marks.

Two things to know: `--sample` restricts measurement and figures to one sample
but derived spectra are still exported for **every** sample, so the derived tree
and `provenance.json` always describe the whole experiment; and
`bands_all_samples.png` includes controls-only samples, which show as a single
point rather than a trend.

Measurements are flagged when the peak lands on a search-window edge, when
signal-to-noise is below 10, and when a position drifts more than 5 cm-1 from
its configured centre.

## Baseline correction

Opt-in, never the default, and never applied in the loader. `--baseline` writes
`<sample>_overlay_baseline.png` alongside the untouched raw figure and labels the
title as corrected; `--baseline-diagnostic` writes
`<sample>_<window>_baseline_check.png`, a grid with one row per step showing the
raw spectrum with its fitted baseline beside the corrected result.

Parameters live in `data/raw/<experiment>/baseline.json` and may be set per
window:

    {
      "lam": 1e6,
      "p": 0.01,
      "n_iter": 10,
      "windows": {"high": {"lam": 1e8}}
    }

`lam` is the smoothness penalty, `p` the asymmetry, `n_iter` the number of
reweighting passes. **Different windows often need different smoothness**,
because their backgrounds differ in kind — a flat background beneath a narrow
line is a different problem from a broad hump beneath a broad band envelope, and
a fit flexible enough for the first will arc up under the second and absorb its
wings.

Each parameter resolves independently, most specific first: `--baseline-lam` /
`--baseline-p` / `--baseline-n-iter`, then `windows.<label>`, then the top level,
then a built-in fallback. Every run prints the value and origin for each window,
and says explicitly when a CLI flag has overridden a per-window setting. An
unknown key under `windows`, or any out-of-range value, is an error.
