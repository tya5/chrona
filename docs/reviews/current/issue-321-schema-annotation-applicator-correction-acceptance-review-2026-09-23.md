# #321 Schema Annotation Applicator Correction Acceptance Review

**Authority:** Specification 56 and the schema-annotation applicator correction
plan and architecture review.

**Result:** Accepted.

## Delivered correction

- The inventory-driven annotation lint now traverses every `allOf` branch.
  Pure `$ref` reuse remains exempt, while local reference constraints and
  nested conditionals are discovered even behind structural composition.
- A structural composition carrier is traversed without duplicating ordinary
  property documentation.  Its nested applicators remain independently gated.
- Focused negative fixtures prove that both a conditional hidden behind a
  structural `allOf` and a local `allOf` assertion fail with a stable schema
  pointer when their description is absent.
- Live View conditional forms and live constrained reference branches now carry
  author-facing descriptions; examples remain validated for conditional forms.

## Architecture conclusion

The correction is confined to author-facing schema metadata and its repository
quality gate.  It adds no parser fallback, schema registry, diagnostic policy,
or dependency into Core, View, Layout, Scene, or renderer paths.  The inventory
remains the sole definition of the live corpus.

## Verification

- Annotation and normative-reference gates: passed.
- Focused annotation/reference tests: **12 passed**.
- `python conformance/run_conformance.py`: passed.
- `python tools/check_import_direction.py`: **8 packages, 28 edges, all inward**.
- `pytest -n 4 -q`: **443 passed, 7 skipped**.
- All eight declared public materializer checks passed; the generated SVG diff
  is empty.
- Wheel build and isolated installed-wheel smoke: passed.
