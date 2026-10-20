# Issue1827 — Theme reference and copy-ID correction

[Pre-code plan/design/architecture review](https://github.com/tya5/chrona/issues/1827#issuecomment-6293022355).
Reference implementation `f7fbf8533`; the [bounded row6 correction](https://github.com/tya5/chrona/issues/1827#issuecomment-6294442418)
follows merged B implementation1835. Other row ownership is unchanged; parent1827 remains open.

| Literal row1 acceptance | Disposition | Evidence |
| --- | --- | --- |
| a reference page (role → what it paints → which tokens), generated from the vocabulary resource where possible, so it cannot drift. Linked from the skill. | focused/package checks met; release pending | `skills/chrona/references/theme-role-reference.md` projects every packaged semantic and registered Theme consumer/property contract. `tools/theme_role_reference.py --check` rejects stale bytes; its conformance gate also runs for docs-only PRs. `SKILL.md` links the portable reference and remains200 lines. Generator/link/copy/wheel tests pass. |
| preset copy --id NEW renames consistently; the sort rule is either removed or stated in the error. | focused checks met; release pending | Existing B source copies every declared resource consistently and states the token sort rule. The correction reuses Layout's ID schema before writing and quotes YAML scalars. The24-test catalogue batch covers absent/existing-empty destination preservation, digit-leading/257-character refusal,256-character acceptance and all15 presets across9 YAML-like names. Actual CLI renders pass for an ordinary name, true/null/yes and the256-character boundary. |

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

The copy correction stays at the usecase serialization/preflight boundary:
no schema widening, resource-identity compatibility alias or pinned-catalog edit.
