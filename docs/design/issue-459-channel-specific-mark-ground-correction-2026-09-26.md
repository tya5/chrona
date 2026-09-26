# Design Correction — Channel-Specific Mark Ground (#459)

The #459 probe found that HALCYON's categorical planned fill and group
background intentionally share the same Scheme category slot. Darkening that
slot changes both and cannot create contrast. Treating the existing mark's
stroke as a visible outline is a clean structural solution under Specification
46's already-declared dual-channel mark contract; it requires no new public
schema or colour-scale syntax.

## Selected channel rule

For a filled Rect, evaluate its fill at bounds centre. If it also has a
positive-width stroke, evaluate the stroke at the left-edge block midpoint.
Each channel has its own topmost earlier opaque ground at its own painted
sample. For a stroke-only Rect, evaluate only its painted edge. For a Symbol,
use the completed bounds centre for fill and left-edge midpoint for stroke as
finite outline approximations. The mark passes if at least one painted
channel meets its floor; the finding reports the winning channel, that
channel's sample coordinate, ground identity/kind/colour, and ratio. A
non-flat/transparent host beneath one channel is not silently replaced with
canvas: that channel is unsupported; a different, fully evaluable channel may
still carry the mark. For Text, only the fill is evaluated.

Theme roles may supply an explicit contrasting stroke and width to preserve a
light categorical fill while making the mark's outline visible. In particular,
planned, actual, snapshot, missing-actual, network-node and progress-fill may
need this treatment. The `calendar-closed` decoration remains stroke-only and
must be recoloured against its actual surface. The design does not make the
Scene observer invent strokes: the completed Scene and adapter both receive
the Theme-selected channels.

## Whole-architecture check and migration

Scheme categories retain semantic colour identity. Theme chooses the outline
role and stroke width. Layout geometry is unchanged; Scene preserves dual
channels and paint order; adapters serialize both explicitly. This is
consistent with Specification 46 and the existing Color Scale owner. It
avoids an invented dark category palette or renderer-side halo. The #459
implementation plan must cover channel-specific tests and atomic Theme/Scheme
plus public-artifact migration. Published base: `3043a1b1`.
