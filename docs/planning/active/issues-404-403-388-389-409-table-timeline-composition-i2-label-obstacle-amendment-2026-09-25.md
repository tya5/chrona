# Implementation Plan Amendment — I2 Label Obstacle Closure (#404, #388)

**Precondition:** the row-allocation ownership correction is published and
the v0.5/v0.10 migration is complete.

Before accepting I2 row allocation:

1. retain all completed marks as label obstacles;
2. exempt only the declared host mark for an `inside` candidate;
3. add direct tests proving an outside label cannot overlap a sibling or
   another row's mark, while a contrast-safe inside host label remains legal;
4. keep row requirements limited to Theme minimum, track feasibility, and
   padding; and
5. render immutable-context overflow through its Context repair language,
   then regenerate and inspect public materializer evidence.

Acceptance requires no new unsafe text/mark overlaps, the revised draft
extent threshold, immutable Context wording, focused tests, full `pytest`,
and generated-artifact review.
