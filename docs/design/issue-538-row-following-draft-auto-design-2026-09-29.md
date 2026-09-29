# Design — Row-Following Draft Auto Sizing (#538)

Predecessor: [published work record and design plan](../planning/active/issue-538-row-following-starter-work-record-2026-09-29.md), published in PR #561 at `c8bab542`.
Successors: [architecture review](../reviews/current/issue-538-row-following-draft-auto-architecture-review-2026-09-29.md) and [implementation plan](../planning/active/issue-538-row-following-draft-auto-implementation-plan-2026-09-29.md).

## Contract

`WIDTHxauto` is a Draft content-sizing request. Its synthetic Render Context may continue to use the finite 900-unit block seed required for closure validation, but that seed is not a minimum for the final auto-sized Scene. Layout resolves the smallest positive integral logical viewport block extent that accommodates the measured natural table-timeline requirement and the complete resolved normal-flow profile. Intrinsic profile minima, title/axis/legend/note measurements, margins, and normal-flow spacing remain part of that result. Satisfying the content host alone is insufficient if another normal-flow placement or profile minimum requires more extent. The final LayoutManifest allocation must verify the selected extent; overflow added only to the completed canvas does not count as satisfying it. Round the selected extent upward to the next whole scene unit. For content with no rows, the positive finite Layout floor is one scene unit; any larger intrinsic profile requirement wins.

Finite Draft viewports and immutable Context viewports retain #468 semantics: their requested block extent is a minimum. They do not shrink below the explicit request. If content exceeds it, Layout reallocates the whole normal-flow profile to the least sufficient finite extent. Fixed, capped, or anchored hosts that cannot gain capacity retain the requested allocation, short-source evidence, and truthful visible fallback; they do not cause a speculative reallocation or render refusal. The completed canvas still includes emitted geometry as required by Specification 33 §13; that overflow does not count as successful allocation or manufacture blank space.

Natural timeline sizing uses the pre-fill requirement already derived from per-row minima, measured table text, mark geometry, lane requirements where applicable, group headers, and padding. `rowDistribution: fill` runs only after the final timeline host is selected and distributes only its actual surplus. Fill-expanded rows must never become a subsequent sizing input. Thus a compact auto request packs rows at their natural requirements, while an explicit larger minimum can produce fill rows. More rows or larger measured requirements grow the auto result; the three-row starter does not retain unused space attributable to the synthetic 900-unit seed.

Layout remains the owner of complete canvas, slot, and row geometry. Render ingress carries the auto-versus-finite request distinction to Layout; Scene transports the completed result and adapters serialize it. No starter-specific View rule, Scene adjustment, or adapter sizing is introduced. No View or Layout Profile schema change is needed.

## Scope and migration

Relevant implementation seams are `resolve_content_block_extent` in `src/chrona/presentation/layout/engine.py`, the sizing call in `src/chrona/usecases/render_review.py`, and Draft request construction in `src/chrona/presentation/model/closure.py`. The default View and Layout declarations need no semantic change. Existing copied presets are unaffected because their bytes and identities do not change.

This intentionally changes the rendered dimensions of Draft auto requests whose content fits within 900 units. Explicit finite Draft and immutable Context outputs keep the 900-unit minimum. Any public generated Scene/SVG whose render uses an auto request must be regenerated and compared; immutable materializers should remain byte-identical unless they expose a real existing content-host deficiency. Missing sources, invalid profiles, and true fit shortages keep their current errors or typed fallback behavior.

## Normative specification proposal

Before product code, amend Specification 33 §13.1 to distinguish a Draft auto content-sizing request from a finite requested minimum: the synthetic finite closure seed MUST NOT be treated as the auto result's lower bound; auto MUST choose the least positive integral whole-profile allocation that satisfies declared natural content requirements and profile minima; rounding is upward; fill surplus is allocated only after that result; explicit finite Draft and immutable viewport minima remain unchanged. State the empty-content floor and fixed/capped fallback in the same section. Specification 08's Scene/adapter boundary and Specification 50's typed shortage behavior remain unchanged.

## Acceptance evidence

The fresh initialized starter must emit Scene and SVG whose block extent follows its three rows and required geometry, without unused 900-unit-seed space. All rows, marks, table text, axis, legend, title, and notes must remain within completed geometry; notes remain after the plot in normal flow. Row-count and larger-requirement variants must grow monotonically. A finite 900-unit request must remain at least 900, and an auto case requiring more than 900 must grow. Pack and fill profiles must prove that only post-sizing surplus is distributed. A fixed/capped profile must preserve the truthful shortfall. Focused tests, affected public materializer checks, artifact review, CI/release evidence, and an acceptance row for each literal criterion are required.
