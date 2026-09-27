# Architecture Review — Readable Defaults (#483, with #423)

**Decision:** design approved for implementation planning. **Reviewed design:** [#483 design](../../design/issue-483-readable-defaults-design-2026-09-26.md). This is a design review, not issue acceptance.

| Boundary | Authority checked | Result |
| --- | --- | --- |
| Theme / Scheme | Specifications 07 and 34, Theme v0.11 | Existing tokens and role properties only (`opacity`, `marker`, `dash`), plus one Scheme's palette. No schema or code change. Inheritance: `onboarding-variation` re-pins its base identity. |
| Layout | Specification 24 | Unaffected except source-terminal marker geometry, which Layout already completes from the marker token. |
| Scene / adapters | Specifications 08 and 63 | `dash` is already carried by `ScenePaint` and serialized by the SVG adapter. The PNG path rasterizes the SVG. Baseline visual profiles admit stroke dash; to be verified in the batch. |
| Contrast | `presentation-contrast` gate, the #310 contrast policy | Darker axis bands must keep axis-label contrast; the existing gate checks this in conformance. |
| #478 (other session) | its I478-3 role/property admission design | `as-of`/`asOf` are Path roles that serialize `dash`, so they must be admitted there. Recorded on #478 if a conflict arises at rebase. |
| #481 / item 2 | #481 design (in progress) | Item 2 is sequenced after #481; no overlap in this slice. |

**Risks:**
- The PNG rasterizer's dash rendering is verified by viewing the PNG output.
- The axis band's `neutral` differs per scheme. The mechanical check and the contrast gate together cover every shipped scheme.

No unresolved user choice remains.
