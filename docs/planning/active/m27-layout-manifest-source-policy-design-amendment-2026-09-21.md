# M27 Layout Manifest Source Policy Design Amendment — 2026-09-21

**Status:** Design correction complete; R3B2 is paused pending Manifest implementation.

`LayoutDecision` currently records a source but not the source's declared priority or
overflow policy. A v0.5 Scene cannot truthfully decide whether an absent Detail family
is legal from that incomplete output. The Layout Manifest therefore gains immutable
`priority` and `overflow` fields for slot decisions, copied verbatim from the resolved
Layout Profile during solve. Non-slot decisions carry `null` values.

The v0.5 Detail resolver consumes these fields only from the Manifest. It MUST NOT
re-read the Layout Profile or recreate a Settings-shaped compatibility object. This is
a derived-manifest extension, not a new authoring resource or legacy rollback.
