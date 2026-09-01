# 010 — scale-exclusion-and-layout — PHASE A

Supersedes nothing. Measures two proposed changes; implements neither.

Date: 2026-09-01

**HEAD is `583414a`** — "Add annotated overlay figures behind --annotate".
**Entry 009 landed nothing on HEAD.** It was a PHASE A and was never committed;
its report and `INDEX.md` line are still uncommitted in the working tree:

    M prompt_outputs/INDEX.md
    ?? prompt_outputs/009-additional-bands-phaseA.md

So `data/raw/irradiation_sara/bands.json` still holds the **original eight
bands**. Every measurement below is against that config, not against entry 009's
proposed thirteen.

**Scope of this phase.** Read-only. Nothing created, edited, moved or deleted
except this file and its `INDEX.md` line. `plot` and `quantify` were not run.
Nothing was `git mv`d. The `git mv` behaviour in D11 was established in a
**throwaway git repository in the session scratchpad**, outside the project —
the project's own `figures/` tree was never modified, and
`git status --short figures/` is empty.

---

## 1. Blockers and decisions needed

**Three. All three are things measurement found rather than confirmed.**

**D-A — Change 2 would make the six reference overlays invisible to git, and the
loss is silent until the day it matters.** Proven, not reasoned: with the
current `.gitignore`, a path one level deeper is ignored —

    $ git check-ignore -v figures/irradiation_sara/ech2/ech2_overlay.png
    .gitignore:40:figures/*/*   figures/irradiation_sara/ech2/ech2_overlay.png

`git mv` still succeeds and keeps the file tracked, because gitignore governs
only untracked files. But in a throwaway repo reproducing the exact rules, once
such a file is untracked for any reason it **cannot be added back**:

    $ git rm --cached figures/exp/s/s_overlay.png
    $ git add figures/exp/s/s_overlay.png
    The following paths are ignored by one of your .gitignore files:
    figures/exp/s
    hint: Use -f if you really want to add them.
    git add exit: 1

The baseline that `test_raw_plot_reference` exists to compare against would be
gone, and `RULES.md` records that there is no second copy. **`.gitignore` must be
updated in the same commit as the move, not after.** The working replacement is
in D9 and is verified.

**D-B — `bands_all_samples.png` has no sample to live under.** Change 2's scheme
is `figures/<experiment>/<sample>/`, but `quantify` writes one experiment-level
figure that is by definition not per-sample. It has to stay at
`figures/<experiment>/`, which makes the tree mixed-depth. Decide whether that
is acceptable, or whether it goes somewhere else. This is not a detail: it is
the one output the proposed scheme has no place for.

**D-C — Change 1's flag value is a band name, and band names are completely
unvalidated.** Confirmed by reading `load_bands_config`: the name is the JSON
object key, passed straight to `BandSpec(name=name, ...)` with **no check of any
kind** — not a character class, not a length, not a pattern. A band may legally
be called `si 522`, `a/b`, `..`, or anything else JSON permits as a key. If that
string is interpolated into a filename, `_save` will happily act on it:

    output_path.parent.mkdir(parents=True, exist_ok=True)

so a `/` silently creates a directory and `..` climbs one. Compounding it,
**`write_sample_overlays` does not call `guard_not_under_raw` at any of its three
write sites** — only `quantify_experiment` guards its figure paths (D8). Decide
whether the flag encodes the band name into the filename at all, and if so what
sanitising or validation is required first.

---

## 2. What I could NOT check, and why

- **How either change looks.** Every number below is renderer or arithmetic
  evidence from figures built in memory. Nothing was saved or opened. D3's claim
  that ech2 "becomes readable" is a percentage-of-panel-height argument, not a
  visual judgement.
- **Whether the pixel comparison still passes after a real `git mv`**, because
  the phase forbids moving anything. I established the two facts it rests on —
  the blob OID is preserved exactly, and the working-tree bytes are untouched by
  a rename — in the scratch repo (D11), which is as close as read-only gets.
  The actual verification is one test run after the move and is named in D11.
- **The other four samples under Change 1.** D3 covers ech2 and ech4 as asked.
  `--exclude-from-scale` would apply to every sample plotted, and ech1, ech3,
  ech5 and ech6 are unmeasured here. ech3 in particular is documented as
  collapsing after irr3.
- **Whether matplotlib has any autoscale-over-a-subset facility I have missed.**
  I checked the drawn-data path and found none (D2), but this is a claim about
  the library's API surface, not about this repository, and I did not read
  matplotlib's source.
- **What a second experiment would do to Change 2.** There is only one
  experiment in `data/raw/`, so every pattern claim in D9 is verified against a
  single-experiment tree.

---

## 3. PROPOSED DEVIATIONS

**None to the phase's instructions.** Two disclosures about method:

- **D11's `git mv` behaviour was established in a scratch repository** created
  under the session scratchpad, with `.gitignore` copied from the project's
  `figures/` rules. That was the only way to get evidence rather than assertion
  without moving a tracked file, which the phase forbids. Nothing in the project
  was touched; the scratch repo is outside it.
- **D3 was measured twice.** My first recomputation of the lower limit did not
  reproduce the code's clamp rule and produced wrong percentages for the
  corrected cases. Section 7 records the error and the correction; the numbers
  reported in D3 are from the corrected run, which reproduces the current limits
  exactly on the panels the exclusion should not touch — the check that shows
  the method is sound.

---

## 4. Findings — Change 1

### D1 — every y-limit operation in `build_sample_overlay`, in order

There are exactly two blocks, and one of them is in the helper entry 008 added.
Grepped over the whole module: `set_ylim` / `get_ylim` appear at five places,
three of them inside `_annotate_band_centres`.

**First, immediately after the per-panel drawing loop:**

        if logy:
            panel.set_yscale("log")
        else:
            # Intensities are photon counts and cannot be negative, so the
            # autoscale margin dipping below zero is meaningless space. Clamp it
            # away, but ONLY when autoscale actually went negative. Forcing every
            # panel to start at zero would add a large empty band under samples
            # whose baseline sits well above it - ech6's low window spans
            # 16941-37168 and would lose nearly half its height. Keep conditional.
            bottom, top = panel.get_ylim()
            if bottom < 0:
                panel.set_ylim(bottom=0, top=top)

**Then the legend, then — only when annotating — the reserved-band extension
inside `_annotate_band_centres`:**

    # Raise the top so the reserved band is empty, compressing what is already
    # drawn into the rest. The bottom never moves.
    bottom, top = panel.get_ylim()
    if logy:
        low, high = float(np.log10(bottom)), float(np.log10(top))
        panel.set_ylim(bottom, float(10.0 ** (low + (high - low) / (1.0 - fraction))))
    else:
        panel.set_ylim(bottom, bottom + (top - bottom) / (1.0 - fraction))

**Order per panel, as the code runs:**

1. `panel.plot(...)` for every step — **this is what sets the limits**, by
   matplotlib's implicit autoscale. No explicit call.
2. `set_xlabel`.
3. `set_yscale("log")` **or** the conditional negative clamp above.
4. `panel.legend(..., loc="best", ...)`.
5. `if bands is not None: _annotate_band_centres(...)` → reads `get_ylim`,
   raises the top, and anchors the legend below the reserved band.

Note the clamp condition is on the **limit**, not the data: `if bottom < 0`. On
corrected panels whose data genuinely goes negative, the panel floor is still
forced to 0, so the negative excursion is cut off. That is existing behaviour
and is not this phase's business, but it matters for reproducing the limits
(section 7).

### D2 — where an exclusion would have to act. **The limit must be computed by hand.**

**There is no autoscale call to modify.** The top limit is produced by
matplotlib's implicit autoscale over the artists' data limits, triggered by
`panel.plot`. The only calls that touch limits are the two `set_ylim`s quoted in
D1, and neither computes the top — the clamp passes `top=top` straight through.

**The panel cannot be autoscaled over a subset of the drawn data.** Autoscale
works from `dataLim`, which is accumulated per artist from the whole of each
artist's data. There is no facility to mask a sub-range of one line out of it,
and each spectrum is a single `Line2D`.

**Splitting the excluded region into a separate artist is not available either**,
and this is the important constraint: `_assert_drawn_data_is_raw` requires each
drawn line's x and y to be `array_equal` to the full `wave` and `intensity`
arrays of its spectrum. Any scheme that draws the silicon region as its own line
would either break the tripwire or require weakening it, and `CLAUDE.md` says the
tripwire must not be removed.

So the exclusion must be **limit arithmetic only**: compute the max over the
spectra with the excluded window masked, apply matplotlib's margin, and
`set_ylim`. That is explicitly permitted — "Axis limits, colours, scales and
legends are display settings and may change freely. The plotted values may not."

The margin to match is `plt.rcParams["axes.ymargin"]`, measured as **0.05**.

### D3 — what the exclusion actually buys

Measured on real figures. "% now" and "% excluded" are the tallest drawn value
inside each band's search window, as a percentage of panel height. The excluded
window is `si_522` ± 15 = [507, 537].

**ech2, low, RAW — limit falls from 165,644.1 to 13,851.5, a factor of 11.96**

| band | % now | % excluded |
|---|---|---|
| si_522 | 95.3% | 1263.9% (off the top) |
| glycine_893 | 6.2% | **71.0%** |
| glycine_979 | 5.9% | **67.1%** |
| glycine_1328 | 8.0% | **95.5%** |
| glycine_1412 | 4.4% | **46.3%** |

**ech2, low, CORRECTED — limit falls from 160,910.1 to 11,635.6, a factor of 13.83**

| band | % now | % excluded |
|---|---|---|
| si_522 | 95.2% | 1316.9% |
| glycine_893 | 4.1% | **56.6%** |
| glycine_979 | 3.8% | **52.3%** |
| glycine_1328 | 6.9% | **95.0%** |
| glycine_1412 | 2.9% | **39.7%** |

**This is the case the supervisor is complaining about, and the change fixes it
outright.** ech2's four glycine bands go from occupying 2.9–8.0% of the panel —
a band four percentage points tall, which is the "almost flat" complaint — to
39.7–95.5%, spread across the full height.

**ech4, low, RAW — limit falls from 121,789.2 to 104,882.5, a factor of only 1.16**

| band | % now | % excluded |
|---|---|---|
| si_522 | 95.5% | 111.2% |
| glycine_893 | 51.2% | 59.3% |
| glycine_979 | 16.7% | 18.8% |
| glycine_1328 | 82.0% | 95.5% |
| glycine_1412 | 43.6% | 50.4% |

**ech4, low, CORRECTED — factor 1.34**, glycine_893 43.8%→58.7%,
glycine_979 3.5%→4.6%, glycine_1328 71.1%→95.2%, glycine_1412 29.5%→39.5%.

**ech4 barely changes, and that is correct**: its `glycine_1328` is already 82%
of the panel, so silicon was never the constraint there. The flag helps
dramatically where it is needed and does almost nothing where it is not.

**High panels are untouched in all four cases**, exactly as they should be —
`si_522` is a low-window band, so excluding it changes nothing on the high panel:

    ech2 high RAW        now [1729.3, 35997.4] -> excl [1729.3, 35997.4]  IDENTICAL
    ech4 high RAW        now [ 436.4, 246769.4] -> excl [ 436.4, 246769.4]  IDENTICAL
    ech2 high CORRECTED  now [   0.0, 29947.8] -> excl [   0.0, 29947.8]  IDENTICAL
    ech4 high CORRECTED  now [   0.0, 216228.3] -> excl [   0.0, 216228.3]  IDENTICAL

That the recomputation reproduces the current limits **bit for bit** on the four
panels it should not change is the check that the method models the code
correctly. It follows that the flag must act per panel, keyed on the named
band's own `window`.

### D4 — how far the silicon peak runs off the top

| figure | si_522 peak | panel-heights above the new limit |
|---|---|---|
| ech2 low RAW | 157,853.5 | **11.64** |
| ech2 low CORRECTED | 153,224.6 | **12.17** |
| ech4 low RAW | 116,329.9 | 0.11 |
| ech4 low CORRECTED | 104,163.2 | 0.27 |

**On ech2 the silicon band leaves the panel more than eleven panel-heights
below its own peak.** It will not read as a truncated peak; it will read as a
pair of near-vertical lines going off the top edge with no apex, and the eye
gets no cue that the missing peak is 12× the panel. On ech4 it clips only
slightly and looks like an ordinary truncation.

This is worth a decision in itself: a figure whose dominant feature is
off-canvas by that margin needs to say so, or a reader will not know silicon is
there at all. The flag's name appears nowhere on the figure today.

### D5 — filename encoding, band-name characters, and the test enumeration

**Band names are entirely unvalidated.** In `load_bands_config` the name is the
JSON key and the only things checked are the *spec*:

    for name, spec in raw_bands.items():
        where = f"{path} (bands.{name})"
        if not isinstance(spec, dict): ...
        missing = sorted({"centre", "half_width", "window"} - set(spec))
        ...
        bands[name] = BandSpec(name=name, ...)

No character class, no length limit, no pattern. A name may contain a space, a
slash, a backslash, a dot, `..`, or a leading dash. `reference` must be a string
present in `bands`, which is the only constraint on any name and constrains only
that one.

**What would happen to the filename scheme:**

| name | resulting filename fragment | effect |
|---|---|---|
| `si 522` | `..._excl-si 522.png` | a space in a path — legal, awkward to quote, breaks the tidy scheme |
| `a/b` | `..._excl-a/b.png` | **`_save` calls `output_path.parent.mkdir(parents=True, exist_ok=True)`**, so this silently creates a directory and writes inside it |
| `..` | `..._excl-...png` or a traversal, depending on how it is joined | can climb out of `figures/` |
| `si.522` | `..._excl-si.522.png` | harmless, but the stem now has two dots |

Compounding it, **`write_sample_overlays` never calls `guard_not_under_raw`.**
Confirmed by grepping every call site: the guard is used at four places in the
`quantify` path and at `quantify_experiment`'s three figure paths, and **nowhere
in `write_sample_overlays`**, whose `output_directory = figures_root / experiment`
is unguarded. `CLAUDE.md` states "any new write must call it too". This is a
pre-existing gap, not one either change creates, but Change 1 is the first thing
that would put user-controlled text into that path.

**The test enumeration.** As it stands after entry 006:

    # baseline, diagnostic, logy, annotate
    COMBINATIONS = list(itertools.product([False, True], repeat=4))

and the fixture keys on 4-tuples:

    return {
        (baseline, diagnostic, logy, annotate): run(
            spectra,
            root / f"out_{int(baseline)}{int(diagnostic)}{int(logy)}{int(annotate)}",
            baseline, diagnostic, logy, annotate,
        )
        for baseline, diagnostic, logy, annotate in COMBINATIONS
    }

`itertools.product([False, True], repeat=N)` no longer covers the space, because
the new flag is not boolean — it is `None` or a band name. **What changes:**

- `COMBINATIONS` becomes a product over a mixed domain, e.g.
  `itertools.product([False, True], [False, True], [False, True], [False, True], [None, "a"])`
  — the `repeat=` form is gone, and the comment above it grows a fifth name.
- **Rendering goes from 16 combinations to 32** with a single exclusion value.
  Entry 006 measured this module at 9 passed/16.34s with 8 combinations and 15
  passed/30.25s with 16; a further doubling puts it near a minute.
- `run()` gains a fifth parameter, and the `out_` directory name can no longer
  be built from `int(...)` of every flag — a band name is not an int, so that
  path fragment needs its own encoding, which is the same sanitising problem as
  the filename.
- The key tuples grow to 5 elements: **all seven literal tuples** across four
  tests (entry 006 established the count is seven, correcting entry 005's six),
  plus the unpacking and skip condition in
  `test_a_baseline_run_never_writes_the_raw_figure`.
- The two core tests — `test_same_filename_always_means_identical_bytes` and
  `test_differing_content_always_gets_a_different_path` — still need no change;
  they iterate generically.

### D6 — interaction with entry 008's reserved band

**Order: the exclusion must run first, the reserved-band extension second.**

The extension reads the current limits and multiplies the range:

    bottom, top = panel.get_ylim()
    ... panel.set_ylim(bottom, bottom + (top - bottom) / (1.0 - fraction))

If the exclusion ran after it, `set_ylim` would overwrite the extension and the
labels would sit on the data — the exact defect entry 008's F1/F3 work removed.
The natural place for the exclusion is where the negative clamp is (step 3 in
D1's order), which is already before the annotation call at step 5, so the
required order falls out of the existing structure with no reordering.

**Neither invalidates the other's measurement.**

- The exclusion does not disturb the reserved band's arithmetic: `fraction` is
  `reserved / panel_height` where both are **pixel** quantities — measured text
  extents and `panel.get_window_extent(...).height`. Neither depends on the y
  limits. Entry 009 measured the same fractions (13.1% low, 24.9% high) across
  raw, log, corrected and corrected+log figures, which are four different limit
  regimes, confirming the independence empirically.
- The extension does not disturb the exclusion: it only scales the top, and the
  excluded maximum was already excluded when the base limit was computed.

One consequence worth stating: with both active the panel is compressed twice —
once by the exclusion's smaller range and again by the label band. On ech2 low
that is a limit of 13,851.5 with the top 13.1% reserved, so the glycine bands
land at roughly 0.87 × the D3 percentages. `glycine_1328` at 95.5% would then
sit at about 83% and remain inside the data region; nothing collides.

### D7 — can the exclusion alter the six reference figures? **No.**

The gate is the same one entry 007's A6 and entry 008 relied on. The reference
test calls, at all eight of its call sites:

    figure = build_sample_overlay(by_sample[sample])

one positional argument, no keywords. A new parameter defaulting to `None`
therefore takes its default, and the exclusion branch is not entered. In
`write_sample_overlays` the raw filename is additionally produced only under
`if not baseline and not diagnostic:` with both suffixes empty, and
`test_the_raw_filename_is_produced_only_by_the_raw_combination` asserts exactly
one combination reaches it.

The condition is that the parameter genuinely defaults to "no exclusion" and the
limit arithmetic is genuinely gated on it. A version that computed the masked
limit unconditionally and merely chose which to apply would still be safe, but
only by accident; gating the whole branch is what makes the guarantee
structural.

---

## 5. Findings — Change 2

### D8 — every figure output path construction

**In `src/ramsess/report.py`, `write_sample_overlays`** — the base, unguarded:

    output_directory = figures_root / experiment

and its three joins:

    output_directory / f"{name}_overlay{annotated_suffix}{scale_suffix}.png"
    output_directory / f"{name}_overlay_baseline{annotated_suffix}{scale_suffix}.png"
    output_directory / f"{name}_{window}_baseline_check.png"

**In `src/ramsess/report.py`, `quantify_experiment`** — guarded:

    output_directory = guard_not_under_raw(figures_root / experiment, raw_root)
    guard_not_under_raw(output_directory / f"{name}_bands.png", raw_root)
    guard_not_under_raw(output_directory / "bands_all_samples.png", raw_root)

**In `main.py`** — the root, and the two calls that receive it:

    FIGURES_ROOT = PROJECT_ROOT / "figures"
    ...  quantify_experiment(..., FIGURES_ROOT, ...)
    ...  write_sample_overlays(args.experiment, spectra, FIGURES_ROOT, ...)

**In `src/ramsess/plotting.py`, `_save`** — depth-agnostic, and the reason a
deeper tree needs no change here:

    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=DPI, bbox_inches="tight")

**In tests:**

- `tests/test_raw_plot_reference.py` — `FIGURES_DIR = PROJECT_ROOT / "figures" / EXPERIMENT`;
  `reference_png()` returning `FIGURES_DIR / f"{sample}_overlay.png"`; the log
  path `FIGURES_DIR / f"{sample}_overlay_log.png"` twice; and the fixture's
  render target `out / f"{sample}_overlay.png"`.
- `tests/test_annotate_cli.py` — `monkeypatch.setattr(cli, "FIGURES_ROOT", tmp_path / "figures")`
  and `(root / "figures" / EXPERIMENT).glob("*.png")`, plus three assertions on
  bare filenames.
- `tests/test_quantify_experiment.py` — `out_root / "figures"`;
  `out_root / "figures" / EXPERIMENT` twice; two `wrote {figures / ...}` stdout
  assertions; `tmp_path / "out" / "figures" / EXPERIMENT / "sa_bands.png"`;
  and `tmp_path / "out" / "figures" / EXPERIMENT`.
- `tests/test_band_trend_figures.py` — `tmp_path / "figures" / "exp" / f"{sample}_bands.png"`
  and `tmp_path / "figures" / "exp" / "bands_all_samples.png"`.
- `tests/test_output_filenames.py` and `tests/test_annotation_layout.py` assert
  on **bare filenames** from the returned paths, so they are depth-agnostic and
  need no change.
- `tests/conftest.py` — `repository_untouched` watches `PROJECT_ROOT / "figures"`
  wholesale; depth-agnostic.

**That is the complete list**, from grepping `figures`, `\.png`, `figures_root`
and `output_directory` across `src/`, `main.py` and `tests/`.

### D9 — the `.gitignore` rules and what breaks

Verbatim, including the comment that explains the construction:

    # The {sample}_overlay.png reference figures ARE tracked. Every other figure is
    # not.
    #
    # Those overlays are irreplaceable *as a reference*. They can be regenerated,
    # but a regenerated overlay is whatever the code happens to produce at that
    # moment, which makes test_raw_plot_reference.py's comparison self-fulfilling
    # and the test worthless. The stored PNG IS the baseline. Everything else under
    # figures/ is ordinary build output and would commit a fresh binary blob on
    # every plot run.
    #
    # Built up level by level on purpose. Git does not descend into an excluded
    # directory, so a bare `figures/` line followed by a negation would never match
    # anything - the directory has to be re-included before a file inside it can
    # be. The last pattern keys on the _overlay.png suffix alone: it names no
    # sample, and it must not match _overlay_log.png or _overlay_baseline.png.
    figures/*
    !figures/*/
    figures/*/*
    !figures/*/*_overlay.png

**Which patterns stop matching one level deeper.** Tested with `git check-ignore`
against paths that do not exist, so nothing was created:

    NOT ignored : figures/irradiation_sara/ech2_overlay.png          (today, correct)
    IGNORED     : figures/irradiation_sara/ech2/ech2_overlay.png     <- figures/*/*
    IGNORED     : figures/irradiation_sara/ech2/overlay.png          <- figures/*/*
    IGNORED     : figures/irradiation_sara/ech2/ech2_overlay_log.png <- figures/*/*
    IGNORED     : figures/irradiation_sara/ech2/                     <- figures/*/*

**Both of the last two rules break.** `figures/*/*` now matches the *sample
directory* and excludes it, so git will not descend into it at all; and
`!figures/*/*_overlay.png` has one path component too few to match the file. The
reference overlays become ignored — D-A.

**The replacement, following the same level-by-level construction, verified in
the scratch repo:**

    figures/*
    !figures/*/
    figures/*/*
    !figures/*/*/
    figures/*/*/*
    !figures/*/*/*_overlay.png

With those in place, in the probe repo:

    .gitignore:6:!figures/*/*/*_overlay.png   figures/exp/s/s_overlay.png   -> exempt
    s_overlay_log.png ignored -> correct
    re-add succeeded: figures/exp/s/s_overlay.png

So the overlay is exempt, the log figure is still ignored, and a removed overlay
can be added back. Note this only works if `bands_all_samples.png` stays at the
experiment level (D-B), where `figures/*/*` continues to ignore it correctly.

### D10 — hardcoded reference-overlay paths

All in `tests/test_raw_plot_reference.py`; grepping the rest of `tests/` and
`src/` for `_overlay.png` finds no other path construction against the real
tree.

    FIGURES_DIR = PROJECT_ROOT / "figures" / EXPERIMENT

    def reference_png(sample: str) -> Path:
        return FIGURES_DIR / f"{sample}_overlay.png"

    (sample, FIGURES_DIR / f"{sample}_overlay_log.png")
    if (FIGURES_DIR / f"{sample}_overlay_log.png").is_file()

**What each becomes.** `FIGURES_DIR` stays as the experiment directory, and the
two helpers gain the sample component:

    reference_png(sample)  ->  FIGURES_DIR / sample / f"{sample}_overlay.png"
    the log path           ->  FIGURES_DIR / sample / f"{sample}_overlay_log.png"

Three further things in that module are affected but are not paths:

- `if not FIGURES_DIR.is_dir()` skip guards still work, but they now pass when
  the experiment directory exists and the sample directories do not, so the
  skip becomes less informative than it is today.
- `REGENERATE` and `REGENERATE_LOG` are command strings, unaffected.
- The `rendered` fixture writes `out / f"{sample}_overlay.png"` into `tmp_path`,
  which it owns; it need not mirror the new layout, and mirroring it would test
  nothing extra.

### D11 — does `git mv` preserve the bytes, and what does the guard require?

**Yes, and it is verifiable rather than assumed.** In the scratch repo:

    tracked before:  100644 b4e9300a9de59550dbe7431f2c03f89c66bcb2c1 0  figures/exp/s_overlay.png
    $ git mv figures/exp/s_overlay.png figures/exp/s/s_overlay.png
    git mv exit: 0
    tracked after:   100644 b4e9300a9de59550dbe7431f2c03f89c66bcb2c1 0  figures/exp/s/s_overlay.png
    status:          R  figures/exp/s_overlay.png -> figures/exp/s/s_overlay.png

**The blob OID is identical**, and git records a rename. A blob OID is the SHA-1
of the content, so identical OID *is* identical bytes — `git mv` is a path
operation and does not rewrite content. The working-tree file is moved by the
filesystem, not rewritten, so `mpimg.imread` sees the same pixels.

For reference, the six real blobs are:

    c21e76a58fa0c1fad2ec8583fbfe8f7b9ff995c2  ech1_overlay.png
    2a24c48ef69b54472f1307394cc17b8e5602fb28  ech2_overlay.png
    64e542a37a7b2555e5c91d660c868aed9cddb494  ech3_overlay.png
    7380469c0ce5d32914351f60e0f7054d14f68694  ech4_overlay.png
    72d5f430a549b8558009fcd4ff6c6771a05dedcf  ech5_overlay.png
    127fdd7827f143035fce08d29df7ebffc49924fa  ech6_overlay.png

**How to verify rather than assume, after the move:** compare
`git ls-files -s figures/` against that list — the six OIDs must be unchanged
and only the paths different — and run `tests/test_raw_plot_reference.py`,
whose disk half renders a fresh figure and compares pixel arrays. The OID check
proves the bytes survived; the test proves the code still finds them. One
without the other is not enough: the OIDs could match while the test looks in
the wrong place, and the test could pass on a file whose bytes had been
regenerated.

`.gitattributes` pins `*.png binary`, so no line-ending translation applies to
these files in any case.

**What `guard_not_under_raw` requires of the new paths: nothing new.** It raises
only if the resolved target is `raw_root` or has it among its parents:

    resolved = path.resolve()
    root = raw_root.resolve()
    if resolved == root or root in resolved.parents:

`figures/<experiment>/<sample>/` is not under `data/raw/` at any depth, so the
guard is satisfied by construction. Note again that the `plot` path does not
call it at all (D8), so for the six overlays the guard is not in play either
way.

### D12 — what happens to the existing build output

**Nothing moves it and nothing cleans it up.** `figures/irradiation_sara/`
currently holds **34 files, of which 6 are tracked** and 28 are build output:

    TRACKED (6):  ech1_overlay.png ... ech6_overlay.png
    build  (28):  bands_all_samples.png, ech{1..6}_bands.png,
                  ech{1..6}_overlay_baseline.png,
                  ech{2,3,4}_{low,high}_baseline_check.png,
                  ech2/ech4_overlay_log.png,
                  the eight *_annotated*.png from entry 008

A grep for `unlink`, `rmtree`, `shutil` and `rmdir` across `src/` and `main.py`
returns **nothing** — no code path deletes a figure. `_save` only creates
directories and overwrites the single file it is given.

**So after the move the 28 build files would be orphaned at the old level**,
including all eight annotated PNGs, and the next `plot` run would write fresh
copies one level deeper. Both sets would coexist, with the stale ones at
`figures/<experiment>/` and the current ones at `figures/<experiment>/<sample>/`,
and nothing would indicate which is which. They are gitignored, so git will not
mention them.

That is a housekeeping matter rather than a correctness one — `CLAUDE.md` says
"Derived data and every other figure are build output. Delete them freely; they
come back" — but it should be a deliberate step in the change, not a discovery
afterwards. Deleting the 28 is safe; deleting the 6 is not.

### D13 — is the move reversible?

**Yes, and cheaply, provided `.gitignore` moves with it.**

A revert is `git revert` of the commit, or a second `git mv` back. The blob OIDs
are unchanged by either direction (D11), so the six reference figures return
bit-identical and `test_raw_plot_reference` passes again.

**What would be lost:** nothing of the reference figures, and nothing of the
history — git records the rename and `git log --follow` traverses it. Two
smaller things would not survive:

- **The 28 orphaned build files, if they were deleted as part of the change**,
  would not come back with a revert. They regenerate from `plot` and `quantify`,
  so this costs a command, not data.
- **Any figure written after the move and before the revert** would be at the
  new depth and would be left orphaned by the revert, exactly mirroring D12.

The one way to lose something irreversibly is to revert the code without
reverting `.gitignore`, or vice versa. In that state the six overlays are either
ignored at their tracked location, or exempt at a location nothing writes to —
and D-A shows the first of those is recoverable only with `git add -f`. The two
must move together and revert together, which is an argument for them being in
one commit (section 6).

---

## 6. Design recommendation

### Change 1 — the smallest version that works

A new keyword parameter on `build_sample_overlay`, defaulting to `None`,
carrying **the band spec to exclude** rather than its name — the same shape as
entry 006's `bands` parameter, and for the same reason: `plotting.py` must not
look anything up in a config, and a `BandSpec` already carries the `centre`,
`half_width` and `window` the arithmetic needs. `main.py` resolves the name to a
spec, exactly as it already resolves `--annotate` to a band dict, and errors
there if the name is not configured — where the message can name the available
bands.

Inside `build_sample_overlay` the exclusion goes **where the negative clamp is**,
before the legend and before the annotation call, and applies **only to the
panel whose window matches the spec's** (D3 shows the other panel must be left
bit-identical). It computes the masked min and max over the values it has just
drawn, applies `plt.rcParams["axes.ymargin"]`, keeps the existing
`if bottom < 0` clamp, and calls `set_ylim`. Limit arithmetic only — no second
artist, because the tripwire forbids it (D2).

**On the filename, my recommendation is not to interpolate the band name.** D-C
shows names are unvalidated and `_save` will act on a slash. The cheapest safe
scheme is a fixed marker — `{sample}_overlay_scaled{...}.png` — which encodes
*that* an exclusion was applied without encoding *which*. That keeps the flag
boolean-shaped for `test_output_filenames.py`, holding it at 16 combinations
instead of 32, and it satisfies "the same path always means the same bytes" as
long as only one band can be excluded per run. If the experimenter wants the
name in the filename, then validating band names against a conservative
character class becomes part of this change, and that is a change to
`load_bands_config` affecting `quantify` too — a much larger blast radius.

**It must not touch:** `build_sample_overlay`'s default behaviour, the six
reference overlays, the three `REFERENCE_*` dicts, either tripwire, the
diagnostic figure, or the reserved-band arithmetic in `_annotate_band_centres`.

**Also worth doing, and cheap:** put the exclusion on the figure title, the way
baseline correction already announces itself. A reader of ech2's low panel
otherwise has no way to know that a band 12 panel-heights tall has been scaled
out (D4).

### Change 2 — the smallest version that works

Four coordinated edits, and they are not separable:

1. `write_sample_overlays` — `output_directory = figures_root / experiment / name`,
   inside the per-sample loop rather than above it. The diagnostic figure moves
   with its sample.
2. `quantify_experiment` — the per-sample `{name}_bands.png` moves into the
   sample directory; **`bands_all_samples.png` stays at the experiment level**
   (D-B), which needs a decision and a comment saying why.
3. `.gitignore` — the six-line replacement in D9, verified.
4. `tests/test_raw_plot_reference.py` — `reference_png` and the log path gain
   the sample component (D10); `tests/test_quantify_experiment.py` and
   `tests/test_band_trend_figures.py` gain it in their assertions.

`_save` needs no change: it already creates parents to any depth (D8).

**It must not touch:** the six blob OIDs, which are the verification (D11); the
bytes of any tracked file; `guard_not_under_raw`, which is satisfied already.
And the 28 orphaned build files should be dealt with deliberately — deleting
them is safe and they regenerate — rather than left to be discovered.

### One commit or two? **Two, with Change 2 second.**

They are unrelated: one is figure scaling, the other is filesystem layout.
Nothing in Change 1 depends on the tree shape, and nothing in Change 2 depends
on the scale flag. Splitting them keeps each reviewable and each revertible on
its own, which matters more than usual here because **Change 2 is the risky
one** — it moves the only irreplaceable build artefacts in the repository, and
D-A shows the failure mode is silent.

Doing Change 2 second also means it is the tip commit for as long as it takes to
be sure, so `git revert` of a single commit undoes it cleanly.

**Within Change 2, the `.gitignore` edit and the `git mv` must be in the same
commit** (D13). A commit where the files have moved but the ignore rules have
not leaves the reference overlays tracked-but-ignored, which is exactly the
state where the next person to untrack them cannot get them back.

---

## 7. Self-corrections during this phase

**One, and it changed reported numbers.** My first D3 measurement recomputed the
lower limit as `gmin - 0.05 * span` and clamped to zero only when the data
minimum was non-negative. The code's actual rule clamps whenever the *computed
limit* is negative, regardless of the data:

    bottom, top = panel.get_ylim()
    if bottom < 0:
        panel.set_ylim(bottom=0, top=top)

Under the wrong rule the corrected panels came out with negative floors —
ech2 low corrected showed `-1062.4` instead of `0.0`, and the high panels showed
`-2130.7` and `-15067.6` instead of `0.0` — which made every "% excluded" figure
in the corrected rows wrong, and made the high panels look as though the
exclusion changed them when it does not.

Re-run with the code's rule, all four high panels come out **IDENTICAL** to their
current limits, which is the check that the method is sound. D3 reports the
corrected numbers; the first set is recorded here so the correction is visible.

Nothing else measured during this phase was later found wrong.

---

## 8. Everything measured, with the numbers

| what | result |
|---|---|
| HEAD | `583414a`; entry 009 uncommitted, so `bands.json` still holds 8 bands |
| `git status --short figures/` | empty, before and after |
| `axes.ymargin` | 0.05 |
| y-limit sites in `build_sample_overlay` | 2 blocks; the top limit is never computed explicitly |
| ech2 low RAW limit, now → excluded | 165,644.1 → 13,851.5 (**÷11.96**) |
| ech2 low CORRECTED limit | 160,910.1 → 11,635.6 (**÷13.83**) |
| ech4 low RAW limit | 121,789.2 → 104,882.5 (÷1.16) |
| ech4 low CORRECTED limit | 109,421.3 → 81,718.9 (÷1.34) |
| ech2 low glycine bands, % of panel | RAW 4.4–8.0% → **46.3–95.5%**; CORRECTED 2.9–6.9% → **39.7–95.5%** |
| ech4 low glycine bands, % of panel | RAW 16.7–82.0% → 18.8–95.5% |
| all four high panels | **IDENTICAL** limits with and without the exclusion |
| si_522 above the new top, ech2 | **11.64** panel-heights raw, **12.17** corrected |
| si_522 above the new top, ech4 | 0.11 raw, 0.27 corrected |
| band-name validation | **none** — any JSON key is accepted |
| `guard_not_under_raw` in `write_sample_overlays` | **absent**; used only in the `quantify` path |
| `COMBINATIONS` today | `itertools.product([False, True], repeat=4)` → 16 |
| with a non-boolean fifth flag | 32, plus 7 literal tuples → 5-tuples |
| exclusion vs reserved band | exclusion first; fractions are pixel-based and unaffected |
| figure path construction sites | 3 in `write_sample_overlays`, 3 in `quantify_experiment`, 3 in `main.py`, 1 in `_save`, 11 across 4 test modules |
| `figures/irradiation_sara/ech2/ech2_overlay.png` today | **IGNORED** by `figures/*/*` |
| replacement patterns | 6 lines, verified: overlay exempt, log ignored, re-add succeeds |
| `git mv` blob OID | **unchanged** — `b4e9300a…` before and after in the probe |
| untracked-then-re-add under the broken rules | **fails**, `git add` exit 1 |
| files under `figures/irradiation_sara/` | 34 total, 6 tracked, 28 build output |
| code that deletes figures | **none** |
| six reference blob OIDs | recorded in D11 for post-move verification |

---

## 9. Matters next

- **D-A, D-B and D-C gate the two changes.** None of the three is a detail.
- **The `guard_not_under_raw` gap on the `plot` path** is pre-existing and
  independent of both changes, but Change 1 would be the first thing to put
  user-controlled text into an unguarded figure path. Worth closing on its own
  terms rather than as a side effect.
- **Nothing on the figure says silicon has been scaled out.** At 12
  panel-heights off the top (D4) that is a caption or title matter, not a
  plotting one, but it should not be left to the narrator the change exists to
  make unnecessary.
- **Change 1's benefit is entirely ech2's.** ech4 moves by a factor of 1.16.
  If the supervisor's complaint is specifically about ech2, the flag is well
  aimed; if it is about the set of figures, four of the six samples are
  unmeasured here.
- **Entry 009 is still uncommitted.** If its thirteen-band config lands first,
  every percentage in D3 shifts, because the low panel would carry five more
  labels and the reserved band would grow from 13.1% to 40.5%.

---

## 10. Files touched by this phase

`prompt_outputs/010-scale-exclusion-and-layout-phaseA.md` (this file) and one
appended line in `prompt_outputs/INDEX.md`. Nothing else. `data/`, `figures/`,
`src/`, `tests/` and `main.py` are unchanged; no file was moved; the scratch git
repository used for D11 is outside the project.

PHASE A ends here. Awaiting decisions on D-A, D-B and D-C, and an explicit
"PROCEED".
