# Issue 1397 row 3 — implementation plan

Status: implemented locally; PR and release acceptance pending. PR1521 merged
as `e10985a6d`; next public base is READY `c06840468`.
[Design](../../design/issue-1397-days-late-caption-design-2026-10-15.md),
[architecture review](../../reviews/current/issue-1397-days-late-caption-architecture-review-2026-10-15.md),
and [literal acceptance/evidence](issue-1397-days-late-caption-design-plan-2026-10-15.md)
are the authority; do not duplicate their rules here.

| Step / owner | Files | Focused evidence |
| --- | --- | --- |
| 1. Authoring and normalization | `schemas/view-v0.28.schema.yaml`, `presentation/contracts/resources.py`, shared template/count helpers | Optional caption and shared format schema; parsed closed grammar and defaults; invalid declarations/pointers; no network acceptance. |
| 2. Core-to-Presentation handoff | `presentation/model/projection.py`, `usecases/render_review.py` | Pass the existing verdict/count, format only slipped deadlines; all four forms, literal braces, range errors, kept/absent cases. Update internal typed-contract callers without shims. |
| 3. Layout and diagnostics | `layout/surface_deadlines.py`, new `layout/deadline_captions.py`, `layout/surface_composer.py`, `model/info_diagnostics.py`, diagnostic consumer in `usecases/draft_render.py` | Two anchors, real text metrics, complete bounds/baseline/font identity, plot edges, collisions/priority, repeated-host identities, counted drops/provenance, outline/wobble envelope, no run/tick or prior content changes. |
| 4. Theme and Scene projection | `model/theme_tokens.py`, `model/semantic_registry.py`, `scene/capabilities.py`, `scene/v05_builder.py` | Optional caption text role and explicit text fallback; actual SVG text and ordering; 4.5:1 gate; identical Layout-to-Scene geometry; representative PDF/typeset projection. |
| 5. Release review | Relevant living Specs06/07/49/50; one row3 acceptance record | Focused combined suite; schema-equivalence L1/L2/L3; exact-head PR snapshot and reproduction; exact published main three-OS pytest/conformance/wheel smoke. |

The TextPlacement handoff also carries typed subjects (`surface_quality.py`);
outside captions do not use host_placement_id as a generic provenance link.

Local evidence: combined103 focused cases (including actual SVG/PDF and Typst/
TikZ copy, all four count forms, fallback/drop/contrast/provenance and existing
deadline contracts); schema-equivalence L1(additive View property)/L2/L3 PASS.
Independent static implementation review found no remaining blocker. Final PR
snapshot, CI and exact-main release remain required, not assumed from local tests.

Publish steps 1–4 together as one atomic product PR after their focused checks;
formatting alone is not a visible deliverable. Product changes include the
normative specification updates and synthetic tests. Inspect generated
SVG/Scene/report evidence as one batch; never edit derived-owned reports or
`examples/**`. No public fixture migration is expected because the feature is
opt-in. Use this worktree's venv, not another checkout's editable environment.

CI supplies full pytest and release gates; do not repeat the full suite locally.
Record all failing checks and their dispositions. Before push/merge, fetch
current main, inspect exact changes/conflict risk and verify trusted readiness.
Publications are serial; adopt concurrent main changes without force-pushing.

Keep parent1397 open: this is only row3. A default-off snapshot alone does not
prove the new feature; actual enabled SVG, formatting, fallback/drop counts,
contrast and adapter projection are required. If these steps expose a changed
contract, correct and publish the design/review/plan before resuming code.
