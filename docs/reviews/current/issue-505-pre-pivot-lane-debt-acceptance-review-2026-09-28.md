<!-- chrona:literal-acceptance/v1 -->

# #505 pre-pivot lane debt — acceptance review

**Implementation:** `fa34dfd5` (retired path removal), `2bb5606f`
(three-Scene route test), `404f8c6b` (derived evidence repair),
[PR #520](https://github.com/tya5/chrona/pull/520). **CI:** [run
36435758625](https://github.com/tya5/chrona/actions/runs/36435758625)
passed Ubuntu, macOS and Windows conformance/full pytest/wheel and the
newest-Python public-materializer reproduction. The first run failed conformance on stale
diagnostic line anchors and deleted historical links; an unrelated #486
review-format defect was present on its public base. The corrective commit
refreshes the inventory, links historical reviews to the exact pre-pivot
commit, and makes #486's existing five-row review structurally valid.

## Literal issue acceptance

### Issue #505

- Source: [Issue #505](https://github.com/tya5/chrona/issues/505)
- Observed: 2026-09-28

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Every item above is either removed or kept with a named current consumer and a one-line purpose in code or spec. | met | [Schema](../../../schemas/scene-v0.6.schema.yaml) states current consumers/purposes for four retained fields; [live facet composition](../../../src/chrona/presentation/layout/lane_mark_facets.py) replaces dead allocation/mapper; retired audit, seed and test-only preflight are gone. | — |
| 2 | No Scene field remains in the public schema without a consumer or a documented purpose. | met | [Scene schema](../../../schemas/scene-v0.6.schema.yaml) documents fixed membership, exact emitted ownership/obstacles and shared clearance; [three-Scene test](../../../tests/unit/chrona/usecases/test_render_review.py) consumes clearance, while Scene model and serialization validate the inventory. | — |
| 3 | `staged_modules.txt` lists no lane module whose stated condition is already met. | met | [Staged list](../../../tools/staged_modules.txt) is empty; [reachability guard](../../../tools/check_module_reachability.py) reports 107 reachable modules and 0 staged, and rejects the retired allocator/preflight entry points. | — |
| 4 | The 02/11/12 route-versus-label check exists as a Scene-level test, and the review cites the real test names. | met | `test_public_lane_scene_routes_never_cross_required_lane_or_member_labels` in [render-review tests](../../../tests/unit/chrona/usecases/test_render_review.py) renders all three public closures and checks dependency segments against required visible labels; the [#467/#494 release review](issue-467-494-lane-acceptance-review-2026-09-27.md) now cites it. | — |

## Programme-level criteria (optional)

None.

## Verification and architecture

Focused Layout/Scene/render-review batch: 128 passed. The new 02/11/12
parameterized Scene check: 3 passed. Local conformance, float/reachability
guards and the 29-slide `tools/regenerate_public_examples.py --check --jobs 4`
batch passed. No committed Scene/SVG/PNG changed; the generated diagnostic
inventory changed only because deleted functions and shifted code lines no
longer have their old anchors. The fixed Project/View membership and live
subtrack/footprint path remain; Layout owns finished geometry and routes,
Scene carries identity/primitive evidence, and adapters remain unchanged.
Historical slice reviews point to pre-pivot commit `f3688940` instead of
missing current files. Final acceptance requires the linked CI run to pass
before PR merge or issue closure; this release gate is met on implementation
commit `404f8c6b`.
