# Architecture Review — Project-Generic Presets (#479)

**Decision:** design approved; implementation is sequenced after #467 L3. **Reviewed:** [#479 design](../../design/issue-479-project-generic-presets-design-2026-09-27.md).

| Boundary | Result |
| --- | --- |
| View / Projection | Group order and the first-appearance domain are derived from selected items in Projection, where group keys already live. |
| Theme / Scheme | `palette` is an ordered list of existing category slots; #421's check covers wrap-around. |
| Preset package | Two optional fields in v0.1, following the repository's in-place additive practice; explicit CLI flags keep precedence. |
| CLI / visual profiles | The preferred profile is validated against the target kind; no silent upgrade beyond the preset's declaration. |
| #467 | Lanes change the preset Views first; #479 edits them afterwards. |

**Risk:** the palette wrap-around on projects with many groups yields separability warnings. That is intended and visible.
