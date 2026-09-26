# Implementation plan — elevated preset starter compatibility (#460)

**Design:** [#460 design](../../design/issue-460-elevated-preset-starter-design-2026-09-26.md).
**Review:** [architecture review](../../reviews/current/issue-460-elevated-preset-starter-architecture-review-2026-09-26.md).

1. Change the gradient and shadow fidelity values in
   `examples/controller-z/themes/elevated-light.yaml` to
   `decorative-optional`, retaining the existing flat fill and rich-profile
   effects. Confirm packaged resource mirrors and generated public evidence
   are updated only where affected.
2. Make `tests/cli/test_cli.py` enumerate every ID in the shipped
   `presets/library.yaml`, copy it, initialize a fresh starter, and render
   without a profile exception. Keep a separate required-treatment rejection
   fixture and rich-profile assertion. Run focused CLI and capability tests.
3. Inspect actual default and rich SVG output, public materializer bytes and
   conformance. CI supplies full pytest, wheel/smoke and newest-Python
   reproduction. Publish implementation and a separate literal-acceptance
   review with exact CI/commit evidence before closing #460.

The Theme resource changes meaning for default baseline output intentionally;
no Project, preset schema, target selection, or adapter migration is planned.
