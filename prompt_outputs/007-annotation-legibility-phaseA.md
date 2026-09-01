# 007 — annotation-legibility — PHASE A

Supersedes nothing. Measures the cost of three defects the experimenter found in
the eight figures built by `prompt_outputs/006-annotated-overlays-phaseB.md`.

Date: 2026-09-01
HEAD at time of writing: `42557f4`
Entry 006 is built and green but **not committed**; its changes are in the
working tree. Everything measured below is against that working tree, not
against HEAD.

**Scope of this phase.** Read-only. Nothing created, edited, moved or deleted
except this file and its `INDEX.md` line. `plot` was not run. Figures were built
in memory and closed; nothing was saved. `ANNOTATION_FONT_SIZE` was rebound on
the imported module object inside a throwaway process to measure the font
trade-off — **no file was modified**, and the original value was restored before
each script exited. `git status --short figures/` is empty at the end of this
phase, as it was at the start.

**How the numbers were produced.** Two throwaway read-only scripts in the
session scratchpad plus three inline `-c` runs, all under
`.venv\Scripts\python.exe`. They call the real `_annotate_band_centres` on real
figures and read geometry through the Agg renderer. The reserved fraction is
**recovered from the limits the function actually set** —
`fraction = 1 - old_range / new_range` — rather than recomputed from the
formula, so no arithmetic is duplicated and a mistake in the helper would show
up rather than be reproduced.

---

## 1. Blockers and decisions needed

**One decision, and it is a genuine trade-off that measurement uncovered rather
than confirmed.**

**D1 — F3's intended fix works, but it moves the legend onto the traces in four
more panels than it rescues.** `bbox_to_anchor` does constrain `loc="best"`
(A5), and applying it removes the one label collision: **1 of 16 panels → 0 of
16**. But confining the legend below the reserved band takes away the empty
region it had been escaping into, and on log-scaled panels the traces fill the
remaining space. Measured across all sixteen panels, counting traces whose
points fall inside the legend's box:

    before anchoring: 1 panel affected,  7 trace-touches
    after  anchoring: 5 panels affected, 30 trace-touches

The four newly affected panels are all `--logy`: `ech2 logy high`,
`ech2 baseline+logy low`, `ech4 logy low`, `ech4 logy high`. Full table in A5.
So the fix as specified trades one label overlap for four legend-over-data
overlaps. **Decide:** accept that trade (labels are the point of the figure and
a legend over traces is the ordinary state of most plots); or apply the anchor
only on linear panels; or drop `loc="best"` for a fixed corner on annotated
panels; or leave F3 unfixed. I am not choosing this — it is a judgement about
which overlap the conference audience should see.

Nothing else blocks. F1 and F2 are both straightforward and their costs are
small and measured.

---

## 2. What I could NOT check, and why

- **How any of this looks.** No figure was saved and none was opened. Every
  claim about overlap and clearance is geometry read from the renderer — bounding
  boxes, pixel counts, transforms — not an inspection of an image. That is
  sufficient to say whether two boxes intersect; it is not sufficient to say
  whether a label at 11pt reads from the back of a lecture theatre, which is
  F2's actual question and is not measurable from here.
- **Whether F2's target size is right.** I measured what each candidate size
  costs (A2, A3). Which size is legible on the experimenter's projector is his
  call, and the numbers are here to choose from.
- **The exact behaviour of a reordered `panel.legend(...)` call**, because
  testing it would require editing `build_sample_overlay`, which this phase may
  not do. I established instead that **no reordering is needed** (A5), which
  makes the question moot for the recommended route. If the experimenter prefers
  the reordering route, that claim is unverified and would need PHASE B to prove
  it against `test_raw_plot_reference.py`.
- **Whether the anchored legend would collide with the *rules* rather than the
  labels.** I checked label boxes and trace points. The vertical rules currently
  span the full panel (F1), so a legend anywhere sits on top of eight of them in
  the low window; once F1 shortens them that stops being true above the data but
  remains true below. Not measured, because F1's fix changes it.

---

## 3. PROPOSED DEVIATIONS

**None.** This phase measured what was asked and implemented nothing.

Two disclosures about method, neither a departure from the request:

- **`ANNOTATION_FONT_SIZE` was rebound in memory** to measure A2 and A3, since
  the row count and reserved fraction cannot be obtained any other way without
  editing the file. The module attribute was restored before each script ended
  and no file was touched.
- **A2 and A3 were also measured at 13, 14, 15 and 16**, beyond the four sizes
  requested, because the four requested sizes all gave the same row count and
  the interesting boundary lies outside them. Reporting only 8/10/11/12 would
  have made the low window look unconditionally safe when it is not.

---

## 4. Findings

### A1 — the `axvline` call, and whether the per-label bottom is known there

Quoted verbatim from `_annotate_band_centres`:

    for spec in selected:
        panel.axvline(
            spec.centre,
            color=ANNOTATION_COLOR,
            linewidth=ANNOTATION_RULE_WIDTH,
            alpha=ANNOTATION_RULE_ALPHA,
            zorder=ANNOTATION_ZORDER,
        )

**The vertical extent is not expressed at all.** Neither `ymin` nor `ymax` is
passed, so both take `Axes.axvline`'s documented defaults of 0 and 1 — axes
fractions, spanning the full panel height. That is F1: the rule runs from the
bottom of the panel to the top, straight through its own label, which is centred
on the same x.

Two things follow, and they matter for how small the fix is.

**The extent is expressed in the right units already.** `ymin`/`ymax` are axes
fractions, and the label rows are positioned in axes fractions too. So the fix
needs no unit conversion and no dependence on the data limits — which is what
lets it survive the `set_ylim` that happens further down, and lets it work
identically on a log axis.

**The per-label bottom edge is NOT yet computed at this point, but every input
to it is.** The order inside the function today is:

1. measure each label, filling `widths` and `heights`;
2. assign `rows`;
3. compute `line_height`, `gap`, `row_heights`, `reserved`, `fraction`;
4. **draw the rules** ← here;
5. raise the top limit;
6. walk `cursor` down the rows and place the labels, computing each row's
   `y = 1.0 - cursor / panel_height`.

The bottom edge of the label at `index` in row `r` is
`y(r) - heights[index] / panel_height`. `heights` exists from step 1 and the row
membership from step 2, but `y(r)` is only produced by the `cursor` walk in step
6, after the rules are drawn.

**What would have to move: the rule drawing, into the placement loop.** The
`for spec in selected:` loop at step 4 would become a per-label `axvline` inside
the step 6 loop, where `y` is in scope, passing
`ymax = y - heights[index] / panel_height` less a small clearance. That is the
smallest change: it moves one loop rather than restructuring the function, and
it is the only place where row membership, label height and row position are all
in scope at once.

Moving the rules below `set_ylim` is safe: `ymin`/`ymax` are axes fractions and
do not depend on the y limits, so a rule drawn before or after the limit change
occupies the same place on the panel.

One consequence worth knowing: rules and labels currently share
`ANNOTATION_ZORDER`, and equal-zorder artists draw in insertion order. Moving
the rules after the labels could swap which is on top. Once the rule stops below
its label they no longer overlap, so this stops mattering — but it stops
mattering *because* of the fix, not independently of it.

Scope: `_annotate_band_centres` in `plotting.py`, read in full.

### A2 — rows per panel at font sizes 8, 10, 11 and 12

Measured with the real renderer, on the real figures, in memory.

| panel | fs 8 | fs 10 | fs 11 | fs 12 |
|---|---|---|---|---|
| ech2 low | 1 row | 1 row | 1 row | 1 row |
| ech2 high | 2 rows | 2 rows | 2 rows | 2 rows |
| ech4 low | 1 row | 1 row | 1 row | 1 row |
| ech4 high | 2 rows | 2 rows | 2 rows | 2 rows |

**No requested size changes the row count anywhere.** The membership is
identical too, at every size:

    low  row 0: si_522, glycine_893, glycine_979, glycine_1328, glycine_1412
    high row 0: glycine_2975, glycine_3146
    high row 1: glycine_3012

ech2 and ech4 agree exactly, and a spot check on `--baseline --logy` at size 12
gives the same rows and the same fractions — confirming again that placement
depends only on centres, panel geometry and font, never on the data.

**Why the row count is stable, and where it stops being stable.** The clearance
test compares a fixed pixel gap between centres against a requirement that grows
with the font, so a large enough font must eventually collide. Measured margins
on the two tightest low-window pairs, in display pixels:

| font size | label width (line height) | `glycine_893`→`glycine_979` gap 23.6 px | `glycine_1328`→`glycine_1412` gap 23.1 px |
|---|---|---|---|
| 8 | 11.4 px | need 13.8, margin **+9.8** | need 13.8, margin **+9.3** |
| 10 | 14.3 px | need 16.5, margin **+7.1** | need 16.5, margin **+6.6** |
| 11 | 15.6 px | need 17.9, margin **+5.7** | need 17.9, margin **+5.1** |
| 12 | 17.0 px | need 19.6, margin **+4.1** | need 19.6, margin **+3.5** |
| 14 | 19.4 px | need 22.4, margin **+1.3** | need 22.4, margin **+0.7** |
| 16 | 22.3 px | need 25.7, margin **−2.1** COLLIDES | need 25.7, margin **−2.6** COLLIDES |

**The low window's tipping point is between 14 and 15**, confirmed directly:

    fs 12: low = 1 row
    fs 13: low = 1 row
    fs 14: low = 1 row
    fs 15: low = 2 rows
    fs 16: low = 2 rows

So **the experimenter's headline concern — that a bigger font pushes the low
window from one row to two — does not materialise at any of 8, 10, 11 or 12.**
Size 12 keeps 3.5 px of margin on the tightest pair; size 14 keeps 0.7 px, which
is close enough to the boundary that a font-metric change or a different
matplotlib could flip it.

The high window's `glycine_2975`→`glycine_3012` pair is 10.2 px apart and needs
13.8 px even at size 8, so it is already in row 1 and stays there at every size.
It never gets better.

Scope: both windows of ech2 and ech4, all eight sizes, via the real
`_annotate_band_centres` and direct renderer measurement of the pair margins.

### A3 — reserved band as a fraction of panel height

Recovered from the limits the function set, not recomputed.

| panel | fs 8 | fs 10 | fs 11 | fs 12 |
|---|---|---|---|---|
| ech2 low | 19.5% | 24.6% | 26.7% | **29.7%** |
| ech2 high | 37.9% | 47.9% | 52.0% | **58.1%** |
| ech4 low | 19.5% | 24.6% | 26.7% | **29.7%** |
| ech4 high | 37.9% | 47.9% | 52.0% | **58.1%** |

All four panels are 423.5 px tall in the build, and the fraction is
dpi-invariant, so these hold at save time too.

**This, not the row count, is what a larger font costs.** The high window is
already giving up 37.9% of its height to labels at size 8. At size 11 it passes
half — **52.0%**, more label band than data. At size 12 it is 58.1%, meaning the
seven traces are compressed into the bottom 41.9% of the panel.

The low window is far more comfortable: 19.5% at size 8 rising to 29.7% at size
12, because it needs only one row.

The asymmetry is entirely the second row in the high window. A one-row panel
reserves roughly `pad + row_height + gap`; a two-row panel reserves that plus
another `row_height + gap`, and `row_height` is the longest band name's rendered
length, which is the dominant term.

PD2's guard from entry 006 — the raise when the reserved band would fill the
panel — did not fire at any size tested, including 16.

Scope: as A2.

### A4 — is `ANNOTATION_COLOR` used for both rule and text? CONFIRMED

Both uses quoted. In the `label` closure:

    def label(centre: float, y: float, name: str):
        return panel.text(
            centre,
            y,
            name,
            transform=blended,
            rotation=90,
            fontsize=ANNOTATION_FONT_SIZE,
            color=ANNOTATION_COLOR,
            horizontalalignment="center",
            verticalalignment="top",
            zorder=ANNOTATION_ZORDER,
        )

and in the rule:

        panel.axvline(
            spec.centre,
            color=ANNOTATION_COLOR,
            linewidth=ANNOTATION_RULE_WIDTH,
            alpha=ANNOTATION_RULE_ALPHA,
            zorder=ANNOTATION_ZORDER,
        )

One constant, `ANNOTATION_COLOR = "0.35"`, feeding both. Those are the only two
uses in the module.

**What would have to change for the text to be darker than the rule:** the
single constant splits into two — one for the label text, one for the rule —
each with its own one-line comment, matching how `ANNOTATION_RULE_WIDTH` and
`ANNOTATION_RULE_ALPHA` are already rule-specific. Both call sites then name
their own constant. That is a two-line change plus a comment, and it touches
nothing outside `_annotate_band_centres` and the constant block.

Worth noting for F2: the rule already has `ANNOTATION_RULE_ALPHA = 0.45` applied
on top of the colour, so the rule renders lighter than the text does even today
— alpha is not applied to the label. The perceived faintness of the *text* comes
from `"0.35"` alone. Making the text darker therefore does not require touching
the rule's appearance at all, if the current rule weight is acceptable; splitting
the constant is what allows one to move without the other.

Scope: `plotting.py`, grepped for every occurrence of `ANNOTATION_COLOR`. Two,
both quoted.

### A5 — the legend call, and whether `bbox_to_anchor` can be applied conditionally

The call in `build_sample_overlay`, verbatim, with the comment above it:

        # One legend per panel, listing only the steps drawn in that panel: a
        # sample can be missing a step in one window but not the other.
        handles = [
            Line2D([], [], color=colour, linestyle=linestyle, linewidth=LINE_WIDTH)
            for colour, linestyle in (
                _style_for_step(step, min_step, max_step) for step in sorted(set(panel_steps))
            )
        ]
        panel.legend(
            handles,
            [_step_label(step) for step in sorted(set(panel_steps))],
            loc="best",
            frameon=True,
            title="step",
        )

        # Last, so the labels are measured against the panel's final limits and
        # the reserved band is added on top of the clamp above, not before it.
        if bands is not None:
            _annotate_band_centres(figure, panel, window, bands, logy)

**Is the reserved fraction available where the legend is created? NO.** The
legend is created unconditionally, before the `if bands is not None:` gate, and
`fraction` is a local of `_annotate_band_centres` computed part-way through it.
At the moment `panel.legend(...)` runs, nothing has measured a label.

**But no reordering is needed, because the legend can be adjusted after the
fact.** `Legend.set_bbox_to_anchor(bbox, transform=...)` mutates the existing
legend object, and `_annotate_band_centres` already holds both the panel and the
fraction. So the whole of F3 fits inside the annotation helper, on a code path
the unannotated figure never enters.

**Does `loc="best"` honour `bbox_to_anchor`? CONFIRMED — tested directly**, on
the one panel that actually fails (`ech4`, `--baseline --logy`, low), matplotlib
3.11.1:

    as built           : legend y0 frac = 0.572
    after bbox_to_anchor: legend y0 frac = 0.016  y1 frac = 0.428
    labels overlapping legend now: none
    legend loc setting still: 0

`_loc` remains 0, which is `best` — so the placement is still searched, just
searched inside the anchor box. The legend moved from the middle of the reserved
band to the floor of the panel and the collision is gone. This was the crux of
F3 and it holds.

**Across all sixteen panels**, applying `(0, 0, 1, 1 - fraction)` in axes
coordinates: label overlaps go **1/16 → 0/16**.

**And here is D1.** Counting traces with at least one point inside the legend's
box, before and after:

| panel | before | after |
|---|---|---|
| ech2 plain low | 0/7 | 0/7 |
| ech2 plain high | 0/7 | 0/7 |
| ech2 logy low | 0/7 | 0/7 |
| **ech2 logy high** | 0/7 | **7/7** |
| ech2 baseline low | 0/7 | 0/7 |
| ech2 baseline high | 0/7 | 0/7 |
| **ech2 baseline+logy low** | 0/7 | **7/7** |
| ech2 baseline+logy high | 0/7 | 0/7 |
| ech4 plain low | 0/7 | 0/7 |
| ech4 plain high | 0/7 | 0/7 |
| **ech4 logy low** | 0/7 | **2/7** |
| **ech4 logy high** | 0/7 | **7/7** |
| ech4 baseline low | 0/7 | 0/7 |
| ech4 baseline high | 0/7 | 0/7 |
| ech4 baseline+logy low | 7/7 | 7/7 |
| ech4 baseline+logy high | 0/7 | 0/7 |
| **total trace-touches** | **7** | **30** |

Every newly affected panel is log-scaled. The reason is structural: a log axis
spreads the traces over the whole panel, so once the top band is forbidden there
is no empty region left and `best` must pick the least-bad spot on the data. The
linear panels are unaffected — all six of them stay at 0/7.

**If the experimenter prefers the reordering route instead** — moving
`panel.legend(...)` below the annotation call and passing `bbox_to_anchor` at
creation — then on the unannotated path the sequence would go from
"clamp → legend" to "clamp → (gate not taken) → legend", with no artist added in
between, which should be byte-identical. **That is reasoning, not a measurement**
(see section 2), and `test_raw_plot_reference.py` is the thing that would prove
it. The `set_bbox_to_anchor` route needs no such proof because it never touches
the unannotated path at all.

Scope: `build_sample_overlay` and `_annotate_band_centres` in `plotting.py`;
matplotlib 3.11.1; all sixteen panels measured.

### A6 — does the reference test still pass, and what could disturb it?

**It passes, right now, on the current working tree:**

    51 passed in 7.57s

and `git status --short figures/` is empty, so the six committed reference PNGs
are unmodified.

**Which of F1, F2, F3 could alter the bytes it compares:**

| defect | could it alter the reference bytes? | why |
|---|---|---|
| **F1** — shorten the rules | **No** | The change is confined to the `axvline` call inside `_annotate_band_centres`, which runs only when `bands is not None`. The reference test calls `build_sample_overlay(by_sample[sample])` with one positional argument, so `bands` is `None` and the helper is never entered. |
| **F2** — bigger, darker labels | **No** | `ANNOTATION_FONT_SIZE` and `ANNOTATION_COLOR` (or its successors) are read only inside `_annotate_band_centres`. Same gate, same reasoning. Splitting the colour constant adds a module-level name, which no unannotated code path reads. |
| **F3** — constrain the legend | **Depends entirely on the route.** Via `set_bbox_to_anchor` inside `_annotate_band_centres`: **No**, same gate. Via reordering or parameterising `panel.legend(...)` in `build_sample_overlay`: **Yes, possibly** — that is code the unannotated path executes, and the reference test is precisely the guard that would catch it. |

This is the strongest argument for the `set_bbox_to_anchor` route over the
reordering route, independent of which is tidier: one of them cannot touch the
six reference figures by construction, and the other can only be shown not to
have touched them by running the test.

Note also that `REFERENCE_YLIM` in that module pins the unannotated y limits.
Annotation raises the top limit, but only on the annotated path, so those pins
are unaffected by all three fixes on the recommended route.

Scope: `tests/test_raw_plot_reference.py` run in full; the gate in
`build_sample_overlay` read directly.

---

## 5. Recommendation — the minimum change for each defect

Recommendations only. Nothing was implemented and no code was written.

**F1 — the rule through its own label. Smallest change: move the rule-drawing
loop into the label-placement loop and pass `ymax`.** All the inputs already
exist (A1); what is missing is only that the row's `y` has not been computed
when the rules are drawn. Drawing each rule where its label is placed puts row
membership, label height and row position in scope together, and
`ymax = y - heights[index] / panel_height` less a small clearance stops the rule
just under its own label. The clearance should be a dimensionless multiple of
the measured line height, as `ANNOTATION_ROW_GAP` and `ANNOTATION_TOP_PAD`
already are — not a pixel count and not a number of cm-1. No unit conversion is
needed since `ymin`/`ymax` are already axes fractions, and it works unchanged on
a log axis. Touches one function; cannot reach the unannotated path.

**F2 — too small, too faint. Smallest change: raise `ANNOTATION_FONT_SIZE`, and
split `ANNOTATION_COLOR` into a text colour and a rule colour.** On size, the
measurements say **11 or 12 are both safe**: neither adds a row in any panel,
and 12 still leaves 3.5 px of margin on the tightest low-window pair. **I would
not go past 12** — 14 leaves 0.7 px and 15 flips the low window to two rows.
The real cost is the reserved band, not the rows: the high window goes from
37.9% of panel height at size 8 to 52.0% at 11 and 58.1% at 12 (A3). If the
high window's traces being squeezed into 42% of the panel is unacceptable, size
10 (47.9%) or 11 (52.0%) is the compromise, and there is no setting that both
enlarges the text and leaves the high window's band alone, because the band is
the text. On colour, splitting the constant is a two-line change (A4); the rule
already carries `ANNOTATION_RULE_ALPHA` on top of the colour, so the text can be
darkened without the rule following it. Touches the constant block and two call
sites; cannot reach the unannotated path.

**F3 — the legend in the reserved band. Smallest change:
`panel.get_legend().set_bbox_to_anchor((0, 0, 1, 1 - fraction), transform=panel.transAxes)`
inside `_annotate_band_centres`, after `fraction` is computed** — guarded for
`get_legend()` returning `None`, since nothing in the helper's contract
guarantees the caller made a legend. This needs **no reordering** of
`panel.legend(...)` (A5), keeps `loc="best"` as specified, and — decisively —
cannot alter the six reference figures by construction, whereas the reordering
route can only be shown safe by running the test (A6). **But it should not be
implemented until D1 is answered**, because it takes label overlaps from 1/16 to
0/16 while taking legend-over-trace panels from 1 to 5, all four new ones
log-scaled. If the answer is "linear panels only", the same one-line fix applies
under `if not logy:`, which keeps every measured improvement (all six affected
linear panels are already at 0/7 before and after, and the one real collision,
`ech4 baseline+logy low`, is log-scaled — so a linear-only fix would **not**
fix the actual defect). That asymmetry is worth stating plainly: **the single
panel that currently collides is a log panel, so any fix that spares the log
panels does not fix F3 at all.**

**Sequencing.** F1 and F2 are independent of each other and of F3, carry no open
questions, and cannot touch the reference figures. F3 is the only one gated on a
decision. They could be done in one pass or F3 deferred; nothing in F1 or F2
depends on how F3 is resolved.

**What any of them must not touch:** `build_sample_overlay`'s unannotated path,
the six `{sample}_overlay.png` files, `REFERENCE_YLIM`/`REFERENCE_XLIM`/
`REFERENCE_STRUCTURE` in `tests/test_raw_plot_reference.py`, either tripwire,
and the diagnostic figure, which takes no annotation.

---

## 6. Matters next

- **D1 is the only gate.** F1 and F2 could proceed without it.
- **The high window's reserved band is the real constraint on F2**, and it is
  driven by the second row, which is driven by `glycine_2975` and `glycine_3012`
  sitting 10.2 px apart on the drawn figure. Nothing about font size fixes that
  pair; only a different label scheme would — shorter names, or a numbered key.
  Not proposed, but it is where the next increment of legibility would come from.
- **Size 14 is 0.7 px from flipping the low window to two rows.** If anyone
  raises the font later, that margin is the thing to re-measure, not the row
  count as it stands.
- **Entry 006's PD2 guard has still never fired**, including at size 16.
- **The tests added in entry 006 do not cover any of F1, F2 or F3.** They assert
  filenames, byte-difference and the CLI gate — none of which changes under any
  of these fixes. Whatever PHASE B does here will pass the existing suite
  unchanged, which means the suite is not evidence that these three defects were
  fixed. New assertions would have to be written for that, and entry 006's STEP
  4e is the precedent for proving they fail first.

---

## 7. Self-corrections during this phase

None. No claim made during this phase was later found wrong.

Entry 006's reported measurements were re-derived here and all held: the row
memberships, the 1-of-16 legend collision, and the reference test passing.

---

## 8. Everything measured, with the numbers

| what | result |
|---|---|
| HEAD | `42557f4`; entry 006 in the working tree, uncommitted |
| `tests/test_raw_plot_reference.py` now | 51 passed in 7.57s |
| `git status --short figures/` | empty, before and after this phase |
| matplotlib | 3.11.1 |
| `axvline` vertical extent as written | neither `ymin` nor `ymax` passed → defaults 0 and 1, full panel |
| per-label bottom known at the `axvline` loop | no; inputs yes, `y` not computed until the placement loop |
| panel height | 423.5 px, all four panels |
| rows, low window, fs 8/10/11/12 | 1 / 1 / 1 / 1 |
| rows, high window, fs 8/10/11/12 | 2 / 2 / 2 / 2 |
| rows, low window, fs 13/14/15/16 | 1 / 1 / **2** / 2 |
| low-window tipping point | between 14 and 15 |
| tightest low pair margin, fs 8/10/11/12 | +9.3 / +6.6 / +5.1 / +3.5 px |
| tightest low pair margin, fs 14/16 | +0.7 / −2.6 px |
| high-window pair `2975`→`3012` | 10.2 px apart, needs 13.8 px even at fs 8 — never clears |
| reserved band, low, fs 8/10/11/12 | 19.5% / 24.6% / 26.7% / 29.7% |
| reserved band, high, fs 8/10/11/12 | 37.9% / 47.9% / 52.0% / 58.1% |
| PD2 raise fired | never, up to fs 16 |
| `ANNOTATION_COLOR` uses | 2 — label text and rule, both quoted |
| `loc="best"` honours `bbox_to_anchor` | yes; `_loc` stays 0, legend moved y0 0.572 → 0.016 |
| legend/label overlaps, before → after anchor | 1/16 → 0/16 |
| panels with legend over traces, before → after | 1 → 5 |
| trace-touches by a legend, before → after | 7 → 30 |
| newly affected panels | all four log-scaled |
| linear panels affected by the anchor | 0 of 6 |
| row layout depends on data | no — same rows and fractions on `--baseline --logy` at fs 12 |
| F1/F2 can alter the reference bytes | no, both gated behind `bands is not None` |
| F3 can alter the reference bytes | no via `set_bbox_to_anchor`; possibly via reordering `panel.legend` |

---

## 9. Files touched by this phase

`prompt_outputs/007-annotation-legibility-phaseA.md` (this file) and one
appended line in `prompt_outputs/INDEX.md`. Nothing else. `data/`, `figures/`,
`src/`, `tests/` and `main.py` are exactly as entry 006 left them.

PHASE A ends here. Awaiting an answer to D1 and an explicit "PROCEED".
