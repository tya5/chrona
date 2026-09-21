# Review Presentation Policy Binding

**Status:** Proposed — M27 D27-3
**Depends on:** Specifications 06, 07, 08, 24, 25, 26, 28, 30, and 33; ADR-0028.
**Owns:** the mapping of declared presentation resources to completed Review Scene
families. It creates no new semantic Project data or renderer configuration resource.

## 1. Policy closure

All Review SVG display policy is resolved before Scene construction. M27 requires no
new user-facing resource type or schema version: the required fields are already owned
by the resolved View, Review Detail Profile, Summary Profile, Layout Profile, Theme,
Color Scheme, and Render Context. An absent required field is a validation or resolved
input diagnostic, never a renderer fallback.

| Scene family | Selection/wording owner | Geometry owner | Decoration owner | Required diagnostic |
|---|---|---|---|---|
| Heading, subtitle | Detail templates + closed template values | title slot / measured text | Theme typography/text roles | `E_PRESENTATION_INPUT_INCOMPLETE` |
| Table header/cell | View `tableColumns`, including `missing` | table slot / measured columns | Theme table/text roles | `E_PRESENTATION_INPUT_INCOMPLETE` |
| Axis band, tick, label | Layout axis levels/formatting + Context locale | axis/timeline slots; measured label | Theme axis roles | `E_PRESENTATION_OUTPUT_OVERFLOW` |
| Group band/header/separator/row shade | View grouping and selected profile mode | timeline rows/groups | Theme group and row paints | `E_PRESENTATION_INPUT_INCOMPLETE` |
| Planned/baseline/Actual/milestone | View comparison facets + Style roles | timeline scale and lanes | Theme mark tokens | `E_PRESENTATION_PRIMITIVE_MISSING` |
| Variance/missing Actual | View facets + Detail wording | mark ports / lanes | Theme marker and pattern tokens | `E_PRESENTATION_INPUT_INCOMPLETE` |
| Dependency/leader/arrow | View relations/annotations + routing policy | finite router and obstacles | Theme stroke/marker tokens | `E_PRESENTATION_OUTPUT_OVERFLOW` |
| Legend/coverage | Detail profile | legend slot / measured text | Theme legend roles | `E_PRESENTATION_INPUT_INCOMPLETE` |
| Notes, group detail, observations, milestones | View annotations + Detail profile | respective resolved slot / measured text | Theme notes/detail roles | `E_PRESENTATION_INPUT_INCOMPLETE` |
| Summary panel | Summary profile | summary slot / measured panel | Theme summary roles | `E_PRESENTATION_INPUT_INCOMPLETE` |

## 2. Complete-or-absent slot rule

A Layout Profile source remains a region request, not an implicit request for an
unrelated panel. If it is present, its associated resolved input family is either:

1. non-empty and emitted completely; or
2. empty and explicitly permitted by the selected Detail/Summary Profile; or
3. rejected before SVG creation.

`title`, `table`, `timeline`, and `timeline-axis` are always required by the Review
surface. A present `legend`, `notes`, `group-details`, `observations`, `milestones`, or
`summary` slot must not be silently reserved and left blank because the composer lacks
an implementation.

## 3. Canonical declarative policy fixture

The following fixture is design evidence for one generic Review surface. It identifies
the resource choices required for complete output; it is not a preset ID branch and is
validated as real resources in D27-4.

```yaml
reviewPolicy:
  view:
    grouping: {by: field, field: team, order: [platform, firmware], missing: unassigned}
    comparison:
      facets: [planned, actual, finishDelta, missingActual, unmatchedActual]
    tableColumns:
      - {id: Activity, source: title, missing: blank}
      - {id: Review, source: {field: review}, missing: em-dash}
  detail:
    heading: "{title}"
    subtitle: "{windowStart} – {windowLastVisible}"
    legend: [planned, actual, variance, milestone, missingActual]
    missingActualLabel: "Actual not reported"
  layout:
    sources: [title, table, timeline, timeline-axis, legend, notes, group-details, observations, milestones, summary]
    axis: {levels: [quarter, month], formatting: {quarter: year-quarter, month: short-month}}
  theme:
    roles: [heading, subtitle, body, axis-major, planned, actual, milestone, variance-behind, missing-actual, legend, summaryHeader]
  target: {kind: svg, capabilities: [sourceMetadata, accessibleText, semanticRoles, marker, tableSemantics, hierarchicalAxis]}
```

## 4. Explicit prohibitions

- A module MUST NOT select policy by Project ID, View ID, example manifest, output
  filename, locale of the host process, or a renderer-specific configuration file.
- A missing table value enum MUST NOT appear as literal source text.
- A 28-day numeric stride, ISO label fallback, default font size, default marker, or
  default missing-Actual wording MUST NOT appear in Scene or SVG code.
- Color Scheme may change only resolved color values; it does not change semantic
  facets, typography, geometry, wording, or primitive presence.
