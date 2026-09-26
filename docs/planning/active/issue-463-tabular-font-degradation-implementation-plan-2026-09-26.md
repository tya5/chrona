# Implementation Plan — Missing Tabular Digits (#463)

**Base:** `0a1b2c770dfabc31452d639300ad5009dc5328a2`.
**Design:** [selected contract](../../design/issue-463-tabular-font-degradation-design-2026-09-26.md),
[architecture review](../../reviews/current/issue-463-tabular-font-degradation-architecture-review-2026-09-26.md).

## Literal acceptance gates

1. `chrona render --system-fonts` with Hiragino Sans or Georgia and a bundled Theme succeeds, with a warning naming the numeric role.
2. The committed corpus is unchanged, since its packaged faces have tabular digits.

## Slices and publication

1. **Exact draft capability and effective treatment.** Extend
   `presentation/fonts/system.py` and `presentation/model/closure.py` to
   carry deterministic per-role effective spacing and warning records. Pass
   one effective draft Theme view through `usecases/render_review.py` to
   Layout and Scene so metrics and `TextLayout.numeric_spacing` match. Keep
   immutable font-metrics-v3 and resource closure unchanged. Portable tests
   in `tests/unit/chrona/presentation/renderers/test_target_registry.py`
   use a face without tabular advances and assert measured/painted mode.
2. **Warning transport.** Extend `scene/model.py`, `scene/serialization.py`,
   `schemas/scene-v0.6.schema.yaml`, and `app/cli.py` for the exact structured
   warning. Test that Scene and CLI name the role and face once per role and
   that a missing proportional mode remains a refusal. Run macOS integration
   with Hiragino Sans and Georgia if installed.
3. **Release review.** Compare all committed materializer bytes (they should
   be unchanged), run focused tests and conformance locally, and inspect CI
   full matrix/newest-Python public materializers/wheel. Record literal
   acceptance and exact run in
   `docs/reviews/current/issue-463-tabular-font-degradation-acceptance-review-2026-09-26.md`.

The two code slices may be one atomic PR/commit because an effective mode
without warning transport would be unobservable. Publish the acceptance
review separately after the implementation gate.
