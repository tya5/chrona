# Issue1827 — row1 Theme authoring reference

[Pre-code plan/design/architecture review](https://github.com/tya5/chrona/issues/1827#issuecomment-6293022355).
Implementation `f7fbf8533`; rows2–6 belong to dev B, so parent1827 remains open.

| Literal row1 acceptance | Disposition | Evidence |
| --- | --- | --- |
| a reference page (role → what it paints → which tokens), generated from the vocabulary resource where possible, so it cannot drift. Linked from the skill. | focused/package checks met; release pending | `skills/chrona/references/theme-role-reference.md` projects every packaged semantic and registered Theme consumer/property contract. `tools/theme_role_reference.py --check` rejects stale bytes; its conformance gate also runs for docs-only PRs. `SKILL.md` links the portable reference and remains200 lines. Generator/link/copy/wheel tests pass. |

Architecture: no new runtime registry/schema or Theme/paint behavior. The table
distinguishes Scene paint roles from Theme geometry/measurement roles and named
value tokens from Color Scheme intents. Point paint notes use the existing
resolver: planned/gate, not an inference from the Detail key named milestone.
Layout Profile `viewDefaults` and explicit View precedence are described at their
actual owners. Circle, small-caps and legend-role guidance uses current contracts;
wording keys are not presented as role IDs. Repository-only regeneration is marked.

Focused45 generator/conformance-runner/skill/link/copy/wheel tests pass, then10
generator/runner tests pass after tightening exact row matching (overlap).
An actual wheel was built and inspected: packaged reference bytes equal the
source (SHA2566334ec588da5d2ab12c91393b81bf0e8b51268f049a35470c8abca2fa32acdbc),
and packaged `SKILL.md` retains the link and exact source bytes. No renderer,
schema, example or public generated artifact is authored. Shared publication
with the independent1830 layout fix may change public geometry only through that
fix; the official batch audit and exact-main three-OS release remain required.
