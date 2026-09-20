# Controller Z: design, implementation and rendered-slide review

## Conclusion

The v0.2 presentation work is **not P1–P5 complete**. Passing the existing
115 tests is not evidence that all settings in the inventory are consumed.
This review supersedes earlier unqualified completion claims. The visible
Controller Z slide is improved here without changing schedules, observations,
group membership or dependency endpoints.

## Findings

| Priority | Evidence | Status |
| --- | --- | --- |
| High | `gantt_surface.py` passed the schema's groupPaints object to HTML escape, which requires a string. | Fixed: explicit color and opacity access; regression test. |
| High | Remote `pyproject.toml` specified `hatchling`, not the PEP 517 backend module `hatchling.build`. | Correct backend restored in this publication; wheel build not verified. |
| High | `presentation_settings.py` selects preset bases by ID without checking revision/contentIdentity. | Open; immutable preset closure remains incomplete. |
| High | `presentation_layout.py` does not implement the full content/min/max/gap contract; renderer rounds rectangles to integers. | Open; generalized layout completion cannot be claimed. |
| High | `font_metrics.py` resolves regular font metrics while SVG requests bold; fallback glyphs, shaping and baseline behavior do not meet the full design contract. | Open; raster validation of this slide is not multilingual/general font proof. |
| Medium | Heading/subtitle, legend labels and legend spacing ignored v0.2 configuration. | Fixed in gantt path for the fields exercised here; measured legend layout now diagnoses overflow. |
| Medium | Actual bar height, routing parameters, row sizing, stroke styles and other inventory fields still have fallback literals or are unconsumed. | Open; all-field mutation coverage required. |
| Medium | Specification 29's all-output requirement conflicts with later v0.1 exclusion/completion wording. | Open design decision; reconcile before implementation of that scope. |
| Medium | Built-in settings/schema loading relies on repository-relative documentation files. | Open; installed-wheel behavior needs coverage. |

## Design gate and scope

No new schema or renderer-specific Controller Z branch was introduced.
Existing Theme (paint/typography), Layout (regions/legend) and Detail
(title/subtitle/legend/coverage) ownership suffices for these corrections.
The unresolved scope and immutable-closure issues above require a separate
design-consistency pass before broader implementation. They are not waived.

## Visual changes

- Keep the 1600 × 900 format and the complete eight-row gantt.
- Use stable group-keyed blue, mint and rose bands to separate owners.
- Use a shorter presentation heading, retaining full project title in SVG metadata.
- Keep the process name and actual date range in the subtitle.
- Increase outer margins and title hierarchy; reduce unused footer space.
- Measure configurable legend labels instead of fixed item advances.
- Preserve both +4d variance labels, missing-actual notices, unmatched observation
  count, seven dependency routes and milestone symbols.

The complete, editable settings are in
`examples/controller-z/variants/editorial/settings.yaml` (JSON syntax is valid YAML).
The font content hash intentionally identifies the installed regular Nimbus Sans
font used for this render; another font installation must supply matching metrics.

## Reproduction and acceptance

```sh
.venv/bin/python tools/verify_presentation_v2.py \
  --settings examples/controller-z/variants/editorial/settings.yaml \
  --output examples/controller-z/variants/editorial/expected.svg
node tools/verify-gantt-svg.cjs examples/controller-z/variants/editorial/expected.svg examples/controller-z/variants/editorial/preview.png
.venv/bin/pytest -q
```

The harness compares two renders. New tests cover group color/opacity,
input immutability, text escaping, subtitle visibility, measured legend spacing,
legend overflow and mark/relationship invariance under text-only changes.
The raster check measures annotated table/group text, not every SVG text node.
This focused acceptance does not close the outstanding P1–P5 issues.

Verified in this workspace: **119 tests passed** (two existing RefResolver
deprecation warnings); raster verification checked **14 annotated text lines,
zero width overflows**. The final PNG was visually inspected at 1600 × 900.
