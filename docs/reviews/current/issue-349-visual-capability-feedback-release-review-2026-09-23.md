# #349 Visual Capability Feedback Release Review

**Decision:** accepted; the post-hoc feedback is resolved on `main`.

## Delivered correction

- Scene capability failures now become `RenderFailed` at the render-use-case
  boundary with their stable code, exact role-property pointer, and a canonical
  author-facing message. A baseline render of the elevated theme reports
  `E_VISUAL_CAPABILITY_UNSUPPORTED` at
  `/body/roles/group-band/gradientAngle` before an adapter is invoked.
- Completed icon placement carries only its View binding provenance. Baseline
  validation reports an unsupported icon at `/body/iconBindings/0`; SVG/PNG
  v0.7 capabilities remain unchanged.
- `decorative-optional` treatment is omitted by Scene completion for baseline.
  The same public PNG render with v0.6 admits the completed treatment, and a
  decoded-pixel comparison proves it changes the artifact.
- A PDF request naming an SVG rich profile rejects at
  `/body/target/visualProfile` before creating an artifact. No direct rich
  Scene-to-PDF adapter check is retained as product evidence.

## Architecture result

Theme remains the role-binding authority, Layout remains geometry owner, Scene
completes or omits treatments and transports provenance, profile policy admits
completed values, and adapters serialize only. The correction adds neither a
generic profile nor a PDF rich route, target fallback, compatibility alias, or
new capability.

## Verification

- Focused Scene, visual-profile, renderer, and CLI tests: passed.
- Full suite: `509 passed, 11 skipped`.
- `python conformance/run_conformance.py`: PASS.
- Structural gates: module reachability, Scene primitive delivery, View
  dispatch reachability, and import direction: PASS.
- All declared public materializers reproduced their artifacts in check mode.
- Wheel build and installed-wheel smoke outside the checkout: PASS.
- GitHub Actions run 35867668141: passed on Ubuntu and macOS.

