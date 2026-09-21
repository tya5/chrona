# M27 Product-Path Inventory — 2026-09-21

**Status:** D27-1 complete. This is an observed inventory, not an implementation
authorization.

## Evidence basis

The current public `render-review` route resolves an immutable Render Context and
Layout Manifest, but then calls `review.svg.render_table_timeline_svg`, which calls
`scene.review.compose_review_scene` and `renderers.table_timeline.render_gantt`.
That path emits a reduced `ReviewScene` and gives every text primitive the one
`text.body.size` value. The current route does not consume the existing normalized
`SurfaceContentInput`, Detail profile, summary profile, or completed `SceneSurface`
serializer.

`renderers.scene_svg.render_scene_surface_svg` already serializes the richer
renderer-neutral Scene vocabulary named by Specifications 08 and 30, including
role-specific typography, group surfaces, axis bands, comparison/missing-Actual marks,
patterns, routed Paths, annotations, legend, and summary/detail families. It is not
reached by the product CLI. `scene.marks`, `layout.axis`, `layout.labels`,
`layout.routing`, `scene.annotations`, `review.surface_content`, and `review.detail`
provide related generic mechanisms but are currently disconnected from that route.

## Capability trace

| Lost capability (#33) | Current product-path behavior | Existing declared owner/mechanism | D27 disposition |
|---|---|---|---|
| Role typography, title, subtitle | One body font; title only | Theme typography; Detail templates; `SceneSurface` Text | Restore through completed Scene Text; no serializer font default |
| Month/quarter bands and readable labels (#30) | Literal 28-day ISO labels; no bounds check | Layout axis policy; `layout.axis`; Scene axis-band/tick/Text | Resolve calendar intervals declaratively and reject required label overflow |
| `tableColumns.missing` (#31) | Enum value printed literally | View column policy; normalized `SurfaceContentInput` cells | Normalize `blank`/`em-dash`/`unknown` before Scene |
| Group headers, bands, row shading | No emitted family | View grouping; Theme group paints; Scene group surfaces | Restore only when the resolved View/Layout declares the family |
| Plan/Actual/milestone/variance/missing Actual | Bare rectangles/diamond; no variance or hatch | View comparison facets; Style roles; Theme; Scene marks | Restore complete conditional families without inferred Actuals |
| Routed dependencies and arrowheads | One straight Line without marker | Layout router; Theme marker; Scene Path | Route finite declared ports and serialize completed marker policy |
| Legend, coverage, annotations, detail, summary | Slots may reserve space but render nothing | Detail/Summary Profiles; `SurfaceContentInput`; Scene slot families | Required present slot must emit its declared family or diagnose incomplete input |
| Example reproducibility (#29) | No public materializer or byte-identity check | Example manifest; immutable Context/Store closure | Add generic CLI-driven materializer and artifact conformance |

## Authority and reachability decision

The target product path is:

`immutable Render Context → projection + resolved Detail/Summary → ResolvedPresentationInput
→ Layout Manifest + completed SceneSurface → scene_svg → SVG`.

The old `ReviewScene` / `table_timeline` pair is not a second product presentation
model. D27-2 must decide its explicit disposition: retire it after migration, or reduce
it to a private compatibility-free adapter that constructs the same completed
`SceneSurface`. A public parallel serializer is prohibited.

The following properties must never be reintroduced as code constants: axis stride or
wording, missing-value text, typography sizes, color/opacity, bar shapes/heights,
variance treatment, group paints, legend entries, panel content, or example selection.
Their existing resource owner is retained unless D27-2 adds a versioned field and
normative owner.

## Issue disposition

- #29, #30, #31, and #33 remain open and are the M27 scope.
- #28 reports the old v0.4 acceptance-test failure. The current test is named
  `test_v05_example_contexts_bind_exact_source_bytes` and includes Color Scheme
  identity. D27-4 will run artifact reproduction evidence; after that verification,
  #28 is an obsolete report to close separately, not an M27 implementation change.

## D27-1 exit check

Every reported regression has a resource authority and an existing or explicitly
required generic mechanism. No capability requires Project/Schedule/Actual mutation,
example-specific runtime behavior, a new renderer output target, or restoration of the
superseded layout grammar. D27-2 can now define the normative composition contract.
