# Implementation Amendment — Host Numeric Capability (#447)

Before H1/H2 acceptance, update `presentation/fonts/importer.py` to extract
only actual numeric modes for volatile draft hosts, and
`model/font_metrics.py` to parse partial modes only when explicitly invoked
for that volatile path. Keep declared resource validation strict. Validate
the requested Theme role modes in `model/closure.py` before Layout. Add
proportional Hiragino, unsupported-tabular, and unchanged declared-v3 tests.
Then resume the H1/H2 gates in the [implementation plan](issues-457-447-fit-and-host-font-implementation-plan-2026-09-26.md).
