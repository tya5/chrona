<!-- chrona:literal-acceptance/v1 -->

# Acceptance Review — Fit Completion and Exact Draft Host Fonts (#457, #447)

**Implementation base:** `899bed16d768ef15bc9255f9e9b91aae26079ec6`.
**Design:** [fit and host-font design](../../design/issues-457-447-fit-and-host-font-design-2026-09-26.md), [residual-fit correction](../../design/issue-457-residual-fit-correction-2026-09-26.md), [specification supersession](../../design/issue-457-fit-specification-supersession-2026-09-26.md), [host cap-height correction](../../design/issue-447-host-cap-height-correction-2026-09-26.md).
**Decision:** accepted for release at the implementation base, subject to
publication of this review and remote verification.

## Literal issue acceptance

### Issue #457

- Source: [Issue #457](https://github.com/tya5/chrona/issues/457)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Every corpus view drafts at 1600x900, 800x450 and 600x340 with exit code 0, drawing whatever does not fit visibly, with warnings. | met | `python -m tools.check_draft_viewport_matrix --cli`: 63/63 exit 0, 916 `W_LAYOUT_*` warnings; API matrix also 63/63 and checks the SVG viewBox against Layout's completed canvas. See [batch tool](../../../tools/check_draft_viewport_matrix.py) and narrow [immutable integration test](../../../tests/integration/test_materialize_example.py). | — |
| 2 | No fit-related refusal remains reachable from the draft or immutable path. | met | [Per-site audit](issue-457-fit-raise-site-audit-2026-09-26.md), [no-refusal structure test](../../../tests/unit/chrona/presentation/layout/test_fit_closure_structure.py), 63-case Draft matrix and narrow immutable Context render; remaining errors are invalid input or caught candidate failures. | — |
| 3 | Any remaining layout error message names the placement and the required and available extents. | met | No valid-fit refusal remains, hence no remaining fit-error message needs those fields. Completed shortages instead carry typed warnings with placement ID and required/available extents; [normal-flow test](../../../tests/unit/chrona/presentation/layout/test_intent_engine.py) and [text-visual test](../../../tests/unit/chrona/presentation/layout/test_visual_targets.py). Invalid schema/reference errors cannot have measured fit extents and are outside this issue's fit-error scope. | — |

### Issue #447

- Source: [Issue #447](https://github.com/tya5/chrona/issues/447)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | On a host with fontconfig, `--system-fonts` resolves a single-file family at 400 and at 700 to its regular and bold faces. | met | Real `DejaVu Sans` 400/700 Ubuntu CI and real `Helvetica Neue` 400/700 local macOS in [system-font tests](../../../tests/unit/chrona/presentation/fonts/test_system.py). The selected files/indices differ and exact OS/2 weights are checked. | — |
| 2 | It resolves a face inside a `.ttc`, and the PNG is painted with that face. | met | Real local macOS Hiragino TTC resolution, exact indexed face metrics, and [PNG test](../../../tests/unit/chrona/presentation/renderers/test_target_registry.py) asserting selected TTC-only font-file handoff, Scene asset identity, and nonuniform painted pixels inside the title bounds. | — |
| 3 | `Hiragino Sans` resolves by its English family name. | met | Real macOS `Hiragino Sans` [system-font test](../../../tests/unit/chrona/presentation/fonts/test_system.py) reads English typographic/family name from selected TTC face, with partial numeric capability measured without substitution. | — |
| 4 | CI exercises the real `fc-match` at least once. | met | Ubuntu CI executes the [real fontconfig test](../../../tests/unit/chrona/presentation/fonts/test_system.py) without an injected runner; green implementation run [36211846491](https://github.com/tya5/chrona/actions/runs/36211846491), final follow-up run [36212173257](https://github.com/tya5/chrona/actions/runs/36212173257). | — |
| 5 | A host without fontconfig receives a message that says how to get it, or does not need it. | met | [Unavailable-bridge test](../../../tests/unit/chrona/presentation/fonts/test_system.py) and [declared-font guide](../../guides/declared-font-assets.md) give installation guidance; immutable Contexts do not discover host fonts. | — |

## Programme-level criteria (optional)

The common release gate additionally requires public-materializer byte
identity and the full CI matrix.

## Verification and architecture conclusion

The focused L2/font/adapter/immutable set passed **66 tests**; the later
multiline source-retention correction passed 19 focused/public tests. The 21 public
materializer contexts reproduced byte-identically; no generated SVG or Scene
file changed. Local conformance passed its full inventory, schema, documented
command, architecture, and coverage checks. [Final CI run
36212173257](https://github.com/tya5/chrona/actions/runs/36212173257) completed
successfully at the exact implementation base: Ubuntu, macOS, and Windows
conformance/pytest/wheel-smoke jobs and newest-Python public-materializer
reproduction are all green. The previous material run
[36211846491](https://github.com/tya5/chrona/actions/runs/36211846491) was
also green before the final multiline-source correction.

Layout owns the natural fit fallback, warnings, text/icon composition, and
completed canvas. Scene projects these; SVG uses the completed viewBox. Draft
host-font ingress closes exact face identity and metrics before Layout, and
immutable Contexts remain host-independent. The [architecture
review](issue-457-fit-specification-architecture-review-2026-09-26.md)
reconciles older specification text. No force push, compatibility fit-refusal
branch, or generated-artifact rewrite was used.
