# Design — CLI Output Extension and Target Identity (#469)

**Plan:** [design plan](../planning/active/issue-469-output-extension-design-plan-2026-09-26.md).
**Issue:** [#469](https://github.com/tya5/chrona/issues/469).
**Normative authority:** [Specification 08](../specification/08-scene-and-rendering.md),
§3.2.1, and [ADR-0018](../decisions/ADR-0018-output-capability-contract.md).

## Use cases and selected behavior

1. A Draft user naming `board.png` without `--format` gets a PNG target and
   PNG bytes. The same inference applies to `render-workspace`.
2. A caller naming `board.png` with `--format svg` gets a syntax diagnostic
   before resource closure, rendering, or any output write.
3. An immutable `render-review` target remains the Context's target. Its
   optional `--format` asserts that target; its output suffix must agree with
   that target even when `--format` is omitted.

CLI target negotiation is one application-boundary operation, shared by the
three artifact-writing render commands. It does not change Scene geometry,
adapter byte construction, target capability profiles, or Context identity.

## Filename and target contract

The recognized suffixes, compared case-insensitively on the final path
component only, are exact:

| Suffix | Target kind |
| --- | --- |
| `.svg` | `svg` |
| `.png` | `png` |
| `.pdf` | `pdf` |
| `.typ` | `typst` |
| `.tex` | `tikz` |

No aliases, including `.typst` and `.tikz`, are declared. An absent suffix
is allowed: for Draft without `--format` it selects SVG; with explicit
`--format` it uses that format; for immutable Context it uses the Context
target. An unknown non-empty suffix is rejected with
`E_RENDER_OUTPUT_EXTENSION`, naming the suffix and the recognized suffixes.
This is deliberate: neither silently writing SVG nor guessing a new adapter
from an arbitrary extension is safe. A recognized suffix with a target
different from an explicit Draft `--format` or immutable Context target is
rejected with `E_RENDER_OUTPUT_FORMAT_MISMATCH`, naming both the suffix's
target and the requested/Context target. Both diagnostics are CLI syntax
failures (exit 2, `component=cli`, `sourceRef=/output`) and write no artifact.

For Draft, `--format` becomes optional at the parser boundary (absent is
`None`). One function resolves the effective target from explicit format,
known suffix and extensionless SVG fallback. The effective target is passed
to Draft closure and typesetter descriptor validation; it is not stored in
the filename or inferred by the adapter. For immutable rendering, the
Context target is read first, the existing explicit `--format` assertion is
checked, and the same suffix validator checks that target.

Validation order: unknown suffix; explicit format/suffix mismatch for Draft;
then typesetter descriptor, resource closure, target capability and rendering.
For immutable Context, load/validate Context, assert explicit `--format`,
then validate suffix against its declared target before rendering. A missing
typesetter descriptor for inferred `.typ`/`.tex` remains the existing
`E_RENDER_TYPESETTER_DESCRIPTOR`, not a fallback to SVG. The operation never
creates the output file on any negotiation error; an existing output is not
overwritten by these errors.

## Ownership and migration

The CLI application layer owns output-path convention and diagnostics. Draft
closure owns typed target identity and typesetter environment; immutable
Context owns its declared target. Scene carries completed primitives and
adapters only serialize the selected target. No core resource schema,
materializer manifest, or renderer byte contract changes.

This intentionally removes two old behaviors: `.png` (and other known
suffixes) no longer silently receive SVG when `--format` is omitted, and
unknown suffixes no longer accept arbitrary bytes even with explicit format.
Use a recognized suffix or an extensionless path. Existing explicit
`--format svg --output name.png` is now an error. `.typst`/`.tikz` users
should rename to `.typ`/`.tex` or use extensionless output; this is not a
compatibility alias because it would expand the public convention without
a need in the issue's declared target list.

## Alternatives rejected

- Rejecting every omitted `--format` would keep users writing routine
  explicit flags and is less useful than deterministic inference.
- Inferring in the adapter would put path policy below the target capability
  and Context boundary, permitting Scene/adapter drift.
- Writing declared bytes to a conflicting extension with a warning would
  preserve the exact silent-mislabel failure mode for downstream consumers.

## Acceptance and evidence

CLI tests exercise all five suffixes, case-insensitive recognition, unknown
and extensionless behavior, explicit conflicts, guided Draft, immutable
Context, and no-write errors. Actual PNG magic bytes and SVG/PDF/Typst/TikZ
target selection are checked. Conformance and public materializer checks
must remain green and byte-identical, followed by CI and a literal issue
acceptance review. See the [architecture review](../reviews/current/issue-469-output-extension-architecture-review-2026-09-26.md)
and subsequent implementation plan.
