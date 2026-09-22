# Issue 85 — Surface Quality Remediation Design Review

**Reviewed baseline:** `7470ffe851b8055989b8cdd271833448492b838a`
**Design-plan authority:** `issue-85-surface-quality-remediation-design-plan-2026-09-22.md`

## Result

Issue #85 is approved as four ordered, independently verifiable corrections.
The work keeps Project and Actual as semantic truth, makes normalization decide
human-facing values, makes Layout decide every geometry and density outcome,
uses Theme for paint/form intent, and keeps SVG as a serializer of completed
primitive roles.  No correction may be selected by example, slide, or output
target name outside its declared input.

## Closed decisions

### D85-1: Actual absence is a semantic display state

For a table column sourcing `facet: actual` with `missing: in-progress`,
normalization evaluates the selected `ReviewItem` with the Actual-set `asOf`:

| Item / observation condition | Display |
| --- | --- |
| observed actual | formatted actual fact |
| span, no actual, `planned.start ≤ asOf < planned.end` | `in progress` |
| point, no actual | `—` |
| span not started by as-of, or completed planning interval with no actual | `—` |
| no usable as-of fact | `—` |

`in-progress` remains accepted View vocabulary but is no longer a literal
fallback.  The normalizer owns this decision because it owns selected item,
Actual and table-value facts; Layout receives only the resulting string.

`dateRange` is corrected as the current display formatter, not a new schema
syntax: the deterministic `en-US` result is `08 Mar – 06 Apr`, retaining a
year at a cross-year boundary and rendering a point as its date.  Formatting is
explicitly parameterized by the Render Context locale.  Unsupported locale
data is a stable normalization diagnostic rather than host-locale fallback.
The initial public locale is `en-US`; additional declared locale tables are
future data additions, not calls to the host locale.

### D85-2: every plotted text item uses the label candidate solver

Plot member labels and standalone finish deltas both become `LabelRequest`s in
Layout.  Each has measured bounds, an anchor mark, stable identity, candidate
order, timeline bounds, accepted marks, accepted labels, axis text and required
annotations as obstacles.  `auto` tries `start`, then `end`; an explicit side
has one candidate.  No accepted label may overlap any mark, another accepted
label, or leave its timeline bounds.  The declared `suppress` policy produces
an explicit suppressed placement and warning; `diagnose` rejects before Scene.

Finish delta has exactly one representation: it is included in the member-label
request when `visibility.labels.content` names it, otherwise it is its own
candidate request with the existing `finish-delta` semantic.  The former
unconditional coordinate beside the actual/planned finish is deleted.  This is
a Layout refactor, not a Scene coordinate fix.

Table allocation gains a Theme metric `table.column.gutter.inlineSize`.  Layout
subtracts `gutter × (columns − 1)` before feasibility/allocation, records the
same deterministic gutters between placements, and raises
`E_LAYOUT_TABLE_OVERFLOW` if required text plus gutters cannot fit.  It does
not uniformly shrink required text.

### D85-3: present source content and calendar density are Layout facts

Slots are complete-or-diagnose only when their normalized source has content.
A layout slot that intentionally has no selected content is empty; a slot
declared `required` with an authoring contract that requires content is rejected
at normalization.  The shipped ASTER/controller legend slots are intended
content, so their contexts bind a review-detail profile; ASTER also gains the
matching authored profile.  ASTER notes are intentionally optional and the
layout changes that slot priority accordingly.  This distinguishes an authoring
choice from a renderer fallback.

Calendar normalization supplies all closed dates plus the subset caused by
declared non-working exceptions.  Layout chooses candidates using the resolved
`timeline.dayWidth` and optional Theme metric
`timeline.calendarClosed.minimumDayWidth`: at or above the threshold it places
all closed-day bands; below it places only declared exception bands.  The
metric is Theme-owned visual density policy; View only selects whether calendar
and exception shading is eligible.  No alpha is inferred and no renderer makes
the density decision.

Group headers remain a View grouping choice.  When `presentation: header` is
selected, Layout requires the existing group-header metric and places text from
the selected group label.  HALCYON authoring binds the metric only for the
grouped wallboard view; ungrouped briefing/print themes need not carry inert
policy.

### D85-4: Theme form intent is serialized, not inferred

Theme's existing `pattern` token is the completed form intent.  Add optional
typed access to it.  For an SVG Rect, no pattern keeps the existing solid fill;
`outline` serializes as `fill="none"` plus the declared stroke; `diagonal-hatch`
serializes as a deterministic `<pattern>` whose foreground uses the declared
role stroke and whose background remains transparent.  A role naming an
unsupported pattern is a stable renderer diagnostic.

The print Theme declares planned `outline`, actual solid, and missing actual
`diagonal-hatch`, with explicit stroke/fill bindings.  Colour themes remain
unchanged unless their author intentionally adds a pattern.  Scene emits the
same completed semantic primitives; the SVG adapter merely serializes their
declared Theme form.  This is compatible with #122: a future Renderer adapter
must support or diagnose the same resolved form intent.

## Whole-architecture consistency review

| Boundary | Owner and decision | Review result |
| --- | --- | --- |
| Project/Actual → projection | Dates and observations remain authoritative facts. | No scheduler or Project schema change. |
| Projection → content | Actual-state wording and locale formatting are normalized once. | Prevents Layout/renderer semantic interpretation. |
| Content/Theme → Layout | Text measurement, candidates, gutters, group headers and closure density are completed here. | Satisfies Specification 08 §2.2, Specification 50, ADR-0031. |
| Layout → Scene | Completed/suppressed placements become existing semantic primitives. | Scene does not measure or choose coordinates. |
| Theme → renderer | Theme provides explicit colour/stroke/pattern tokens. | Renderer serializes, never chooses which role gets a form. |
| Renderer targets | SVG implements the declared form vocabulary. | #122 can expose this as a shared Renderer capability later. |

Issue #94's completed content boundary remains intact: calendar-exception
facts are explicit `SurfaceContentInput` fields, not rediscovered by Scene;
#99's typed closure boundary remains the sole resource ingress.  This design
adds no raw YAML access to Layout or renderer modules.

## Delivery slices

1. **C85-1 — table semantic correctness.** Context-locale date range
   formatting and conditional Actual absence; neutral tests and HALCYON
   materializer evidence.  Remove point-row property pins.
2. **C85-2 — text and table feasibility.** Generic LabelRequest placement for
   standalone deltas, table gutter metric/allocation, and neutral collision
   tests.  Adapt affected themes/layouts; remove plot overlap/viewport pins.
3. **C85-3 — source completion and density.** Bind authored legend content,
   correct optional ASTER notes, add calendar exception facts/density metric,
   and verify group-header intent.  Remove empty-slot pins and inspect all
   changed public SVGs.
4. **C85-4 — monochrome form serialization.** Add pattern access/definitions,
   print Theme form declarations, renderer contract tests and visual evidence.
5. **C85-5 — release review.** Full suite, property gate with no #85 pins,
   conformance, source-structure inspection, five materializers, generated
   diff review and visual review of all changed slides.

Each source slice has a separate implementation PR.  No next slice starts
until the prior one is merged, and its materializer evidence must remain valid.

## Acceptance

All current #85 output-property fingerprints are removed without adding new
ones.  Date/Actual table content is semantically correct; all accepted plot
text is bounded and non-overlapping; tables reserve positive gutters; required
legend/group content is present; narrow scales reduce closure noise without
dropping exceptions; and print mono distinguishes plan, actual and missing
actual by declared form.  The public generated artifacts change only where
these declared corrections require it.

## Authorization

This review authorizes the Issue #85 implementation plan, then only C85-1 in
that plan.  C85-2 through C85-5 each require C85-1's published merge and the
same remote-main/CI publication gate.
