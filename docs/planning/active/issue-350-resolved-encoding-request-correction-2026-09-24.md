# Design Correction: Resolved Encoded Visual Requests (#350)

**Status:** Design complete.

A View declaration has either a direct reference or encoding. After View
resolution, however, Layout receives the resolved catalog reference *and* the
encoding field/domain provenance. Treating those runtime fields as exclusive
rejects valid encoded selection. The typed Layout request therefore requires a
resolved reference and may additionally carry encoding provenance; only the
raw View schema remains exclusive. This preserves diagnostics without making
Layout reopen View facts.
