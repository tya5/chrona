# Revision stability completion (#1300)

Baseline: READY `165587e6` (PR1449 and derived-main38323738228 succeeded),
independent inspection/delta/critical-priority
slices release-verified by [38290538367](https://github.com/tya5/chrona/actions/runs/38290538367).
Authority: [issue](https://github.com/tya5/chrona/issues/1300),
[selected hint contract](https://github.com/tya5/chrona/issues/1300#issuecomment-6133101982),
Specs08/33/50/56/66 and the current acceptance review. #1427's atomic release
is merged and reconciled. Its exact-main release38317097402 succeeded.
The selected hint design does not authorize the unresolved critical slice.

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
Add the optional field in place to Context v0.17: omission preserves behavior;
a closed inputs object alone does not require a version bump.
The existing SnapshotReader verifies immutable bytes and safe Store addresses;
materialization stages this pin separately from typed semantic resources.
Closure captures bytes/identity. The render use case validates the Scene schema
and same-project provenance before passing neutral geometry evidence to Layout.
Malformed, missing or identity-mismatched inputs fail at ingress; unsupported
route geometry or ambiguous matching is a measured hint miss, never a guess.
Validate supported Scene v0.6/v0.7 documents; v0.6 lacks endpoint identities and
therefore cannot yield a reusable route. Exactly one primary Project provenance
entry must match the current stable Project ID, not its revision/content hash.
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

Reanchoring preserves semantic endpoint/boundary choice and shape family: apply a shared translation
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
before hint implementation.

### Architecture review and implementation plan

Specs08/13/33/50 (routing and closure)/56/66, the Store reader and actual Scene
v0.7 serialization were checked against the selected contract. The public Scene
already carries primary Project ID and unrounded route points/endpoint IDs;
it does not carry selected egress-side IDs. Uniquely reconstruct semantic endpoint
coordinates, not historical egress identity; a tangent alone cannot prove a side.
Try compatible current egress pairs in existing first-fit order through the common
validator, rather than rejecting a valid prior path for multiple current choices.
See the [port correction](../../design/issue-1300-scene-hint-port-correction-2026-10-13.md).
Artifact pins need a distinct contract/closure
value and explicit read-ledger entry, not a fake ResourceReference. Context pin
identity is sufficient for immutable cache/provenance; best validates the input
but consumes neither geometry nor hint counters. No persistent cache is added.
Critical completeness remains unresolved and hints do not satisfy that criterion.

| Slice / publication boundary | Owned files and acceptance evidence |
| --- | --- |
| H1: explicit input and closure | Context v0.17 schema and mirror, contracts/resources.py, model/closure.py, usecases/materialize.py, render_review.py, draft_render.py, app/cli.py; optional pin, exact bytes/hash, same Project ID, supported Scene validation, ledger and materializer round-trip. Focused closure, Draft, CLI and materializer tests; schema equivalence. Publish after normative design. |
| H2: Layout hint reuse, with H1 in one product PR | New Layout hint geometry/identity values and reanchor module; surface_routes.py shares its prepare_route/common candidate gates; model/info_diagnostics.py projects typed counters. Uniquely recover semantic coordinates; offer compatible current pairs in first-fit order before ordinary selection. Preserve boundary choice, shape family and interior channels, normal-domain only. Test painted/unpainted hosts, centred terminals, ambiguity, changed obstacles, degeneracy, explicit windows, all recovery modes, best/no-hint bytes and actual v1/v2 Scene/SVG shape. |
| S: unconditional stability | First strengthen tests/integration/test_revision_delta_anchor_stability.py with no-hint, explicit-suppress controls: nonempty suppressed identities, unchanged delta sides under uniform date shift/unrelated append, and unrelated relation-order permutations. Hold completed endpoint/corridor geometry fixed and inspect actual Scene/SVG. Product changes in routing/label owners require the corridor-local rule to be completed/reviewed first. No independent-criterion waiver. |
| C: protected critical feasibility | routing.py/route_search.py/common validators after reviewer domain selection and completeness/work-accounting proof; quality-overrun and impossible diagnostic controls. Not authorized yet. |
| Release | One batched public materializer comparison per product boundary, primitive/diagnostic deltas disclosed with no authored examples changes. CI full three-OS/conformance/wheel/MCP/newest-Python gate; literal acceptance review keeps original S/C rows open until met. |

H1/H2 counters cover admitted instances exactly once: accepted, invalidated by
current validation, unusable evidence, or absent key; record actual search entry
separately, and retain frontier-expansion receipts. Valid v0.6 input is unusable;
otherwise an absent exact key is absent, ambiguous/unsupported matched evidence
is unusable, a rejected reconstructible candidate is invalidated, and a passing
one is accepted. Every nonaccepted instance enters ordinary selection; count
actual search only when an iterator runs, not when a finite proposal wins.
A usable route is tried only
in the normal domain before first-fit proposals. Unsafe prior recovery is not a
hint admission shortcut. Explicit-window endpoint absence is not a searched
instance. Best and absent-input paths emit no new hint diagnostic. Decoder and
candidate validation are shared seams, not duplicated geometry pipelines.

H1/H2 local evidence: optional neutral pin/schema, immutable closure capture, common
Scene ingress/project validation, read-ledger and Draft flag are implemented.
Focused closure/contract/Draft/ingress tests pass; schema-equivalence against
READY87afea92 passes without changing historical verdicts. Real Store and execution
overlay round-trips preserve exact artifact bytes; corrupt hash and wrong Project
fail through stable diagnostics. H2 carries neutral geometry through preparation,
count closure and final Layout; ordered reanchored proposals use the common
completed-route validator before ordinary search. The actual v1/v2 Scene/SVG test
retains spec-build's translated shape without search. Same-input10/10 routes reuse
without search; best retains byte-identical Scene/SVG and receipts.100 focused
tests pass; public46-context no-hint reproduction passes. Exact-head CI/full
release is still required. Original unconditional stability/critical criteria
remain unfinished; do not close the issue for completing hints alone.

S evidence design: the existing default-relax test can pass with an empty
suppression set. Use a synthetic completed blocker, not a corpus edit or forced
routing result, and retain at least one drawn control. Compare source-keyed
suppressed identities rather than unrelated diagnostic counts. Apply any date
shift to both planned and actual dates. Assert the blocker is actually painted.
This is a test-only implementation boundary, not a new routing contract.
Architecture review finds no demonstrated processing-order defect: dependency
routes and ports are excluded from normal mark/text/label obstacles. Global
shape-channel contacts still need investigation before claiming corridor-local
independence. If stronger evidence fails, stop S and publish a normative design
correction before product code; passing fixtures alone do not prove the general
rule or discharge the separate critical feasibility criterion.

1. Complete selected contracts and architecture review here; update normative
   Context/Scene/routing specifications and publish before product changes.
2. Finalize implementation slices with owned files, migrations and focused tests:
   closure/identity; shared Layout validation and stability; protected critical
   feasibility; first-fit hint reuse/counters; literal release review.
3. Implement only approved slices after #1427 reconciles shared files. Batch
   public outputs once per behavioral boundary; disclose changes, never absorb
   them by editing example data. Let CI supply full release matrix.
