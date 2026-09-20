# M19 Layout Grammar Final Review — 2026-09-19

**Disposition:** Pass — M19 complete.

The runtime accepts only `chrona/layout-profile/v0.1` on the new review path, validates
named regions/slots and source availability, and emits a deterministic content-hashed
Layout Manifest. The deprecated table-timeline profile is rejected rather than becoming
a second composition authority. No Project, Schedule, Actual, View, Style, or Theme fact
is modified during validation.

Evidence: deterministic/unavailable-source tests, Layout Profile CLI rendering, full
conformance, and 89 passing tests. M20 remains responsible for consuming manifest
regions rather than the compatibility adapter's former fixed geometry.
