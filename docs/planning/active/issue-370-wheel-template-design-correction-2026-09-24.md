# Issue 370 wheel template design correction

**Status:** Accepted correction before release gate completion

## Finding

The executable README sequence exposed a release-only defect: `chrona init`
located `examples/halcyon-1` by walking from the source module path.  This
works in an editable checkout but the examples are not wheel data, so an
installed wheel rejects its only supported template with `E_INIT_EXAMPLE`.

## Decision

The initialized `halcyon-1` template is a packaged, immutable application
resource at `chrona.resources/examples/halcyon-1`; the package resource tree
is the exact runtime copy of the corpus template.  The initialization use case
reads it through `importlib.resources`, recursively
copies its bytes into the destination, then performs its existing local
immutable closure construction.  It does not retain a source-checkout path,
add a fallback search path, or make the installed template a mutable Store
input.

The public output remains an ordinary user-owned directory.  The packaged tree
is only Stage-1 seed content; copied Contexts still name local immutable
snapshots and the generated Store configuration as before.

## Architecture review

| Boundary | Result |
| --- | --- |
| Package data | Build configuration owns inclusion; use case reads resource API only. |
| Init use case | Copies declared template and builds closure; no CLI formatting or source-root discovery. |
| Store/Context | Existing local snapshot and identity rules are unchanged. |
| Wheel smoke | Runs the real installed script outside checkout and proves the public README flow. |

No compatibility path is retained for an arbitrary adjacent source `examples/`
directory.  The package resource tree is the one runtime resource address.
