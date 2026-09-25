# Design Correction — Exact Single-Face Draft Scope (#411)

**Status:** accepted correction to the #411 ingress correction.

## Finding

The current Layout measurement contract accepts one `FontMetrics` face for a
render.  Although completed text placements carry a Theme weight, the current
measurement interface has no face-selection argument.  Supplying a regular
system file while a Theme asks the raster adapter to paint a bold role would
therefore violate the core invariant that Layout measures the bytes PNG paints.

## Decision

The first `--system-fonts` release accepts only a resolved Theme whose text
roles all select the same primary family and weight.  Draft ingress derives
that one request from the Theme, resolves and measures exactly that face, and
passes exactly that file to PNG.  A Theme requiring more than one face rejects
with `E_FONT_SYSTEM_MISMATCH`; it never synthesizes, substitutes, or lets the
rasterizer choose a neighbouring weight.

This is deliberately a capability boundary, not a compatibility fallback.
Declared multi-face v3 descriptors retain their existing behavior.  The
future solution is a role/face metric catalog that makes every measurement
call select the same family/weight that its completed placement names.  That
is a broader #410 measurement-contract extension and must be designed and
released atomically rather than embedded incompletely in system discovery.

## Revised acceptance

A uniform-face Theme can render draft SVG and PNG from one installed exact
face without copying font bytes.  A heterogeneous Theme receives an explicit
diagnostic before Layout.  This preserves target honesty while retaining a
useful licensed/corporate-font path for the common uniform-family draft.
