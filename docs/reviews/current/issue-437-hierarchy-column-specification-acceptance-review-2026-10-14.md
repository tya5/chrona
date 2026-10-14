# Hierarchy and column contract review

<!-- chrona:literal-acceptance/v1 -->

[Design/architecture/plan](https://github.com/tya5/chrona/issues/437#issuecomment-6159095150).
Normative designdd2f284a was published before implementation282ac2f2;
publication base READY6ab07ba8. The later accepted #404 View-local contract
supersedes the older Project-edge restriction. Projection now closes only
parent availability and an acyclic local graph, iteratively; authored depths,
automatic Project hierarchy, Core, schema, Layout and adapters are unchanged.
The diagnostic migration is explicit in Spec38. No examples edits.

Root verification used this worktree's own venv/imports:181 projection/message,
contract, hierarchyColumn, synthetic width-grammar and viewport-tool tests passed; import
direction and literal-review checks passed. The reversed12000-row chain tests
deep traversal. The unrelated-subject fixture rejects the retired validator.
PR [snapshot38499477361](https://github.com/tya5/chrona/actions/runs/38499477361)
retains101 members; all92 Scene/SVG files are unchanged. Only the intended
diagnostic inventory changes. That run exposed an obsolete message test still
expecting the retired Project-root restriction; it now checks local parent
availability and cycle messages. The independent main Windows failure in
[release38498812532](https://github.com/tya5/chrona/actions/runs/38498812532)
is also repaired here under [the1474 tool plan](https://github.com/tya5/chrona/issues/1474#issuecomment-6159445038):
use the same interpreter's portable `-m chrona` entry point, not an assumed
sibling console script. Windows/Unix-shaped launcher regressions and the actual
CLI test pass locally. Current-head CI and containing-review exact-main full
release remain required before closure.

## Literal issue acceptance

### Issue #437

- Source: [issue](https://github.com/tya5/chrona/issues/437)
- Observed: 2026-10-14

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| --- | --- | --- | --- | --- |
| 1 | Specification chapter 24, or its successor, states the hierarchy model, and a reader can answer #404's question from the specification alone. | met | [Spec24](../../specification/24-table-timeline-presentation.md#hierarchy-expressions-and-column-width-437) distinguishes Project-derived automatic grouping, explicit View-local nesting and WBS/path display; states mixing/hierarchyColumn diagnostics and links [Spec38](../../specification/38-review-row-composition.md#1-contract) for local parent closure. [Projection tests](../../../tests/unit/chrona/presentation/model/test_projection_rows.py) prove unrelated/Actual/Snapshot subjects, missing parents, cycles and deep acyclic graphs without rewriting Core. | — |
| 2 | The specification describes the column width grammar exactly as `view-v0.17` accepts it. | met | [Spec24](../../specification/24-table-timeline-presentation.md#hierarchy-expressions-and-column-width-437) states the closed content/fill/fr/minmax subset, required members, 0<fr<=1000000 and excluded physical sizes. Compared with [published v0.17](https://github.com/tya5/chrona/blob/a556c099/schemas/view-v0.17.schema.yaml) and [current shared schema](../../../schemas/common-v0.1.schema.yaml); [synthetic boundary tests](../../../tests/unit/chrona/presentation/contracts/test_table_column_width_grammar.py) pin valid and rejected forms/schema pointers. No deprecated reader or new schema is introduced. | — |

## Programme-level criteria (optional)

The proposed generalized documentation checker is optional, not an acceptance
item; this work adds no checker framework.
