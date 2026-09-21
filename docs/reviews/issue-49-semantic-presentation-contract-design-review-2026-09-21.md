# Issue #49 semantic presentation-contract design review

## Review scope

Reviewed the semantic-contract specification against the existing boundary chain:

`Project / Actual → View projection → SurfaceContentInput → LayoutManifest + MeasuredSources → SceneSurface → Theme tokens → SVG materializer`.

## Findings and disposition

| Boundary | Review finding | Disposition |
| --- | --- | --- |
| Project / Actual | Calendar and as-of are already domain facts but Scene reads flattened SurfaceContent fields. | Preserve domain ownership; normalize the selected facts into `TimeContract`. |
| View projection | Explicit rows already carry row/member identity but Scene reconstructs some identity and tracks. | Make row/member identity and track allocation contract data, then consume placements. |
| SurfaceContentInput | Contains raw compatibility fields such as `show_member_labels` alongside canonical choices. | Restrict it to ingress; its aliases are removed from all downstream reads. |
| Layout | Measurements exist, but table widths and row/track geometry are calculated in Scene. | Introduce `LayoutPlacement` as the sole geometry handoff. |
| Scene | Literal role strings, token names, and layout calculations are interleaved. | Registry owns semantic-to-role/binding mapping; Scene only emits declared primitives. |
| Theme | Optional metric and role spellings have been handled locally. | Declare canonical bindings and ingress aliases in the registry; resolve before Scene. |
| Materializer | Correctly owns generated evidence, but its gate reaches errors late. | Invoke contract validation before rendering and require context coverage in materializer tests. |
| Legacy contract | Deleted Settings/Theme pathway must not become a compatibility shortcut. | Explicitly excluded; only current public inputs are adapted at ingress. |

## Architecture decision

The proposed contract sits between current authoring/model validation and existing Layout/Scene. It does not add another renderer abstraction or duplicate the domain model. Its purpose is to make the existing boundary explicit and executable.

## Design closure

- Single canonical semantic owner: closed.
- Explicit alias/compatibility boundary: closed.
- Layout versus Scene responsibility: closed.
- Theme binding validation: closed.
- Evidence and test traceability: closed.
- Legacy contract non-restoration: closed.

The design is consistent with the #49 recovery specification. Implementation may now be planned.