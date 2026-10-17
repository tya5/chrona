# Issue419 — semantic mapping resource

Status: V1 implemented; reviewer-required rationale retained and official
artifact equivalence verified. Final current-base CI and release remain pending.
Source base: trusted-ready published main
`8f425600eec47bb46c2f24fa0b82f38b1687bfad`.
[Reviewed scope](https://github.com/tya5/chrona/issues/419#issuecomment-6234966527):
dev A owns V1/S1/S2; dev B owns C1 and Issue344 Level 1.

## Published baseline and open questions

- The pre-V1 registry had117 actual `_binding` declarations, not123; the
  frozen equivalence inventory and field consumers are recorded below.
  The issue's older claim that primitive kind and Theme role are unread is not
  current: Scene kind checks and Layout/Theme resolution consume them.
- Spec49 owns the closed semantic→Theme→placement→Scene contract. Spec06/60
  expose one planned-mark colour encoding. Project `fields` and field roles
  already reach projection. Issue344 generalizes existing profile-v0.3 field
  definitions and package validation; it does not add Project `fieldDefinitions`.
- The remaining Style proposal is recorded here only; Spec49 documents the
  implemented V1 vocabulary, not prospective Style behavior. Keep the existing View
  `colorEncoding` input accepted and lower it into the same typed intent used
  by Style. This work does not retire that syntax or require incompatible
  Context/preset migration.

## Literal acceptance (parent remains open during partial delivery)

1. The semantic vocabulary is a versioned resource with a schema.
2. A design set can introduce a visual distinction the product did not anticipate, without a code change.
3. The presentation coverage report derives distinctions from resources rather than from source.
4. No field in the registry is unread.
5. The report lists every purpose drawn in the corpus with its realized role count, generated from committed Scenes.
6. Adding a purpose to the semantic registry without a classification fails the check.
7. The 31-of-40 figure, or its successor, is visible in a committed, checked document.

Rows5–7 are the consolidated issue433 acceptance, not optional follow-ups.
V1 addresses rows1/4; its release acceptance remains separate from the
unfinished Style and coverage rows. Do not close the parent for V1 alone.

## Design plan and publication boundary

1. Inventory all current bindings, grouped by mechanism; trace meaning, role,
   paint and every field consumer. Separate stale measurements from current facts.
2. Define the versioned mapping resource/schema shape, YAML-addable
   distinctions and closed predicate vocabulary. Preserve existing View
   `colorEncoding` as an accepted input to the same typed intent.
3. Specify the single typed-field connection for issue344, RC public/internal
   contracts, conflict and missing-fact behavior, provenance and scoped legends.
4. Compare only needed lessons from official Vega-Lite encoding/conditions and
   design-token specifications; review whole-architecture ownership against
   Spec04/06/07/08/33/49/56/60/62 and adjacent designs.
5. Keep this work record as the proposal; update normative specifications only
   alongside the implementation slice that changes their contract. No schema,
   runtime, examples or generated changes in this design amendment.
6. Post one current Status linking this record. Implementation may proceed
   within the reviewed boundaries below; deferred choices remain explicit.

Evidence: complete117-entry inventory; synthetic YAML use cases for role and
scoped encoding outcomes; literal acceptance→planned test/report mapping;
architecture consistency and migration review. Docs/literal checks apply to
this publication; future implementation uses focused tests and official
public-output/full release CI rather than an unneeded local full suite.

## Architecture review and proposed implementation sequence

The proposal preserves Spec07's Style/Theme split and Spec49's
completed-placement boundary; it does not place predicates in Theme or
geometry in Style/Scene. Existing View `colorEncoding` remains valid and lowers
to the same typed intent; no incompatible syntax or atomic resource migration
is required. Spec04 dates and observed facts remain unchanged. Spec56 controls
resource identity and shared schema vocabulary. Issue344's typed Project field
uses the same source accessor; no profile-specific backdoor. Coverage433 is
derived from vocabulary plus actual Scenes and does not infer model cardinality
from role counts.

These are the reviewed implementation slices. V1 may begin after this amended
record is published; subsequent slices follow the stated dependency order:

| Slice | Owners / changes | Acceptance evidence and publication |
| --- | --- | --- |
| V1 | schemas/resource registration, semantic registry loader, wheel resource, Spec49/56 | All117 binding records equal old values; every field has a consumer; unknown/missing/duplicate/version/identity negatives; full materializer counts. Publish resource replacement without two authorities. Rows1/4. |
| S1 | View facts, Style evaluator/contracts, Theme-role compatibility, Spec06/07/60 | Neutral unseen field combination, role and encoding outcomes, conflicts/missing/type errors, repeated/source-specific occurrences; geometry uses resolved typography/strokes. Rows2/3. |
| S2 | closure, Style references, shipped resource support and legend composition | Same typed intent for Style and existing View `colorEncoding`; exact pins/copy/wheel closure; scoped swatches retain canonical selector in Scene/provenance. A scoped legend requires its title. The derived scope qualifier is opt-in, not forced; an unrenderable optional qualifier does not refuse otherwise valid encoding. No atomic migration or second evaluator. Rows2/3. |
| C1 | coverage/classification resources, tools, checked reports | Derive every registered/drawn purpose; state/role cardinalities distinct, unclassified purpose fails, intentional equivalences and current single-role fraction visible. Rows3/5/6/7. |

Each code publication needs focused neutral tests, official batched SVG/Scene
counts and design-conformance review, followed by CI's full release gate.
Final schema spellings and exact owned files are finalized in the implementation
plan; no draft numeric budgets or project-specific predicates become acceptance
requirements.

S1 readiness review found two seams to complete before code: the existing
`FieldRoleBindings.read()` collapses absence and null, while legacy colour
encoding reads the primary Project's field directly; S1 needs presence-aware,
source-specific projected facts through the shared accessor. Coordinate that
accessor with Issue344; do not create another declaration/evaluation engine.
Occurrence role intent must also reach Layout's mark geometry and table text
measurement before placement. A Scene-only role replacement cannot implement
the approved contract. Preserve exact column-source and occurrence identities
during normalization rather than recovering them from rendered text.
Carry typed occurrence identity through marks, cells and labels; object ID
alone aliases comparison and repeated occurrences. A selected Theme role must
not replace the vocabulary's semantic identity or weaken its contrast class.
Complete the role's typography, mark geometry and stroke extents before fit
and routing, then preserve that completed role/paint through placement to Scene.

Reviewer confirmed this amendment in
[comment 6234922800](https://github.com/tya5/chrona/issues/419#issuecomment-6234922800)
and stated no additional review is needed if applied as written in
[comment 6234966527](https://github.com/tya5/chrona/issues/419#issuecomment-6234966527).
The reviewed inventory verification remains:117 unique rows exactly match the
117 AST bindings. This amendment changes documentation only; no
product/schema/examples/generated changes.

## Selected resource and Style contract

The host vocabulary (`chrona/semantic-vocabulary/v0.1`, kind
`semantic-vocabulary`) and authored Style (`chrona/style/v0.2`, kind `style`)
are separate resources using the shared envelope and exact pinned references.
The bundled
vocabulary replaces the Python binding table and declares semantic ID,
primitive family, purpose, Scene role, Theme role, contrast class and state
classification. It declares host-produced meanings, not geometry. Style rules
produce either a Theme-role reference or a color-scale encoding over
View-projected facts. A design may add rules over admitted facts and Theme roles,
but cannot invent schedule facts, Scene kinds, purposes, adapter capabilities,
or weaker contrast requirements. Custom Theme role names remain constrained by
primitive-family and contrast compatibility.

Resource identity, duplicate IDs, unsupported versions, missing referenced
bytes and identity mismatches fail closure. The vocabulary is explicit in
resolved closure/provenance, including when the wheel-owned default applies.
Context/preset references use existing pinning rules; they need not all migrate
atomically. Package support may carry supported declarative Style resources,
but packages cannot register host meanings or arbitrary geometry.

The illustrative YAML shape is:

```yaml
version: chrona/style/v0.2
kind: style
id: review-treatment
body:
  rules:
    - id: behind-cell
      when: {purpose: table-cell, columnSource: {comparisonFacet: finishDelta}, comparisonCategory: behind}
      then: {role: variance-behind}
    - id: payload-risk
      when:
        purpose: planned
        fields: [{source: {fieldRole: responsible}, equals: payload}]
      then:
        encode:
          channel: fill
          source: {field: risk}
          scale: risk
          domain: [low, high]
          legend: {title: 'Risk — payload team'}
```

This is a design example, not an accepted schema instance. Initial selector
keys are exactly `semantic`, `purpose`, `comparisonCategory`, `columnSource`,
`roles`, and `fields`, with these initial use cases and focused test subjects:

| Selector | Existing meaning or author use case |
| --- | --- |
| `semantic` | Target `forecast` separately from `planned` while retaining their existing shared Theme role. |
| `purpose` | Apply a treatment to planned marks across admitted span/point semantics. |
| `comparisonCategory` | Treat behind/on-track/ahead table occurrences as the current variance bindings do. |
| `columnSource` | Limit the variance treatment to `finishDelta` cells, as the example above does. |
| `roles` | Select the original scheduling-derived critical fact without reading a Theme name. |
| `fields` | Scope a risk encoding to the responsible payload team through the existing field-role alias. |

Defer `facet`, `sourceType`, and `relationKind` until named use cases are
approved. Predicates are intersection-only. `roles` reads only original View
Projection facts, never a Theme name or another rule's output. `fields` use the
existing typed source accessor. Missing optional facts do not match; unknown
selectors, undeclared fields/roles, wrong scalar types and incompatible targets
are pointed closure errors. No expression language, path traversal, arbitrary
negation, callbacks, coordinates, time, or numeric ordering is introduced.

Each rule has a unique ID and exactly one role or encoding outcome. The first
encoding channel is `fill` only. Its targets are admitted fillable semantic
families (planned/actual/snapshot member marks and table cells); a stroke-only
relation is not a fill target. Another channel requires its own reviewed
contract. Existing
Spec60 domain ordering, palette folding, separability and Theme scale-to-Scheme
mapping are reused. Existing View `colorEncoding` stays accepted and lowers to
the same typed intent as Style; there is no second evaluator and no retirement
or incompatible migration of the existing syntax. A matching encoding with a
missing source value retains Spec60's explicit refusal. Role assignment selects
the baseline Theme treatment; an encoding overrides only its named channel,
as existing View `colorEncoding` already does. Role and fill are independent
assignment axes; conflicting assignments on one axis fail with both rule IDs
and occurrence identity.
Identical assignments coalesce with all matched rule IDs retained. Different
role assignments or different encodings of the same channel fail; input order
does not select a winner. No match retains existing semantic paint; there is no implicit catch-all or
specificity/last-wins precedence.

View owns occurrence selection, stable object/relation/column identity and
immutable facts. Style evaluates those facts into occurrence-keyed role/encoding
intent and matched-rule IDs. Theme/Scheme completes paint and typed typography/
mark attributes before Layout measurement and placement. Scene emits completed
geometry and paint relations; adapters do not interpret raw fields or authored
rules. Text/stroke changes therefore enter Layout before fit/routing.
Issue344's typed Project fields use this same field accessor: schema validates
namespaced ID/type/allowed values, View projects the field on its source
occurrence, and Style refers to it through `source: {field: ...}`. Do not add a
profile-specific lookup path. `fieldRole` remains a Project-owned alias into
that accessor, not a second evaluator. Until that field support exists, only fields
admitted by the live Project contract are usable. Multi-source comparisons
retain source identity; absence is distinct from null or invalid value.

## Scoped legends, diagnostics and coverage

Derived scale entries come from values actually painted after rule matching and
conflict resolution, in domain order. Identity includes Style/rule/scale/scope
and value. A non-global rule requires an authored non-empty legend title; the
canonical normalized selector is available beside swatches in Scene and
provenance. A visible qualifier derived from that selector is an opt-in legend
member, not mandatory output. If the optional qualifier cannot be rendered,
that alone does not refuse the encoding. A scoped key must not be described as
global. Scope identity is the canonical normalized `when` JSON under pinned
Style/rule identity, not title text or current match count. Rules with no
realized matches produce no misleading scale entry. Global means the rule uses
only `purpose` and/or `semantic`; any additional fact selector is scoped even
when all current occurrences match. Swatches use the completed paint, including
palette-folded Other. Semantic legend keys remain
separate.

Failure diagnostics distinguish invalid vocabulary/rules, unknown facts,
conflicts, incompatible role/target and missing required legend title, and carry
resource pointer, rule IDs and subject identity. Existing scale errors remain
Spec60 errors. Successful provenance reports matched rules without warning on
intentional non-matches.

Coverage is derived from vocabulary plus committed Scene outputs, not a curated
source list. Every registered purpose requires a classification, even if not
currently drawn. Report drawn-purpose realized role counts and slides, model
state cardinality separately, realized state/role pairs, intentional
equivalences or gaps, and unpainted purposes. The Issue433 numerator is the
number of distinct drawn purposes with exactly one realized visual role; its
denominator is all distinct purposes actually drawn. Registered-but-unpainted
purposes remain separate rows, not zero-role denominator entries. The current
117-entry inventory and 31/40 historical figure are baseline evidence only;
the generated checked report supplies the successor measurement.

## RC, ownership and release conditions

RC promises versioned resource envelope/identity, vocabulary semantic IDs,
purposes, Theme-role names and existing `colorEncoding`. Style v0.2 is an RC
promise only if V1, S1 and S2 land before the RC trial; otherwise it remains
experimental. V1 must precede RC. Dev A owns V1/S1/S2. Dev B owns Issue344
Level 1 and may begin C1 independently whenever that work is parked or done:
V1 preserves the registry's Python read APIs. Any necessary signature change
must update C1 callers atomically. Both lanes use the same field accessor.
S2 may mechanically update example resource references, pins and renamed
members, listing them in its PR count table; changes to what a slide shows
remain reviewer-owned ([owner clarification](https://github.com/tya5/chrona/issues/419#issuecomment-6235010287)).
Python types, factory grouping, cache representation, inventory order
and physical packaging are internal. Focused neutral tests, public materializer
evidence and the release CI gate are required at each implementation boundary.

## Prior-art lessons

[Vega-Lite conditions](https://vega.github.io/vega-lite/docs/condition.html)
separate predicates from field/value encodings; retain that separation, not an
expression language. Its [legends](https://vega.github.io/vega-lite/docs/legend.html)
follow resolved scales; Chrona additionally records predicate scope and requires
an authored title for a scoped key.
[DTCG format](https://www.designtokens.org/tr/2025.10/format/) contributes typed
values and explicit references/errors, not semantic inference from folders or a
reason to mix Theme values with View facts.

## V1 implementation plan

Baseline: the117 bindings inspected on the reviewed design base remain the
same on current main. The amendment `ae75ab664` merged in PR1664 as `d0df1e8aa`
before product implementation. Reconcile the next
code PR with the latest trusted-ready main after PR1661. This plan is
published separately before code, without creating another design authority.

- **Resource/schema:** one wheel-owned `semantic-vocabulary.yaml`, version
  `chrona/semantic-vocabulary/v0.1`, kind `semantic-vocabulary`, id `chrona-core`.
  Ordered `body.bindings` records carry exactly `semanticId`, `primitiveFamily`,
  `purpose`, `sceneRole`, `themeRole`, `contrastClass` (nullable). Preserve all117
  values and order; classification metadata belongs to C1, not V1. The new
  schema reuses the presentation envelope and existing shared definitions where
  applicable; register its lifecycle in the schema inventory without modifying
  frozen shared parts. No runtime Python copy of the records remains.
- **Loader/registry:** resource location and validation in `chrona.resources`,
  immutable cached records consumed by `model/semantic_registry.py`. Retain
  existing internal lookup/family helpers, enum meaning and contrast dispatch;
  derived indexes are not a second authority. A test-only frozen baseline
  proves every old value/order, rather than generating its expectation from
  the new resource under test.
  Architecture boundary: `chrona.resources` must not import
  `chrona.schema_diagnostics`, which already depends on resource loading.
  Bootstrap resource errors carry the validator's native message and JSON
  pointer; rich authored-ingress explanation remains in the existing contract
  boundary. The schema still owns structural validation. Import-direction and
  focused diagnostic tests must pass before accepting the loader.
- **Identity/closure:** one typed `SemanticVocabularyContract`, registered in
  `contracts/resources.py` and exported through `contracts/__init__.py`.
  Normal and Draft closure append the same validated wheel-owned resource;
  Scene provenance records kind/id/version-revision/content identity. Identity
  is SHA-256 of loaded resource bytes, as for existing untransformed resources
  (Spec13), not a hash of a differently serialized mapping. The resource is
  host-owned, not an authored Context override, implicit directory scan or
  package registration hook. Existing Contexts need no syntax migration.
- **Failures:** reject absent bytes, wrong envelope id/kind/version, malformed
  fields/enums, duplicate semantic IDs before map construction, and mismatched
  expected content identity. Retain existing version/schema/closure identity
  diagnostics at their normal boundaries. Resource-load failure uses
  `E_SEMANTIC_VOCABULARY_RESOURCE`; duplicate ID uses
  `E_SEMANTIC_VOCABULARY_DUPLICATE_ID` at its binding's `semanticId` pointer.
  No fallback to a Python table or partially loaded registry is allowed.
- **Tests/evidence:** schema/loader negatives;117-value and accessor equality;
  all fields' existing consumers; immutable/mutable-input isolation; normal and
  Draft closure identity; source/wheel resource equality; Scene schema and
  vocabulary reachability; focused Layout/Scene/contrast regressions. Official
  materializers must retain paths and primitive/purpose/role counts and SVG
  visual bytes. Scene resource-provenance additions are intended, counted
  separately from geometry/paint changes. Do not edit bot-owned public outputs.
  Refresh affected `tests/fixtures` mirrors with the standard materializer and
  exact synthetic Scene characterizations for the intentional provenance delta;
  SVG bytes and every non-provenance Scene fact must remain unchanged.
- **Publication:** one V1 code PR contains resource, schema, loader, closure,
  tests and implemented Spec13/49/56 updates, followed by its concise slice
  acceptance evidence. Reviewer reviews the PR/count table; exact-head CI and
  exact-main three-OS release precede slice acceptance. Parent419 remains open
  for S1/S2 and dev B's C1. Any discovered contract gap returns to this record
  and architecture review before code resumes.

Current verification, artifact counts, CI findings and release status are
recorded once in the [literal acceptance review](../../reviews/current/issue-419-semantic-resource-acceptance-review-2026-10-17.md).

## S1 implementation contract and architecture review

S1 keeps the approved six selectors and independent role/fill outcomes; it
does not add a predicate language or project declarations. The source example
above now uses the exact View column source, not an ambiguous shorthand.
`columnSource` accepts the shared View source shape; source mappings compare
canonically, not by displayed text. `roles` requires all named original roles.
`fields` requires all equality predicates; booleans do not equal numeric1.

Use one frozen occurrence key carrying row/member, object, source kind, semantic
facet and optional column identity. Evaluation reads immutable original facts
only. Equal assignments coalesce while retaining every matched rule ID;
different roles or different encodings on the same channel are errors, even if
their concrete colours happen to agree. Rule order is not precedence. Encoding
identity includes resolved field, scale and domain, not legend display copy.

The shared field accessor must retain presence separately from value and carry
the source profile's field descriptor. Style `when.fields` names must have a
profile-v0.3 declaration; legacy opaque fields remain usable by existing View
`colorEncoding` and by its equivalent encoding outcome. Both use the same
accessor/encoding path, not a compatibility evaluator. Optional absence does
not match; explicit null stays present. Project/profile validation, including
null validity, belongs to Issue344's validator, not Style. Predicate literals
must match the declared scalar/cardinality/enum contract without coercion.
Resolve each snapshot's own pinned packages; scenarios retain primary package
identity and validate after overlays. Do not infer declarations from values or
invent profile inheritance in presentation code.

Source-scoped package identity correction: Spec13 §5.1 currently rejects any
duplicate `(kind, id)` with different identities, which conflicts with primary
and snapshot Projects pinning different revisions of the same package. Amend
that rule with the immutable-closure implementation: profile-package resources
may coexist at distinct full identities only when explicitly pinned by distinct
source Projects. Validate every declared Store reference before deduplication;
deduplicate equal full identities, never merely package IDs. Each source resolves
its own extension reference and packageId; an ambiguous or missing match is an
existing closure identity/required error. Within one source, conflicting package
declarations remain invalid. Other resource duplicate rules are unchanged.
This keeps identity resolution in closure and definition interpretation in
the extension owner; Style receives neither a global package-id merge nor
unverified declarations. Verify the rule through real contract ingress, not
only mocked collector tests. Publish this correction before accepting the
snapshot closure implementation; no new Scene resource kind is needed.

Retain Scene `visualRole` as the canonical semantic/host role: changing it
would alter host, pattern and contrast classification. Add optional paired
`semanticId` and `themeRole` on Style-treated primitives in live Scene v0.7.
The former joins the pinned host vocabulary; the latter records selected
appearance. Derive contrast class from that vocabulary, never a duplicated
Scene class or the arbitrary Theme role. Preserve purpose and all structural
Scene behavior. Scene replay validates the vocabulary identity before semantic
lookups; adapters still need only completed paint and geometry. Coverage counts
the effective appearance role (`themeRole` when present, otherwise `visualRole`)
while retaining canonical semantics; coordinate this input with dev B C1.

Complete selected typography, mark/symbol geometry and stroke extents before
Layout fitting, obstacles and routes. Propagate evaluated intent through
`SurfaceContentInput` into marks, table cells and labels, including fixed lanes
and folded hosts; completed placements retain the selected Theme role. Do not
mutate the global registry or replace roles only after geometry is complete.
No Style means no new primitive metadata and unchanged prior behavior.

S1c composition detail: retain the source container kind in occurrence keys,
so an ordinary row and a folded group cannot alias. Fixed-lane final aliases
reuse their original source row/member key through the existing lane-owner
join; generated placement IDs are not parsed. Table cells retain the actual
subject item key and the exact immutable View column source before measurement.
Store evaluated intents in one immutable index on `SurfaceContentInput`.
Resolve each occurrence's selected mark roles into its own canonical-role
frame and recompute the existing mark-stack allocation there; never merge
different occurrences into one global role override. Provisional footprints
and final composition consume the same index. Extract shared mark-role
geometry from the surface owner to avoid a composition/import cycle.
For an explicitly selected role, required geometry/text bindings and a point
symbol must exist on that role; incompatible treatment is the planned
`E_STYLE_ROLE_INCOMPATIBLE`, not implicit inheritance from the old role.
Unstyled marks keep their existing variant-symbol and alignment fallbacks.
This is internal identity/composition, not a schema or scheduling change;
Spec38 View membership, Spec49 canonical semantics and passive Scene ownership
remain unchanged. Publish this detail before its implementation.

Canonical mark correction: logical temporal facets and realized vocabulary
bindings are not interchangeable. Existing primary points use `gate` when the
base Theme declares it; forecast points retain `forecast`, and comparison
points retain their existing binding. Derive the Style semantic from that
existing host-binding rule before evaluation, independently of the selected
Style role. Preserve logical facet names and stable placement IDs. Use one
shared model helper for this canonical binding; Layout joins its exact intent
back to the logical geometry role, and Scene records the same binding rather
than reinterpreting the selected role. Thus `semantic: gate` can target an
existing gate, while legacy `target: planned` still excludes it. No new Theme
predicate or point-target syntax is admitted. Review against Spec07/49/60:
this moves the existing canonical host decision out of Scene, preserves
unstyled paint/geometry and keeps Style separate from scheduling and fitting.
Before Scene production is accepted, test point/span/forecast/comparison
bindings with and without the existing gate declaration, exact Style identity,
and unchanged unstyled output. Other S1c identity/frame work remains reusable.

Theme capability correction: the live Theme schema already admits arbitrary
role names and mark/symbol properties, and the generic token readers consume
them, but the capability projection rejects their combination. Admit the
bounded mark-geometry and `symbol` properties through a named Style-selected
mark consumer for ordinary authored role names and existing Rect/Symbol role
contracts. Reuse one property-family definition with the canonical mark
registrations, not a second name table or a validator bypass. Keep reserved
generated namespaces and specialized fill-only state contracts unchanged;
unknown properties and unsupported catalogue-pattern applicability still fail.
Assignment completion still requires the exact bindings used by its canonical
primitive family and returns `E_STYLE_ROLE_INCOMPATIBLE` when incomplete.
Review against Spec07/49/56 and the existing consumer gate: no schema or new
syntax is needed; this connects already admitted data to implemented generic
consumers without weakening scheduling, canonical Scene kinds or contrast.
Verify real custom-role Theme ingress and the neutral YAML→Style→Layout path,
not only manually assembled token views; retain the unrelated rejection tests.

Architecture review: this implements Spec07/49's Style→Theme→Layout boundary,
uses Spec13 resource closure, preserves Spec04 scheduling and Spec08/46 passive
Scene/adapters, and shares Issue344's declarations/accessor. Update normative
Spec06/07/08/46/49/60 with implementation; replace the historical v0.1
source-order Style rule rather than retaining two live evaluators. Additive
optional Scene fields leave v0.6 frozen and follow Spec56's widening rule.

## S1 implementation plan

| Unit / owned files | Focused acceptance and publication |
| --- | --- |
| S1a: `schemas/style-v0.2.schema.yaml`, shared `common` definitions and schema inventory; contracts and new model evaluator | Six selectors, exact column sources, intersection, original facts, independent role/fill outcomes, deterministic conflict/coalescing, source identities, immutable inputs; parser negatives and schema equivalence. Publish contract/model before integrating owners. |
| S1b: shared field accessor, projection and render orchestration | Reuse the resolved descriptor authority from Issue344 after its overlapping PR lands. Test declared/opaque fields, aliases per source, absent/null, literal types, snapshot pins and scenarios. No second field engine. |
| S1c: content, `surface_marks`/`mark_geometry`, lane footprint/label owners, table/text placements | Selected role affects actual geometry/measurement before routing; test custom mark height/stroke and text size in ordinary, lane and folded cases. Scene receives completed roles/paint. |
| S1d: Scene model/serialization/contrast and effective-role report handoff | Paired metadata round-trip, pinned vocabulary and wrong-purpose/identity negatives; arbitrary role cannot erase contrast or host semantics. SVG/PDF serialize the same completed output. Coordinate report lookup with dev B. |
| S1 gate: existing literal review plus one code PR | Neutral unseen field combination demonstrates a new authored distinction. Run focused and structural tests, schema equivalence, batched official SVG/Scene counts, actual PNG inspection, reviewer review and exact-main three-OS release. Parent remains open for S2/C1. |

Pointed failures: existing structural/version and Spec60 scale diagnostics,
plus `E_STYLE_RULE_ID_DUPLICATE`, `E_STYLE_FACT_UNKNOWN`, `E_STYLE_FACT_TYPE`,
`E_STYLE_RULE_CONFLICT`, `E_STYLE_ROLE_INCOMPATIBLE`, `E_STYLE_TARGET` and
`E_STYLE_LEGEND_TITLE_REQUIRED`. Include resource pointer, rule IDs and subject
identity where established. Scoped encodings require their authored title at
admission; S2 composes scope provenance and optional visible qualifier.
S1a–d are coherent commits in one S1 PR, not four main synchronization cycles.
The S1 contract/architecture review is published as `9a9063ca5`; publish this
implementation plan before S1 product changes. S2 remains the subsequent
closure/preset/legend slice. Scalar equality introduces no array-membership
or resource-reference predicates; other field consumers retain their contracts.

S1a verification: typed ingress, immutable values and pure occurrence evaluation
are implemented; full Style-to-Layout orchestration remains incomplete. The focused
contract/model/schema-accounting batch passes187 tests, including quoted and
unquoted YAML date normalization through the existing ingress helper. Schema equivalence
passes with2 added schemas,39 unchanged,578 documents/468 mapped,5 previously
invalid documents and739 probes; L2+L3 takes15.4s. The added Style conformance
fixture covers the new resource kind. Schema inventory, annotations/references,
and inward imports pass. No rendered-output or full S1 acceptance is claimed.

S1b integration: `FieldRoleBindings.read_result()` is the shared presence-aware
lookup; `read()` remains its value-returning convenience. Observed scale values
now consume that same accessor, retaining order and existing null omission.
Profile descriptor extraction waits for dev B's overlapping344 PR; no duplicate
definition merge is introduced. Immutable and Draft closure retain source
Project/extension-index edges to the exact verified package identity; snapshots
resolve their own pins even across Stores sharing an ID/revision token.
Snapshot and scenario validation uses the proper source definitions before
scheduling. The focused Draft/app/closure/accessor batch passes280 tests;
real CLI/MCP provider tests pass15 (overlap), including provenance, containment
and hash rejection. No Project-relative Store fallback is implemented.

S1c integration in progress: existing View colour encoding now lowers to the
shared evaluator before source paint completion. Canonical Scene-role selectors
retain planned/forecast eligibility without admitting gates by shared purpose;
scale domain, order and diagnostics remain owned by the existing resolver.
The mark geometry resolver accepts selected Theme roles while preserving
canonical geometry keys and planned/actual symbol fallback. Occurrence-frame,
preflight, typography and Scene-producer connections are not yet complete.
The focused evaluator/content/geometry and legacy encoding batch passes151
tests; module reachability (283 modules) and inward imports pass without an
allowlist. Generic Draft integration tests now provide an explicit temporary
Store containing the exact declared package bytes rather than bypass closure.
The remaining Draft test callers share that Store fixture without changing
Project pins. Focused migration batches pass147 preset/default tests,11 surface
wiring tests,21 cache/CLI checks (overlap), and41 render-library tests; the cache
key includes package bytes. Corpus-marked tests remain for planned CI gates.

Draft provider design and implementation amendment: inject the existing
`SnapshotReader` port into explicit/guided Draft ingress and `DraftRenderRequest`.
Local Project bytes stay Draft; referenced packages are read from their named
immutable Stores through the same closure loader and source edges as Context
rendering. CLI `render`/`render-workspace` expose optional `--store-config`;
their outer adapter may use the existing project-local Store-config discovery,
never source-file address fallback. A package-provider reference uses the
existing packaged reader. Library callers supply their reader; an unresolved
declared package fails with the established Store-config/closure diagnostic,
not an empty definition catalogue. No declarations means unchanged rendering.
Migration: Draft renders that previously ignored declared extensions must now
provide a resolvable Store configuration/reader; supplied identities and Store
integrity are always enforced. Do not invent a new local package declaration.
Agent tools retain workspace access boundaries: inject only their existing
authorized reader, never discover or open a Store outside the allowed scope.
`render_draft` accepts the existing optional `storeConfig` argument shape used
by Store tools, defaulting to workspace `.chrona/store.yaml`; use the same
contained-Store opener before reading any non-package reference.

Architecture review: Spec13 owns reference closure; Spec15 keeps mutable Draft
separate from immutable evaluation; extension validation remains in Issue344.
Presentation receives only the core reader port, with provider/config selection
in outer adapters; no presentation→operational/storage import is introduced.
Implement in one S1b unit: closure resolvers and source edges; shared request
port; operational reader reuse and CLI/agent adapter wiring; Spec13/15 and CLI
reference evidence. Test declared/undeclared packages, cross-store snapshot
pins, package provider, absent config, hash mismatch, required identity and
workspace boundary refusal, plus unchanged no-extension output. Publish this
amendment before provider code; it is published at `dd793d584`/`f8cbc5672`.
Retain the same eventual S1 PR.

S1d carrier verification: paired Scene metadata, canonical host identity and
pinned-vocabulary replay checks pass14 focused cases, including unchanged
no-Style bytes and retained mark contrast under an arbitrary appearance role.
Scene delivery has247 owned fields; schema/inward-import gates pass. Schema
equivalence passes2 added schemas and1 reviewed optional Scene widening,
578 documents/468 mapped,5 known invalid and739 probes (L2+L3 14.6s).
Completed Layout production, role compatibility and the actual evaluator
consumer remain required. Module reachability currently rejects the unconnected
evaluator; do not add an allowlist or treat partial carrier tests as S1 acceptance.

## V1 equivalence inventory (117-entry baseline)

This inventory groups entries by the mechanism families in
`presentation/model/semantic_registry.py`, not by primitive kind. Counts by
kind are 9 marks, 13 lines, 39 decorations, 54 labels, and 2 icons. The
contrast totals are 39 unclassified, 38 `GROUND_TEXT`, 22 `DECORATION`, 9
`MARK`, and 9 `STATE_TEXT`. `—` means no contrast class is declared.

The fields are consumed as follows: `semantic_id` is the closed lookup key for
`semantic_binding()` and family helpers; `primitive_kind` constrains Scene
primitive compatibility and lane-purpose validation; `purpose` is carried
into Scene/serialization and used in validation and contrast resolution;
`scene_role` is the completed paint role used by Scene construction and
contrast classification; `theme_role` selects the Theme paint/typography
role in Layout/Scene resolution; `contrast` is optional policy input used by
Scene validation and `scene/contrast_policy.py`. The principal consumer is
`scene/v05_builder.py`; additional consumers include `scene/model.py`,
`scene/pattern_host.py`, `scene/contrast_policy.py`, Layout's lane/axis/legend/
background/label modules, and resource/Theme resolution. These are current
code facts, not a proposed resource contract.

Each row is `semantic | kind | purpose | Scene role | Theme role | contrast`.

### Comparison marks and icons

| Semantic | Kind | Purpose | Scene role | Theme role | Contrast |
|---|---|---|---|---|---|
| planned | mark | planned | planned | planned | MARK |
| forecast | mark | forecast | planned | planned | — |
| actual | mark | actual | actual | actual | MARK |
| snapshot | mark | snapshot | snapshot | snapshot | MARK |
| gate | mark | planned | gate | gate | MARK |
| missingActual | mark | missingActual | missing-actual | missing-actual | MARK |
| summaryBar | mark | summary-bar | summary-bar | summaryBar | MARK |
| progressFill | mark | progress-fill | progress-fill | progressFill | MARK |
| iconMark | icon | icon-mark | icon-mark | icon-mark | — |
| labelVisual | icon | label-visual | text | text | — |

### Time, deadline, calendar, period, and canvas

| Semantic | Kind | Purpose | Scene role | Theme role | Contrast |
|---|---|---|---|---|---|
| asOf | line | as-of | as-of | asOf | — |
| asOfLabel | label | as-of-label | text | text | GROUND_TEXT |
| asOfCone | decoration | as-of-cone | as-of-cone | as-of-cone | — |
| deadlineMark | line | deadline-mark | deadline-mark | deadline-mark | MARK |
| deadlineMarkOutline | decoration | deadline-outline | deadline-mark-outline | background | — |
| deadlineCaption | label | deadline-caption | text | text | GROUND_TEXT |
| asOfLabelChip | decoration | label-chip | as-of-label-chip | as-of-label-chip | — |
| calendarClosed | decoration | calendar-closed | calendar-closed | calendarClosed | DECORATION |
| calendarException | decoration | calendar-exception | calendar-exception | calendarException | DECORATION |
| periodBand | decoration | period-band | period-band | period-band | DECORATION |
| periodLabel | label | period-label | period-label | period-label | STATE_TEXT |
| periodLabelChip | decoration | label-chip | period-label-chip | period-label-chip | — |
| canvasTexture | decoration | canvas-texture | canvas-texture | canvas-texture | — |
| canvasOverlay | decoration | canvas-overlay | canvas-overlay | canvas-overlay | — |
| canvasOverlayGradient | decoration | canvas-overlay-gradient | canvas-overlay-gradient | canvas-overlay-gradient | — |
| regionFrame | decoration | region-frame | region-frame | region-frame | — |
| frameGlyph | decoration | frame-glyph | frame-glyph | frame-glyph | — |

### Axis bands, labels, and rules

| Semantic | Kind | Purpose | Scene role | Theme role | Contrast |
|---|---|---|---|---|---|
| axisBand | label | axis-band | axis-band | axis | GROUND_TEXT |
| axisBandDecoration | decoration | axis-band | axis-band-decoration | axis-band-decoration | DECORATION |
| axisBandDecoration2 | decoration | axis-band | axis-band-decoration2 | axis-band-decoration2 | DECORATION |
| axisLabel | label | axis-label | text | axis | GROUND_TEXT |
| axisLabel2 | label | axis-label | axis-label2 | axis2 | GROUND_TEXT |
| axisLabel3 | label | axis-label | axis-label3 | axis3 | GROUND_TEXT |
| axisGrid | line | axis-grid | axis-major | axis-major | — |
| axisGridMinor | line | axis-grid | axis-minor | axis-minor | — |
| axisRule | line | axis-rule | axis-rule | axis-rule | — |
| axisCellSeparator | line | axis-cell-separator | axis-cell-separator | axis-cell-separator | — |

### Grouping, rows, observations, and table

| Semantic | Kind | Purpose | Scene role | Theme role | Contrast |
|---|---|---|---|---|---|
| groupBand | decoration | group-decoration | group-band | group-band | DECORATION |
| rowBand | decoration | row-decoration | row-band | row-band | DECORATION |
| rowRule | decoration | row-rule | row-rule | row-rule | DECORATION |
| tableColumnRule | decoration | table-column-rule | tableColumnRule | tableColumnRule | DECORATION |
| groupHeaderBand | decoration | group-header-band | group-header-band | group-header-band | DECORATION |
| groupHeaderStrip | decoration | group-header-strip | group-header-strip | group-header-strip | DECORATION |
| groupTab | decoration | group-tab | group-tab | group-tab | DECORATION |
| groupHeader | decoration | group-header | group-header | groupHeader | GROUND_TEXT |
| groupDetail | label | group-detail | text | text | GROUND_TEXT |
| observationSource | label | observation-source | text | text | GROUND_TEXT |
| observationColumnLabel | label | observation-column-label | text | text | GROUND_TEXT |
| observationCell | label | observation-cell | text | text | GROUND_TEXT |
| observationAttentionCell | label | observation-cell | variance-ahead | variance-ahead | — |
| observationCriticalCell | label | observation-cell | variance-behind | variance-behind | — |
| titleText | label | title-text | heading | heading | GROUND_TEXT |
| kickerText | label | kicker-text | kicker | kicker | GROUND_TEXT |
| subtitleText | label | subtitle-text | subtitle | subtitle | GROUND_TEXT |
| slotHeading | label | slot-heading | slot-heading | slot-heading | GROUND_TEXT |
| tableColumnLabel | label | table-column-label | text | text | GROUND_TEXT |
| tableCell | label | table-cell | text | text | GROUND_TEXT |
| tableVarianceAhead | label | table-cell | variance-ahead | variance-ahead | STATE_TEXT |
| tableVarianceOnTrack | label | table-cell | variance-on-track | variance-on-track | STATE_TEXT |
| tableVarianceBehind | label | table-cell | variance-behind | variance-behind | STATE_TEXT |
| missingActualCell | label | table-cell | missing-actual-cell | missing-actual-cell | STATE_TEXT |

### Plot member labels and finish deltas

| Semantic | Kind | Purpose | Scene role | Theme role | Contrast |
|---|---|---|---|---|---|
| memberLabel | label | member-label | text | text | GROUND_TEXT |
| memberLabelInsidePlanned | label | member-label | member-label-inside-planned | member-label-inside-planned | GROUND_TEXT |
| memberLabelInsideActual | label | member-label | member-label-inside-actual | member-label-inside-actual | GROUND_TEXT |
| memberLabelInsideSnapshot | label | member-label | member-label-inside-snapshot | member-label-inside-snapshot | GROUND_TEXT |
| memberLabelInsideScenario | label | member-label | member-label-inside-scenario | member-label-inside-scenario | GROUND_TEXT |
| memberLabelChip | decoration | label-chip | member-label-chip | member-label-chip | — |
| finishDelta | label | finish-delta | variance-on-track | variance-on-track | — |
| varianceAhead | label | finish-delta | variance-ahead | variance-ahead | — |
| varianceBehind | label | finish-delta | variance-behind | variance-behind | — |
| forecastFinishDelta | label | forecast-finish-delta | variance-on-track | variance-on-track | — |
| forecastVarianceAhead | label | forecast-finish-delta | variance-ahead | variance-ahead | — |
| forecastVarianceBehind | label | forecast-finish-delta | variance-behind | variance-behind | — |
| finishDeltaChip | decoration | label-chip | finish-delta-chip | finish-delta-chip | — |
| milestoneDigestEntry | label | milestone-digest-entry | text | text | GROUND_TEXT |

### Relations and network

| Semantic | Kind | Purpose | Scene role | Theme role | Contrast |
|---|---|---|---|---|---|
| dependency | line | dependency | dependency | dependency | — |
| dependencyHalo | decoration | dependency-halo | dependency-halo | dependency-halo | DECORATION |
| dependency-critical | line | dependency | dependency-critical | dependency-critical | — |
| relationLabel | label | relation-label | text | annotation | GROUND_TEXT |
| networkNode | mark | network-node | network-node | network-node | MARK |
| networkLabel | label | title-text | text | text | GROUND_TEXT |
| networkEdge | line | network-edge | network-edge | network-edge | — |
| criticalEdge | line | critical-edge | critical-edge | critical-edge | — |

### Legend, notes, and annotations

| Semantic | Kind | Purpose | Scene role | Theme role | Contrast |
|---|---|---|---|---|---|
| legendEntry | decoration | legend-swatch | legend-swatch | legend-swatch | — |
| scaleLegendEntry | decoration | legend-swatch | planned | planned | — |
| legendLabel | label | legend-label | text | legend | GROUND_TEXT |
| projectNote | label | project-note | text | annotation | GROUND_TEXT |
| annotationListText | label | annotation-list-text | text | annotation | GROUND_TEXT |
| noteIndex | label | note-index | note-index | note-index | GROUND_TEXT |
| annotationCalloutBox | decoration | annotation-box | annotation-callout-box | annotation-callout-box | — |
| annotationCalloutText | label | annotation-text | annotation-callout-text | annotation-callout-text | GROUND_TEXT |
| annotationCalloutLeader | line | annotation-leader | annotation-callout-leader | annotation-callout-leader | — |
| annotationHighlightBox | decoration | annotation-box | annotation-highlight-box | annotation-highlight-box | — |
| annotationHighlightText | label | annotation-text | annotation-highlight-text | annotation-highlight-text | GROUND_TEXT |
| annotationNoteBox | decoration | annotation-box | annotation-note-box | annotation-note-box | DECORATION |
| annotationNoteText | label | annotation-text | annotation-note-text | annotation-note-text | STATE_TEXT |
| annotationNoteLeader | line | annotation-leader | annotation-note-leader | annotation-note-leader | — |
| annotationArrowBox | decoration | annotation-box | annotation-arrow-box | annotation-arrow-box | — |
| annotationArrowText | label | annotation-text | annotation-arrow-text | annotation-arrow-text | GROUND_TEXT |
| annotationArrowLeader | line | annotation-leader | annotation-arrow-leader | annotation-arrow-leader | — |
| annotationKindBar | decoration | annotation-kind-bar | annotation-kind-bar | annotation-kind-bar | DECORATION |
| annotationKindAccent | decoration | annotation-kind-accent | annotation-kind-accent | annotation-kind-accent | DECORATION |
| annotationKindStamp | decoration | annotation-kind-stamp | annotation-kind-stamp | annotation-kind-stamp | DECORATION |
| annotationArtwork | decoration | annotation-artwork | annotation-artwork | annotation-artwork | DECORATION |
| annotationBorderStart | decoration | annotation-border-start | annotation-border-start | annotation-border-start | DECORATION |
| annotationBorderEnd | decoration | annotation-border-end | annotation-border-end | annotation-border-end | DECORATION |
| annotationBorderTop | decoration | annotation-border-top | annotation-border-top | annotation-border-top | DECORATION |
| annotationBorderBottom | decoration | annotation-border-bottom | annotation-border-bottom | annotation-border-bottom | DECORATION |
| annotationKindLabel | label | annotation-kind-label | annotation-kind-label | annotation-kind-label | STATE_TEXT |
| annotationKindSecondary | label | annotation-kind-secondary | annotation-kind-secondary | annotation-kind-secondary | STATE_TEXT |
| annotationHeading | label | annotation-heading | annotation-heading | annotation-heading | STATE_TEXT |

### Summary panels

| Semantic | Kind | Purpose | Scene role | Theme role | Contrast |
|---|---|---|---|---|---|
| summaryHeader | label | summary-header | text | summary | GROUND_TEXT |
| summaryMetric | label | summary-metric | text | summary | GROUND_TEXT |
| summaryFigureValue | label | summary-figure-value | metric | metric | GROUND_TEXT |
| summaryFigureCaption | label | summary-figure-caption | subtitle | subtitle | GROUND_TEXT |
| summaryCaption | label | summary-caption | summary-caption | summary-caption | GROUND_TEXT |
| summaryUnit | label | summary-unit | summary-unit | summary-unit | GROUND_TEXT |
