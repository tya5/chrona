# Design Correction — Axis Template Components and Equivalence (#432)

**Amends:** [selected design](issue-432-axis-name-table-design-2026-09-26.md).
**Discovered before product code:** a week template needs ISO week-year, which
can differ from calendar year at a boundary; the first design's placeholder
list omitted it. Collision checking also needs to distinguish a true
all-month alias from a coincidental collision for one month.

`isoYear` and `isoWeek` are both allowed closed placeholders. They derive
from the natural interval's ISO calendar, not the clipped View edge. A
template may contain only literal text and simple named placeholders from
the finite list; attribute/index access, conversions and format specifiers
are invalid.

For each pair among the six month forms, evaluate all twelve month buckets
at a fixed representative year. If the forms match for all twelve, the table
must declare exactly one directed alias to a canonical form. If they match
for only some months, reject the table as ambiguous rather than calling it
an equivalence. If they never match, a declared alias is false and invalid.
The checked audit reports every all-month alias. This rule also applies
across month-only and year-bearing forms, although they will normally differ.

The architecture boundary is unchanged: Layout consumes closed table data;
Scene and adapters receive completed text. This correction adds no View or
Render Context field beyond the published design and does not alter fiscal or
ISO week facts.
