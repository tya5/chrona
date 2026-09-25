# Issue #414 — Semantic Realization Programme Release Review

**Status:** accepted.
**Programme implementation:** `91beae82`, `a362989f`, `4b157f95`, `145d44ca`
**Final implementation CI:** [run 36125813453](https://github.com/tya5/chrona/actions/runs/36125813453)

## Release disposition

The programme's finite realization report now has no unresolved row.  It
measures declared state families against committed Scene roles without reading
an adapter, and its remaining many-to-one mappings are explicit intentional
equivalences rather than unobserved distinction loss.

| Programme criterion | Public evidence | Result |
| --- | --- | --- |
| Measurement is standing and reproducible | `semantic_realization.py`, `tools/semantic_realization_coverage.py`, and the checked report define and render the finite family inventory. | Pass |
| A selected non-equivalent state cannot disappear silently | The report classifies it as `gap`; all current rows are `realized`. | Pass |
| Table comparison facts reach output semantics | #402 supplies typed cell facts and separate variance/missing-observation roles; both table families are realized in HALCYON and Orion evidence. | Pass |
| Annotation purpose reaches output semantics | #413 supplies purpose-specific box/text/leader placements and Controller Z realizes callout, highlight, note, and explanatory-arrow. | Pass |
| Intentional neutrality is explicit | An unavailable finish variance remains neutral only under the recorded equivalence reason; it is not inferred by Scene. | Pass |
| Output and evidence remain reproducible | Materializers reproduce committed Scene/SVG bytes, reports are fresh, and no coverage row has the `gap` disposition. | Pass |

## Verification

* checked semantic-realization and presentation-coverage reports, diagnostic
  inventory, focused normalizer/Layout/Scene/report tests, and public
  materializer byte checks passed;
* generated Controller Z annotation SVG was reviewed for independently
  treated callout, highlight, note, and explanatory-arrow placements;
* `python conformance/run_conformance.py` passed;
* CI run 36125813453 passed on Ubuntu, macOS, and Windows, including parallel
  full pytest, conformance, structural and report gates, wheel build, and
  installed-wheel smoke.

## Architecture review

The report is observational: it reads finite registry declarations, normalized
corpus selections, and committed Scene primitives.  It does not select a
semantic, make Layout geometry, or inspect SVG/pixels.  The productive paths
remain typed normalization -> Layout placement closure -> Scene registry
projection -> adapter.  This preserves the responsibility boundaries while
making omissions auditable before gallery curation relies on the vocabulary.

## Final disposition

Issue #414 is complete.  The report deliberately measures the families whose
declared state-to-visual distinction was in scope for this programme; it is not
a claim that every single-purpose primitive must acquire state variation.
