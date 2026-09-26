# Implementation Plan — Coherent Draft Allocation and Starter Gate (#468)

**Published design base:** `7ffa309180d2ce3e1fc96007b5f9d765f7fef35c`.
**Authorities:** [design](../../design/issue-468-coherent-draft-allocation-design-2026-09-26.md),
[architecture review](../../reviews/current/issue-468-coherent-draft-allocation-architecture-review-2026-09-26.md),
Specifications [33](../../specification/33-intent-oriented-layout.md),
[08](../../specification/08-scene-and-rendering.md) and
[50](../../specification/50-constraint-driven-gantt-surface-quality.md).
The [fixed-host correction](../../design/issue-468-fixed-host-allocation-correction-2026-09-26.md)
and [review](../../reviews/current/issue-468-fixed-host-allocation-correction-review-2026-09-26.md)
amend I468-1 before product publication.

## Literal issue acceptance

1. `chrona render examples/halcyon-1/project.yaml` with no flags emits no `W_LAYOUT_MARK_OVERFLOW`, `W_LAYOUT_ROW_DENSITY` or `W_SCENE_TEXT_INTERSECTION`.
2. With an explicit `--viewport 1600x900` on the same project, overflowing rows stay inside the `timeline` and `table` slots or grow them together; no note is overprinted. A test covers this.
3. The default draft render shows month labels on the timeline.
4. The Scene perceptibility gate (#446) or an equivalent check fails when a text primitive intersects another one in a committed or starter render.

## I468-1 — Layout content-coherent allocation

Own `src/chrona/presentation/layout/engine.py` and
`src/chrona/usecases/render_review.py`. Generalize the Draft-only finite
extent resolver into a Layout content-allocation function and use it before
final `solve_layout` on table-timeline requests, fixed or auto, Draft or
immutable. Preserve truthful visible fallback when a valid fixed/capped host
cannot grow. Avoid a Scene/adapter offset or warning suppression.

Focused tests: Layout solver and Draft/immutable render integration, explicit
900-high HALCYON-1 slot/row/mark/note containment, neutral fixed/capped
profile and large-row fixture. Check exact warning changes and actual SVG
canvas. Regenerate affected public materializers with
`tools/regenerate_public_examples.py --write --jobs 4`; review all Scene/SVG
diffs as a batch, including unintended paint/geometry effects. Run focused
tests, public byte check and conformance, then fetch/check/publish this
coherent code-and-evidence unit. CI full matrix gates its acceptance.
The resolver must prove its final candidate satisfies every declared host;
otherwise retain the original finite request and #449 visible fallback.
Specifically characterize fixed-host `03-launch-campaign` and anchored
`11-overlay-briefing`: neither may acquire an unhelpful extra canvas or
translation just because the content requirement exceeds a fixed slot.

## I468-2 — Draft default and axis resource

Own `src/chrona/app/cli.py`, `src/chrona/presentation/model/closure.py`,
`examples/halcyon-1/views/default-draft.yaml` and any packaged mirror,
README/first-project guidance and direct tests. Centralize a `(1600, None)`
Draft default for CLI render/workspace/guided and typed Draft ingress while
retaining finite synthetic Context seed. Add a quarter band/labels and month
labels to the bundled View using existing View v0.22 syntax; no schema
migration. Test bare CLI default, explicit fixed viewport, typed ingress,
copy-preset identity, multi-locale month text and actual SVG pixels/text.
Check all affected starter/wheel resource mirrors and public materializer
bytes, run focused tests and conformance, then publish as a second unit with
its own CI gate.

## I468-3 — Starter perceptibility and release

Own `tools/check_starter_perceptibility.py` (or a narrowly shared extension
of the existing tool), `conformance/run_conformance.py`, and focused tool/
integration tests. Render the real bundled starter once, serialize completed
Scene and call the one #446 evaluator; fail on any `E_` finding. Inject a
text intersection in a test and prove the same command/gate fails. Keep the
committed-scene gate unchanged and avoid a numeric exception baseline.
Run focused tests and conformance, publish the gate, inspect its three-OS
full pytest/conformance/wheel and newest-Python materializer CI.

## Acceptance and publication

For each material slice, inspect generated SVG and Scene as a batch, run
focused tests locally, verify public materializer bytes and conformance, and
let CI run the full matrix. Before each push fetch `origin/main`, inspect
ahead/behind, staged targets and conflict risk. After each push confirm the
remote commit and CI. If implementation exposes a missing rule, stop that
slice and publish a design correction, whole-architecture review and plan
amendment before resuming code. After all three units, write a literal-row
acceptance review with exact commits/commands/artifact diffs/SVG observation,
publish it separately, verify release CI, then close #468. No source or
resource may be left incompatible with the published runtime at a slice
boundary.
