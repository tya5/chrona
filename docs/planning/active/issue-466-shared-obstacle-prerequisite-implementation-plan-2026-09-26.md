# Implementation Plan — Shared Obstacle Prerequisite (#466, Stage 1)

**Design base:** [#466 design](../../design/issue-466-general-placement-design-2026-09-26.md) and [architecture review](../../reviews/current/issue-466-general-placement-architecture-review-2026-09-26.md), published at `48dcd674fd3e2435dcc2fe746214e9fa32936a6f`.
**Consumer:** [#467 lane design](../../design/issue-467-collision-aware-lane-rows-design-2026-09-26.md).
**Boundary:** this plan implements only the typed shared-obstacle prerequisite. It does not implement #466's View candidate grammar, nearest-free plot search, tail/balloon Theme, or close #466. Those later parts require their own completed design/review and amended plan.

## Literal #466 acceptance ledger

1. One obstacle set is computed per surface and used by every placement and leader route. A committed test shows a note beside a dependency line no longer covers it.
2. Placement candidates are declared as region, search, obstacles and connector. The existing rung names expand to candidates, and all committed evidence is unchanged by that refactor.
3. A nearest-free search exists. With candidates plot → nearest-free → tail and no rail slot, HALCYON-1 `02-programme-board` places all three notes without covering a mark, a label or a dependency path, and without crossing the as-of line.
4. The same slide with candidates plot → nearest-free first, then rail, falls back to the rail when the plot is made too crowded, with a diagnostic naming the candidate used.
5. Placement is deterministic and bounded. The placement decision records the candidate chosen and the search count.
6. A Theme can draw the tail and balloon outline. A Theme without it renders as today.
7. The specification describes the model once, and no longer as a list of per-rung behaviours; `06-view-model.md` and `44-usable-explicit-rows-and-annotation-rail.md` point at it.

This stage can establish the shared inventory and dependency-line proof for item 1, and the canonical obstacle subsection for item 7. Items 2–6 remain `not met`; the acceptance review must say so and leave #466 open.

## Independently publishable slices

| Slice | Owners/files | Focused evidence | Publication gate |
| --- | --- | --- | --- |
| O1 typed inventory | New `src/chrona/presentation/layout/obstacles.py`; adapt `labels.py`, `routing.py`, `annotations.py`; unit tests in `tests/unit/chrona/presentation/layout/` | Stable ID/class/region/host geometry; rectangle vs stroked-segment intersections; deterministic query and explicit port/host exemption; old label/route API characterization | Commit, push, inspect CI before O2; no public resource change |
| O2 composer wiring | `surface_composer.py` and focused composer tests | Exactly one index per composition; mark/text/axis registration, semantic route query/registration, annotation box and leader query/registration; dependency-line fixture; no row background obstacle | Commit, push, inspect Scene/SVG differences and CI before #467 uses seam |
| O3 acceptance boundary | `docs/reviews/current/issue-466-shared-obstacle-prerequisite-review-2026-09-26.md`; public example evidence if changed | Focused tests, `tests/integration/test_materialize_example.py` public reproduction, generated Scene/SVG diff batch, all #466 literal rows marked; CI full matrix | Publish review and leave issue open; record exact merge/base commit |

Before every publication fetch `origin/main`, inspect ahead/behind and exact staged/generated diff, push serially, verify remote SHA and CI. Use `.venv311`; do not run a redundant full local pytest without a concrete risk. If O2 reveals a need to change candidate order or resource semantics, stop and complete the later #466 design instead of hiding it in the obstacle adapter.

## Structural gate

The index is an object with one monotone phase history, not several lists independently assembled for labels, relations and annotations. A route may exempt only its named endpoint ports. A label may exempt only its named host mark. Dependency routes must query accepted required labels; annotations query those routes. Scene/adapter code must not import the inventory or repair Layout geometry. The public `automatic` byte baseline is characterized; any intentional changed bytes in O2 must be explained by a previously overlapping obstacle, not attributed to a new View policy.
