# Design — Knobs for Hard-Coded Label Behaviour (#573)

**Plan:** [implementation plan](../archive/planning/issue-573-label-behaviour-knobs-implementation-plan-2026-09-30.md); **review:** [architecture review](../archive/reviews/issue-573-label-behaviour-knobs-architecture-review-2026-09-30.md), whose amendments A1-A3 are part of this design.

## Decisions

1. **Layout owns both knobs.** They are arrangement policy relative to the type size, not appearance tokens. `layout-profile-v0.9` gains an optional `reviewSurface.memberNames` object, added in place under Spec 56 §3.2 (optional and additive, so no version bump):
   - `maxEndGapEm`: a non-negative number, default `2`. The bound is `maxEndGapEm` times the label's font size, replacing `2 * font_size`.
   - `search`: `side-band` or `full-band`. When absent, today's rule applies unchanged: `full-band` for a lane row under `rowDistribution: fill`, `side-band` otherwise. When present it is used for every member name, independently of how rows are distributed.
2. **Derived profiles carry it with no new mechanism.** A derived Layout Profile declares its own complete `reviewSurface`, which `profile.py` copies whole; `overrides` reach only nodes under `root`. `memberNames` therefore travels with the profile that declares it, and a derived profile that omits it gets the defaults.
3. **(Deferred, review A2; not in I573-1.) The bound is measured from the item's last own drawn mark.** For an item with a planned mark and a later actual mark the end gap runs from the right edge of the rightmost mark of that item, not from the planned host alone. Without an actual mark, or with one inside the planned extent, nothing changes. This is a behaviour change only for a label whose item has an actual mark past its planned end, which today can only be placed by overflowing; the affected slides are regenerated and reviewed against the rule and the approved targets. The `attached-milestones` example with its original data is the synthetic proof (the label clears its own actual mark within the default 2 em).
4. **Spec 50 states the default and the knob** in §3.2: the bound is `maxEndGapEm` (default 2) times the font size (the last-drawn-mark wording waits on decision 3), and the search policy is `memberNames.search` with its default coupling described as the default, not as a rule.
5. **One reach value bounds both two-em constants (review A1).** The nearest-perimeter association distance at the same call site uses the same `maxEndGapEm * font_size` , otherwise values above 2 are inert.

## Tests

Synthetic only. Two `maxEndGapEm` values give two bounds on a fixture whose actual mark sits a known distance past the plan; both `search` values are exercised on a lane row and on an automatic row; a Layout without `memberNames` renders byte-identically to today for every public slide that has no slipped actual mark.

## Boundaries

Layout Profile schema (additive field), Layout placement, Spec 50. No Theme, View, Scene or adapter change.
