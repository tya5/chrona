# M14 Review SVG Final Review — 2026-09-19

**Disposition:** Superseded — group presentation correction required.

`chrona render-review` consumes explicit Project, Actual, View, Style, and Theme inputs.
Its output keeps planned and Actual values separate, labels known finish variance, makes
missing/unmatched Actual visible, and carries stable SVG source metadata. It never
mutates Project or scheduling state. Evidence: Controller Z review SVG, 86 tests, full
fixture conformance, XML validation, and deterministic repeat output.

The prior adapter did not consume `View.grouping`; it cannot claim configurable group
presentation until the correction is implemented.
