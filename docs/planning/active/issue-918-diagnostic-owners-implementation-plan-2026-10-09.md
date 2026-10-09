# Issue 918 — implementation plan

Base: published design `e6b02ac2a84f65cf82e0c48821c6482dffbfe89c`.
Authorities: [design](../../design/issue-918-diagnostic-owners-design-2026-10-09.md),
[architecture review](../../reviews/current/issue-918-diagnostic-owners-architecture-review-2026-10-09.md),
and [literal A1–A15 checklist](issue-918-diagnostic-owners-design-plan-2026-10-09.md).
Product implementation starts only after this plan is published.

| Slice | Files / owners | Acceptance and focused evidence |
| --- | --- | --- |
| S1 result tuple closure | `commands/actual_commands.py`, `storage/snapshots.py`, operational leading-code consumers, `tools/diagnostic_inventory.py`, existing command/storage/inventory tests | A6: all constructor tuple forms inventoried; revision/key/observation/snapshot identity named in results and automation rows; unchanged atomic/replay behavior; operand-removal mutations killed. |
| S2 owner detail closure | `presentation/layout`, `scene`, `renderers`, `icons`, `model`, `review`, `color_scheme`, `contracts`, `fonts`, `schema_diagnostics`, `usecases`, `operational`; each owner's existing unit tests; quality policy | A1–A5: inspect all sites, detail or explicit operand-free `sufficient` reason; inventory counts reduced in the same publication; per-code provoking operand tests and mutation proof, separately per heterogeneous owner family. |
| S3 provenance closure | typed subject model; Layout producer/completion/member-label/mark modules and `surface_quality`; Scene model/builder non-rendered handoff; `render_review`, `warning_ledger`, `diagnostic_messages`; focused producer/ledger tests | A10–A11: pointer/title capture before source loss, suppressed placements, ordered multi-owner sources, no fake owners, escaped IDs, unchanged identities/collapse/multiplicity/Scene facts and SVG/PNG bytes. Coordinate dev B's `layout/engine.py` before any overlap. |
| S4 transport and acceptance | `app/cli.py`, CLI characterization golden/tests, `app/test_agent_tools.py`, `skills/chrona/references/diagnostics.md`, owner mutation-evidence matrix, one literal acceptance review | A7–A12: one stdout success envelope on every render route, unchanged exit/failure semantics, agreed normative reference, complete row-by-row MCP parity and golden delta audit. |

Independent, non-overlapping S1/S2 owners may implement in parallel; root owns
shared policy, usecase/CLI integration and all Git publication. No schema or
corpus migration is authorized. Recheck all diagnostic-string consumers when
detail is added. A mutation table records code, owner, invoking test, removed
operand and killed result; inventory alone cannot accept a code.

Publish completed implementation slices as coherent commits on one product PR,
not separate micro-PRs/golden refreshes. Run focused tests as owners finish;
batch inventory, conformance, CLI parity and public artifact review once the
integrated changes are ready. CI owns full three-OS pytest, wheel/smoke and
public materializers; do not author bot-owned derived files or duplicate full
pytest locally. Audit image/Scene bytes and warning counts separately from
intentional message/console changes. Close only when A1–A12 are directly proven
and the exact-main release containing the acceptance review is green; archive
closed records separately. Stop for design correction before implementing a
new rule outside the published contract.

## Review follow-up: one integrated publication

S1–S4 are merged in PR 1276 at `48465773`. Publish the amended design plan,
selected design/architecture review with Specs 40/66, and this implementation
amendment before source edits. Reconcile the next successful derived-main tip
without rewriting published history. The new slice has three parallel owners:

| Owner | Files | Focused acceptance |
| --- | --- | --- |
| Scale model/application | `model/color_scale.py`, `usecases/render_review.py`, color-scale unit and group-tint integration tests | A13: structured stable code/detail/pointer, RFC6901 scale IDs, both View encoding and grouping tint failures; outer use-case conversion also catches later value selection from valid mappings; preserve Scheme category provenance. |
| View/Layout annotations | `model/surface_content.py`, `review/v05_content.py`, `layout/annotations.py`, `layout/surface_annotations.py`, anchor/projection tests | A14: canonical source capture, metadata excluded from equality/repr, invalid facet/endpoint versus unavailable actual mark reason, direct and application failure paths; no changed eligibility/fallback. |
| Materializer/cache adapter | `tools/materialize_example.py`, adapter unit tests, `tests/support/render_cache.py`, cache tests | A15: all real rejected/failed rows preserved by existing report mapper, exit/status/pointer/details, silent success and typed silent library failure; nonempty stdout warning mutation isolation. |

Root owns specification/review files, integration tests where shared, all Git
publication and release acceptance. No agent commits or edits another owner's
files. Use distinctive synthetic inputs and detail-removal assertions; batch
focused tests, inventory, acceptance-review validation and PR artifact audits
after integration. CI supplies full pytest/public reproduction and the final
automatically dispatched exact-main three-OS/wheel gate. Do not duplicate that
dispatch or author generated reports/SVG/Scene. Re-read issue comments before
matching-head merge and before closure; all A1–A15 remain required.
