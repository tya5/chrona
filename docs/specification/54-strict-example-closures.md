# Strict canonical example closures for Issue #54

## Decision

#44's content-identity field is optional for general resource references. Canonical examples
used as reproducible public evidence are a stricter product profile: their closure is fully
pinned.

## Strict example profile

For each context selected by an example manifest, the materializer requires a
`contentIdentity` for:

- the context's project, view, theme, color scheme, and layout references;
- every selected input reference, including nested snapshot-project references; and
- every declared font-metrics asset.

The materializer copies authored bytes unchanged, verifies each present digest against those
bytes, and passes the resulting closure to the strict CLI. It never adds, removes, or rewrites
a pin.

A non-example caller may use the normal #44 opt-in policy. The strictness belongs to the
canonical example-materializer profile, not to the generic reference format.

## Diagnostics

Before invoking the CLI, a missing required strict-example identity yields
`E_CONTENT_IDENTITY_REQUIRED` with the authored context path of the reference or font asset.
A supplied resource digest mismatch yields `E_CONTENT_IDENTITY`; a supplied font-asset
digest mismatch yields `E_MATERIALIZER_FONT_IDENTITY`. No missing pin may surface as an
unrelated font-resolution diagnostic.

## Evidence

A generated SVG is accepted only after strict closure validation and public CLI rendering.
Check mode and `--write` use the same validation path; `--write` cannot replace evidence
after any closure failure. All canonical contexts must byte-reproduce without `--write`.
