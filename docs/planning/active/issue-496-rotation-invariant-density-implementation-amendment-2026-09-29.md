# #496 implementation amendment: intrinsic density

**Amends:** [Slice 1 plan](issue-496-theme-asset-catalogues-implementation-plan-2026-09-28.md) and its [coverage amendment](issue-496-density-and-note-host-implementation-amendment-2026-09-29.md). **Design/review:** [intrinsic density amendment](../../design/issue-496-rotation-invariant-density-amendment-2026-09-29.md), [architecture review](../../reviews/current/issue-496-rotation-invariant-density-architecture-review-2026-09-29.md).

For Slice 1, evaluate density on the 128×128 tile-local fundamental cell using the already-defined 16-chord periodic predicate; do not inverse-rotate a fixed axis-aligned viewport. Add an 8×4 stripe fixture at both 0° and 45° and require 1,250 basis points in each, plus the existing 1,250/2,500/5,000 dither and wrapped-arc fixtures. No later slice or publication boundary changes.
