# 005 — annotated-overlays — PHASE A

Supersedes nothing.

Date: 2026-09-01
HEAD at time of writing: `42557f4`
Working tree at start: clean apart from entry 004 and its `INDEX.md` line,
written earlier in this session and already reported.

**Goal being verified.** Adding ANNOTATED COPIES of the sample overlay figures,
in which each configured band is labelled on the plot so a conference audience
can see which peak is which. Needed for ech2 and ech4; the feature must not be
special-cased to those samples. The existing reference overlays must remain
byte-identical, and the annotated output must be a NEW path under the existing
filename scheme.

**Scope of this phase.** Read-only. Nothing was created, edited, moved or
deleted except this file and its `INDEX.md` line. `plot` and `quantify` were not
run. Nothing was written under `data/derived/` or `figures/`. The six
`figures/irradiation_sara/{sample}_overlay.png` files were not opened at all —
not for reading, not for writing. Everything executed ran through
`.venv\Scripts\python.exe`.

**How the numbers below were produced.** One throwaway read-only script at
`…\scratchpad\verify_b8.py` (session scratchpad, outside the project tree) plus
two inline `-c` invocations. They import `ramsess.io.load_experiment`,
`ramsess.analysis.correct_baseline` and `ramsess.plotting.build_sample_overlay`,
build figures **in memory only**, read geometry and text extents from them via
the Agg renderer, and close them. `figure.savefig` is never called and no path
is opened for writing. This is the same in-memory technique
`tests/test_raw_plot_reference.py` uses for its structural assertions.

---

## 1. Blockers and decisions needed

**Two decisions. Both are design choices the experimenter owns, and neither can
be resolved from the code.**

**D1 — the low window's dynamic range makes a single linear-axis annotated
figure genuinely bad for ech2, and no amount of label placement fixes it.**
Measured, corrected, ech2 low: `si_522` reaches 153,224.6 while `glycine_1412`
reaches 4,595.1 — a factor of 33. With the panel autoscaled to the silicon peak,
all four glycine bands sit between 2.4% and 7.2% of panel height (full table in
B8). Labels placed just above each peak land in the bottom 7% of the panel,
stacked on top of each other and on the traces; labels placed near the top of
the panel need leader lines running most of the panel's height. ech4 is much
better behaved — its low-window glycine bands reach 3.6%, 30.3%, 43.8% and 74.7%
— so the problem is sample-dependent, and the feature must not be special-cased
to the samples where it happens to look fine. Decide one of: accept crowded
labels in ech2's low window; annotate on `--logy` as well and present the log
variant for ech2; or annotate only bands above some fraction of panel height and
say on the figure which were omitted. I am not choosing this; it is a judgement
about what the conference audience should see.

**D2 — annotation forces `plot` to read `bands.json`, which it has never
read.** Confirmed in B6: plain `plot` currently loads **no config file at all**,
and `load_bands_config` requires `window_ranges` from `common_window_ranges`,
which `plot` does not compute. It raises `FileNotFoundError` when `bands.json`
is absent. So the feature makes an experiment without `bands.json` — a perfectly
valid state today, since `plot` works without one — into an error case for the
new mode. Decide whether an absent `bands.json` under the annotate flag should
be a hard error naming the expected path (consistent with `quantify`), or a
printed notice that falls through to an unannotated figure. My recommendation is
in section 4; the choice is the experimenter's because it sets whether the
annotated path is "a plotting mode" or "a quantify-adjacent mode".

Nothing else blocks. Every structural assumption in the request checked out.

---

## 2. What I could NOT check, and why

- **Whether `tests/test_raw_plot_reference.py` currently passes.** I did not run
  the suite. It reads the six reference PNGs (via `mpimg.imread`, read-only) and
  writes only to `tmp_path`, so running it would have been safe — but the
  prompt singled those six files out and PHASE A builds nothing, so I left it
  alone. This matters: the premise "the existing reference overlays must remain
  byte-identical" assumes they are byte-correct *now*. If that test is already
  failing, the premise is already broken and `RULES.md` says the failure is the
  finding, not something to regenerate past. **Worth running before PHASE B**,
  and it is a one-command read-only check.
- **How the annotated figure actually looks.** No figure was saved, so every
  statement in B8 about crowding is derived from measured geometry — panel
  widths in points, cm-1 per point, and real text extents from the Agg renderer
  — not from looking at a rendered image. The arithmetic is in B8 and can be
  re-run; the aesthetic judgement cannot be made from it alone.
- **Whether matplotlib's `annotate` with automatic placement would resolve the
  collisions.** I measured static text extents at fixed positions. matplotlib
  has no built-in label-collision solver for this case, and I did not evaluate
  any third-party one — installing anything is forbidden in this phase and
  adding a dependency would be a deviation regardless.
- **`tests/` was not audited for other places a new flag would surface**, beyond
  the two test modules the request names (B3, B4). A grep-level sweep of the
  whole test tree was not part of the request and I did not do one, so the B3
  answer is scoped to `test_output_filenames.py` alone.

---

## 3. PROPOSED DEVIATIONS

**None.** This phase did exactly what was asked, built nothing, and proposes no
implementation. Section 4 is a recommendation, as requested, not a plan.

One disclosure that is not a deviation but should be on the record: **B8 asked
for the drawn y-range "for both the raw and the baseline-corrected case", and
the corrected case required computing baseline corrections.** I did that in
memory using the parameters resolved by hand from
`data/raw/irradiation_sara/baseline.json` (low `lam` 1e6, high `lam` 1e8, `p`
0.01, `n_iter` 10 — printed by the script and reproduced in B8), rather than by
running `plot --baseline`, which the prompt forbids. The numbers are therefore
what `plot --baseline` would draw, computed without running it.

---

## 4. Findings

### B1 — `build_sample_overlay`'s actual structure. CONFIRMED, with detail

It draws **one figure per sample containing both spectral windows**, as two
side-by-side panels forming a broken x-axis. Confirmed by reading the function
in full.

**Axes: two, side by side, one row.** Quoting the subplot construction:

    figure, axes_list = plt.subplots(
        1,
        len(windows),
        figsize=FIGURE_SIZE,
        squeeze=False,
        gridspec_kw={"width_ratios": spans, "wspace": PANEL_GAP},
    )
    axes = list(axes_list[0])

`len(windows)` is the number of window labels present, so it is 2 for a
both-windows sample and **1 for a single-window sample**, which is drawn as one
ordinary panel with no break marks. `windows` is built in physical order:

    windows = [w for w in WINDOW_ORDER if w in by_window]

so low is always the left panel and high the right, never alphabetical.

**Panel widths are proportional to each window's measured wave span**, via
`width_ratios=spans`, so cm-1 per inch matches across the break. Measured on
ech2: low panel 0.4457 of figure width, high panel 0.3104, and **5.057 cm-1 per
point in both** — identical to three decimals, which is the property that makes
a shared annotation scale possible across the break.

**What is plotted on each panel:** every step of that sample in that window, one
line per step, ascending by step. The plotting loop:

    for window, panel in zip(windows, axes):
        panel_steps = []
        for spectrum in by_window[window]:
            colour, linestyle = _style_for_step(spectrum.step, min_step, max_step)
            if baseline_params is None:
                values = spectrum.intensity
            else:
                values, fitted = correct_baseline(
                    spectrum, **baseline_params[spectrum.window]
                )
            (line,) = panel.plot(
                spectrum.wave,
                values,
                color=colour,
                linestyle=linestyle,
                linewidth=LINE_WIDTH,
            )

**Traces per axis for a seven-step sample: seven.** Confirmed independently by
`REFERENCE_STRUCTURE` in `tests/test_raw_plot_reference.py`, which pins
`"ech2": (2, [7, 7], [1, 1])` and `"ech4": (2, [7, 7], [1, 1])` — two panels,
seven data lines each, one break-mark artist each. So an annotation scheme must
survive seven overlaid traces, not one.

**Legend: one per panel, `loc="best"`, framed, titled "step".** Quoting:

    panel.legend(
        handles,
        [_step_label(step) for step in sorted(set(panel_steps))],
        loc="best",
        frameon=True,
        title="step",
    )

`loc="best"` matters for this feature: the legend is placed by matplotlib into
whatever region it judges emptiest, so adding text to the plot can **move the
legend**. That is a real coupling between annotation and the existing layout.
The comment above it explains why it is per-panel: a sample can be missing a
step in one window but not the other.

**Figure size: `FIGURE_SIZE = (11.0, 5.5)` inches**, i.e. 792 × 396 points,
measured. `PANEL_GAP = 0.05` is the `wspace`. `DPI = 200` at save time.

**The x-axis is NOT shared, and neither is the y-axis.** `plt.subplots` is
called with no `sharex` and no `sharey`. The docstring states the y axes
autoscale independently "because within a sample one window's maximum can be an
order of magnitude above the other's", and the reference test asserts the y axes
are not joined:

    assert not left.get_shared_y_axes().joined(left, right)

Contrast `build_baseline_diagnostic`, which does pass `sharex=True`.

**It returns an open figure and does not save.** The last lines:

        if baseline_params is None:
            _assert_drawn_data_is_raw(drawn)
        else:
            _assert_drawn_data_is_corrected(drawn_corrected)
        return figure

Saving is `plot_sample_overlay`'s job — a thin wrapper that calls
`build_sample_overlay` then `_save`. The docstring is explicit: "Nothing is
saved and the figure is left open: the caller owns it and must close it."

**One more thing that constrains this feature: the tripwire.**
`_assert_drawn_data_is_raw` iterates a `drawn` list of `(line, spectrum)` pairs
built as each line is plotted — not re-derived from `panel.lines`. The comment
says why:

    # Each line is paired with its spectrum as it is drawn. Re-deriving the
    # mapping from panel.lines at save time would depend on draw order and on
    # filtering out the break-mark artists, and a tripwire that can silently
    # mis-pair is worse than no tripwire at all.

So **adding artists to a panel does not confuse the tripwire** — it only ever
inspects the lines it was explicitly handed. An annotation drawn with
`axes.text` or `axes.annotate` adds no `Line2D` at all and is invisible to it.
An annotation drawn with `axes.plot` (a marker at each centre) *would* add a
`Line2D` to `panel.lines`, which the tripwire still ignores, but which
`data_lines()` in the reference test does not — see B4.

Scope: `build_sample_overlay`, `plot_sample_overlay`,
`_assert_drawn_data_is_raw` and `_spectra_by_window` in `plotting.py`;
`REFERENCE_STRUCTURE` in `tests/test_raw_plot_reference.py`; geometry measured
on the real ech2 figure.

### B2 — the suffix computation and every path `plot` can produce. CONFIRMED

Quoted verbatim from `write_sample_overlays` in `report.py`, comment included
because it states the design rule:

    # Filenames encode every flag that changes what is drawn, so that the same
    # path always means the same bytes and no combination can overwrite
    # another's output. Only `logy` needs encoding: it changes the two overlay
    # figures, and the diagnostic figure does not take it at all. The scheme is
    # computed here from the flags this function already has rather than being
    # injectable - if a caller ever needs to override it, this is the place.
    scale_suffix = LOG_SCALE_SUFFIX if logy else ""

And the constant, with its own comment:

    # Appended to the figures whose content depends on the y-scale, so a log-scaled
    # run cannot land on the linear run's filename. The diagnostic figure never
    # takes `logy`, so it carries no suffix.
    LOG_SCALE_SUFFIX = "_log"

The three write sites, quoted:

    if not baseline and not diagnostic:
        path = plot_sample_overlay(
            group, output_directory / f"{name}_overlay{scale_suffix}.png", logy=logy
        )

    if baseline:
        path = plot_sample_overlay(
            group,
            output_directory / f"{name}_overlay_baseline{scale_suffix}.png",
            …

    if diagnostic:
        …
        for window in sorted(by_window, key=window_sort_key):
            path = plot_baseline_diagnostic(
                by_window[window],
                output_directory / f"{name}_{window}_baseline_check.png",
                …

**Every output path `plot` can currently produce, and the flag combination that
produces it.** The three booleans are `(baseline, diagnostic, logy)`:

| combination | paths written |
|---|---|
| F, F, F — no flags | `{sample}_overlay.png` |
| F, F, T — `--logy` | `{sample}_overlay_log.png` |
| F, T, F — `--baseline-diagnostic` | `{sample}_{window}_baseline_check.png` |
| F, T, T — `--baseline-diagnostic --logy` | `{sample}_{window}_baseline_check.png` (identical bytes) |
| T, F, F — `--baseline` | `{sample}_overlay_baseline.png` |
| T, F, T — `--baseline --logy` | `{sample}_overlay_baseline_log.png` |
| T, T, F — `--baseline --baseline-diagnostic` | `{sample}_overlay_baseline.png` + `{sample}_{window}_baseline_check.png` |
| T, T, T — both plus `--logy` | `{sample}_overlay_baseline_log.png` + `{sample}_{window}_baseline_check.png` |

**Five distinct filename patterns.** Note the guard `if not baseline and not
diagnostic:` — **`--baseline-diagnostic` alone suppresses the raw overlay**. A
diagnostic run does not also write `{sample}_overlay.png`. That is the mechanism
by which the six reference files are only ever produced by the no-flag run, and
`test_the_raw_filename_is_produced_only_by_the_raw_combination` asserts exactly
that.

`--sample` and `--force` do not appear in any filename: `--sample` restricts
which samples are written, not what any one file contains, and `--force` only
gates whether anything is written at all.

Scope: `write_sample_overlays` and `LOG_SCALE_SUFFIX` in `report.py`.

### B3 — how `test_output_filenames.py` enumerates combinations. `itertools.product`

Quoting the enumeration, which is a single line at module level:

    COMBINATIONS = list(itertools.product([False, True], repeat=3))  # baseline, diagnostic, logy

So it is **`itertools.product`, not a hardcoded list** — eight 3-tuples. But the
`repeat=3` is only one of five places the arity is baked in. The tuples are
consumed structurally throughout:

    def run(spectra, root: Path, baseline: bool, diagnostic: bool, logy: bool):

    return {
        (baseline, diagnostic, logy): run(
            spectra,
            root / f"out_{int(baseline)}{int(diagnostic)}{int(logy)}",
            baseline,
            diagnostic,
            logy,
        )
        for baseline, diagnostic, logy in COMBINATIONS
    }

    for baseline, diagnostic, logy in COMBINATIONS:
        if not baseline and not diagnostic and not logy:
            continue

and four tests index `all_runs` with literal 3-tuples:

    linear = all_runs[(False, False, False)]
    log = all_runs[(False, False, True)]
    …
    linear = all_runs[(True, False, False)]
    log = all_runs[(True, False, True)]
    …
    assert producers == [(False, False, False)]
    …
    without = {k: v for k, v in all_runs[(False, True, False)].items() if "check" in k}
    with_logy = {k: v for k, v in all_runs[(False, True, True)].items() if "check" in k}

**Exactly what would have to change if one new boolean flag were added to
`plot`:**

1. `COMBINATIONS` — `repeat=3` becomes `repeat=4`, and the trailing comment
   listing the flag order gains the new name. **This doubles the rendered
   combinations from 8 to 16**, and the `all_runs` fixture is already described
   in its own docstring as "the slow part of this module".
2. `run()` — a fourth parameter, threaded into the `write_sample_overlays` call.
3. The `all_runs` dict comprehension — the key tuple, the `out_{…}` directory
   name, the unpacking in the `for` clause, and the extra positional argument.
4. `test_a_baseline_run_never_writes_the_raw_figure` — its unpacking
   `for baseline, diagnostic, logy in COMBINATIONS` and its skip condition
   `if not baseline and not diagnostic and not logy`.
5. **Every literal 3-tuple index becomes a 4-tuple** — six of them, across four
   tests (listed above). These fail with `KeyError`, not with a helpful message,
   so they must all be found; a missed one is a hard failure rather than a
   silent pass, which is the good direction.

The two core tests — `test_same_filename_always_means_identical_bytes` and
`test_differing_content_always_gets_a_different_path` — need **no change at
all**. They iterate `all_runs` generically and never mention arity. That is the
module's real strength: the guarantee itself is arity-independent, and only the
scaffolding around it is not.

Scope: `tests/test_output_filenames.py`, read in full. Not a sweep of the rest
of `tests/`.

### B4 — does the reference test render only the no-flag path? CONFIRMED

**All eight `build_sample_overlay` call sites in that module pass a single
positional argument and no keywords.** Grepped and confirmed:

    100:    figure = build_sample_overlay(by_sample[sample])
    112:    figure = build_sample_overlay(by_sample[sample])
    130:    figure = build_sample_overlay(by_sample[sample])
    145:    figure = build_sample_overlay(by_sample[sample])
    162:    figure = build_sample_overlay(by_sample[sample])
    179:    figure = build_sample_overlay(by_sample[sample])
    236:    figure = build_sample_overlay(by_sample[sample])
    313:    figure = build_sample_overlay(by_sample[sample])

The eighth-listed (in the `rendered` fixture) is the one that produces the
pixel comparison:

    figure = build_sample_overlay(by_sample[sample])
    try:
        target = out / f"{sample}_overlay.png"
        figure.savefig(target, dpi=DPI, bbox_inches="tight")

and the comparison itself:

    on_disk = mpimg.imread(path)
    expected = mpimg.imread(rendered[sample])
    assert on_disk.shape == expected.shape, …
    assert np.array_equal(on_disk, expected), …

So: **the no-flag path only, `logy=False` and `baseline_params=None` by default,
compared pixel-by-pixel as float arrays against the six committed PNGs.**
CONFIRMED.

**Could a new flag defaulting to False alter the bytes that test compares?
No — and three separate things guarantee it, at three different levels.**

1. **Signature-level.** The test calls `build_sample_overlay(spectra)` with no
   keywords. A new parameter defaulting to `False` is not passed, so it takes
   its default. This holds only if the new parameter is genuinely defaulted and
   the annotation is genuinely gated on it — a parameter that defaults to `True`
   or an annotation drawn unconditionally would change these bytes immediately,
   and the test would catch it. That is the test working, not a risk.
2. **Path-level.** `write_sample_overlays` writes the raw name only under
   `if not baseline and not diagnostic:`, and a new flag would extend the suffix
   or the condition — the six reference names are already asserted to be
   produced by exactly one combination
   (`test_the_raw_filename_is_produced_only_by_the_raw_combination`).
3. **Structural-level, and this is the one to watch.** `REFERENCE_STRUCTURE`
   pins the artist counts per panel, and the helpers that count them are:

        def data_lines(axes):
            return [line for line in axes.lines if line.get_linestyle() != "None"]

        def break_marks(axes):
            return [line for line in axes.lines if line.get_linestyle() == "None"]

   These partition `axes.lines` by linestyle. **An annotation drawn as a
   `Line2D` — a marker at each band centre via `axes.plot`, or a vertical rule
   via `axes.axvline` — would land in one of these two buckets and change the
   pinned counts**, breaking `test_panel_and_line_counts_are_unchanged` and
   `test_every_line_still_carries_the_raw_file_data` (which asserts
   `len(drawn) == len(source)`). An annotation drawn with `axes.text` or
   `axes.annotate` adds a `Text` artist, not a `Line2D`, and is invisible to
   both helpers. This is not a reason to avoid `axvline` — under a flag
   defaulting to False the annotated path is never built by this test — but it
   is the specific trap if the annotation ever leaks into the default path.

Also relevant: the module docstring records that these are structural
assertions rather than a byte hash, deliberately, "because a byte hash breaks on
any matplotlib, freetype or libpng upgrade". The **disk** comparison is still
pixel-exact, but both sides are rendered by the same matplotlib at test time.

Scope: `tests/test_raw_plot_reference.py`, read in full.

### B5 — the `plot` argparse block. Quoted in full

Verbatim from `main.py`:

    plot = subparsers.add_parser("plot", help="write one overlay figure per sample")
    plot.add_argument("--experiment", help="name of the folder under data/raw/")
    plot.add_argument("--sample", help="restrict output to this sample")
    plot.add_argument("--logy", action="store_true", help="use a log y-scale on both panels")
    plot.add_argument(
        "--force", action="store_true", help="draw even if hard checks fail"
    )
    plot.add_argument(
        "--baseline",
        action="store_true",
        help="draw baseline-corrected spectra instead of raw",
    )
    plot.add_argument(
        "--baseline-diagnostic",
        action="store_true",
        help="write a per-window figure showing each fit and its result",
    )
    plot.add_argument("--baseline-lam", type=float, help="override the baseline smoothness")
    plot.add_argument("--baseline-p", type=float, help="override the baseline asymmetry")
    plot.add_argument(
        "--baseline-n-iter", type=int, help="override the baseline iteration count"
    )

Shape of a new boolean flag, therefore: `action="store_true"`, hyphenated name,
one-line lower-case help string with no trailing full stop. Note also the
existing precedent for **rejecting a flag combination in `main.py` rather than
downstream**, which is directly relevant to D2:

    supplied = [flag for flag, value in tuning.items() if value is not None]
    if supplied and not baseline_mode:
        print(
            f"error: {', '.join(supplied)} requires --baseline or --baseline-diagnostic",
            file=sys.stderr,
        )
        return 1

Scope: `main.py`, read in full.

### B6 — THE KEY DEPENDENCY QUESTION. CONFIRMED: `plot` does not read `bands.json`, and does not have what `load_bands_config` needs

**Tracing the `plot` path from `main.py`.** Every file it opens:

1. `load_experiment(RAW_ROOT, args.experiment)` — reads the `.txt` spectra.
   Common to all three subcommands, before dispatch.
2. `resolve_baseline_config(...)` — **only inside `if baseline_mode:`**, where
   `baseline_mode = args.baseline or args.baseline_diagnostic`. Reads
   `baseline.json` and nothing else.
3. `write_sample_overlays(...)` — opens no config; it takes
   `baseline_params` already resolved.

**So plain `plot`, with no flags, loads no configuration file whatsoever.** Only
the `.txt` files. Corroborated at module level: `report.py` contains exactly two
config reads, at the `is_file()` / `read_text` pairs in the baseline loader and
in `load_bands_config`, and

    load_bands_config    called from report.py:1380 only — inside quantify_experiment
    common_window_ranges called from report.py:1379 only — inside quantify_experiment

Both are called from `quantify_experiment` and nowhere else in `src/` or
`main.py`. The only other callers anywhere are in `tests/test_quantify.py`.
CONFIRMED.

**`load_bands_config`'s exact signature:**

    def load_bands_config(
        experiment_folder: Path, window_ranges: Mapping[str, tuple[float, float]]
    ) -> tuple[str, dict[str, BandSpec], dict[str, tuple[float, float]]]:

**What it requires from the caller: yes, window ranges computed from loaded
spectra.** Quoting its docstring:

        window_ranges: The wave range every file of each window label shares,
            from :func:`common_window_ranges`. Its keys are the window labels
            present in the experiment, and are the only ones the config may
            name. Not the modal ranges: see that function for why.

It is not decorative. `valid_windows = sorted(window_ranges)` is what rejects a
band naming a window the experiment does not contain, and the ranges bound every
search window and noise region so that "a centre that no spectrum can measure
fails here rather than at measurement time, before anything has been written".
`common_window_ranges` returns the **intersection** — the highest minimum and
lowest maximum across every file with that label — deliberately not the modal
range, because `measure_band` checks each spectrum against its own axis.

**What it does when `bands.json` is absent: it RAISES.** Quoted:

    path = experiment_folder / BANDS_CONFIG_NAME
    if not path.is_file():
        raise FileNotFoundError(
            f"no band configuration found; expected {path}. "
            f"Create it to describe which bands to measure."
        )

Not empty, not a default. Contrast the baseline loader in the same module, which
returns empty and falls through to built-in defaults:

    path = experiment_folder / BASELINE_CONFIG_NAME
    if not path.is_file():
        return {}, {}

The two configs are deliberately asymmetric: a missing `baseline.json` has a
sensible default, a missing `bands.json` does not, because there is no default
answer to "which bands".

**Does `plot` currently have, at the point where it would need them, everything
`load_bands_config` requires?**

- `experiment_folder`: **yes, trivially.** `main.py` already holds
  `RAW_ROOT / args.experiment` and passes it to `resolve_baseline_config`.
- `window_ranges`: **NO.** `plot` never calls `common_window_ranges`. But it
  does hold `spectra`, which is that function's only argument — the call is
  `common_window_ranges(spectra)` and nothing more. `common_window_ranges` is
  already a public function in `report.py`, already imported into the test
  suite, and reads no files.

**Verdict: a small addition, not a plumbing change.** The missing input is one
pure function call over data `plot` already holds. What *is* new is a genuine
new dependency of the `plot` path on `bands.json` and on the error behaviour
that comes with it — which is D2, a design question rather than a plumbing one.

Scope: the `plot` and `quantify` branches of `main.py`;
`write_sample_overlays`, `load_bands_config`, `common_window_ranges`,
`resolve_baseline_config` and the baseline file loader in `report.py`; plus a
repository grep over `src/`, `main.py` and `tests/` for both callers.

### B7 — does `plot` depend on `data/derived/`? CONFIRMED: no dependency at all

`DERIVED_ROOT` is defined once in `main.py` and referenced exactly once more:

    main.py:25:DERIVED_ROOT = PROJECT_ROOT / "data" / "derived"
    main.py:114:                DERIVED_ROOT,

Line 114 is inside the `quantify` branch, in the `quantify_experiment(...)` call.
`write_sample_overlays` has no `derived_root` parameter — its signature takes
`experiment, spectra, figures_root, sample, logy, force, baseline, diagnostic,
baseline_params`. And `plotting.py` contains **zero** occurrences of "derived"
or "DERIVED" in any form. CONFIRMED.

**Which of the two the code could annotate without acquiring a new dependency.**

- **Configured centres** — `bands.json`, `centre` per band. Under `data/raw/`,
  tracked in git, present in a fresh clone. Annotating these acquires a
  dependency on `bands.json` (B6) but on nothing generated.
- **Located maxima** — `bands.csv`, the `position` column. **Under
  `data/derived/`, gitignored build output** (established in entry 004: `git
  check-ignore` gives `.gitignore:21:data/derived/`, and the file is untracked).
  Annotating these would make `plot` depend on a file that a fresh clone does
  not have, that only `quantify` produces, and whose staleness `plot` has no way
  to detect — `provenance.json` records the raw hashes but `plot` would have to
  read and verify them to know the CSV still describes the spectra it is
  drawing.

There is a second reason beyond the dependency, and it is the stronger one:
`bands.csv` is written by `quantify`, which measures on **baseline-corrected**
data unconditionally. Its `position` values are maxima of the corrected
spectrum. Drawing them onto a **raw** overlay would mark positions derived from
a different array than the one on screen. For ech2 and ech4 the located
positions happen to be close to the centres — drift is under 5 cm-1 in 55 of the
56 rows per sample (entry 004, A7) — so the two annotations would look nearly
identical here, which makes the coupling easy to adopt and hard to notice.

**So: configured centres, without question.** They are the only option that
keeps `plot` free of `data/derived/` and free of the raw-versus-corrected
mismatch.

Scope: `main.py`, `write_sample_overlays` in `report.py`, and a repository grep
for "derived" over `src/**/*.py` and `main.py`.

### B8 — LABEL PLACEMENT FEASIBILITY. Measured

Baseline parameters used for the corrected case, resolved by hand from
`baseline.json` and printed by the script:

    {'low':  {'lam': 1000000.0,   'p': 0.01, 'n_iter': 10},
     'high': {'lam': 100000000.0, 'p': 0.01, 'n_iter': 10}}

**Drawn y-range per window, across all seven steps.** "@centre" is the value at
the wave sample nearest the configured centre — not the located maximum, which
is B7's distinction. Min and max are across the seven steps.

**ech2 low** — raw range 2,042.0 .. 157,853.5; corrected range −485.2 ..
153,224.6

| band | centre | raw @centre min..max | corrected @centre min..max | raw, % of panel max |
|---|---|---|---|---|
| si_522 | 522 | 148,893.8 .. 157,853.5 | 144,449.3 .. 153,224.6 | 100.0% |
| glycine_893 | 893 | 9,348.9 .. 10,263.9 | 5,990.8 .. 6,589.9 | 6.5% |
| glycine_979 | 979 | 9,034.5 .. 9,776.6 | 5,841.1 .. 6,081.9 | 6.2% |
| glycine_1328 | 1328 | 11,332.5 .. 13,289.1 | 8,408.8 .. 11,058.5 | 8.4% |
| glycine_1412 | 1412 | 6,411.7 .. 7,213.9 | 3,709.7 .. 4,595.1 | 4.6% |

**ech2 high** — raw range 3,286.9 .. 34,439.7; corrected range −672.6 ..
28,489.7

| band | centre | raw @centre min..max | corrected @centre min..max | raw, % of panel max |
|---|---|---|---|---|
| glycine_2975 | 2975 | 28,067.5 .. 34,370.3 | 22,317.7 .. 28,150.0 | 99.8% |
| glycine_3012 | 3012 | 17,433.9 .. 22,393.0 | 11,593.8 .. 16,356.3 | 65.0% |
| glycine_3146 | 3146 | 8,664.6 .. 10,416.6 | 2,521.1 .. 3,538.6 | 30.2% |

**ech4 low** — raw range 7,143.2 .. 116,329.9; corrected range −998.6 ..
104,163.2

| band | centre | raw @centre min..max | corrected @centre min..max | raw, % of panel max |
|---|---|---|---|---|
| si_522 | 522 | 100,153.7 .. 116,329.9 | 86,602.3 .. 104,163.2 | 100.0% |
| glycine_893 | 893 | 51,549.0 .. 59,992.2 | 38,331.8 .. 45,659.6 | 51.6% |
| glycine_979 | 979 | 11,679.3 .. 21,662.6 | 3,187.7 .. 3,760.2 | 18.6% |
| glycine_1328 | 1328 | 80,909.7 .. 100,228.3 | 69,505.2 .. 77,780.0 | 86.2% |
| glycine_1412 | 1412 | 38,770.9 .. 53,511.1 | 27,259.9 .. 31,594.4 | 46.0% |

**ech4 high** — raw range 11,633.4 .. 235,572.5; corrected range −4,554.1 ..
205,714.8

| band | centre | raw @centre min..max | corrected @centre min..max | raw, % of panel max |
|---|---|---|---|---|
| glycine_2975 | 2975 | 184,640.1 .. 232,694.2 | 161,746.7 .. 202,842.2 | 98.8% |
| glycine_3012 | 3012 | 114,620.9 .. 148,423.4 | 91,653.0 .. 118,483.6 | 63.0% |
| glycine_3146 | 3146 | 41,198.8 .. 59,851.9 | 21,256.5 .. 29,926.1 | 25.4% |

**Note the corrected minima are negative in every window** — down to −4,554.1 in
ech4 high. Any annotation anchored to zero rather than to the trace would sit
inside the data on a corrected figure.

**Headroom above the traces, measured from the real figures:**

| sample / window | ylim | highest drawn value | headroom |
|---|---|---|---|
| ech2 low | 0.0 .. 165,644.1 | 157,853.5 | 4.70% of panel height (7,790.6 counts) |
| ech2 high | 1,729.3 .. 35,997.4 | 34,439.7 | 4.55% (1,557.6 counts) |
| ech4 low | 1,683.9 .. 121,789.2 | 116,329.9 | 4.55% (5,459.3 counts) |
| ech4 high | 436.4 .. 246,769.4 | 235,572.5 | 4.55% (11,197.0 counts) |

That is matplotlib's default 5% autoscale margin, essentially untouched. **There
is no reserved space above the traces.** A label placed above the tallest peak
would sit in a band ~4.6% of panel height — about 18 points on a 396-point
figure — which fits one line of 8pt text with almost nothing to spare, and only
for the tallest peak. For every other band the "space above the trace" is space
occupied by nothing, but it is also space the seven overlaid traces of *other*
steps pass through.

**Does the low window's dynamic range leave usable headroom on a linear axis?
For ech4, yes. For ech2, no.** ech2's four glycine bands sit at 4.6%, 6.2%, 6.5%
and 8.4% of panel height, all four within a 4-percentage-point band near the
floor, while `si_522` occupies the top. ech4's spread is 18.6%, 46.0%, 51.6%,
86.2% — genuinely usable. This is D1.

**Drawn geometry, measured on the real ech2 figure (built in memory, not
saved):**

    figure size: 11.0 x 5.5 inches = 792 x 396 points
    low  panel: width 0.4457 of figure = 4.903 in = 353.0 pt; xlim 120.764 .. 1906.029 (span 1785.265)
    high panel: width 0.3104 of figure = 3.414 in = 245.8 pt; xlim 2316.469 .. 3559.649 (span 1243.180)
    scale: 5.057 cm-1 per point in BOTH panels

The identical scale across the break is the `width_ratios=spans` design working,
and it means one annotation rule can apply to both panels without adjustment.

**Centre-to-centre proximity in drawn x-units, with real measured text
extents.** Label widths are `Text.get_window_extent` under the Agg renderer,
converted to points. "Half-widths sum" is the minimum centre-to-centre distance
two horizontally-centred labels need in order not to touch.

At **fontsize 8** (the size `plotting.py` already uses for its trend-figure
legends):

    low window
      si_522       -> glycine_893    gap  371 cm-1 =  73.4 pt; need 37.1 pt -> clears
      glycine_893  -> glycine_979    gap   86 cm-1 =  17.0 pt; need 48.2 pt -> COLLIDES
      glycine_979  -> glycine_1328   gap  349 cm-1 =  69.0 pt; need 50.8 pt -> clears
      glycine_1328 -> glycine_1412   gap   84 cm-1 =  16.6 pt; need 53.3 pt -> COLLIDES
    high window
      glycine_2975 -> glycine_3012   gap   37 cm-1 =   7.3 pt; need 53.3 pt -> COLLIDES
      glycine_3012 -> glycine_3146   gap  134 cm-1 =  26.5 pt; need 53.3 pt -> COLLIDES

Measured label widths at 8pt: `si_522` 25.9, `glycine_893` 48.2, `glycine_979`
48.2, `glycine_1328` 53.3, `glycine_1412` 53.3, `glycine_2975` 53.3,
`glycine_3012` 53.3, `glycine_3146` 53.3 points.

At **fontsize 9** every gap that collided at 8 still collides, and by more —
widths rise to 30.2 / 56.2 / 61.9 points. Dropping to 8 buys nothing structural.

**Four of the seven adjacent pairs collide with horizontal labels at the band
centre.** The worst is `glycine_2975` → `glycine_3012`: 37 cm-1 apart, which is
**7.3 points** on the drawn figure, against labels 53.3 points wide. They
overlap by a factor of seven. No font size in a usable range fixes that —
clearing 7.3 points would need labels under 7.3 points wide, i.e. about one and
a half characters.

**What this rules out and what it leaves.** Horizontal labels at the band
centres are not viable. What remains viable, none of which I am proposing here:
rotated (90°) labels, whose *width* becomes the line height (~10 pt at 8pt
font) and which clear every gap except `glycine_2975` → `glycine_3012` at 7.3
pt; short numeric labels (`522`, `2975`) instead of full band names, roughly
halving widths but still not clearing 7.3 pt; staggering labels across two or
three vertical rows; or a numbered-marker scheme with a key, which decouples
label width from the gap entirely.

Scope: ech2 and ech4 only, both windows, all seven steps each, from the real
`data/raw/` files. Geometry measured on the ech2 figure; the low/high panel
widths and cm-1-per-point are properties of the window spans and `FIGURE_SIZE`,
which ech4 shares, but I measured them on ech2 and did not re-measure on ech4.

### B9 — is `plotting.py` under the genericity constraint? CONTRADICTED as stated — it is not named

**The rule names one module.** Quoting `CLAUDE.md`'s hard rules in full:

    - `src/ramsess/analysis.py` stays generic. Nothing in it may be specific to
      glycine, silicon, this instrument or these window ranges: no band positions,
      no sample assumptions, no tuned magic numbers presented as universal
      constants. It operates on an arbitrary intensity array and takes every
      parameter from its caller. If a future analysis genuinely needs a band
      position, that position is configuration, never a literal in the module. The
      module also writes no files and prints nothing.

`analysis.py`, and nothing else. **`bands.py` picks the constraint up by its own
docstring**, not by the hard rule:

    Deliberately generic, like :mod:`ramsess.analysis`. Nothing here knows about any
    particular sample, substrate, instrument or wavenumber: every band position,
    width and noise region is supplied by the caller from configuration. There are
    no literals describing any dataset in this module, and it writes no files and
    prints nothing.

**`plotting.py` carries no such statement.** Its module docstring imposes a
different constraint entirely — no transforms, not no specifics:

    All matplotlib work lives here. Intensities are drawn as raw counts: nothing in
    this module smooths, baseline-corrects, normalises or rescales the data.

(That first sentence is itself now slightly loose, since `build_sample_overlay`
gained an opt-in baseline mode that calls `correct_baseline`. I note it because
I read the line closely; it is not this task's business and I propose nothing
about it.)

Grepping `CLAUDE.md` and `README.md` for `plotting`, the five substantive hits
are about the tripwire, the Agg side effect, the lazy import, the six
alphabetical sorts, and the settled raw path. **None imposes genericity.**

**So the applicable constraint on `plotting.py` is the general one**, which is
repo-wide and does apply:

    - Hardcode nothing about the dataset. Sample names, experiment names, step
      counts, file counts and window ranges are discovered at runtime.

**What experiment-specific knowledge `plotting.py` already contains.** Grepped
the module for `ech[0-9]`, `glycine`, `silicon`, `si_5`, `522`, `893`. **Exactly
one hit, and it is in a comment, not in code:**

            # Intensities are photon counts and cannot be negative, so the
            # autoscale margin dipping below zero is meaningless space. Clamp it
            # away, but ONLY when autoscale actually went negative. Forcing every
            # panel to start at zero would add a large empty band under samples
            # whose baseline sits well above it - ech6's low window spans
            # 16941-37168 and would lose nearly half its height. Keep conditional.

That is a sample name and two measured intensities, cited as the **evidence for
a conditional**, not used as a value. The code itself reads `if bottom < 0:` and
contains no number from this dataset. By comparison, `analysis.py` and `bands.py`
have zero hits for the same pattern, in code or comment.

The other module-level constants — `CONTROL_STEP = 0`, `IRRADIATION_COLORMAP`,
`FIGURE_SIZE`, `X_LABEL = "Raman shift (cm-1)"`, `Y_LABEL = "Intensity
(counts)"` — describe the filename convention and Raman spectroscopy generally,
not this experiment. `WINDOW_ORDER` is imported from `io.py`, where `CLAUDE.md`
records it as a hardware constraint rather than a dataset assumption.

**Bearing on this feature:** band positions must come from `bands.json`
regardless — the general hard rule forbids literals, and B7 already rules out the
alternative source. But `plotting.py` is not held to `analysis.py`'s stricter
standard, so a *drawing* function may legitimately take band specs as a
parameter and know what a band is. What it may not do is contain a centre.

Scope: `plotting.py`, `analysis.py` and `bands.py` grepped for
experiment-specific literals; `CLAUDE.md` and `README.md` grepped for statements
about `plotting.py` and for the genericity rule.

---

## 5. DESIGN RECOMMENDATION

Not an implementation. Reasons given for each choice; the two open questions are
D1 and D2 in section 1.

**New flag on `plot`, not a subcommand, not an unflagged extra output.**

- *A separate subcommand* would duplicate the whole `plot` preamble —
  experiment resolution, `load_experiment`, preflight gating, `--sample`,
  `--force`, the baseline flag family and their validation — for a figure that
  differs from `plot`'s by some text artists. `CLAUDE.md` says to split a module
  when it has two responsibilities, not to make it smaller; the same reasoning
  applies to a subcommand. This is one responsibility: draw a sample's overlay.
- *An extra output with no new flag* is the worst option and would break a
  stated guarantee. Every existing `plot` invocation would start writing an
  additional file, and — more seriously — a user who runs plain `plot` expecting
  the six reference figures would get an annotated file alongside them with no
  way to decline. The filename scheme's whole premise is that flags select
  content.
- *A new boolean flag* matches every existing precedent in B5 and costs what B3
  measures: `COMBINATIONS` goes to `repeat=4`, rendering doubles from 8 to 16,
  and six literal 3-tuples become 4-tuples. That cost is real but bounded, and
  the two core guarantees in that module need no change at all.

**Filename: `{sample}_overlay_annotated{scale_suffix}.png`, and the baseline
variant `{sample}_overlay_baseline_annotated{scale_suffix}.png`.** This slots
into the existing scheme without disturbing it: the suffix is composed from the
flags `write_sample_overlays` already holds, at the one place its comment names
as "the place" to change the scheme. Ordering matters — putting `_annotated`
before `{scale_suffix}` keeps `_log` last, which is how `_baseline_log` already
reads, so the pattern stays "content flags, then scale". The combination count
doubling is the honest cost of a fourth boolean and is not avoidable by naming.

Two sub-questions the experimenter should settle, because they change the count:
whether annotation is offered on the diagnostic figure (**recommend no** — that
figure is for judging a fit, not for reading peaks, and it already takes no
`logy`), and whether annotation is offered with `--logy` (**recommend yes** —
D1 may make the log variant the better conference figure for ech2, and refusing
it would be deciding D1 by omission).

**Annotate configured centres, not located maxima.** B7 settles this on two
independent grounds: located maxima live in `bands.csv` under `data/derived/`,
which is gitignored build output that only `quantify` produces and whose
staleness `plot` cannot detect; and those positions are maxima of the
**corrected** spectrum, so drawing them on a raw overlay would mark positions
derived from a different array than the one on screen. Configured centres come
from `bands.json` under `data/raw/`, tracked, present in a fresh clone. The two
would look nearly identical on ech2 and ech4 — drift under 5 cm-1 in 55 of 56
rows per sample — which makes the wrong choice easy to make and hard to notice,
and is a reason to be explicit rather than a reason it does not matter.

**Labelling eight bands across two windows over seven traces.** B8 rules out the
obvious approach: horizontal labels at the centres collide on four of seven
adjacent pairs, worst at `glycine_2975` → `glycine_3012`, 37 cm-1 = **7.3
points** apart against 53.3-point labels. Reducing the font size does not help —
at 9pt the same four collide, and clearing 7.3 pt needs a label under two
characters wide. The measured headroom above the traces is ~4.6% of panel
height in all four panels, matplotlib's default margin, so there is no reserved
band to place labels into without extending the axis. My recommendation, in
preference order: **rotate labels 90°**, which makes the relevant extent the
line height (~10 pt at 8pt) rather than the string width and clears every gap
except the 7.3-pt one; anchor each label to the top of its panel rather than to
the trace, with a thin vertical rule down to the axis, so label placement is
independent of the seven overlaid traces and of the dynamic range that causes
D1; and **extend the y-limit** to create the band the labels sit in, which is a
display setting the tripwire explicitly permits ("Axis limits, colours, scales
and legends are display settings and may change freely") and which the reference
test does pin — but only for the unannotated path, which this does not touch.
That still leaves `glycine_2975`/`glycine_3012` needing a stagger onto two rows.
Note also that the per-panel legends use `loc="best"`, so adding artists can
move them; whatever is drawn should be checked against that rather than assumed
independent.

**When `bands.json` is absent.** `load_bands_config` raises `FileNotFoundError`
naming the expected path (B6). My recommendation: **let it raise, and catch it in
`main.py` the way the other config errors are caught** — `main.py` already has
the pattern, both for `FileNotFoundError` in the `quantify` branch and for the
"flag X requires flag Y" rejection quoted in B5. Reasons: the user asked for
annotation, and silently producing an unannotated figure gives them a file that
looks like a plain overlay under a name promising annotation, which violates
"the same path always means the same bytes" in spirit — the same name would mean
annotated or not depending on a file's existence. It is also consistent with
`CLAUDE.md`'s "Fail loudly … Never skip, guess or substitute a default", and
with the deliberate asymmetry between the two configs. Plain `plot` must keep
working with no `bands.json`; only the annotate flag requires one. This is D2
and the experimenter may reasonably prefer the notice-and-fall-through.

**The smallest change that achieves this**, in scope terms only:

- `plotting.py`: `build_sample_overlay` takes an optional band-spec argument
  defaulting to `None`, and draws the annotations only when it is given. It must
  take specs from its caller and contain no centre — B9's general hard rule.
- `report.py`: `write_sample_overlays` takes the new boolean, extends the suffix
  at the one place its comment designates, and passes the specs through.
- `main.py`: one `add_argument` in the shape of B5, plus the
  `common_window_ranges(spectra)` + `load_bands_config(...)` call, gated on the
  flag. This is argument parsing and dispatch plus two library calls, which
  stays inside `main.py`'s stated remit; if it does not, the pair belongs in
  `report.py` behind one function.
- `tests/test_output_filenames.py`: the five arity changes B3 enumerates.
- A test that the annotated path is byte-different from the unannotated one, in
  the spirit of the module it joins.

**What it must NOT touch.** `build_sample_overlay`'s default behaviour, in any
way that changes a pixel — B4 is the guard and the new parameter must default to
off. The six `{sample}_overlay.png` files and `REFERENCE_STRUCTURE`,
`REFERENCE_YLIM`, `REFERENCE_XLIM` in `tests/test_raw_plot_reference.py`; if any
of those needs changing, the change has escaped its flag. Both tripwires. The
annotations must not be drawn as `Line2D` artists on the default path, because
`data_lines()` and `break_marks()` partition `axes.lines` by linestyle and would
count them (B4). `quantify`, `bands.csv` and anything under `data/derived/` —
B7. `bands.json` itself, which is the experimenter's file. And
`analysis.py` and `bands.py`, which have no part in this at all.

---

## 6. Matters next

- **Run `tests/test_raw_plot_reference.py` before PHASE B.** It is the one
  premise of this task I did not verify (section 2), and if it is already red
  the "byte-identical" requirement is already violated and that is the finding.
- **D1 and D2 need answers before any code.** They are not implementation
  details; they determine what the figure is.
- **The 8-to-16 combination doubling in `test_output_filenames.py` is the main
  hidden cost**, and its `all_runs` fixture already calls itself the slow part
  of the module. Worth knowing before it is discovered as a slow test run.
- **`plotting.py`'s module docstring says "nothing in this module smooths,
  baseline-corrects, normalises or rescales the data", which the opt-in baseline
  mode has already outgrown** (B9). Noted in passing, out of scope here, not
  proposed.

---

## 7. Self-corrections during this phase

None. No claim made during this phase was later found wrong.

---

## 8. Everything measured or validated, with the numbers

| what | result |
|---|---|
| axes per figure | `len(windows)` — 2 for both-window samples, 1 otherwise |
| traces per axis, seven-step sample | 7; pinned as `(2, [7, 7], [1, 1])` for ech2 and ech4 |
| figure size | 11.0 × 5.5 in = 792 × 396 pt; `DPI` 200 at save |
| x-axis shared | no; y-axis shared | no (asserted by the reference test) |
| legend | one per panel, `loc="best"`, `frameon=True`, `title="step"` |
| saves or returns | returns an open figure; `plot_sample_overlay` saves |
| suffix computation | `scale_suffix = LOG_SCALE_SUFFIX if logy else ""`, `LOG_SCALE_SUFFIX = "_log"` |
| distinct filename patterns from `plot` | 5, over 8 flag combinations |
| combination enumeration | `itertools.product([False, True], repeat=3)` |
| sites needing change for a 4th flag | 5 (incl. 6 literal 3-tuple indices in 4 tests); 2 core tests need none |
| `build_sample_overlay` calls in the reference test | 8, all single positional arg, no keywords |
| config files plain `plot` reads | **none** |
| `load_bands_config` callers in `src/` + `main.py` | 1 — `quantify_experiment` |
| `common_window_ranges` callers in `src/` + `main.py` | 1 — `quantify_experiment` |
| `bands.json` absent | raises `FileNotFoundError` naming the path |
| `baseline.json` absent | returns `{}, {}` and falls back to defaults |
| `DERIVED_ROOT` references in `main.py` | 2 — the definition and the `quantify` call |
| "derived" occurrences in `plotting.py` | 0 |
| cm-1 per drawn point | 5.057 in both panels |
| low panel width | 0.4457 of figure = 353.0 pt; xlim span 1785.265 |
| high panel width | 0.3104 of figure = 245.8 pt; xlim span 1243.180 |
| headroom above traces | 4.70% (ech2 low), 4.55% (ech2 high, ech4 low, ech4 high) |
| ech2 low corrected, si_522 vs glycine_1412 | 153,224.6 vs 4,595.1 — factor 33 |
| ech2 low glycine bands, % of panel max (raw) | 4.6, 6.2, 6.5, 8.4 |
| ech4 low glycine bands, % of panel max (raw) | 18.6, 46.0, 51.6, 86.2 |
| corrected minima | negative in all four panels; worst −4,554.1 (ech4 high) |
| adjacent-pair collisions, horizontal labels @8pt | 4 of 7 |
| worst pair | `glycine_2975`→`glycine_3012`: 37 cm-1 = 7.3 pt vs 53.3 pt labels |
| label widths @8pt | 25.9 (`si_522`) to 53.3 pt (four-digit glycine names) |
| label widths @9pt | 30.2 to 61.9 pt; same 4 pairs collide |
| genericity rule names | `analysis.py` only; `bands.py` self-imposes; `plotting.py` neither |
| experiment-specific literals in `plotting.py` | 1, in a comment (`ech6`, 16941–37168); 0 in code |
| same in `analysis.py`, `bands.py` | 0 |

---

## 9. Files touched by this phase

`prompt_outputs/005-annotated-overlays-phaseA.md` (this file) and one appended
line in `prompt_outputs/INDEX.md`. Nothing else. `data/raw/`, `data/derived/`,
`figures/` — including the six reference overlays, which were not read —
`src/`, `tests/` and `main.py` are untouched.

PHASE A ends here. Awaiting answers to D1 and D2 and an explicit "PROCEED".
