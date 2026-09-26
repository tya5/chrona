# Architecture Review — Explicit Unfilled SVG Paint (#456)

**Result:** Accepted for implementation planning.

The design closes an adapter encoding gap identified by comparing the
completed Scene channel contract in specification 46 with actual SVG initial
values. Its rule is a direct mapping of `fill: absent` to `fill="none"`; no
source contract, semantic role, or Layout/Scene ownership moves to the
adapter. Pattern fill must be supplied as a single explicit override so a
common formatter cannot accidentally suppress it.

The contrast mechanism introduced for #431 observes completed Scene paint.
It is valid only when the target adapter faithfully represents that paint.
This correction restores that precondition and adds an artifact-level guard.
The #431 release review's Scene evidence alone is insufficient to prove the
existing SVG output; its visible-output criterion must be rechecked after
regeneration.

The nine Theme declarations already select outline treatment. Keeping those
values is an explicit appearance decision based on their recorded stroke
contrast and avoids changing corpus semantics merely to conceal an SVG bug.
Visual review remains an acceptance gate; a disappointing outline requires a
separate design correction before Theme values are changed.

No new public schema version or compatibility path is needed. This design is
consistent with specification 08 (deterministic SVG projection),
specification 46 (completed paint), and the one-way Layout → Scene → adapter
boundary.
