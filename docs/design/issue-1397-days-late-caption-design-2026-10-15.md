# Issue 1397 row 3 — deadline captions

Design complete for implementation planning. [Plan](../planning/active/issue-1397-days-late-caption-design-plan-2026-10-15.md).
Supersedes the provisional caption recommendations on branch
`wip/issue-1397-row3-caption-note`, not the other deadline rows.

## Authoring and normalized intent

```yaml
deadlines:
  show: slipped
  caption:
    template: "{daysLate} days late"
    format: {form: english-words, capitalize: true}
```

`caption` is optional in the existing v0.28 deadline object. It requires a
nonempty, single-line `template`; optional `format` references the shared
`countTextFormat` definition. The runtime default is digits, minimumDigits 1,
capitalize false. The shared parser accepts only `{daysLate}` and literal
`{{`/`}}`; no figure references or inline role marks. Literal-only templates
are allowed, like other text templates. Malformed templates fail with
`E_VIEW_DEADLINE_CAPTION_TEMPLATE` at `/body/deadlines/caption/template`.
Invalid formats and unsupported numeric ranges retain the existing
`E_VIEW_FIGURE_FORMAT_INVALID` / `E_VIEW_FIGURE_FORMAT_RANGE` codes, with the
caption format pointer. No invented figure identity or fallback format.

Normalize deadlines into typed display/caption intent, replacing the internal
show-string field rather than maintaining two competing contracts. The Core
still owns `DeadlineStatus.days_late` and its slipped verdict. The use case
passes both into the review projection and expands the parsed caption with
`format_count`; Layout receives completed author text, never a template or
count-format evaluator. Expand only for slipped, View-shown deadlines. A kept
deadline under `show: all` never requests a caption. No calendar, domain fact,
figure scope, scheduler, or `W_DEADLINE` behavior changes.

## Typography and semantic identity

Register `deadlineCaption` as Text, purpose `deadline-caption`, ground text.
Default typography and paint use the existing Theme `text` role. A Theme may
declare `deadline-caption` to tune its typography; its own `fill`, when bound,
selects caption ink, otherwise the explicit `text` paint alternative applies,
as with existing heading roles. Caption ink remains subject to the required
4.5:1 ground-text gate. It never borrows `deadline-mark.stroke` or its 3:1 mark
classification. This corrects the provisional draft and needs no Theme
migration. Register the optional text role with the existing measurement,
Text paint and viewer-fit capabilities, not Path capabilities.

One caption belongs to each drawable planned host occurrence, not to snapshots,
scenarios or folded headers. Placement id is `deadline-caption:<mark instance>`;
sourceRef is the Project object id and slot is timeline. The anchor retains
the planned placement identity, but an outside caption MUST NOT set
`hostPlacementId`: that existing contract means text contained inside its host.
Carry typed subjects on TextPlacement into primitive provenance instead of
inferring ownership from a drawing id. Carry the same subjects to diagnostics and
Scene. The existing outside-window/folded diagnostics remain authoritative;
no extra caption-drop count is emitted when no deadline run is drawn.

## Layout and omission

The caption is optional decoration: complete existing member labels, routes,
relation labels and annotations first. Do not reroute a relation or evict its
label to make room. Then, in Project and planned-host order:

1. Measure once using the selected text role and existing Layout text helpers.
   Vertically center the completed text box on the run's horizontal line.
2. Try immediately right of the clipped run end, then immediately left of the
   tick. Each offset includes the completed deadline ink envelope plus the
   existing typography-relative label gap `max(1px, fontSize / 4)`.
3. Require full text bounds inside the plot and no collision with completed
   marks, required text/label visuals, routes, annotations, deadline ink, or
   previously accepted captions. Use the existing obstacle predicate; no host
   exemption permits text to cover its bar. Opaque outline grounds and declared
   maximum wobble envelopes count as deadline ink. Reuse the Layout-owned
   stroke-envelope calculation; Scene does not supply geometry.
4. Accept the first fit and register its bounds for later captions. If neither
   fits, omit only that caption. Emit counted
   `I_LAYOUT_DEADLINE_CAPTION_DROPPED` through the existing typed presentation
   info channel (surface and positive occurrence count), with explicit subjects
   for dropped hosts. Tick/run and all prior placements remain unchanged.

Layout returns complete TextPlacements (bounds, baseline, lines, treatment,
font asset identity and explicit subjects). Scene emits them through the ordinary
semantic text path and paint/contrast gates. SVG/PDF/typeset adapters serialize
the same primitives without choosing positions or reformatting days.

## Compatibility and verification

Absent caption returns before new role lookup, measurement or obstacle work;
existing resources and generated visual bytes remain unchanged. The typed
internal show-string contract changes cleanly; update its callers and tests
without a compatibility branch. No public schema version bump (Spec 56).
Acceptance evidence is defined once in the linked plan; the implementation
plan identifies exact tests and publication units.
