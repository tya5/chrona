# Architecture Review — Calendar-Closed Extent Orientation (#389, #409)

**Result:** Accepted.

The correction preserves the system's ownership chain: semantic orientation is
declared by the registry, physical domains by Layout Profile, measured bounds
by Layout, treatment by Theme, and primitive emission by Scene/adapters.  A
closed day is a column-oriented calendar primitive; treating it as a
row-oriented review-surface band would collapse the semantic distinction and
make Scene evidence misleading.

The role-specific schema constraint is preferable to a permissive generic enum
plus runtime exceptions: invalid `calendarClosed: table|both` resources fail
at profile validation, while the three row-oriented roles retain their useful
finite choices.  This keeps the arrangement extensible without making the
renderer or View infer geometry.
