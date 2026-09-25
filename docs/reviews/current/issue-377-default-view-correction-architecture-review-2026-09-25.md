# Architecture Review: Generic draft default View (#377)

**Decision:** Accepted.

The correction keeps semantic selection in View, treatment in Theme/Scheme,
and composition in Layout.  `selected-planned` is existing View intent, not a
CLI or renderer fallback.  Optional Actual comparison makes the default usable
for the first Project file without changing immutable Context policy.
