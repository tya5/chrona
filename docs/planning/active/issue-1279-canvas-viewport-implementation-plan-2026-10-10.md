# Issue #1279 — canvas viewport implementation plan

Public design base: `2f5d20a407957113e22c10e343a20f43f4fb49eb` on ready main `5360a127`.
[Design](../../design/issue-1279-canvas-viewport-design-2026-10-10.md) and
[architecture review](../../reviews/current/issue-1279-canvas-viewport-architecture-review-2026-10-10.md)
define the contract; [design plan](issue-1279-canvas-viewport-design-plan-2026-10-10.md)
contains every literal acceptance criterion.

| Slice | Owned files / evidence | Acceptance and publication |
| --- | --- | --- |
| 1. Typed diagnostic | New `layout/canvas_viewport.py`; request/result fields in `surface_quality.py`, `dependency_network.py`, Scene input/model, delivery registry; synthetic helper tests | Full-edge comparison, no auto-block constraint, deterministic slot union/top-five facts, fitting none. Publish coherent typed closure on the work branch. |
| 2. Completion and report | Capture declaration in `usecases/render_review.py`; both Layout completion paths; Scene projection; `warning_ledger.py` / `diagnostic_messages.py`; integration/report tests | One shared warning identity/payload, real negative-origin/overflow/fitting/auto and both surfaces. All geometry preserved; existing network warning retained. One product PR contains slices 1–2. |
| 3. Acceptance | One batched current-main/materializer comparison, CI artifact audit, concise acceptance review | Every SVG/viewBox checked, exact warning-slide list in PR, geometry unchanged and no authored examples/derived files. PR matrix then automatic exact-main three-OS release; only then close. |

Focused tests: new `test_canvas_viewport_warning.py` helper and
`test_canvas_viewport_warning_render.py` integration suites,
existing dependency-network/canvas/auto-block/Scene projection and warning-ledger
tests, Scene delivery and literal acceptance validators. Run S0/conformance only
where changed transport delivery requires it; CI supplies full pytest/conformance,
newest-Python materializers and wheel smoke. No redundant local full pytest.

No resource/schema migration or generated mirrors are authored. Publish serially
from the latest ready main, using ordinary merges; #918/#927 retain merge priority.
Pause and correct the design before code if attribution or transport changes its
contract. Record actual commands/commit/artifact evidence in the final review.
