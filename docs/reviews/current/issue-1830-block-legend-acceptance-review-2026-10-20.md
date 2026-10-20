# Issue1830 — block legend row measurement

[Pre-code plan, design and architecture review](https://github.com/tya5/chrona/issues/1830#issuecomment-6292764430).
Implementation `78d26e249`; no schema, preset dimensions or corpus-data changes.

| Literal acceptance | Disposition | Evidence |
| --- | --- | --- |
| Expected: a block legend's source measurement reserves each actual max(text line,swatch height) row and declared inter-entry gaps; completed placement consumes the same geometry. Cover mixed-height entries and text-only keys synthetically, retain genuine overflow warnings, inspect actual SVG, and disclose batched public-output effects. Layout remains the geometry owner; do not inflate preset dimensions or edit corpus data to mask the mismatch. | focused/initial artifact evidence met; final head/release pending | `test_block_legend_minima.py`: exact65.6 minimum/preferred/completed extent, heterogeneous/text-only keys, origin, empty/misaligned inputs and unchanged generic stack. `test_block_legend_measurement.py`: fixed/auto actual SVG, two30px circles plus6px gap=66; forced40px slot retains overflow warning. Actual auto/cramped SVG rasters inspected. [Official50-slide audit](https://github.com/tya5/chrona/pull/1838#issuecomment-6294319757):2 changed SVG pairs inspected, zero primitive/label/dependency/diagnostic additions or removals; final-head artifact confirmation and exact-main three-OS CI required. |

Architecture: Layout's legend producer supplies neutral per-run block minima;
the existing source measurer closes rows/gaps and placement encloses every row,
not only the label bottom. Unrelated stack defaults stay unchanged. Inline/grid
and known-width completion retain their owners. Legacy half-swatch gap arithmetic
uses Decimal composition, not a new tolerance. Scene/adapters gain no sizing rule.
Fixed allocation remains fixed; declared visible-overflow may enlarge the Scene
canvas envelope, with its existing warning rather than silent fitting.

Focused43 synthetic/source/legend tests and41 adjacent fixed/auto/swatch tests
pass (overlap);3 new actual-SVG controls and3 fixed Scene/SVG digest controls pass.
No local full suite or public-corpus regeneration. CI supplies one disposable
snapshot and public-output count/byte audit before acceptance; no authored
generated output or resource tuning.

CI39445994029 found five stale test-fixture Scenes and one candidate-height
assertion. Regenerate only those fixture mirrors: each changes one legend-slot
finite-decimal value, with every SVG and all other Scene bytes retained. The
candidate test now records its actually inflated batch, not the original batch;
its strict excess-height assertion and final geometry/canvas identity checks stay.
The separate stale-base readiness failure requires following current ready main.
