# Thin-connector design reuse completion (#1341, #1344)

Published code baseline: READYfb54b240. Mainaea06f4b adds the1300 release
record; its trusted gate/release is pending. Adopt the current READY main before
product publication. No previous-session local work is assumed.

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
