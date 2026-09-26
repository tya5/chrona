# Architecture review — as-of collision correction (#458)

**Correction:** [collision consequence](../../design/issue-458-as-of-label-collision-correction-2026-09-26.md).

Accepted. Specification 50 gives Layout collision and candidate selection;
Scene's responsibility is faithful projection. Suppressing an obstacle in
Scene or exempting only as-of from Layout's collision set would split geometry
authority. #446's text-intersection gate and exact suppressed-ID check remain
independent release evidence. This correction changes review expectations,
not the public schema or the approved component ownership.
