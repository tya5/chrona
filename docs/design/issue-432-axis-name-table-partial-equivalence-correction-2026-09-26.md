# Design Correction — Month-Specific Form Coincidence (#432)

**Amends:** [selected design](issue-432-axis-name-table-design-2026-09-26.md)
and [template correction](issue-432-axis-name-table-template-validation-correction-2026-09-26.md).
**Discovered while validating the first catalog data:** English `May` is
both its short and long month name. Thus a valid `en-US` table has a real
one-month collision, and the previous rule that rejected all partial-month
collisions cannot represent it.

Every pair among the six month forms is compared for all twelve months in a
fixed representative year. Any equal output, whether for one month or all
twelve, must have one explicit coincidence record naming the selected alias,
canonical form, and exact sorted month numbers. Missing, false or imprecise
records invalidate the table. The checked public audit lists every record.
When an author selects the alias on one of its coincident months, Layout
emits `W_LAYOUT_AXIS_FORM_EQUIVALENT` with table ID, alias, canonical form and
month number. No warning is emitted for a month where the forms differ.

This includes `en-US` `long-month` → `short-month` in May and their
year-bearing counterparts, as well as all-month Japanese short/long aliases.
It neither changes the author-facing View syntax nor moves formatting out of
Layout. It makes the prior no-silent-equivalence acceptance implementable for
ordinary language data without inventing unnatural month names.
