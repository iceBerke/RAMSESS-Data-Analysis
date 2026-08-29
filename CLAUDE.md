# RAMSESS analysis — working agreement

## Two-phase protocol

Every task runs in two phases. Do not start PHASE B until the user replies
"PROCEED".

**PHASE A — verification only.** Read files, list directories, run read-only
commands. Create, edit, move and delete nothing. Install nothing. Check every
assumption in the request against the actual data and report each as
CONFIRMED / CONTRADICTED / UNKNOWN with the concrete evidence used — a count, a
printed line, a min/max. Then list PROPOSED DEVIATIONS: anything the plan needs
changed. Then stop and wait.

**PHASE B — implementation.** Only after "PROCEED". Build exactly what was
specified, nothing more.

## No silent changes

If you want to do anything not written in the request — rename something, add a
helper, install a package, restructure a path, "improve" an API — do not do it.
Stop, list it under PROPOSED DEVIATIONS, wait. This applies even when the change
seems trivially correct or obviously beneficial. If an assumption turns out
false, do not work around it: report and wait.

## Report back after PHASE B

State every file created or modified with its line count, the full stdout of
anything run, anything done differently and why, and anything noticed that
matters for the next step.

## Data

    data/raw/<experiment>/*.txt     read-only input, never modify
    data/raw/<experiment>/*.json    experimenter-written config, never generate
    data/derived/<experiment>/      generated data, gitignored
    figures/<experiment>/           generated output, gitignored except for
                                    the {sample}_overlay.png references

**Nothing may write under `data/raw/`.** Raw files are the experiment and are
the only thing here that cannot be regenerated; derived data and figures are
reproducible from raw plus config. `guard_not_under_raw` in `io.py` enforces
this at every write site and raises naming the path. It guards the sites that
call it, not the process, so any new write must call it too. Config files under
`data/raw/` are hand-written by the experimenter; never create or edit them.

Samples are irradiated cumulatively. Filenames — `<sample>_<window>_0.txt` for
the control, `<sample>_<window>_irr<N>.txt` for irradiation step N. `<window>` is
exactly `low` or `high`, lowercase. N is a positive integer with no upper bound,
so `irr10` and `irr123` must work, and the sample part may itself contain
underscores: split the stem from the right.

Format, as verified: one header line `'#Wave\t\t#Intensity'` (two tabs) followed
by two whitespace-separated float columns, wave then intensity. Line endings are
CRLF. A small number of legacy files have no header at all and their first line
is data — skip line 1 only when it starts with `#`, never unconditionally.

Facts **measured for `irradiation_sara`** (46 files). These are that
experiment's values, not invariants: a future experiment on different grating
settings will differ, and nothing in the code assumes these numbers.

- 575 points per spectrum, in every file.
- Low window spans 201.912–1824.880; high window spans 2372.977–3503.141.
- The two windows are disjoint, separated by a gap of about 548 cm-1.
- Wave spacing is not uniform: low mean 2.83, high mean 1.97. Never assume a
  constant step or rebuild an axis with `linspace`. Wave is strictly increasing
  everywhere; no NaN, infinite or negative intensity.
- Some samples are controls-only, with no irradiation steps. That is valid data,
  and step sequences may have gaps. Report both, do not treat them as errors.
- Some files are exported at lower precision, giving wave axes that differ by
  about 0.005. Below 0.01 that is a precision difference, not an axis mismatch.

Windows sort in physical order, low before high, never alphabetically. The order
and the set of valid labels both come from `WINDOW_ORDER` in `io.py`; sorting
goes through `window_sort_key`, which raises on an unknown label — except at the
display-only sites described below, which use `window_display_order_key` and do
not raise. Code that picks a window still selects it by name rather than
trusting position.

`WINDOW_ORDER = ("low", "high")` is hardcoded on purpose. These are the only two
windows the RAMSESS instrument produces — a physical constraint of the hardware,
not an assumption about this dataset — so a file carrying any other window label
is correctly a hard failure. Do not "fix" this into a configurable list. If the
instrument itself ever changes, the constant changes with it.

There are two window sort keys, and picking the wrong one is a real mistake:

- `window_sort_key` is the strict one and **raises on an unknown label**. Use it
  wherever labels are validated — which is everywhere they come from loaded
  spectra. An unrecognised label there is a hard failure, not something to sort
  around.
- `window_display_order_key` orders known labels physically, puts unknown ones
  after them alphabetically, and **never raises**. It is for display only, at
  the few printing sites whose input is not guaranteed validated. Never use it
  in a validation path: an ordering helper must not be mistaken for a check.

Only one site needs the tolerant key: the baseline parameter block in
`print_baseline_config`. `resolve_baseline_config` accepts whatever labels its
caller declares — `test_arbitrary_window_labels_are_supported` pins that — so
the strict key would raise on a label the resolver legitimately supports.

Six sites sort window labels alphabetically **on purpose** and were reviewed and
left alone: `report.py` 167, 227, 368, 414 and 1312, and `plotting.py` 373.
Each either builds an error message, where the ordering only decides which item
is named first, or sits on the label-agnostic baseline path. `report.py:1312`
is additionally a no-op — the cross-window notice can only ever list one window,
because a cross-window row is by definition in the window the reference is not.
None is worth a test. This was settled deliberately; do not reopen it without a
reason that is not cosmetic.

## Check severity and gating

Checks are HARD or SOFT. HARD means a file is not what its name says: duplicate
content hashes, a wave range off the modal range for its window label,
overlapping window ranges, or wave axes within a group that differ in length or
by more than 0.01 cm-1. Everything else is SOFT - step gaps, missing controls,
single-window samples, missing header lines, sub-0.01 precision differences.

`plot` refuses to draw anything when a HARD check fires, and `--force` overrides
that refusal after printing a banner. `inspect --strict` exits non-zero on HARD
findings; plain `inspect` never gates. SOFT never affects an exit code.

Any new subcommand that touches data must gate itself with a single
`preflight(subcommand, experiment, spectra, force=...)` call, passing its own
name so the messages read correctly. Do not add gating to `inspect`.

Window ranges are derived per experiment from the files, never hardcoded.

## The raw-data tripwire

`_assert_drawn_data_is_raw` in `plotting.py` checks, before every figure is
returned, that each drawn line's x and y data is `array_equal` to the `wave` and
`intensity` arrays of the spectrum it came from, and raises naming sample, window
and step if not. It runs on every plot call, not only under test.

This is a permanent integrity guarantee and **must not be removed**. Axis limits,
colours, scales and legends are display settings and may change freely; the
plotted values may not. Without the tripwire, a transform introduced anywhere in
the drawing path would produce a plausible-looking figure of the wrong numbers.

## Baseline correction

Baseline correction exists as an opt-in plotting mode. It is **never the default
and never happens in the loader** — the loader returns file contents and nothing
else, always. Raw figures and corrected figures have different filenames and
both persist; a baseline mode never overwrites, replaces or deletes a raw figure.
Every corrected figure states in its title that it is corrected, so it cannot be
mistaken for a raw one.

Its parameters (`lam`, `p`, `n_iter`) are **per-experiment configuration**, not
source-code constants, and may be set **per window**:

    {
      "lam": 1e6, "p": 0.01, "n_iter": 10,
      "windows": {"high": {"lam": 1e8}}
    }

Different spectral windows can genuinely need different smoothness, because
their backgrounds differ in kind: a flat background under a narrow line is not
the same problem as a broad hump under a broad band envelope. Too flexible a fit
in the second case arcs up under the band and eats its wings.

Resolution runs per parameter per window, most specific first: a CLI flag, then
`windows.<label>`, then the top level of `baseline.json`, then a built-in
fallback. The keys under `windows` are whatever labels the experiment contains;
an unknown one is an error naming it. A CLI flag is global and beats even a
per-window setting — when it does, the notice says so and names both values.
Whichever source supplied each value is printed for every window on every run,
and falling back to a built-in default prints an explicit notice. A malformed or
out-of-range `baseline.json` raises; it never falls back silently. Do not create
`baseline.json` automatically — that is the experimenter's file.

When a baseline mode is active the drawn values are legitimately not the file
contents, so the tripwire changes form rather than switching off: the drawn line
must equal the corrected array, and corrected plus fitted baseline must
reconstruct the raw array to within a data-scaled tolerance. That proves the
correction was a pure subtraction.

## Band quantification

`quantify` measures the bands configured in `data/raw/<experiment>/bands.json`
first, and writes only once measurement has succeeded. **Nothing is written
until then.** A failed run leaves no derived tree at all — not a partial one,
not even the directory — so a tree that exists is always one whose measurements
completed and can never be mistaken for a successful export.

The ordering is what makes that guarantee, not the validation. Config checks
catch the errors they can name and give a better message for them, but ordering
covers every way a run can fail, including the ones neither check anticipates.
Do not move the writes back above the measurement.

On success it exports the corrected spectra to `data/derived/<experiment>/` as
three columns — wave, corrected, fitted baseline — so raw is recoverable by
summing columns 2 and 3, alongside a `provenance.json` recording the parameters
used, their sources, the input hashes and a UTC timestamp.

The band configuration:

    {
      "reference": "si_522",
      "bands": {"si_522": {"centre": 522, "half_width": 15, "window": "low"}},
      "noise_regions": {"low": [1162, 1282]}
    }

Band names are arbitrary. `reference` names the band everything is normalised
against and must exist in `bands`. `noise_regions` is optional; without it no
signal-to-noise is computed and the summary says so rather than guessing a
region. Validation rejects unknown windows, a missing reference, search windows
that overlap within one spectral window, and out-of-range windows.

`quantify` deliberately has **no baseline flags**, unlike `plot`. Derived data
must be reproducible from raw plus config alone; a CLI override would let
someone generate derived files whose parameters exist only in their shell
history. `plot` is exploratory and keeps the escape hatch; `quantify` is the
record and does not.

Normalised columns, including the `cross_window` marker, belong to the secondary
si_522-normalisation path; see "Analysis approach and what was tried".

Two behaviours worth knowing. `quantify --sample` restricts *measurement and
figures* to that sample but still **exports derived spectra for every sample**,
so `provenance.json` describes the whole experiment rather than a partial tree.
And `bands_all_samples.png` includes controls-only samples, which appear as a
single point rather than a trend.

Measurements are also flagged when the peak lands on a search-window edge (the
real peak is probably outside it), when signal-to-noise falls below 10, and when
a located position drifts more than 5 cm-1 from its configured centre.

## Analysis approach and what was tried

Primary measurement: the absolute corrected glycine band height per step within
a sample - the `height` column of `bands.csv`. Not a ratio, not normalised.
`si_522` is measured and reported as an instrument-stability check, not as the
divisor for the primary answer.

Normalising to `si_522` was tried and set aside. Silicon sits beneath the
glycine layer, so anything changing that layer's transparency changes the
denominator without any chemistry. On ech4 it produced an apparent rise in
normalised glycine (0.4402 to 0.5007) while the absolute height was flat
(43,634 to 43,363) and `si_522` fell 12.6%: an artefact of the reference, not a
result. The normalisation code path is retained and works, but is secondary.
`bands.json` currently requires `reference`, so it is always active when
`quantify` runs; making `reference` optional is a known pending change, deferred
to a later step. Cross-window normalisation - a band in one spectral window over
a reference in the other - belongs to that secondary path only, and is marked by
the `cross_window` column.

Band-to-band ratios (COO- to backbone modes) were specified then cancelled
before implementation. They answer a different question, preferential loss of
the carboxyl group, and can be revisited if the chemistry becomes the focus. A
si_522-versus-glycine correlation diagnostic was also specified and cancelled:
it conflates trend with step-to-step fluctuation and discriminated for no sample.

Sample status as measured. ech2: flat, `si_522` stable. ech4: flat in absolute
terms (43,634 to 43,363) with `si_522` down 12.6%; neither series is monotonic -
glycine_893 peaks at 47,930 at irr5 and `si_522` rises to 104,163 at irr2 before
falling - which is part of why no confident trend is claimed. ech3: collapsing
in both after irr3, so its measurements past irr3 are not trustworthy.

## Raw plotting is settled

The raw plot path - `plot` with no baseline flags and **no `--logy`** - is
settled functionality, and the six `{sample}_overlay.png` files in
`figures/irradiation_sara/` are the reference output. Changing either the code
path or those figures requires an explicit request. `--logy` writes
`{sample}_overlay_log.png` and never touches the reference files.

`tests/test_raw_plot_reference.py` guards the path two ways. Structurally, on
figures built in memory: panel count, lines per panel, each line's data against
the raw file arrays, axis limits, the break-mark artists. And on disk, by
rendering a fresh reference and comparing pixel arrays against the real file, so
an overwritten, log-scaled, stale or deleted figure fails. Both avoid a pinned
PNG hash, which would break on any matplotlib, freetype or libpng upgrade and
report only that a hash changed. The disk checks skip, naming the command to
run, when `figures/` has not been generated - but the six `{sample}_overlay.png`
files are tracked, so a fresh clone has them and the disk checks run from the
start. A regenerated overlay would be whatever the code produces at that moment,
which makes the comparison self-fulfilling; the committed PNG is the baseline.
Every other figure is gitignored build output and a fresh clone has none.

## Figure filenames

Every flag combination that draws something different writes to a different
path, so **the same path always means the same bytes** and no combination can
overwrite another's output:

    {sample}_overlay.png                    plot
    {sample}_overlay_log.png                plot --logy
    {sample}_overlay_baseline.png           plot --baseline
    {sample}_overlay_baseline_log.png       plot --baseline --logy
    {sample}_{window}_baseline_check.png    plot --baseline-diagnostic

`--logy` has **no effect on the diagnostic figure** - `build_baseline_diagnostic`
takes no `logy` parameter - so that figure carries no scale suffix and
`--baseline-diagnostic` with and without `--logy` write the same bytes to the
same name. Two combinations may share a path only when their content is provably
identical. `tests/test_output_filenames.py` asserts this over all eight
combinations. The suffix is computed inside `write_sample_overlays` from the
flags it already holds; if a caller ever needs to override the scheme, that is
where to change it.

## Developer notes

Importing `ramsess.plotting` calls `matplotlib.use("Agg")` at import time. This
is a deliberate global side effect — the backend must be chosen before `pyplot`
is imported, so it cannot be deferred into a function. It fixes the backend for
the whole process. `report.py` therefore imports `plotting` lazily inside
`write_sample_overlays`, so the `inspect` path never pulls matplotlib in.

`build_sample_overlay` returns an open figure and does not save; the caller owns
and must close it. `plot_sample_overlay` wraps it to save and close. Tests use
the former so they can inspect a real figure without monkeypatching.

## Tests

    .venv\Scripts\python.exe -m pytest

Tests live in `tests/`, use synthetic experiments written to `tmp_path`, and
never write `data/` or `figures/`. Exactly two read `data/raw/`, and the list is
meant to stay short — extend it only with a reason, and update it here:

1. `test_cli_output.py` runs the real `inspect` against `data/raw/` and compares
   stdout to `tests/fixtures/inspect_irradiation_sara.txt`.
2. `test_raw_plot_reference.py` builds the overlay for each of the six real
   samples, because the reference output it guards is those figures; a synthetic
   fixture would guard something else.

**The suite must pass before any change is considered complete.** Regenerate the
golden fixture only when the output is deliberately changed, never to make a
failing test pass.

## Audited and deliberately not acted on

From the dead-code audit at `bb9dba9`. Recorded so the next audit reads these as
settled rather than re-raising them. Two are confirmed dead and scheduled; the
rest are known and fine.

**Confirmed dead, deferred to the config-extraction step, which touches this
area anyway:**

- `VALID_WINDOWS` in `io.py` is a redundant alias for `WINDOW_ORDER`, referenced
  once at the label check in `load_spectrum`. Safe to delete and fold into
  `WINDOW_ORDER`.
- The eight re-exports in `src/ramsess/__init__.py` have no consumer. Nothing
  inside the repository imports the package root — every internal import goes to
  `ramsess.io` directly, which was verified. That there is no consumer *outside*
  the repository is the experimenter's statement, not something the audit could
  check. Safe to delete on that basis.

**Known, no action:**

- `build_all_sample_band_trends` accepts `min_snr` and never uses it, so the
  all-samples figure does not ring weak points the way the per-sample figure
  does. Latent rather than active: no experiment configures `noise_regions`, so
  no measurement is weak and neither builder draws a ring today. Deferred to the
  trend-figure work. Decide then whether to implement the marking or drop the
  parameter — do not simply delete it.
- `venv/` in `.gitignore` matches nothing here. Harmless convention against a
  common alternative layout.
- The signal-to-noise path — `estimate_noise`, the `~` flag, the weak-band
  listing — has never run against real data, because no `bands.json` configures
  `noise_regions`. Synthetic tests only. Not a defect; know it before trusting
  that path the first time a noise region is configured.

The deliberate-looking-dead items already documented elsewhere in this file —
the `bands.py` defence-in-depth checks, the Agg import side effect, the six
alphabetical window sorts — are settled. Do not re-raise them either.

## Hard rules

- Hardcode nothing about the dataset. Sample names, experiment names, step
  counts, file counts and window ranges are discovered at runtime.
- Loaders never transform data. No smoothing, baseline correction, normalisation,
  spike removal, resampling, reordering or unit conversion in the I/O layer.
- Fail loudly on non-conforming filenames, naming the file and what was expected.
  Never skip, guess or substitute a default.
- Never swallow an exception silently.
- `src/ramsess/analysis.py` stays generic. Nothing in it may be specific to
  glycine, silicon, this instrument or these window ranges: no band positions,
  no sample assumptions, no tuned magic numbers presented as universal
  constants. It operates on an arbitrary intensity array and takes every
  parameter from its caller. If a future analysis genuinely needs a band
  position, that position is configuration, never a literal in the module. The
  module also writes no files and prints nothing.
- Type hints and a docstring on every public function.
- Always use the project venv at `.venv/`. Never install into or run with the
  system interpreter. Run everything as
  `.venv\Scripts\python.exe main.py <subcommand>`.
- Small modules, one clear responsibility each. Logic lives in `src/ramsess/`.
  `main.py` is the single entry point and does argument parsing and dispatch
  only — no analysis, formatting or plotting logic. New commands become
  subcommands of it; never add top-level scripts alongside it. Do not split a
  module to make it smaller; split it when it has two responsibilities.
