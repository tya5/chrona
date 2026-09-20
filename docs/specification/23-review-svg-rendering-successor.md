# Review SVG Rendering Successor Design

**Status:** Proposed  
**Owns:** the M14 Review SVG adapter boundary over an explicit Presentation closure.

## 1. Purpose

M14 makes the first review-oriented SVG useful for engineering decisions: planned and
observed Actual timing are independently visible, known variance is labelled, and
annotations retain their source identity. It is a rendering successor only. It does
not change Project scheduling, infer a forecast, resolve Actual alignment, or treat
SVG geometry as editable Project data.

## 2. Required closure and authority

One render request names an immutable Project, resolved schedule, View, Style, Theme,
optional Actual set, review-SVG profile, and target capability declaration. The adapter
MUST reject a View requiring Actual when no Actual set is supplied. It MUST use the
View's stable-ID selection, grouping, ordering, temporal window, and visibility; it
MUST use Style roles and fully resolved Theme tokens rather than renderer defaults.

`Project → Schedule → View Projection → Style/Theme → Review Scene → SVG` is the only
M14 path. Actual observations remain independent observations. A positive finish delta
means later than plan and is labelled `+Nd`; it never reschedules a successor.

## 3. v0.1 review profile

`review-svg-profile-v0.1.schema.yaml` declares only renderer policy:

- `axis`: Date-only weekly grid plus month labels; its window is supplied by View;
- `comparison`: planned upper bar, actual lower bar, and a textual variance marker;
- `missingActual`: hatch plus text alternative; and
- `annotations`: deterministic callout/leader layout with a diagnostic on collision.

`groupPresentation` is user-selected renderer policy: `none`, `separator`, `band`, or
`header-and-separator`, with an explicit inter-group row gap. The View alone decides
the stable group key (`objectType` or a declared field) and group order; the profile
never infers a group from titles, colours, or SVG positions. Style/Theme may supply
`group-header`, `group-separator`, and `group-band` roles/tokens. Thus the same Project
can render an owner-oriented review, a task-shape review, or an ungrouped review.

The first profile supports the existing linear Date Scene profile, stable item stacking,
semantic dependencies, and semantic or presentation annotations. Gate/point objects use
a diamond for planned and an outlined diamond for Actual. Span endpoints retain Core's
half-open interval meaning even where labels display an inclusive end date.

## 4. Scene and target rules

Every emitted primitive carries a deterministic `sceneId`, a `sourceRef`, a primitive
purpose (`planned`, `actual`, `variance`, `annotation`, or `dependency`), and resolved
role/token metadata. The SVG maps these to `data-scene-id`, `data-source-ref`, and
`data-purpose`; it supplies an accessible title/description and a text equivalent for
all non-colour distinctions. An unmatched Actual is displayed in a separate diagnostic
area and never attached by title similarity.

The adapter requires `sourceMetadata`, `accessibleText`, `semanticRoles`, and `marker`
capabilities. Missing requirements block export. Its artifact and manifest are passed
through the existing Output and Release Package boundaries without becoming either
semantic storage or a replacement schedule.

## 5. Explicit non-goals

M14 does not add automatic workflow transitions, progress forecasting, DateTime axis
behavior, resource/cost charts, arbitrary renderer script, PDF/raster output, or
freeform canvas coordinates. Owner/workflow-specific styling needs a later, versioned
Style selector extension; it is not inferred from arbitrary `fields` in this adapter.

## 6. Connection review

| Layer | M14 consumes | M14 must not change |
|---|---|---|
| Project/Scheduler | stable IDs and resolved Date placements | planning semantics or dependencies |
| Actual | latest explicitly supplied observation | schedule, forecast, or alignment |
| View | selection/window/group/order/visibility | colours or coordinates |
| Style/Theme | roles and resolved tokens | selector semantics or token fallback |
| Scene/Output | identity-preserving primitives and capabilities | semantic authority or release acceptance |

This closes the prior direct `Schedule → minimal SVG` shortcut for the review path;
the legacy minimal command remains a compatibility adapter until M14-3 deprecates it.
