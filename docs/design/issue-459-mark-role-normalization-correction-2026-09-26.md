# Design Correction — Scenario Mark Role Normalization (#459)

The initial #459 design listed `scenario` as a Scene visual role. Inspection of
published `v05_builder.py` and `surface_composer.py` shows that scenario source
marks are deliberately projected through the `snapshot` Scene binding. No
`scenario` Scene visual role exists. Creating one for contrast alone would
split a stable semantic mapping and change public Scene output unnecessarily.

The finite classified Scene mark set is therefore `planned`, `actual`,
`snapshot`, `missing-actual`, `summary-bar`, `progress-fill`, and
`network-node`. Scenario source marks are covered by `snapshot`; milestone
point symbols are covered by their emitted mark role. The #459 design's
separate `scenario` role entry is superseded. No schema or identity migration
is needed for this correction.

Whole-architecture review: Source/View semantics remain upstream; the Scene
registry remains the one completed visual vocabulary; the contrast observer
classifies that vocabulary without recreating source-kind distinctions. The
implementation plan's registry coverage is amended accordingly. Published
design base: `d1f5cbce`.
