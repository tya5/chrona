<!-- chrona:literal-acceptance/v1 -->

# Issue #1584 — hierarchy fallback

Base `a07b31a4b49d1168c370443d72174338578aacc9`.
[Approved scope and importer transfer](https://github.com/tya5/chrona/issues/1584#issuecomment-6217536606).
[Current plan and evidence](https://github.com/tya5/chrona/issues/1584#issuecomment-6203805177).
Importer `--role` and its guide example belong to dev B #1585, not this release.
Final-head public snapshot/CI and exact-main three-OS release remain required.

## Literal issue acceptance

### Issue #1584

- Source: [Issue #1584](https://github.com/tya5/chrona/issues/1584)
- Observed: 2026-10-16

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Synthetic tests: role bound, unbound with groups, unbound and flat. | met | [Model tests](../../../tests/unit/chrona/presentation/model/test_responsible_hierarchy_fallback.py) cover bound/nested/intermediary/flat cases and unchanged explicit hierarchy; [render tests](../../../tests/integration/test_view_root_group_fallback.py) verify group headers, no group bars, independent role diagnostics, bound output identity and correct secondary-source errors. | — |
| 2 | The #1582 CSV renders three team groups with team headers in `target-b`, `marquee`, `sunday`, `yuya` and `executive-light`, viewed as PNG. | met | Reviewer explicitly confirms this row uses hierarchy fallback without role binding. Five combined #1582/#1584 PNGs independently viewed: Backend/Frontend/QA headers, no group bars, both started Actuals/progress. Three generic-design suppressed relations warn explicitly; no inputs were tuned. [Evidence](https://github.com/tya5/chrona/issues/1584#issuecomment-6203805177). | — |
| 3 | HALCYON (role bound) output byte-identical; other public changes listed with counts. | not met | [Five bound-role controls](https://github.com/tya5/chrona/issues/1584#issuecomment-6204311050) preserve all10 paired SVG/Scene bytes. Prior full public preflight preserves50SVG+50Scene; final-head CI count table remains required before release. | — |

Architecture: Project owns containment; View projection resolves a private typed
root-group source, distinct from authored full-tree hierarchy. Layout receives
resolved groups, Scene/adapters remain unchanged. Only the handled grouping
diagnostic is omitted. Schema equivalence against ready main passes: expected
structural delta1/equal37,575 corpus documents,739 diagnostic probes.
