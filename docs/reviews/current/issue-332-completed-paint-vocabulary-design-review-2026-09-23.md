# #332 Completed Paint Vocabulary: Architecture Review

## Decision

Adopt `ScenePaint` as the completed decorative payload of every primitive and
surface canvas. Keep `visualRole` solely as selected semantic provenance.
Theme/Scheme resolve policy; Scene performs the one-way typed conversion;
adapters serialize or reject. Do not extend adapters with additional role
lookups, per-target defaults, or a literal primitive-colour API.

## Review of architectural boundaries

| Boundary | Finding | Decision |
| --- | --- | --- |
| Project / Actual | No paint input is semantic schedule data | They cannot construct `ScenePaint`. |
| View | Selects families, not appearance values | No override syntax is added. |
| Layout | Owns geometry and routing | It neither reads Theme paint nor emits width/dash. |
| Theme / Scheme | Owns stroke policy and concrete colors | Add closed `strokeWidth` and `dash` bindings; retain Scheme bindings. |
| Scene | Has geometry but adapters reopen roles | Introduce resolver and canvas paint. |
| SVG / typeset | Look up fill/stroke and omit width/dash | Remove token-view input; serialize or reject. |
| Materializer | Public closure evidence | Regenerate checks after all adapters use ScenePaint. |

## Consistency corrections

Specification 08 and the v0.5 runtime description currently describe
`visualRole` as adapter paint input. That conflicts with completed-placement and
adapter-projection rules. #332 updates those statements atomically with the
contract migration. Specification 46 is normative and creates no parallel model.

Existing `pattern` and `marker` tokens remain semantic form choices. Pattern
does not authorize SVG to invent hatch width. Implementation either gives that
form a completed value or rejects the unsupported form.

## Rejected alternatives

- Keep roles and add width/dash lookups in renderers: makes them Theme evaluators.
- Add arbitrary `color` / CSS attributes: bypasses Scheme provenance.
- Put width/dash in Layout metrics: confuses appearance with geometry allocation.
- Silently default missing width/dash: hides an incomplete closure.

## Acceptance review requirements

Acceptance requires schema and resolver failures, all primitive-family channel
contracts, adapter isolation, SVG/TikZ bytes, public materializer artifacts,
and the full suite. It must show that no renderer imports `ThemeTokenView` and
generated SVG contains no hard-coded hatch stroke width.
