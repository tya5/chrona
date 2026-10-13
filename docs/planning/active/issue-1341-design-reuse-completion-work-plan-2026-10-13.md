# Thin-connector design reuse completion (#1341, #1344)

Published code baseline: READYaea06f4b; #1300's containing three-OS release is
still running. Adopt the current READY main before product publication. No
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

Slice2 implementation: presentation closure and nine new frozen shared grammar
definitions are complete locally. Focused contracts/style/render/schema/diagnostic
batch227 PASS; schema inventory, annotations, references and equivalence against
READYaea06f4b PASS. Existing accepted schema verdicts/diagnostics are preserved;
the optional column `style` admission has one explicit L1 delta. Real synthetic
SVG and completed Scene equality pass; provenance is not erased. Public snapshot
inspection and release CI remain pending; no whole-issue acceptance claim.
