# Design Correction: Summary Visual Selector Closure (#350)

**Status:** Complete — replaces the ambiguous `summary.id` target form.

## Finding

A summary panel emits more than one text placement: its header,
`summary:{panel}`, and one or more metric value/caption runs such as
`summary:{panel}:{metric}:value`. The prior `{kind: summary, id}` selector
therefore matches a family rather than one occurrence and violates the
one-target/one-placement invariant.

## Corrected target forms

The generic `summary.id` form is removed. The View discriminated union instead
admits exactly these forms:

| Target selector | Placement |
| --- | --- |
| `{kind: summary, panel}` | `summary:{panel}` header |
| `{kind: summary, panel, metric, part: value}` | `summary:{panel}:{metric}:value` |
| `{kind: summary, panel, metric, part: caption}` | `summary:{panel}:{metric}:caption` |

The View projection owns panel and metric identity; Layout performs only the
literal mapping and rejects an absent result. `part` is required for a metric
target, so no selector can silently decorate both value and caption. Direct
references are admitted; field encoding remains prohibited.

## Architecture review and acceptance

This closes an occurrence identity at View rather than adding a Layout search
policy. It preserves Summary profile fact authority, Theme/Layout/Scene
boundaries, and the no-dead-door constraint. I350R-4 must exercise all three
forms and show that obsolete `summary.id` fails schema validation.
