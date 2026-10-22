# 44. Usable explicit rows and annotation rail

## Explicit-row members

Each explicit ReviewRow member remains an independently addressable ReviewItem. When `visibility.labels` is enabled, Scene composition emits one member-label Text primitive adjacent to that member's mark, using the item's title and the `text` role. Automatic rows retain their existing table label behavior; this rule introduces no new table source or renderer contract.

Mark geometry is independent of the number of members in its row. Theme metric `timeline.mark.blockSize` supplies the common mark block size. Layout may offset stacked members vertically, but it MUST NOT shrink their mark size as member count rises. If the requested row cannot accommodate the resulting stacked tracks, Layout grows the row naturally and records visible overflow; it does not refuse a valid fit shortage.

Each mark contributes concrete start/end ports. A relation between members of the same row routes between their distinct mark ports; a coincident port is rejected as `E_PRESENTATION_ROUTE_UNAVAILABLE`, never passed as a one-point Path to a renderer.

A snapshot member uses visual role `snapshot`; Theme defines `snapshot.fill`. Primary uses `planned` and actual uses `actual`. No legacy Theme/Settings paint map is consulted.

## Annotation rail

The rail is one configuration of the [unified annotation candidate model](06-view-model.md#9-annotations-and-layout-intent): an `annotations` slot region, row-aligned search, shared completed-surface obstacle query and leader connector from the mark port. Timeline row rectangles are not candidate-placement obstacles. Layout completes the box and leader; Scene projects them unchanged. Legacy rail declarations retain their normalized intent; completion follows the current safety and declared overflow policies.

A required annotation does not authorize a box over another object's mark.
A declared rail leader follows Specification33's mandatory-connection rule:
clear routing first, then an explicitly diagnosed hairline naming crossed
obstacles rather than losing its leader. This is a connector-only exception;
plot callouts/tails stay strict. Box exhaustion follows Specification33's explicit
terminal-list/suppression rule; Layout does not invent a destination.
An optional annotation may be omitted only under its explicit policy.

A slot declaring `visible-overflow` permits the full natural frame's inline
overhang while searching the same finite vertical positions against the
shared obstacle inventory. This preserves Specification07's unbreakable or
explicitly nonwrapping filled-note text; overhang alone is not an unsafe
candidate. The whole frame must still clear other completed content and any
required leader must complete atomically, either clear or with the explicitly
diagnosed rail-crossing disposition. Track full box extents, not only
body text. The box and required heading/body text carry the visible-overflow
disposition and existing note-named warnings. When no safe box completes, the
explicit terminal list naturally stacks below preceding boxes and list
records as specified in Specification33. Physical anchor order and View-order
ties apply; required peer notes must not share a clamped fallback position.

## Reusable Project-note placement (#1343)

The two new declarations are table-timeline intent and follow the existing
dependency-network exclusion of annotation placement; network Views reject
them rather than silently ignoring completed-note intent.
Project annotations remain the authority for narrative text, kind and
`anchor.object`. An effective View MAY declare
`annotationBindings`, an ordered finite list of `{kind, temporalKind, purpose,
facet, endpoint}`. `kind` matches the exact Project kind; `temporalKind` is
`point`, `span` or `any`, classified from the selected object's resolved
planned temporal shape, never its painted mark or Actual availability.
Purpose, facet and endpoint reuse the existing annotation vocabulary.
Bindings contain no Project IDs, coordinates or executable selectors.

`annotationPlacement` maps purpose to one existing placement spelling:
`{candidates: [...]}` or `{placement: ...}`. It introduces no alternative
candidate language. The Layout profile MAY offer this map through
`viewDefaults.annotationPlacement`; a View's declared map replaces that
whole member, including an explicitly empty map. Kind-to-purpose and
facet/endpoint bindings belong to the connector View, not the Layout profile.

When annotations are visible, expansion considers each Project note whose
anchor object has a selected primary/combined occurrence or folded point.
Ghosts do not create duplicate notes. The first matching binding wins;
within each binding, notes sort by their Project annotation key. Unmatched
kinds and unselected anchors retain the existing unconsumed notes-slot
behavior. Missing requested facet/endpoint geometry retains the existing
Layout anchor diagnostic; no fallback facet or guessed coordinate is added.

Explicit `annotations` retain their declared order and existing behavior.
Any explicit `projectAnnotation` reference overrides automatic expansion of
that note; multiple explicit occurrences remain explicit author intent.
Automatic notes follow the explicit list in binding/key order. An automatic
ID is `<Project annotation key>-<purpose>`. A collision with another final ID
rejects as `E_PRESENTATION_ANNOTATION_IDENTITY`, with both source references;
it never silently replaces an unrelated explicit annotation. Automatic notes
consume Project narrative once and do not duplicate it in the notes slot.
An explicit annotation without candidates/placement MAY inherit its purpose
policy; declared candidates/placement replace that policy without merging.
An unresolved policy rejects as `E_PRESENTATION_ANNOTATION_POLICY_MISSING`.

Pure Presentation normalization closes selection, identity, narrative and
typed anchor intent without mutating Project or resource inputs. Generated
anchor diagnostics reference `/annotations/<escaped key>/anchor` in the
Project, not an invented View-list index. Layout receives the resulting
ordinary typed annotation intents and owns measurement, candidate search,
obstacles, box and connector geometry. Scene/adapters remain projection.
Both natural slot measurement and placement consume this same closed intent:
annotation SourceInput includes resolved narrative/numbering/visual advances,
and notes SourceInput includes only unconsumed notes. Neither re-reads the raw
View list or counts consumed Project notes. This corrects the existing
prefix-only measurement of Project-referenced annotations. Legacy naturally
sized annotation/notes hosts may change allocation; fixed five-design note
placement and serialized SVG remain acceptance gates. Existing explicit
selection/identity/candidates are not changed or kept behind a compatibility
measurement path.

## Boundary with slide vocabulary

This specification deliberately excludes overlay tracks, group headers, calendar bands/as-of markers, legend swatches, and configurable label formats. Those are additive Review vocabulary owned by #42.
