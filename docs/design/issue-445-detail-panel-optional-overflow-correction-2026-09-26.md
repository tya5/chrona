# Design Correction — Optional Detail-Panel Overflow (#445)

**Corrects:** `issue-445-detail-panel-readability-design-2026-09-26.md`  
**Status:** Accepted correction before implementation.

## Finding

The initial #445 design correctly prohibited adapter-local text clipping, but
did not specify the completed artifact for an unbreakable detail-panel token
in an optional `clip-optional` slot.  Current SVG/Typst/TikZ Text rendering
has no text clipping primitive, and the v0.5 Scene builder currently emits
all group-detail/milestone `TextPlacement` values unconditionally.  Passing
an oversized natural line through with `clip-optional` would therefore be a
false declaration and a renderer-visible overflow.

## Corrected decision

`clip-optional` means Layout suppresses the affected optional semantic entry
after it has measured and proved it cannot fit, rather than asking an adapter
to crop Text.  Layout retains the completed source identity and measurement in
a structured `FitWarning`:

```text
FitWarning(
  code="W_LAYOUT_DETAIL_PANEL_CLIPPED",
  placement_id=<group-detail or milestone id>,
  source_ref=<source>,
  failure_kind="detail-panel",
  behaviour="clip-optional",
  required_inline=<natural unit width>,
  required_block=<line block extent>,
  available_inline=<panel inline size>,
  available_block=<panel allocation>
)
```

The completed `TextPlacement` is retained internally with
`overflow="suppressed"`, `required=False`, and source content/font facts for
inspection.  It is not projected as a Scene Text primitive.  Scene carries
the warning verbatim, satisfying the observable-disposition rule without
pretending the adapter clipped text.  The Scene builder's generic side-content
emission must consistently skip suppressed placements, as it already does for
member labels and Layout visual resolution.

`ellipsize-with-source` still resolves an oversized unit to measured ellipsis;
`visible-overflow` still emits the natural unit plus
`W_LAYOUT_VISIBLE_OVERFLOW`.  All three dispositions are completed in Layout,
and no legacy `diagnose` behavior is added.

## Why this is the clean boundary

The correction reuses the existing finite suppression representation instead
of adding adapter clip state, a Scene paragraph policy, or an incompatible
Layout Profile syntax.  It preserves the rule that only a source-declared
optional slot may omit a semantic entry; Layout Profile validation already
rejects `clip-optional` for required slots.  It also keeps #446 free to check
the resulting slot/text/warning facts rather than interpreting clipping.

## Required amended evidence

- a direct Layout fixture proves each of visible overflow, ellipsis, and
  optional suppression for an oversized unbreakable unit;
- Scene projection excludes the suppressed Text but serializes its structured
  warning; and
- diagnostic inventory/documentation is regenerated for the new warning.
