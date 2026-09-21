# M27 v0.5 SVG Role Contract Design Amendment — 2026-09-21

**Status:** Design correction complete; I27-R3 implementation authorized.

The current Theme v0.2 schema already permits semantic color bindings, but the
published example themes do not bind every role required by the completed v0.5 Scene.
The SVG adapter must not introduce fallback colors. Therefore, an SVG-capable resolved
Theme MUST bind: `background.fill`, `text.fill`, `table-header.fill`,
`axis-major.stroke`, `planned.fill`, `actual.fill`, `missing-actual.fill`,
`variance-ahead.fill`, `variance-on-track.fill`, `variance-behind.fill`,
`dependency.stroke`, and `annotation.fill`/`annotation.stroke` when that optional
family is selected. Group roles remain explicit existing `group:<id>.fill` or the
generic `group-band.fill` selected in Scene construction.

These are semantic current-Theme bindings to Color Scheme intents, not a legacy paint
map. A selected required primitive whose binding is absent diagnoses
`E_THEME_ROLE_REQUIRED` before SVG output.
