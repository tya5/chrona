# Acceptance Review — #410 I410-2 Tabular Metrics v3

**Design:** `e6e40ede`; **substitute correction:** `ebc5e0a3`;
**architecture reviews:** `0fd9c656`, `2d884eec`; **implementation plan:**
`1cb6f43a`.

## Accepted scope

I410-2 replaces the live Render Context boundary with v0.16 and the declared
font-metrics boundary with v3.  A selectable primary face carries complete
proportional and tabular ASCII-digit maps, and `FontMetrics.width` accepts only
the already-selected finite mode.  The bundled Noto Sans faces and the optional
Noto Sans JP provider are regenerated as v3 resources.  The draft-only emoji
substitute remains a character fallback and deliberately has no numeric map.

`signedDays` normalizes to the semantic `numeric` typography role.  Table
allocation has one role-aware Layout measurement callback; natural widths,
ellipsis, and alignment do not have a table-specific feature inference.  The
HALCYON and Orion Themes which materialize signed-day Views define that role
with tabular figures.  Headers and all other cell formats remain `text`.

Scene transports an explicit numeric spacing value for every text run.  SVG,
Typst, and TikZ serialize that completed value; none reads font tables or
chooses a fallback feature.  The authority chain remains Theme → Layout → Scene
→ adapter.

## Evidence and verification

* All 21 public Contexts moved to v0.16/v3 and all 21 committed Scene/SVG
  pairs were regenerated together.
* The HALCYON programme-board Scene has 26 tabular table text runs and 107
  explicit proportional runs; its SVG projects matching `tabular-nums` and
  `proportional-nums` attributes.  Existing Noto Sans default-tabular geometry
  remains unchanged where expected, while the feature selection is now
  explicit and measurable.
* Focused v3 metric/importer/resolver, Layout allocation, Scene, and adapter
  tests passed (74 focused assertions in the final run).  They cover pnum vs
  tnum width selection, incomplete/nonuniform map rejection, substitute
  capability separation, signed-cell measurement, and all target projections.
* `python conformance/run_conformance.py` passed.  The diagnostic and declared
  value inventories were regenerated and their checks passed.
* Structural delivery, reachability, semantic registry, import-direction,
  encoding, presentation-coverage, and semantic-realization checks passed.
* The test suite was run with `pytest -q -n 4` after regeneration; the
  independently recovered partitions include 450 passed in `tests/unit/chrona`
  and 201 passed / 18 skipped in `tests/cli tests/acceptance`.  The integration
  corpus and tool partitions completed without failures.
* A fresh primary wheel passed the size gate and installed-wheel smoke outside
  the checkout.

## Architecture result

The v0.15/v2 pair has no production reader.  Optional substitute fonts cannot
silently become numeric authorities, and render adapters cannot drift from the
geometry which Layout measured.  I410-2 is accepted as the completed numeric
metrics prerequisite for I412-1 and I411-1.
