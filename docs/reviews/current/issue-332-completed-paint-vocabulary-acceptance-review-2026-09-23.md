# #332 Completed Paint Vocabulary: Acceptance Review

## Accepted outcome

The Scene boundary now carries completed renderer-neutral paint for the canvas
and every primitive: fill, stroke, stroke width, dash, opacity, and completed
pattern form. Theme/Scheme remain the sole policy source; the resolver performs
the one-way conversion before adapter invocation. SVG, Typst, TikZ, raster, and
PDF routes no longer receive `ThemeTokenView`.

## Evidence

| Requirement | Evidence |
| --- | --- |
| Typed closure and validation | `ScenePaint`, Theme v0.3 `strokeWidth` / `dash` bindings, focused paint tests |
| Projection closure | table-timeline and dependency-network projection tests prove every primitive and canvas have paint |
| Adapter isolation | renderer imports contain no `ThemeTokenView`; public render port is `SceneSurface + viewport` |
| Exact output | SVG tests cover fill, stroke, width, dash, opacity, marker, and rejection of missing paint |
| Public resources | all five Theme resources explicitly bind stroke widths; eight materializer SVG artifacts regenerated |
| Regression gate | `pytest -q`: 420 passed, 7 skipped (2026-09-23) |

## Architecture review

The implementation preserves Project/Actual semantics, View selection, and
Layout geometry. It removes adapter-side policy recovery rather than adding a
compatibility path. The only optional opacity completion occurs in the typed
Scene resolver as documented in the published correction; adapters always
serialize an explicit value. Missing stroke width, invalid dash, incomplete
channels, and unsupported forms fail before output instead of silently
downgrading.

## Issue disposition

#332 is complete. Its completion satisfies the remaining deferred scope of
#315 (stroke width, mixed fill/stroke payload, and dash vocabulary); #315 may
therefore close after this review is published.
