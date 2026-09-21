# M27 v0.5 Scene Migration Design Review — 2026-09-21

**Decision:** The migration amendment is closed and implementation planning is
authorized.

The review confirms that Specification 37 supplies the previously missing runtime
bridge without reviving legacy settings, Theme shapes, or a parallel layout grammar.
ThemeTokenView is derived from the immutable current closure, Layout Manifest remains
the sole geometry boundary, and `SceneSurface` remains the only public SVG input. All
display distinctions remain selected through editable current resources.

The runtime has no new semantic authority, persistent schema, output target, or
example-specific branch. Its required diagnostics and A27 fixtures cover missing
tokens, missing slots, measured axis overflow, incomplete normalized input, and
deterministic reproduction. A corrected implementation plan may now authorize code.
