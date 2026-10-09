<!-- chrona:literal-acceptance/v1 -->

# Issue 918 — diagnostic owner acceptance

Status: follow-up focused acceptance recorded; release pending, do not close.
Source: [issue 918](https://github.com/tya5/chrona/issues/918), observed
2026-10-10, including the consolidated 919–922 bodies.
Merged implementation: `484657736a8fa7dbc5c8668ffc20d57f6c5f23ab` in
[PR 1276](https://github.com/tya5/chrona/pull/1276), accepted head
`ab2650030bb55b95d4cc6f34dc5c97dde1cb2e8a` on ready base
`e1a6f8122aa14b57392ac0363a35e09ff5ab1cbe`.
Follow-up source: `e66136cfe72e5c44a67a89c7d286d7ee49f82123` on ready
main `2487d752ed45b6c8c55fe9d183a20ccaf3abadea`; public artifact and
exact-main release proof for this follow-up remain required.
[Initial PR CI](https://github.com/tya5/chrona/actions/runs/37952231069)
exposed four Scene negative-probe equivalence failures: its consumer treated
owner detail as part of the code. The corrected consumer retains the leading
code; schemas, baseline probes and expected deltas are unchanged.
[Candidate CI](https://github.com/tya5/chrona/actions/runs/37955021163)
passed conformance, derived preview, MCP floor and newest-Python reproduction.
All three pytest shards failed on remaining test consumers of the old bare-code
and stderr contracts, removed-helper imports and an archived-schema fixture.
Two JSON parsing failures capture two CLI invocations without draining the first
success envelope; they do not demonstrate duplicate emission by one command.
Consumer corrections were verified by
[corrected PR CI](https://github.com/tya5/chrona/actions/runs/37959980414):
all three pytest shards, conformance, MCP floor, newest-Python reproduction
and derived-ready passed. Exact-main three-OS/wheel release remains required.
Authorities: [design](../../design/issue-918-diagnostic-owners-design-2026-10-09.md)
and [work record](../../planning/active/issue-918-diagnostic-owners-design-plan-2026-10-09.md).

## Literal issue acceptance

### Issue #918

- Source: [Issue #918](https://github.com/tya5/chrona/issues/918)
- Observed: 2026-10-10

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Every code of these three packages is either raised with detail at every site or has a `sufficient` entry with a reason; their `sites` counts in the policy are gone (the ratchet `tests/unit/tools/test_diagnostic_inventory.py` enforces it; each fix lowers its count in the same PR). | met | Inventory validates 1,609 sites, zero bare reachable sites; [policy](../../../conformance/resolvability-quality-policy-v0.1.yaml) has no remaining entries; [ratchet tests](../../../tests/unit/tools/test_diagnostic_inventory.py). | — |
| 2 | Each fixed code has a test that provokes it and asserts the value is named (mutation-checked). | met | [Owner tests](../../../tests/unit/chrona/presentation/renderers/test_renderer_diagnostic_details.py), exhaustive original-code test audit and owner mutation evidence below; heterogeneous Scene/Layout/renderer primitive owners are checked separately. | — |
| 3 | Every code of these packages is raised with detail at every site or has a `sufficient` entry with a reason; their `sites` counts in the policy are gone (the ratchet enforces it; each fix lowers its count in the same PR). | met | Same complete [inventory/policy ratchet](../../../tests/unit/tools/test_diagnostic_inventory.py), including icon/font/model/review owners. No `sufficient` exemption is used. | — |
| 4 | Each fixed code has a test that provokes it and asserts the value is named (mutation-checked). | met | [Owner tests](../../../tests/unit/chrona/presentation/model/test_model_contract_diagnostic_details.py); the same exhaustive original-code test audit and restored owner mutations below. | — |
| 5 | `usecases` and `operational` codes are raised with detail or classified `sufficient` with a reason; their policy `sites` counts are gone. | met | Zero bare reachable inventory; [materializer tests](../../../tests/unit/chrona/usecases/test_materialize_diagnostic_details.py) and [operational tests](../../../tests/unit/chrona/operational/test_authoring_diagnostic_details.py). | — |
| 6 | The Actual-command and snapshot result tuples carry `"E_X: detail"` strings (or a detail field), and the automation-result rows built from them name the revision, key or observation; tests that compared whole tuples are updated. The inventory is extended to read these tuple literals so the ratchet covers them. | met | Published S1 `9125ca33`; [automation bridge tests](../../../tests/unit/chrona/operational/test_actual_result_details.py), command/snapshot owner tests, tuple inventory cases. | — |
| 7 | The options and the choice are recorded with how to reverse it. | met | [Selected design](../../design/issue-918-diagnostic-owners-design-2026-10-09.md), Render transport section, compares alternatives and specifies explicit Spec 66/skill/golden reversal. | — |
| 8 | `render` has one documented machine channel for warnings that matches the other commands, or the disposition (keep stderr) is recorded with its reason. | met | Spec 66 and [skill reference](../../../skills/chrona/references/diagnostics.md); [success-envelope tests](../../../tests/unit/chrona/app/test_cli_render_result.py); all 19 successful render cases use stdout and empty stderr. | — |
| 9 | Goldens, the skill reference and Spec 66 agree; the MCP `render_draft` rows equal the CLI rows (existing test). | not met | Local golden and [CLI/MCP parity test](../../../tests/unit/chrona/app/test_agent_tools.py) agree; CI cross-platform characterization remains pending. | — |
| 10 | Every `W_LAYOUT_*` and `W_SCENE_*` row names the Project object it is about (`sourceRef` and the title in the message) where the placement belongs to one. | met | [Scene producer tests](../../../tests/unit/chrona/presentation/scene/test_diagnostic_provenance.py), Layout icon/shape producer tests and [ledger tests](../../../tests/unit/chrona/usecases/test_warning_provenance.py) cover explicit typed joins, escaped IDs, suppression, multiple subjects and ownerless findings; golden rows below. | — |
| 11 | Scene diagnostics, SVG and PNG bytes and the multiplicity invariant are unchanged (existing tests). | not met | [Local 114-case comparison](../../../tests/cli/test_cli_characterization.py): all 37 generated files byte-identical, warning identities/counts unchanged. Candidate public artifact below preserves all 140 SVG/Scene files and newest-Python reproduction passed; full pytest and exact-main release remain required. | — |
| 12 | The CLI golden and the MCP `render_draft` warnings agree and are reviewed row by row. | met | [CLI/MCP tests](../../../tests/unit/chrona/app/test_agent_tools.py) retain real-render parity and exercise the actual MCP envelope projection for every successful golden case: 19 cases, all 22 rows, including empty/info/multi-owner detail. Complete CLI row audit below. | — |
| 13 | Expected detail: `scale=owner, missing=[m0,…], extra=[bus,…], at /body/scales/owner/slots`. | met | [Synthetic production tests](../../../tests/integration/test_color_scale_failure_provenance.py) prove stable code, scale/missing/extra keys and escaped canonical `/body/colorScales/<id>/slots` for both callers; the actual schema uses `colorScales`, not the example's `scales`. Late value errors retain the View pointer. | — |
| 14 | Expected detail: the View pointer `/body/annotations/<i>/anchor` and the reason, e.g. "object titlecard has no completed actual mark". | met | [Synthetic render transport](../../../tests/integration/test_annotation_anchor_failure_transport.py) proves unobserved/in-progress actual rejection, annotation/object/reason and canonical View pointer; [owner tests](../../../tests/unit/chrona/presentation/layout/test_annotation_routing_diagnostic_details.py) cover absent endpoint/invalid fields/post-resolution provenance and bounded text without truncating pointers. | — |
| 15 | The "readable render-warning transport" part of this issue should include the materializer's failure path. | met | [Standalone adapter tests](../../../tests/unit/tools/test_materialize_example_failure_transport.py) preserve all typed rejected/failed diagnostics and details through the shared mapper; success/library silence remains. [Cache test](../../../tests/integration/test_render_cache.py) proves nonempty stdout warnings and nested mutation isolation without stderr fallback. | — |

## Programme-level criteria (optional)

None; the literal issue and release gates above control acceptance.

## Focused and artifact evidence

Python 3.11 integrated owner/provenance/inventory/CLI tests: 220 passed;
renderer value assertions: 15 passed; latest-main overlapping Layout tests:
26 passed; complete golden-row MCP projection plus real-render parity:
20 passed; same-pass recording/full-envelope maintenance tests: 2 passed;
schema-equivalence consumer/regression suite: 32 passed.
Remaining diagnostic consumer corrections: 591 passed (16.64s), covering
store-address rejection, role/ground contrast and Scene serialization details
with the unchanged archived-schema guard.
CLI failed-node batch: 11 passed (42.95s), including three successive-command
captures, exact warning fields, multiplicity and importer operands.
Render consumers: three focused nodes passed before an interrupted slow batch;
the skill-envelope node passed separately. Updated collision, legend, attachment
and platform-specific font consumers await CI; no complete corpus run is claimed.
Latest-main lane/inventory/render-envelope focused batch: 29 passed (8.57s).
These are focused checks, not a substitute for full release CI.

Follow-up integrated batch: 124 passed (11.42s), including inventory,
View normalization, anchor/model owner tests, real synthetic render failures,
materializer transport and nonempty warning-cache isolation. Owner batches:
scale/separability/group tint 45 passed; annotation/projection 84 passed;
adapter/cache 14 passed. Detail-removal mutations killed scale-value and both
anchor-code operand assertions; materializer diagnostic-detail loss and cache
stderr fallback also failed their synthetic assertions. All mutations were
restored before the integrated run. Bounded long-input anchor tests preserve
the complete pointer and cap message operands. Scale resolver codes remain
unchanged; upstream Scheme ingress retains its own schema code/pointer.

The MCP projection test supplies the characterized ledger rows to the real
`render_draft` tool envelope without rerendering 19 images; the retained
end-to-end test separately compares real CLI and MCP rendering. Long successful
render stdout is stored in full rather than as a stream digest so no warning
row is silently treated as empty. The expanded HALCYON stdout has exactly
the previously characterized SHA-256 `dc54115d13347ef1b4773b3cf08098f17e0970c079978bef90c489d13eb29bd8`.

### Owner mutation evidence

All temporary source mutations were restored before the integrated clean run.
Each mutation removed owner detail (code-only helper/raise, or blank typed
`detail`); the invoking tests assert distinctive real operands. The inventory
also removes read-only code predicates rather than classifying them as raises.
A separate read-only audit found literal test references for all 151 original
policy IDs and checked operand assertions in the changed owner tests; literal
reference coverage alone is not mutation evidence.

| Owner / invoking tests | Mutation and killed assertions |
| --- | --- |
| Actual result/automation and snapshot owner tests | Code-only tuples for all six Actual and six snapshot code families; each family's operand assertions fail. Clean S1 bridge/inventory run: 80 passed. |
| [Icon importer/normalizer](../../../tests/unit/chrona/presentation/icons/) | Code-only owner details across 31 importer/normalizer codes: 46 failures; restored owner run: 118 passed. |
| [Font metrics/resources](../../../tests/unit/chrona/presentation/model/test_font_resources.py) and existing metric tests | Two font-code owner mutations: 22 failures; restored: 26 passed. |
| [Review detail normalization](../../../tests/unit/chrona/presentation/review/test_detail_normalization.py) | Detail helper removal: 10 failed, 11 passed. |
| [Review content](../../../tests/unit/chrona/presentation/review/test_v05_content.py) | Eight code families: 11 failed, 53 passed; group-ordinal raise separately killed. |
| [Theme token](../../../tests/unit/chrona/presentation/model/test_theme_tokens.py) and [scheme](../../../tests/unit/chrona/presentation/test_color_scheme_diagnostic_details.py) tests | Code-only token helper: 8 failures; scheme helper: 21 failures. Restored combined owner run: 111 passed. |
| [Model/contracts/font/schema](../../../tests/unit/chrona/presentation/model/test_model_contract_diagnostic_details.py) | Owner detail removals for axis, surface-content, info, semantic, schema, authoring, fonts, contracts and ingress were caught; restored owner batch: 172 passed. Added font-input blank detail kills its missing-face/index assertion; scheme blank detail kills all four binding cases. |
| [Placement candidates](../../../tests/unit/chrona/presentation/model/test_placement_candidates.py) and [color scale](../../../tests/unit/chrona/presentation/model/test_color_scale.py) | Helper removals: 19 and 12 failures respectively; restored combined run: 39 passed. |
| [Lane candidate/preflight/subtrack](../../../tests/unit/chrona/presentation/layout/test_lane_diagnostic_details.py) | Eight code families: candidate mutation 1 failure, subtrack/preflight mutations 4, label preflight 2; restored focused run: 34 passed. |
| [Annotation/obstacle/routing/search/topology](../../../tests/unit/chrona/presentation/layout/test_annotation_routing_diagnostic_details.py) | Owner helper removals: annotation 5 failures, obstacle 9, route 1, search 2, topology 1; restored run: 70 passed. |
| [Text/axis/as-of/mark-aware geometry](../../../tests/unit/chrona/presentation/layout/test_text_axis_diagnostic_details.py) | Ten code-family helper/direct-raise mutations killed; restored owner run: 91 passed. |
| [Mark/path/pattern/icon/balloon/image-slice](../../../tests/unit/chrona/presentation/layout/test_mark_geometry_diagnostic_details.py) | Eight code families, including two heterogeneous primitive owners: all code-only mutations killed; restored combined run: 131 passed. |
| [Surface-quality and profile invariants](../../../tests/unit/chrona/presentation/layout/test_geometry_diagnostic_details.py) | Eight invariant codes: 12 new cases killed; duplicate-node detail removal separately killed. Restored combined quality run: 53 passed. |
| [Layout content resolution](../../../tests/unit/chrona/presentation/layout/test_content_resolution_diagnostic_details.py) | Code-only shortfall raise: 1 failure; both resolution raises: ordering and duplicate cases fail. Restored source has unchanged predicates. |
| [Scene primitives/text layout](../../../tests/unit/chrona/presentation/scene/test_scene_diagnostic_details.py) | Primitive detail mutation: 4 failures; text-layout detail mutation: 1. Restored focused run: 18 passed. |
| [Scene analysis/serialization/capabilities](../../../tests/unit/chrona/presentation/scene/test_scene_analysis_diagnostic_details.py) | Six code-family detail mutations killed; capability-substitution owner rechecked with two explicit failing cases. Restored owner run: 116 passed. |
| [Renderer owners](../../../tests/unit/chrona/presentation/renderers/test_renderer_diagnostic_details.py) | Actual `registry._failure`, `v05_typeset._error`, `v05_svg._failure` code-only mutations kill 7, 6 and 3 cases respectively across the 12 renderer codes; restored focused run: 15 passed. |
| [Materializer owners](../../../tests/unit/chrona/usecases/test_materialize_diagnostic_details.py) | Thirty source-site details covered; 14 distinctive operand-removal labels all killed; restored focused run: 17 passed. |
| [Operational authoring](../../../tests/unit/chrona/operational/test_authoring_diagnostic_details.py), [authoring materialization](../../../tests/unit/chrona/usecases/test_authoring_materialization.py) and detail admission | Seventeen code-only raise mutations: 23 failed, 30 passed; restored same set: 53 passed. |

Counts are results of distinct focused owner runs, not additive suite totals.
Interrupted broad route/renderer/integration runs are not counted as passes.

The complete 114-case characterization against public baseline `546f7c3f`
preserves all exit codes and all 37 generated files (including Scene/SVG/PNG).
Four owner errors gain detail; 19 successful render console outputs change to
the documented envelope. No public resource or geometry edits are included.
Reproduce raw byte evidence with `CHRONA_CHARACTERIZATION_RAW=<log.jsonl>
python -m tests.cli.test_cli_characterization --record` in separate baseline
and feature worktrees with their own Python 3.11 venvs; compare file hashes,
exit codes and ordered warning identities/counts. Logs are local evidence,
not committed resources.

Audited corrected candidate public artifact:
[11630069335](https://github.com/tya5/chrona/actions/runs/37959980414/artifacts/11630069335),
`derived-snapshot-ab2650030bb55b95d4cc6f34dc5c97dde1cb2e8a`, provider digest
`sha256:daccd1844013f06a66c83f63476d4d04404dc5c55fc64ac2ff72d0aacdb9bd2e`.
Downloaded with `gh run download 37959980414 --repo tya5/chrona --name
derived-snapshot-ab2650030bb55b95d4cc6f34dc5c97dde1cb2e8a`.
The before/after archives have 149 paths each, no retirements, and all 140
SVG/Scene files are byte-identical. Every before-file matches ready main
`e1a6f812`; the only changes are the diagnostic and declared-value inventory
reports. Archive members and the declared changed-path list were checked as
a batch without extracting into the worktree. Corrected-head newest-Python
reproduction and all pytest shards passed; exact-main three-OS release remains
incomplete.

### Every successful-render warning row

Each entry is `code × count → first source/title`; all 22 rows preserve the
baseline order, severity, diagnostic identity, count and occurrences.
`W_DEADLINE` retains its existing deadline pointer; informational suppression
retains its existing summary. Neither is assigned invented Project ownership.

| CLI case(s) | Ordered warnings |
| --- | --- |
| `render-default-svg`, `render-default-no-suffix`, `render-default-png`, `render-format-svg-explicit`, `render-format-png-no-suffix`, `render-viewport`, `render-viewport-width-only`, `render-visual-profile`, `render-starter-emit-scene`, `render-format-pdf` | Each: `W_SCENE_DECORATION_CONTRAST × 2 → /objects/design / Design`. |
| `render-deadline-warning` | `W_SCENE_DECORATION_CONTRAST × 1 → /objects/qa / QA`; `W_DEADLINE × 1 → /objects/qa/deadline`; `W_DEADLINE × 1 → /objects/launch/deadline`. |
| `render-actual` | `W_LAYOUT_ACTUAL_INCOMPLETE × 2 → /objects/design / Design`; `W_SCENE_DECORATION_CONTRAST × 2 → /objects/design / Design`. |
| `render-halcyon-default` | `W_LAYOUT_ACTUAL_INCOMPLETE × 1 → /objects/tvac / System thermal-vacuum`; `W_LAYOUT_LABEL_SUPPRESSED × 6 → /objects/eps / Power system qualification`; `W_SCENE_DECORATION_CONTRAST × 13 → /objects/avionics / Avionics integration`; `I_LAYOUT_PLOT_LABELS_SUPPRESSED × 6`. |
| `render-halcyon-view-theme-scheme-layout`, `render-halcyon-resources-png`, `render-halcyon-emit-scene` | Each: `W_LAYOUT_ACTUAL_INCOMPLETE × 1 → /objects/tvac / System thermal-vacuum`. |
| `render-preset-builtin-id`, `render-preset-copied-path`, `render-preset-with-scheme-override` | Empty warnings, explicit stdout success envelope. |

## Architecture and gate disposition

Layout captures typed subject facts; Scene projects non-rendered sidecars;
usecases join exact primitives and format warning subjects; CLI/MCP serialize
their existing row projections. Serialization whitelists exclude sidecars.
Identity, collapse cause/key, measurement, routing, paint and geometry remain
independent. Relation-only and field/entity-group warnings retain their real
source: endpoint/member attribution would falsely change their ownership.
Canonical pointers, known titles and additional subjects are intentional
provenance, not a full Project dump; do not truncate pointers or silently omit
owners. Owner error text uses bounded operands separately.

Local conformance found stale bot-owned diagnostic/declared-value inventories;
CI derived preview owns those refreshes. Policy-shape and Scene-field delivery
registration failures were corrected and individually checked. Do not edit
generated inventories manually or count this local run as green. The CI
schema-equivalence fix only separates code from owner detail; it does not
reclassify the four known invalid corpus documents or relax an expected delta.
The issue
stays open until every row and the required release gate are met.
