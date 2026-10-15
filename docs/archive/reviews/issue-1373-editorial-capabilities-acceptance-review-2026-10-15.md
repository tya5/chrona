<!-- chrona:literal-acceptance/v1 -->

# #1373: Editorial capability acceptance

## Literal issue acceptance

### Issue #1373

- Source: [Issue #1373](https://github.com/tya5/chrona/issues/1373)
- Observed: 2026-10-15

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | **Table header typography.** Column headers have no Theme text role of their own: they share `text` with the body cells, and the semantic role registry (`presentation/model/semantic_registry.py`) has no table-header role. Editorial's `TASK` / `OWNER` headers therefore cannot be upper-case and tracked as the reference sets them. Needs: a Theme role for column headers (`textRole`-like, size/weight/tracking/transform) and the View member that selects it. | met | [PR1514](https://github.com/tya5/chrona/pull/1514); `test_table_header_role.py` measures changed typography and renders SVG/Typst/TikZ. [Decision](https://github.com/tya5/chrona/issues/1373#issuecomment-6183178335): existing `tableColumnLabel`, no duplicate View selector. | — |
| 2 | **Field to initials column transform.** A `source: {field: owner}` column shows the raw field value; the reference shows initials. Needs: a closed set of cell transforms in the View column grammar (initials first), applied by Layout, so Scene stays completed text. | met | [PR1509](https://github.com/tya5/chrona/pull/1509); `test_initials_cell_transform.py`; closed View `transform: initials`, measured completed cell text. | — |
| 3 | **Nested milestone inside a capsule.** The reference draws a gate inside its parent bar; chrona draws a free-row mark. Needs: a mark placement rule (a point mark hosted by a span mark) in Layout's mark geometry. | met | [PR1530](https://github.com/tya5/chrona/pull/1530); `test_hosted_points.py` has 19 public-render scenarios covering actual SVG, semantic identity, labels/routes, inclusive endpoints, non-lane overlap, frame-drift rejection and typeset serialization. [Final artifact review](https://github.com/tya5/chrona/pull/1530#issuecomment-6186036237) proves all100 default-off SVG/Scene files unchanged; release gates below passed. | — |
| 6 | **A Context cannot render from a package-provider reference.** `LocalSnapshotReader` raises `E_STORE_REFERENCE`, so the HALCYON corpus carries byte-identical copies of the bundled Editorial resources under `examples/halcyon-1/` (guarded by `test_public_preset_evidence`). Needs: a reader that resolves `provider: package` references to the wheel resources. | met | [PR1502](https://github.com/tya5/chrona/pull/1502); `test_shared_design.py::test_a_context_renders_from_package_references_identically_to_local_copies`. Context uses the package reader; raw Project snapshot reader is unchanged. | — |

## Programme-level criteria (optional)

## Architecture and release

Layout alone owns hosting, facet partition, final-frame validation, physical
label bands and endpoint-local routing authority. Semantic lane ownership and
source identities remain unchanged; Scene/adapters serialize completed geometry.
Independent review required final-frame proof and non-lane collision checks;
both are implemented and tested. Routing review also covers terminal setbacks
and fallback stubs. Existing contrast policy remains enforced.

Local evidence: 50 public materializers passed with policy omitted; schema
equivalence L1/L2/L3 passed (one additive profile change, 37 equal schemas,
739 diagnostic probes). Header/initials regressions: 34 passed. After adopting
the font-provider correction in merge `c27aa2e07`, hosted rendering, preset font
sets and diagnostic regressions passed (63 tests). Focused routing/allocation
tests are recorded in the PR with their tested heads; no full local pytest run.

Final-head [CI38692702475](https://github.com/tya5/chrona/actions/runs/38692702475)
passed every required check at `6b535d438`. PR1530 merged as `17c55ec20`.
[Artifact11952957654](https://github.com/tya5/chrona/pull/1530#issuecomment-6186036237)
proves all100 public SVG/Scene files byte-identical; only diagnostic raise-site
inventory and host-policy coverage reports change.

Exact review-containing public READY `5ff6d95b030d8af7f824ec53f914bc147bd90e09`
passed [release38694405464](https://github.com/tya5/chrona/actions/runs/38694405464):
Ubuntu/macOS/Windows full pytest, conformance, wheel/smoke, newest-Python public
materializers and MCP. All four literal criteria are released; issue1373 is
closed. Preset/corpus YAML adoption belongs to the reviewer, not developer scope.
