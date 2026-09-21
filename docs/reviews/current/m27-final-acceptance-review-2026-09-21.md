# M27 Presentation Product-Path Final Acceptance Review — 2026-09-21

**Decision:** Superseded. The materializer/reproduction evidence is valid, but the
rich primitive acceptance amendment reopens M27 for I27-R6.

The public `render-review` path now reaches only the current Context v0.5 → resolved
Theme v0.2/Color Scheme → Layout Manifest → completed v0.5 SceneSurface → v0.5 SVG
adapter closure. No deleted Settings, legacy Theme paint map, fixed 28-day renderer
cadence, or example-ID branch is reintroduced.

The generic materializer builds a temporary immutable snapshot from a manifest-declared
raw Context closure, derives its exact Context reference, and invokes the public CLI.
Controller Z and ASTER reproduce their declared expected SVG bytes; deliberate target
mutation is rejected. Full regression reports 198 passed and every conformance runner
passes.

**Issue evidence:** A27-02 is covered by normalized missing-value tests; A27-03 by
the measured ISO axis rule; A27-07 by `test_materialize_example.py`; and A27-08 by the
CLI's v0.5-only construction route. The remaining A27 coverage is exercised by the
current Scene/Theme/Layout regression suite and materialized examples.
