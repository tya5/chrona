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

### Selected hint input and ownership

`inputs.previousScene` is an optional pinned artifact, not a presentation
resource: `{store, address, revision, contentIdentity}` with a mandatory exact
SHA-256. Scene has no payload resource ID; do not invent one or introduce a
wrapper resource merely to satisfy ordinary resource-reference parsing.
The existing SnapshotReader verifies immutable bytes and safe Store addresses;
materialization stages this pin separately from typed semantic resources.
Closure captures bytes/identity. The render use case validates the Scene schema
and same-project provenance before passing neutral geometry evidence to Layout.
Malformed, missing or identity-mismatched inputs fail at ingress; unsupported
route geometry or ambiguous matching is a measured hint miss, never a guess.
The Context identity already binds the pin for caching/provenance; no extra
Scene metadata is emitted merely to make future hints readable. Omitting the
pin preserves prior output. A draft `--previous-scene` adapter captures the
same pinned bytes without writing the input or bypassing validation.

Match the existing surface/sourceRef/fromInstanceId/toInstanceId identities;
skip decoration and paired-stub fragments. Scene v0.7 supplies unrounded points
and endpoint identities. Layout enumerates old legal ports and uniquely inverts
marker trimming. Painted host geometry supplies anchor evidence; compatible
Theme terminal semantics supplies the centred flag for unpainted rollup ports
(`circle`, `open-circle`, `dot` only). Unknown or incompatible evidence misses.

Reanchoring preserves port sides and shape family: apply a shared translation
when both endpoint corridors translate equally; otherwise replace endpoint
corridors and adjust their adjacent orthogonal joins while preserving interior
channel coordinates. Degeneration, ambiguity or any failed current validator
rejects the proposal. Hinted and searched candidates share preparation, normal
safety, quality, terminal and window checks. First-fit tests hints before its
ordinary candidates; best ignores them and retains its existing receipts.
Counters distinguish accepted hints, unusable/invalidated hints, absent keys
and actual search, with concrete reasons; do not equate endpoint-only changes
with every possible change to routing inputs or claim completeness from reuse.

Architecture review: artifact integrity belongs to closure/use cases, candidate
geometry to Layout, completed data to Scene/adapters, terminal style to Theme.
No Scene routing/measurement, duplicate validator, hidden persistent cache or
project-specific rule is added. Test schema/staging/read-ledger/cache parity,
painted/unpainted ports, marker families, shift/obstruction/new-relation cases,
best/no-hint byte controls and the actual trial. Critical feasibility remains
separate and unapproved pending [domain selection](https://github.com/tya5/chrona/issues/1300#issuecomment-6133315743).
Publish normative Context/CLI/routing contracts and final file-level slices
before hint implementation; this record does not authorize that code yet.

1. Complete selected contracts and architecture review here; update normative
   Context/Scene/routing specifications and publish before product changes.
2. Finalize implementation slices with owned files, migrations and focused tests:
   closure/identity; shared Layout validation and stability; protected critical
   feasibility; first-fit hint reuse/counters; literal release review.
3. Implement only approved slices after #1427 reconciles shared files. Batch
   public outputs once per behavioral boundary; disclose changes, never absorb
   them by editing example data. Let CI supply full release matrix.
