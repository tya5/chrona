<!-- chrona:literal-acceptance/v1 -->

# Issue #1584 — hierarchy fallback

Ready base `b28afc8cf2cca1fd24d87ea0815305d94c3e5351` (includes dev B #1590).
[Approved scope and importer transfer](https://github.com/tya5/chrona/issues/1584#issuecomment-6217536606).
[Current plan and evidence](https://github.com/tya5/chrona/issues/1584#issuecomment-6203805177).
Importer `--role` and its guide example belong to dev B #1585, not this release.
Final-head [CI38920686392](https://github.com/tya5/chrona/actions/runs/38920686392)
and exact review-containing main `e02bcf5a1097d2c6b4a8f85c53376704906dcb70`
[three-OS release38922938016](https://github.com/tya5/chrona/actions/runs/38922938016)
passed; the issue is closed.

## Literal issue acceptance

### Issue #1584

- Source: [Issue #1584](https://github.com/tya5/chrona/issues/1584)
- Observed: 2026-10-16

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic tests: role bound, unbound with groups, unbound and flat. | met | [Model tests](../../../tests/unit/chrona/presentation/model/test_responsible_hierarchy_fallback.py) cover bound/nested/intermediary/flat cases and unchanged explicit hierarchy; [render tests](../../../tests/integration/test_view_root_group_fallback.py) verify group headers, no group bars, independent role diagnostics, bound output identity and correct secondary-source errors. | — |
| 2 | The #1582 CSV renders three team groups with team headers in `target-b`, `marquee`, `sunday`, `yuya` and `executive-light`, viewed as PNG. | met | Reviewer explicitly confirms this row uses hierarchy fallback without role binding. Five combined #1582/#1584 PNGs independently viewed: Backend/Frontend/QA headers, no group bars, both started Actuals/progress. Three generic-design suppressed relations warn explicitly; no inputs were tuned. [Evidence](https://github.com/tya5/chrona/issues/1584#issuecomment-6203805177). | — |
| 3 | HALCYON (role bound) output byte-identical; other public changes listed with counts. | met | [Five bound-role controls](https://github.com/tya5/chrona/issues/1584#issuecomment-6204311050) preserve all10 paired SVG/Scene bytes. Final source dd5c2f781 [artifact12054860837](https://github.com/tya5/chrona/actions/runs/38920686392/artifacts/12054860837) preserves all50SVG+50Scene raw bytes;109 paths before/after,0 added/retired. Each public context has0 changed SVG/Scene primitives/routes/labels/diagnostics. Only diagnostic inventory and presentation coverage reports change. [Final audit](https://github.com/tya5/chrona/pull/1598#issuecomment-6218411692). | — |

## Programme-level criteria (optional)

Architecture: Project owns containment; View projection resolves a private typed
root-group source, distinct from authored full-tree hierarchy. Layout receives
resolved groups, Scene/adapters remain unchanged. Only the handled grouping
diagnostic is omitted. Schema equivalence against ready main passes: expected
structural delta1/equal37,575 corpus documents,739 diagnostic probes.
Owner-based synthetic Projects now explicitly bind responsible=owner; deliberate
unbound fixtures opt out. Affected batches:267 tests passed (then two stale
Scene digests refreshed and passed),114 additional tests passed, final36 passed.
Both refreshed Scene comparisons preserve surfaces/manifest/diagnostics and SVG
bytes; only Project/View provenance identities differ. No product compatibility
inference or weakened geometry assertions were introduced.
