# Issue 1818 — declared burst precision

Status: implementation verified; official artifact and exact-main release pending.
Base: trusted ready `ec8f27ed3`; published design `6bbb74f49`; source `496717707`.
[Current design/architecture/implementation plan](https://github.com/tya5/chrona/issues/1818#issuecomment-6288189726).

| Literal acceptance criterion | Verdict | Evidence |
| --- | --- | --- |
| Resolve the macOS materializer failure with a general, documented rule at its responsible layer; no project-specific branch or hand-edited evidence. | not met | Layout applies declared `scenePrecision` to completed absolute burst vertices; no platform branch, tolerant comparison, trig kernel or authored derived files. Cross-platform release proof remains pending. |
| Add a focused synthetic regression and retain burst padded-text containment and geometry validation. | met | `test_chip_scene_precision.py` (8 tests) and `test_burst_scene_precision.py` (6 real pinned-Context circle/ellipse × 0/3/6 cases); chip/as-of/lane/render-plan batch 76 passed. Tests include subquantum perturbation, explicit half-even, arbitrary high precision, preserved bounds, text coverage and truthful precision refusal. |
| Verify actual declared roadmap-sunday output and exact-main three-OS release; disclose any intended Scene/SVG differences. | not met | Actual macOS public materializer produced the intended new Scene/SVG in `/tmp/chrona-1818-roadmap-sunday.505qVk`; comparison with old evidence correctly reports `E_MATERIALIZER_MISMATCH` until the derived bot publishes it. Primitive count 277→277; paths 18→18; IDs/text/diagnostics unchanged. Maximum numeric displacement 0.001. Official all-slide table and exact-main release remain pending. |

Architecture review (root + independent Luna): existing Context precision flows
through render plan/request, as-of and fixed-lane premeasurement into one Layout
chip completion. Measurement retains the original fit and reserves half-quantum
displacement; final bounds enclose snapped ink and padded-text coverage is checked.
Rectangle/catalogue geometry stays unquantized. Scene/adapters only project the
completed result. No public schema, version, identity or fallback change.
Float-accumulation, inward-import and explicit Scene-delivery checks pass.
CI owns generated reports/materializers and full suites; no duplicate local full run.
Issue stays open until the pending literal release evidence is complete.
