# Issue #414 — Semantic Realization Evidence Foundation Acceptance Review

**Status:** accepted; #414 remains open for its output-realization work.
**Implementation:** `91beae82`, `3cfe565c`
**CI:** [run 36117844604](https://github.com/tya5/chrona/actions/runs/36117844604)

## Accepted boundary

The release establishes a deterministic, checked measurement boundary between
finite admitted semantic-state families and the roles present in committed
inspection Scenes.  It is intentionally not a renderer or pixel oracle.

| Requirement | Evidence | Result |
| --- | --- | --- |
| Finite families have reviewable state/equivalence declarations | `semantic_realization.py` has a typed immutable registry with duplicate and undeclared-equivalence rejection. | Pass |
| Current corpus/Scene evidence is reproducible | `tools/semantic_realization_coverage.py` reads View declarations and committed Scene JSON, emits LF-stable bytes, and is checked in CI. | Pass |
| Adapter inference is excluded | structural unit test rejects renderer/SVG dependencies; the generator does not materialize or parse target artifacts. | Pass |
| Known distinction loss is visible | `semantic-realization-coverage.md` records the finish-variance `text` collapse and annotation-purpose gap. | Pass |
| Existing evidence ownership stays intact | `presentation_coverage.py` remains the schema/slot report; the new report owns only realization triage. | Pass |

## Verification

* focused registry/report tests: 4 passed;
* `python conformance/run_conformance.py`: PASS;
* all three CI platforms passed conformance, structural checks, checked report
  generation, parallel pytest, wheel build, and installed-wheel smoke.

## Architecture review

The report reads declared semantic intent and completed Scene evidence, but
does not choose a role, modify a placement, or interpret adapter bytes.  It
therefore preserves the Project/View -> Layout -> Scene -> adapter authority
chain and makes #402/#413's missing connections reviewable without embedding
their fixes in a reporting tool.

## Remaining disposition

Do not close #414.  The report intentionally records gaps until I402-1 moves
table fact semantics through completed text placement and I413-2 does the same
for annotation purpose.  Their public corpus evidence and a regenerated report
are the closure evidence for #414.
