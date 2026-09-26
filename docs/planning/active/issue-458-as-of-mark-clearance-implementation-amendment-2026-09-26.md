# Implementation amendment — as-of mark clearance (#458)

**Correction:** [mark-clearance design](../../design/issue-458-as-of-mark-clearance-correction-2026-09-26.md).

1. Add an optional declared visible-fallback side to `layout/labels.py` and
   the `LabelRequest` transport. Test ordinary first-side behavior, a named
   alternate fallback, and invalid side rejection.
2. Give only the as-of request the finite seam candidate, axis-inclusive
   search bounds, and mark-clear `above` fallback. Run the HALCYON 04/07
   materializers and `tests/acceptance/output/test_generated_output_properties.py`
   focused on text-over-mark; inspect all changed SVG/Scene artifacts.
3. Run full public materializer reproduction, Scene perceptibility,
   conformance, and CI matrix. The release review must cite the prior red
   run and final green run. Publish this correction before altering code.
