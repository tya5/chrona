# Thin-connector design reuse completion (#1341, #1344)

Published code baseline: READY2347aed5; #1300 is closed after its containing
three-OS release38339181830 succeeded. Adopt the current READY main before product publication. No
previous-session local work is assumed.

Authority: [approved classification6100250980](https://github.com/tya5/chrona/issues/1341#issuecomment-6100250980),
[sign-off6105511858](https://github.com/tya5/chrona/issues/1341#issuecomment-6105511858),
[1344 narrowed scope6097145885](https://github.com/tya5/chrona/issues/1344#issuecomment-6097145885),
Specs06/07/13/33/44/46/56. Slice1 is published through1422; slice3 policy is
covered by1343. Neither is whole-issue acceptance.

## Literal acceptance

| Requirement | Required evidence |
| --- | --- |
| Target B and the four other approved designs reproduce byte-identically on HALCYON, with Theme/Layout/profiles containing no HALCYON id or wording, and with Views containing connection members only. | Actual five-design migration/byte comparison and mechanical purity audit, not synthetic-only evidence. Preserve truthful resource provenance; resolve the identity question before claiming exact Scene bytes. |
| `examples/chrona-roadmap` renders each design by writing only its own thin View and Context. | Actual five-design roadmap renders using shared resources, without copied design declarations. |
| HALCYON is unchanged once its period declares the role. | Original1344 wording; owner6097145885 replaces role selection with explicit View bindings. Preserve the original wording and approved disposition in acceptance. |
| The roadmap renders the Title Card countdown against its own period. | Actual View-bound countdown on roadmap after slot migration. |
| A project without the role renders without error. | Approved1344 replacement: an unsupplied figure/period binding draws nothing with info; explicitly supplied invalid targets remain errors. |
| Do not edit `examples/**`. | Reviewer owns corpus restructuring. Use isolated/synthetic migration evidence; coordinate permanent adoption rather than silently waive public acceptance. |

## Design plan and responsibility review

View keeps project selection, fields/ids, targets and wording. Layout profile
viewDefaults owns design intent; Theme owns paint/typography; ingress closes
overrides before validation; Layout completes geometry, Scene/adapters project.
Existing explicit Views win. Add optional properties in place with shared schema
grammar; no new resource kind or hidden project-specific inference.

| Remaining slice | Design questions, owners and evidence |
| --- | --- |
| 2: columns and presentation defaults | Named columnStyles with source-kind default selection; heading templates/dateForm; grouping presentation/header/tint and colorEncoding scale/target only. Extend contracts/view_defaults.py selectively, preserving connection neighbours and malformed-input errors. Reuse live schema fragments; test immutability, precedence, missing/unknown style pointers and real SVG equality. Audit all current View members against the approved classification, including marker form, period label placement and direct visuals, rather than presume the partial slice1 covers them. |
| 3: annotation closure | Verify1343 annotationPlacement/bindings fully cover the approved policy; reuse that owner, do not implement a second overlay. |
| 4: profile slots, bindings and wording with1344 | Complete exact slot namespaces/source unions, omission versus typo behavior, figure/period binding admission and wording precedence before code. An unbound declared slot is info/undrawn; a View binding to an undeclared profile slot is a pointed error. Reconcile published1344 WIP376454003 against current main; its info_diagnostics.py/render_review.py conflicts are real, not permission failures. |
| 5: purity and normative closure | Mechanical checker across each example and its own Project; distinguish generic design voice/placeholders from project ids/wording. Update Specs06/07/33/46/56 and shared schema/mirror evidence. Review cross-resource identity and whole architecture, not only the merge helper. |

Release questions: reviewer corpus adoption is required by the literal criteria.
Real Context/resource changes affect Scene provenance;1345's public identity
question6110612395 remains unresolved. Never normalize away or falsify identity
to satisfy byte wording. Clarify the intended migration evidence with reviewer.

Sequence: publish this plan; finalize each selected design/architecture review
and normative rule; publish file-level implementation slices; implement only
those slices. Keep optional local tuning separate. Batch public materializers
and generated diffs once per behavior boundary; focused tests locally, full
three-OS/conformance/wheel/newest-Python gates in CI. Keep each literal row open
until actual adoption and required release evidence are published.

## Slice 2 design and implementation boundary

Specification06 §9.2 owns the selected merge contract. Keep existing required
effective-View fields; ingress supplies named-style presentation before schema
validation rather than relaxing admission or using schema `default` annotations.
Do not make standalone View parsing depend on a Layout or make Scene know styles.
The current `endDisplay` and `text` column properties are presentation under the
approved general classification, not project connections; include their existing
grammar in styles. Source-kind names are the live source discriminator, not a
caption, field name, or field value. This general rule does not special-case the
three examples in the approved note.

Architecture review: Specs06/33 retain ingress ownership and original resource
identity (Spec13); Theme still owns referenced roles/scales and Layout still owns
completed geometry. Spec56 requires new shared definitions, no edits to frozen
definitions, and in-place optional additions. Shared grammar must retain local
references correctly when moved; no cross-reference to an unregistered live
resource schema. Marker/period/direct-visual closure remains a separate audited
boundary, not an implicit claim that slice1 was complete.

| Unit | Files and acceptance evidence |
| --- | --- |
| Presentation closure | `contracts/view_defaults.py`, `contracts/diagnostics.py`: pure copy/overlay plus a separate ingress reference check collecting unknown explicit styles in column order at their original pointers; do not defer this cross-resource check to the View-only parser. Preserve independent sibling findings, malformed-input errors and raw identities. Unit tests cover every source discriminator, missing optional defaults, explicit overrides, multiple unknown styles and immutability. |
| Shared schema admission | `schemas/common-v0.1.schema.yaml`, live View/Layout schemas, packaged mirrors and inventory: shared column/heading/group presentation grammar with no connection properties admitted in a style. Keep complete effective-column requirements; add optional `style`. Run schema equivalence against current main and schema/reference/conformance controls. |
| Render acceptance | `tests/integration/test_view_defaults.py` and contract tests: synthetic thin/full Views produce identical SVG and equivalent completed Scene geometry/paint/diagnostics with truthful provenance. Exercise heading whole override, grouping/color split overrides and invalid style diagnostics through actual ingress. Batch public materializers and Scene/SVG diffs in CI; no `examples/**` writes. |

Publish this design/specification boundary before those product changes. The
slice's PR includes focused results and literal issue rows still open for later
slices/adoption; full three-OS release remains required before issue closure.

Slice2 is published in PR1455, source48010710, synced READY2347aed5;
sync38343026629 succeeded and containing-main release38343299409 is live.
Exact-head38342278157 passed every check;
artifact11787143093 confirms92/92 public Scene/SVG identical,0 retirements,
diagnostic/coverage reports only. Shared-schema probes were corrected without
waiving any gate (focused407 PASS;35 snapshot conformance checks PASS).

## Array-entry closure: selected design and implementation

Spec06 §9.2 selects uniform marker/period-label/visual defaults, not id/index
matching or copying mixed arrays. Missing design fields are fillable; wrong-type
explicit fields stay errors. No occurrence is synthesized. Overflow and
side/decorative are presentation under the approved general classification.

Architecture review: ingress owns closure; project selections/order remain in
View, paint/assets in Theme and completed geometry in Layout. Scene/adapters
only project. Original identities, explicit overrides and frozen definitions
remain intact; no new resource kind or placement algorithm.

Implementation: contracts/view_defaults.py fills existing occurrences; live
View/Layout/common schemas share each property; inventory freezes four new
definitions. tests/integration/test_view_defaults.py covers marker/period/icon
actual SVG/Scene equality, no synthesis, order, identity, encoded/direct and
wrong-type controls. Shared-schema definition/subfragment probes are mandatory.
Pre-codee9f0e58a and code636b182f/139e7ead are published; focused357 PASS,
post-merge143 PASS, schema inventory/annotations/references and equivalence PASS
against READY2347aed5. Normal merges retain both branches' published history;
only overlapping plan/probe additions needed reconciliation. The stale style
admission evidence is retired. PR1456 is merged at e94ab055; exact-head
38343692342 passed every check. Artifact11787772456 independently confirms
92/92 public Scene/SVG identical,0 retirements,2 expected reports only.
Containing-main sync and three-OS release verification remain.
Batch public materializers/Scene/SVG via CI; no examples edits. Profile bindings,
purity/adoption and every unresolved literal row remain open.

## Profile connections: design, architecture review and implementation plan

Slice3 requires no duplicate implementation:1343 already closes annotation
policy/bindings. Read-only verification passed29 expansion/integration tests
and76 content tests; five-design isolated migration controls compare actual
SVG, completed primitives and diagnostics, including visible note text.

Use cases: bind a shared countdown to each project's period; bind a summary
metric to a project object; omit an unsupplied metric; replace project-specific
captions and legend labels without copying design resources. Spec06 §9.3 and
Spec46 define the selected connection/omission contract. No period-role layer,
Layout slot registry or new resource kind is needed. Existing explicit sources
remain supported. The1344 WIP is a source of reviewed tests/omission behavior,
not a whole-branch merge: its stale orchestration conflicts must be reconciled.

Architecture review: typed contracts admit author declarations; a pure profile
connection resolver at the use-case boundary checks the selected profiles and
View, then supplies effective copies before scheduling/fact resolution. Core
keeps figure arithmetic, projection keeps selected facts, Layout keeps text
measurement/geometry. Original resource identities and declaration indexes
remain unchanged; omission must not renumber inline SourceRefs. Theme/heading
missing-figure errors do not broaden implicitly. Summary scope/format checks
apply after slot binding. JSON-safe typed info avoids restricting old ids.
Specs06/13/33/44/46/56 and existing annotation/figure owners stay aligned.

| Implementation unit | Files, tests and publication boundary |
| --- | --- |
| Admission and pure connection closure | View/Summary/common schemas and inventory; contracts/resources.py; one profile-binding owner in presentation/review. Add optional View bindings/wording and Summary slot sources in place, share figure/object grammar, preserve existing figure pointers. Test undeclared/colliding slots, malformed bindings, unknown/ambiguous wording, repeated consumers, precedence and immutable identities. Shared definition/subfragment probes and schema equivalence are mandatory. |
| Render wiring and omission | usecases/render_review.py, review/v05_content.py, model/info_diagnostics.py. Wire effective View/Summary/detail copies consistently through all render-plan paths; reconcile1344 missing Summary figure behavior. Preserve original source identities after omission. Test real SVG/Scene countdown/object/legend captions, unbound/empty panels, missing explicit targets, scope/format failures, inline ids and unchanged legacy sources. |
| Acceptance publication | Update this record with focused results; one implementation PR for the connected slice, batch public materializers/Scene/SVG and diagnostic changes via CI. Verify synced exact-main three-OS release. Keep actual five-design adoption/provenance and literal whole-issue acceptance open until evidenced/disposed by the owner. |

Publish this selected design/specification boundary before changing product
code, then publish the finalized implementation plan as a separate commit.
