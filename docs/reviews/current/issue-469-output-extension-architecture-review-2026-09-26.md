# Architecture Review — CLI Output Extension and Target Identity (#469)

**Reviewed:** [design](../../design/issue-469-output-extension-design-2026-09-26.md)
against [Specification 08](../../specification/08-scene-and-rendering.md),
[Specification 22](../../specification/22-output-release-successor.md),
[ADR-0018](../../decisions/ADR-0018-output-capability-contract.md),
Draft closure, immutable Context ingress, CLI diagnostics, and output tests.

## Boundary findings

- Draft target identity remains explicit before closure construction. The
  filename is only CLI ingress metadata, not a new field in Project, View,
  Theme, Layout, Scene, Context, or adapter output.
- Immutable Context authority is preserved: `--format` can assert but not
  replace its target, and the suffix must match that target. No derived
  adapter can reinterpret a completed Scene because of filename spelling.
- The rule is independent of Layout geometry, Scene projection, visual
  capability profiles, output-manifest identity, and release package
  semantics. Specification 22 and ADR-0018 therefore require no semantic
  change; Specification 08 §3.2.1 records the CLI boundary rule.
- The typesetter descriptor is checked after inferred target selection. This
  preserves a single target truth for `.typ` and `.tex` and prevents SVG
  fallback on missing environment data.
- Existing CLI JSON diagnostics are the right failure channel. Suffix errors
  are usage errors before artifact creation, not Scene warnings or adapter
  fidelity loss. The diagnostic inventory and CLI reference must include the
  two new codes.

## Decision and risks

Accepted for implementation planning. The exact five-suffix registry and
unknown-suffix rejection are intentionally incompatible with old arbitrary
extension behavior; the [design](../../design/issue-469-output-extension-design-2026-09-26.md)
specifies migration. No unresolved architectural blocker remains. Verify
that all existing public materializer paths use matching or extensionless
names, and test the immutable and guided paths so a render-only fix does not
leave the same mismatch elsewhere. No product code should be changed before
the implementation plan is published.
