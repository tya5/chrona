# Design Correction — Independent Row and Group Decoration Policies (#431)

**Corrects:** `issue-431-composited-role-contrast-design-2026-09-26.md`.

## Problem

The #431 witness requirement needs a single grouped slide with row bands,
group bands, group-header bands, axis bands, and closed-day decoration.  The
current View field `rowDecoration.mode` conflates row and group selection:
`alternate-rows` removes group bands, while `none` enables all group bands.
It cannot express the required composition and its name does not state the two
independent ownership decisions.

## Correction

Replace the overloaded field with a closed `backgroundDecoration` object:

```yaml
backgroundDecoration:
  rows: none | alternate
  groups: none | all | alternate
```

Layout owns both selections when composing placements.  It emits each enabled
family independently; Theme still determines only `fill`, `outline`, or the
explicit `none` disposition.  Scene continues to project completed placements
and never decides whether a decoration family should exist.

The migration is intentionally non-compatible: every active View declaration
uses the explicit two-field shape.  Existing output intent maps as follows:

| Previous `rowDecoration.mode` | `backgroundDecoration.rows` | `backgroundDecoration.groups` |
| --- | --- | --- |
| `none` | `none` | `all` |
| `alternate-rows` | `alternate` | `none` |
| `alternate-groups` | `none` | `alternate` |

The selected #431 witness uses `rows: alternate` and `groups: all` alongside
its existing group headers, axis bands, and closed days.

## Architectural consistency

This makes View own semantic decoration selection, Layout own placement, Theme
own explicit absence and paint, Scene own completed transport, and the report
own observation.  It removes an overloaded conditional instead of adding a
witness-specific exception.
