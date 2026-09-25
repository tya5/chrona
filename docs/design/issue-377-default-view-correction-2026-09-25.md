# Design Correction: Generic draft default View (#377)

**Decision:** The wheel default uses a generic current-schema View.

It selects all current `span` and `point` objects, orders by planned start then
ID, uses the selected-planned temporal window, has no grouping, and makes
Actual comparison optional.  It presents title and planned dates in the table,
shows plot labels with declared fallback, and suppresses optional relations and
annotations when they do not fit.  It contains no object ID, project field
domain, calendar, or date literal.

The default Theme, Scheme, and Layout may remain the existing portable bundled
HALCYON treatment because they select appearance/composition, not Project
facts.  A user-supplied Actual Set enriches the same default View; its absence
does not make first render fail.
