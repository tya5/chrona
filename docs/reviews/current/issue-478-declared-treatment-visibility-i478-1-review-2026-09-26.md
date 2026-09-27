# I478-1 Review — Typed Suppressed-Label Information

**Implementation:** `0a846388f73fd447670225099533156e49573ab3` on `main`. **Public base:** `a731fe2b` (the separate #476 acceptance-review format repair). **Design and plan:** [#478 design](../../design/issue-478-declared-treatment-visibility-design-2026-09-26.md), [implementation plan](../../planning/active/issue-478-declared-treatment-visibility-implementation-plan-2026-09-26.md). This is a slice review; Issue #478 remains open for I478-2/3 and final acceptance.

## Evidence and byte review

- Focused local command: `.venv311/bin/python -m pytest -q tests/unit/chrona/presentation tests/integration/test_render.py tests/cli/test_cli.py` — **602 passed**. The later exact-count unit addition and two new integration cases were rerun separately — **3 passed**.
- `.venv311/bin/python -m tools.regenerate_public_examples --write --jobs 4`, followed by `--check --jobs 4` — **21 slides reproduced**. Five Controller Z Scene JSON files gained only `I_LAYOUT_PLOT_LABELS_SUPPRESSED:surface=table-timeline;count=1`; comparing parsed JSON after deleting `diagnostics` yielded identical content for all five. No SVG file changed, so no visual/pixel change was introduced by this slice.
- `tools/check_scene_primitive_delivery.py`, `tools/check_issue_acceptance_reviews.py` and regenerated `tools/diagnostic_inventory.py --check` pass. The local whole-conformance invocation was otherwise green except schema-inventory/annotation/reference checks caused by the pre-existing, untracked `schemas/view-v0.23.schema.yaml`; that file was neither staged nor altered. A clean checkout's full conformance and release gates passed in [four-job CI run 36238954660](https://github.com/tya5/chrona/actions/runs/36238954660): Ubuntu, Windows, macOS conformance/full pytest/wheel, and newest-Python public materializer reproduction.
- Controller Z's emitted Scene retains exact `W_LAYOUT_LABEL_SUPPRESSED:member-label:ga:ga` and adds one count; its suppressed member label has no drawable Text primitive. HALCYON's `mission-light` has one suppressed member and a separate suppressed variance label, but the member count remains one. A normal HALCYON mission brief emits no count. The CLI prints one JSON info record with `surfaceId` and `count`.

## Architecture review

Layout assigns a semantic ID to each label request and counts only completed suppressed `memberLabel` placements. `SurfacePlacement.assert_valid` checks the count against completed placements and their per-ID warning facts. Scene passes the typed fact through to inspection diagnostics; the CLI projects it from the typed render result. Neither Scene nor an adapter measures, places, recounts, or draws a suppressed label. Other label suppression, including variance, is not misreported as a missing member name. Scene and SVG geometry are byte-identical to the previous base.

## Literal Issue #478 criterion disposition after this slice

| # | Literal acceptance criterion | State | Evidence / next unit |
| ---: | --- | --- | --- |
| 1 | Rendering `elevated-light` under the default profile emits a diagnostic that names the dropped treatment and the profile that would paint it. | not met | I478-2 will add typed optional-treatment dispositions and target-specific suggestions. |
| 2 | A Theme property on a role that cannot carry it is diagnosed at load time. | not met | I478-3 will add role/property admission with atomic resource migration. |
| 3 | Suppressed plot labels are counted in an info diagnostic, or the View can ask for a visible marker on rows whose label was suppressed. | met | Typed `SuppressedPlotLabels`, Scene diagnostic, CLI info, zero/one/multiple and variance-exclusion tests, and public Scene evidence above. |

I478-1 is accepted. The next public base is `0a846388`; I478-2 may start. This review does not close #478.
