# #466 C4 required-treatment implementation amendment

**Amends:** [C4 plan](issue-466-c4-contrast-closure-implementation-plan-2026-09-27.md). **Approved design/review:** [note-treatment amendment](../../design/issue-466-c4-required-note-text-amendment-2026-09-29.md) and [architecture review](../../reviews/current/issue-466-c4-required-note-text-architecture-review-2026-09-29.md) at `5263de61`. C3 public acceptance remains the implementation gate.

Add a note-role-specific `required` treatment invariant at effective Theme closure (`color_scheme.py`), typed Scene construction (the `ScenePrimitive` model), and serialized Scene contrast evaluation (`scene/contrast_policy.py`). Keep the existing numeric contrast function and exact diagnostic pointer family. Extend focused tests for missing/`deemphasized` treatment at all three boundaries, including a Scene payload that bypasses Theme closure; valid other state-text roles retain their current permitted treatments. These changes join C4 Slices 1+2 and the authored Theme roots in the already atomic C4 publication. No View, geometry, schema version or adapter change is authorized.

The [C3 wallboard amendment](../../design/issue-466-c4-wallboard-root-amendment-2026-09-29.md)
adds `examples/halcyon-1/themes/wallboard.yaml` as a seventh authored Theme
root in that atomic publication; repin its derived `12-glyph-gates.yaml` and
test all seven effective declarations.
