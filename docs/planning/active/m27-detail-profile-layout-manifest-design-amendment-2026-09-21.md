# M27 Detail Profile Layout Manifest Design Amendment — 2026-09-21

**Status:** Design correction complete; I27-R3B2 implementation is authorized.

The existing Review Detail resolver validates slots through deleted Settings layout
data. v0.5 replaces that input with the immutable `LayoutManifest`: it derives the
set of sources and each source's required/optional priority from its decisions. Detail
resolution accepts the current Detail Profile, selected projection items, and this
derived source policy only.

Group details, milestones, and observations are included precisely when their current
Detail Profile section and matching Layout source are present. A Detail section with no
matching source is `E_DETAIL_SLOT_REQUIRED`; a required Layout source with no section
is `E_LAYOUT_SOURCE_UNAVAILABLE`. No Settings compatibility parameter or layout
fallback is permitted.
