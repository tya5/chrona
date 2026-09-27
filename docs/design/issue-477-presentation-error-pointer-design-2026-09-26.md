# Design — Presentation Error Pointer Transport (#477)

**Plan:** [design plan](../planning/active/issue-477-presentation-error-pointer-design-plan-2026-09-26.md).

## Decision

The detector remains the sole owner of diagnostic code, detail and RFC 6901
pointer. `LayoutError`, `ThemeTokenError` and `ScenePaintError` are typed
presentation failures with a `diagnostic_id` and `path`. The render use-case
boundary converts any of these that escape its stages into one `RenderFailed`
with unchanged code, `detail or diagnostic_id` message, `presentation`
component and `path or "/"` source reference. `SceneBuildError` already carries
its cause's pointer and keeps its existing conversion. The CLI only serializes
`RenderFailed`; it neither parses a message nor guesses a resource path.

This includes measurement before the layout solver, layout-profile resolution,
Theme token lookup, completed Layout composition and Scene paint. Keeping the
adapter around the entire render use case prevents a new call site from
falling through the CLI's generic `ValueError` branch. An empty path remains
`"/"`; an actual detector pointer is never replaced with that fallback. The
conversion is error-only and does not change successful Scene/SVG bytes.

## Boundary and failure behavior

```text
Theme/Layout/Scene detector (diagnostic_id, path, optional detail)
  → render-review use case (RenderFailed: same code, pointer and detail)
  → CLI (sourceRef = RenderFailed.source_ref)
```

The use-case adapter must not catch arbitrary `ValueError`, `ClosureError`,
font/import failures, `RenderRejected` collections or `SceneBuildError` as a
pointer-bearing type. Their established handlers remain authoritative. A
`ScenePaintError` is normally wrapped by `SceneBuildError`; the outer adapter
still covers an error from a new Scene path. The pre-existing local
`LayoutError` catch around the solver can be removed when the outer boundary
replaces it, avoiding two ownership points for the same transport rule.

## Alternatives rejected

- Adding three cases to the CLI's generic exception handler would leave
  non-CLI use-case clients with raw exceptions and put presentation transport
  knowledge in the command adapter.
- Extracting a pointer from `str(error)` or exception causes would be fragile
  and could silently change `sourceRef` after wording changes.
- Adding defaults or weakening required Theme metrics/roles would hide the
  missing declarations instead of reporting them.

## Migration and acceptance

No schema, resource version, public diagnostic code, or compatibility promise
changes. Existing successful materializer outputs must be byte-identical.
Focused CLI tests reproduce the header metric and numeric role failures, and a
use-case/CLI boundary test covers all three typed error classes. A failure
test confirms one exact source pointer rather than only a non-root assertion.
The issue's literal acceptance criteria remain the final release gate.

**Successor:** [architecture review](../reviews/current/issue-477-presentation-error-pointer-architecture-review-2026-09-26.md).
