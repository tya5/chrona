# Issue 918 — diagnostic owners: design plan

Status: PR 1276 merged at `484657736a8fa7dbc5c8668ffc20d57f6c5f23ab`;
review follow-up implemented at `e66136cf`, release acceptance pending.
Selected [design](../../design/issue-918-diagnostic-owners-design-2026-10-09.md),
[architecture review](../../reviews/current/issue-918-diagnostic-owners-architecture-review-2026-10-09.md)
and [implementation plan](issue-918-diagnostic-owners-implementation-plan-2026-10-09.md)
include published follow-up phases `32cb2940`, `dca58ecb` and `bce9556f`.
Authority: [issue 918](https://github.com/tya5/chrona/issues/918), including
consolidated issues 919–922. Public baseline:
`546f7c3f9e700afa7553632d8dd6ac0c94a348a0` (`derived-main` successful).
Predecessor: [issue 829 work record](../../archive/planning/issue-829-diagnostic-owner-detail-work-record-2026-10-02.md).

## Published facts and remaining verification

- PR 1276 closes the original inventory's 488 bare sites across 151 codes;
  the current ratchet covers 1,609 sites including Actual/snapshot tuples.
- CLI render warnings now use the documented stdout envelope; MCP parity and
  producer provenance tests passed in PR CI. Scene identities/counts and all
  140 public SVG/Scene files are unchanged in artifact 11630069335.
- Follow-up focused integration passes 124 tests on ready base `2487d752`;
  exact-main release and the follow-up public artifact audit remain pending.

## Design questions and review scope

Use cases: an author identifies the invalid operand; an automation client sees
the conflicting revision/key/observation; an agent finds the Project object
behind a successful-render warning without inspecting multiple machine channels.

1. Owner-local detail: establish when the identifier alone is sufficient and
   when the owner must name the operand/expected form. Review shared helpers
   only within an owner; no generic Core catalogue may guess missing context.
2. Result tuples: design inventory coverage for Actual/intake/snapshot results,
   using the existing leading-code parsing and automation-result contracts.
   Review consumers that compare an entire diagnostic string.
3. CLI: compare optional stdout JSON, unconditional stdout envelope with human
   stderr, and documented existing stderr JSON. Record the selected channel,
   exit semantics, migration and reversal before product changes.
4. Provenance: define typed producer-side Project pointer/title metadata,
   its connection through Layout/Scene warning production and the ledger, and
   handling of relation, View, global and multi-owner findings. Do not infer
   ownership by parsing a placement ID in transport. Preserve Scene strings,
   primitive facts, collapse keys, multiplicity and image bytes.

Architecture review must cover Specs 05/06/08/35/50/56/66 and the issue 782/829
diagnostic contracts: Core/domain intent, View declarations, Theme resources,
Layout completed geometry, Scene completed primitives, adapter serialization,
usecase orchestration and CLI/MCP transport. No geometry, font policy, corpus
or preset tuning is in scope. Check extension points, pointer escaping,
missing titles, failure behavior and any intended incompatibility.

## Design and publication order

Publish this plan first. Complete the selected design and whole-architecture
review next; update normative specifications for CLI/provenance changes.
Publish the implementation plan before product code. Its independently
reviewable slices will cover inventory/result tuples, owner-local detail,
producer provenance, and transport integration. Exact files and tests depend
on the completed design; do not treat this outline as implementation approval.

One coordinating dev A publishes serially. Read-only Luna audits may run in
parallel. Coordinate on the issue before touching any dev B-owned open-PR
file, particularly `presentation/layout/engine.py`; wait for that PR to merge.
#927 stays parked on its unresolved critical-path scope decision.

Evidence: focused tests including value-assertion mutations per fixed code;
inventory ratchet; tuple-to-automation tests; pointer/title and first-occurrence
collapse tests; CLI golden and MCP row-by-row parity; unchanged Scene warning
facts, SVG and PNG bytes; batched public-materializer artifact comparison;
CI full three-OS release including the literal acceptance review. Derived
public evidence is bot-owned, not hand-edited. A remaining or deferred row
keeps the issue open without an approved successor disposition.

## Integrated implementation evidence

S1 is published at `9125ca33`; S2–S4 are published in
[PR 1276](https://github.com/tya5/chrona/pull/1276). The current candidate
ordinarily merges ready main `5ebc493b`; no published branch was rebased.
Python 3.11 focused integration: 220 passed. The inventory validates 1,609
sites with zero bare reachable constructors; the policy retains its unrelated
declared-value and corpus rules. Owner tests include detail-removal mutations.
The 114-case CLI comparison against the baseline preserves all exit codes and
37 generated files byte-for-byte: 19 successful-render envelopes and four
owner-error messages change; 22 warning rows preserve identity and multiplicity.
Relation-only and field/entity-group findings retain their real source, not
invented endpoint/member ownership. Provenance keeps canonical pointers and
known titles; it is excluded from Scene serialization and geometry.
CI identified a schema-equivalence consumer treating Scene error detail as
part of its code; the fix splits the leading code without changing validators,
baseline probes or expected deltas. Complete golden-to-MCP projection checks
cover all 19 success cases and 22 warning rows (20 focused tests passed).
CI full release and public-materializer acceptance remain pending. The local
conformance review found stale bot-owned inventory reports; its policy-shape
and Scene-field ownership failures were corrected and individually rechecked.

## Literal acceptance (release evidence pending)

| ID | Criterion | Evidence owner |
| --- | --- | --- |
| A1 | Every code of these three packages is either raised with detail at every site or has a `sufficient` entry with a reason; their `sites` counts in the policy are gone (the ratchet `tests/unit/tools/test_diagnostic_inventory.py` enforces it; each fix lowers its count in the same PR). | Layout/Scene/renderers and inventory |
| A2 | Each fixed code has a test that provokes it and asserts the value is named (mutation-checked). | Layout/Scene/renderers tests |
| A3 | Every code of these packages is raised with detail at every site or has a `sufficient` entry with a reason; their `sites` counts in the policy are gone (the ratchet enforces it; each fix lowers its count in the same PR). | Icon/model/review/related owners and inventory |
| A4 | Each fixed code has a test that provokes it and asserts the value is named (mutation-checked). | Icon/model/review/related tests |
| A5 | `usecases` and `operational` codes are raised with detail or classified `sufficient` with a reason; their policy `sites` counts are gone. | Usecases/operational and inventory |
| A6 | The Actual-command and snapshot result tuples carry `"E_X: detail"` strings (or a detail field), and the automation-result rows built from them name the revision, key or observation; tests that compared whole tuples are updated. The inventory is extended to read these tuple literals so the ratchet covers them. | Commands/storage/automation/inventory tests |
| A7 | The options and the choice are recorded with how to reverse it. | CLI design and migration |
| A8 | `render` has one documented machine channel for warnings that matches the other commands, or the disposition (keep stderr) is recorded with its reason. | CLI contract and tests |
| A9 | Goldens, the skill reference and Spec 66 agree; the MCP `render_draft` rows equal the CLI rows (existing test). | CLI/MCP integration and reference |
| A10 | Every `W_LAYOUT_*` and `W_SCENE_*` row names the Project object it is about (`sourceRef` and the title in the message) where the placement belongs to one. | Producer provenance and ledger tests |
| A11 | Scene diagnostics, SVG and PNG bytes and the multiplicity invariant are unchanged (existing tests). | Scene/adapters and artifact comparison |
| A12 | The CLI golden and the MCP `render_draft` warnings agree and are reviewed row by row. | Transport acceptance audit |
| A13 | Expected detail: `scale=owner, missing=[m0,…], extra=[bus,…], at /body/scales/owner/slots`. | Scale owner and typed render-failure transport; verify the actual schema pointer rather than inventing the example's `scales` property. |
| A14 | Expected detail: the View pointer `/body/annotations/<i>/anchor` and the reason, e.g. "object titlecard has no completed actual mark". | View normalization, Layout anchor resolution and typed render failure. |
| A15 | The "readable render-warning transport" part of this issue should include the materializer's failure path. | Standalone materializer adapter and shared failure report. |

## Review follow-up design scope

Source: [review comment](https://github.com/tya5/chrona/issues/918#issuecomment-6085291520).
Published scale/anchor messages already name operands, but scale conversion
puts the entire message in `RenderFailed.code`; neither owner preserves the
required resource pointer. The standalone materializer does not serialize
typed failure diagnostics. The test render cache still reads stderr warnings.

Decisions to complete before code: structured scale errors and their canonical
Theme/View ownership; annotation pointer capture before Layout (including
identity/cache exclusion); one adapter failure mapping without library prints.
Review against Specs 06/08/40/50/56/66 and existing typed failure reporting.
Do not change anchor eligibility, color mapping, geometry, success output or
resource syntax. Amend the selected design/architecture review, then publish
the implementation amendment. Three non-overlapping source owners may work
after publication; root integrates once, with one follow-up PR and batched
artifact/full-CI evidence. No issue closure until A1–A15 are directly proven.
