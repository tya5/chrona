# Design correction — R2 full-band search applies to `fill` lanes (#504)

The [R2a correction](issue-504-501-lane-label-search-correction-2026-09-29.md) specified lane-only full-band contact search but did not distinguish `fill` from established `pack` lanes. A public-gallery probe showed that applying the new search to `pack` moved labels and introduced an additional suppressed dependency route in Editorial lanes. That is outside #504's lane-growth use case.

The shared normalized/measured label intent remains a Layout closure for all lane profiles. The R2 full-band contact search and conservative stagger-row minimum apply only when the Layout Profile declares `rowDistribution: fill`. `pack` lane profiles retain their published bounded side-neighborhood search and mark-only row minimum. Non-lane labels remain unchanged. This preserves the independent Editorial gallery and makes `fill` the explicit policy boundary; View membership, Theme treatment, Scene schema, and adapters do not change.

The release gate compares the complete public materializer batch. Intended byte changes are limited to 02/11/12 plus corpus coverage; any other diff requires an explicit design review rather than silent regeneration. The 02 zero-suppression stop gate remains.
