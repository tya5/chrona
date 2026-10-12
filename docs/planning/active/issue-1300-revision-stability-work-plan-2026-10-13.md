# Revision stability completion (#1300)

Baseline: READY `208cf1cc`, independent inspection/delta/critical-priority
slices release-verified by [38290538367](https://github.com/tya5/chrona/actions/runs/38290538367).
Authority: [issue](https://github.com/tya5/chrona/issues/1300),
[selected hint contract](https://github.com/tya5/chrona/issues/1300#issuecomment-6133101982),
Specs08/33/50/56/66 and the current acceptance review. #1427's atomic release
is PR1447; reconcile its published implementation before touching shared routing.
This is the design plan, not approval to implement a guessed hint contract.

## Literal acceptance

| Requirement | Required evidence |
| --- | --- |
| A test pair: a plan and the same plan with every date shifted by the same amount (and, separately, with an unrelated object appended). The set of suppressed relations and each delta label's anchor side are equal between the two Scenes. | Synthetic shift/append Scene and SVG controls without relying on hints. |
| A test where a critical relation has a route: it is never suppressed. Where none exists, the distinct diagnostic is emitted. | Explicit suppress safe/impossible controls, quality-overrun evidence and a justified complete feasibility domain. Unsafe modes follow #1427. |
| The trial's v1 → v2 pair keeps `spec-build` drawn. | Actual supplied fixtures, completed Scene and SVG. |
| `--emit-scene` output diffs line by line (one primitive per line), and its parsed content is unchanged. | Published formatter/CLI controls and exact-main release already pass; retain them. |
| Do not edit `examples/**`. | Authored diff and immutable public-materializer evidence. |
| The trial's v1 → v2 revision rendered with v1's Scene as hints keeps `spec-build` drawn with the same shape. | Serialized previous Scene round-trip, reanchored geometry and actual adapter output. |
| A counter shows that only changed or new relations are searched. | Typed first-fit hint-accepted/search receipts; include obstruction-invalidated hints as changed routing input. |
| Without a hint, output is identical to without the feature. | Incremental hint-feature byte control; best ignores hints and preserves finite-quota results/diagnostics. |

## Design plan and review questions

Use cases: stable ordinary revisions, reusable completed routes, safe critical
routing and reviewable output. Hints supplement, never replace, original criteria.
Core owns scheduling/critical facts; Context/closure owns pinned previous-input
identity; Layout owns instance matching, reanchoring, common candidate validation,
geometry and counters; Scene/adapters remain completed-data projections.

Resolve before code: previous-Scene reference representation and validation;
same-project/surface/instance identity and stale input behavior; serialized port
and shape evidence (not undeclared Python-only fields); common searched/hinted
candidate acceptance; invalidation and no-search counting; corridor-local stable
selection; complete finite critical feasibility under suppress and its quality
override/impossible diagnostic. Check schema identity/migration and untrusted
Scene input against whole closure/Store/Scene/window/contrast contracts.

## Publication and implementation sequence

1. Complete selected contracts and architecture review here; update normative
   Context/Scene/routing specifications and publish before product changes.
2. Finalize implementation slices with owned files, migrations and focused tests:
   closure/identity; shared Layout validation and stability; protected critical
   feasibility; first-fit hint reuse/counters; literal release review.
3. Implement only approved slices after #1427 reconciles shared files. Batch
   public outputs once per behavioral boundary; disclose changes, never absorb
   them by editing example data. Let CI supply full release matrix.
