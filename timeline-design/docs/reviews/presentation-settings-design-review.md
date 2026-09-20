# Presentation Fixed-Value Externalization: Design Review

Baseline reviewed: `e65dc56d01ba9abc85b28b5c9c2a673a1e0d3829`.
This change contains only design documents, schemas, design fixtures, and their
validation. It does not change `src`.

## Connection checks

- Preserve View selection/order/dates and Style semantic roles; create no duplicate
  source of truth for settings.
- Put appearance in Theme, placement in Layout, wording in Detail, runtime dimensions
  in Context, and output policy in Output.
- Connect existing Specifications 27/28 to the consolidated contract in 29. Do not
  silently change v0.1; explicitly migrate to v0.2.
- Include the current Gantt, legacy review, summary, and minimal SVG as four migration
  paths.
- A preset is either complete values or a fixed base plus partial overrides. Arrays
  replace wholly; null deletion is forbidden; unknown keys are rejected.
- Replace fixed-coefficient text measurement with real measurement, not configurable
  coefficients. Semantic, safety, and mathematical rules remain invariant.
- Do not include Controller-Z-specific Python branches or dedicated drawing commands.
- As P4 remediation, do not implicitly infer font metrics or viewport from v0.1
  resources and promote them to v0.2. v0.1 is a diagnostic legacy adapter; v0.2 quality
  requires an explicit closed settings set.

## Validation performed

- `fixtures/validate_presentation_settings.py`: verifies two schemas, four valid
  examples, eleven invalid examples, and agreement of the 78-item inventory with
  defaults.
- `fixtures/validate_conformance.py`: temporal-reference fixtures pass.
- Existing pytest: 104 passed, with two existing RefResolver deprecation warnings.

## Remaining implementation gates (not replaced by design validation)

P1–P5 are defined in `planning/presentation-settings-implementation-plan.md`.
Implementation must verify binding to real font/locale assets, reference hashes,
semantic closure, consumption of every setting, AST fixed-value audit, SVG
reproducibility, and image comparison. A fixture's zero hash is explanatory only, not
an executable asset reference. Do not claim that fixed values have been removed from
implementation or that YAML alone applies every setting at this time.
