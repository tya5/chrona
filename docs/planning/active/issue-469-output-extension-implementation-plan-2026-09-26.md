# Implementation Plan — CLI Output Extension and Target Identity (#469)

**Published design base:** `5e749f3fab58b9e0f747a35dfa234264e5ca1d36`.
**Authorities:** [design](../../design/issue-469-output-extension-design-2026-09-26.md),
[whole-architecture review](../../reviews/current/issue-469-output-extension-architecture-review-2026-09-26.md),
[Specification 08 §3.2.1](../../specification/08-scene-and-rendering.md),
and [ADR-0018](../../decisions/ADR-0018-output-capability-contract.md).

## Literal issue acceptance

1. `--output x.png` without `--format` writes a PNG, or fails with a diagnostic naming the mismatch; it never writes SVG bytes to a `.png` path.
2. `--format svg --output x.png` is diagnosed.
3. A CLI test covers each known extension.

## I469-1 — Atomic target negotiation and CLI integration

Own `src/chrona/app/cli.py`, focused `tests/cli/test_cli.py`, and
`docs/guides/first-project.md`. Implement one application-boundary suffix
registry and target negotiation function: five exact suffix mappings,
case-insensitive recognition, extensionless Draft SVG fallback, unknown
suffix rejection, and recognized suffix/target mismatch rejection. Change
only Draft CLI parser default to `None`; pass the resolved target to both
Draft closures and to typesetter identity validation. Validate immutable
`render-review` output against the Context target after its existing format
assertion. Keep Scene, Layout, adapters and public resource schemas untouched.

Focused tests must cover the five known extensions as a table, their
effective targets, case-insensitive suffixes, extensionless behavior,
unknown suffix, no-write explicit conflict, inferred `.typ/.tex` descriptor
failure, `render-workspace` parity, and immutable Context parity. Use a real
bundled Draft render to prove bare `--output x.png` has PNG magic bytes;
check a real explicit mismatch returns the documented JSON diagnostic and
leaves no output. Verify existing binary render and immutable CLI tests.

The new literal diagnostic constructions change
`docs/diagnostics/inventory.md`; regenerate with
`tools/diagnostic_inventory.py`, inspect the generated diff and actionability
classification, and commit it with code. Update parser help and the first-
project guide so users know the five recognized suffixes, extensionless
default and diagnostics. Keep the generated `cli-reference.md` identical
unless the grammar changes; never hand-edit it. Run focused tests,
`tools/diagnostic_inventory.py --check`,
`tools/check_documented_commands.py --check`, full conformance, and the 21
public materializer byte checks. Confirm no generated Scene/SVG diff is
intended; if any appears, review the full batch before publication. Fetch
`origin/main`, inspect exact staged files/ahead-behind/conflicts, publish one
atomic code-plus-evidence commit, confirm remote SHA, and wait for the CI
three-OS full pytest/conformance/wheel and newest-Python materializers.

## I469-2 — Acceptance and closure

Own `docs/reviews/current/issue-469-output-extension-acceptance-review-2026-09-26.md`.
Copy every literal issue criterion into the standard acceptance table, with
direct evidence from real bytes and negative paths. Record exact commits,
commands, CI run, generated inventory diff and public materializer result.
Review CLI/Context authority, target capability and Scene/adapter boundaries,
extension-point behavior, intended incompatibilities and regression impact.
Publish this review separately after I469-1 CI succeeds, verify its own CI,
then close #469 only when all three literal rows are `met` and the release
gate is green.

If implementation reveals an unhandled suffix/target rule or architecture
breach, stop I469-1 and publish a design correction, whole-architecture
review and implementation-plan amendment before resuming code. Do not add a
local conditional or compatibility alias as an unreviewed exception.
