# I310 Design Correction: Explicit Text-on-Mark Scheme Intent

## Trigger

The approved I310 design requires `memberLabelInside.fill` to meet the
contrast threshold against every eligible comparison-mark fill.  The current
Scheme vocabulary has no intent that can satisfy that requirement for the
public accent, positive, neutral, and warning fills.  Reusing `text` would
silently weaken the safety contract: for example, the executive `text` color
does not meet the threshold on its accent fill.

## Corrected design

Color Scheme v0.1 gains the required `textOnMark` color intent.  Its value is
validated like every other Scheme color and is intended only for text placed
inside a colored mark.  Theme binds `memberLabelInside.fill` to `textOnMark`.

During Theme resolution, Chrona resolves `memberLabelInside.fill` and each
eligible automatic-member-mark fill (`planned`, `actual`, `snapshot`, and
`scenario`) then verifies a contrast ratio of at least 4.5.  A missing binding,
non-color token, or insufficient pair rejects the closure with the stable
`E_SCHEME_INSIDE_LABEL_CONTRAST` diagnostic.  The check is conservative and
does not inspect renderer output or choose colors by source object.

## Architecture review

The correction keeps the responsibility chain intact: Scheme supplies a
semantic palette intent; Theme selects it for an explicit Scene role; Layout
selects the measured `inside` rung only when it fits; Scene projects the
completed selected-rung role; adapters serialize it without contrast policy.
No Project data, renderer branch, or literal primitive color is introduced.

## Implementation amendment

I310 updates the Scheme schema/resolver and every public Scheme atomically
with the Theme bindings and contrast tests.  The existing inside-label schema,
Layout fallback, and Scene-role work remains unpublished until this correction
is merged.  `auto` must continue to exclude `inside`; it becomes available only
through an explicit primary side, fallback ladder, or row/item intent.
