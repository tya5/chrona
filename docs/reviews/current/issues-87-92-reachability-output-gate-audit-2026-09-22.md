# #87 and #92 Reachability and Output Gate Audit

## #92

The six superseded presentation modules and two obsolete compatibility shims
were deleted in `96dfc75`.  `tools/check_module_reachability.py` starts at CLI,
conformance, and tool entry points, rejects every unlisted orphan and every
revived staged module, and runs in both CI platforms.  At this audit it reports
`53 modules reachable, 0 staged, none orphaned`.  The former dual Scene/SVG and
surface-content paths are absent from the source tree.

## #87

The public `materialize` path renders every declared example in check mode.
`test_closure_inputs_are_read` rejects a Context input that the render fails to
consume.  `test_generated_output_properties` asserts placement/viewport/slot
semantics over generated SVG rather than trusting byte identity; its pinned
failure file has no active entries.  These checks run with the full pytest suite
on macOS and Ubuntu.

## Architecture review and disposition

The gates preserve the intended ownership: closure resolves inputs, Layout owns
geometry, Scene projects completed primitives, and renderers serialize.  The
lint does not treat test imports as a product route, so tests cannot keep a
superseded implementation alive.  New features must add a public-boundary test
and semantic output properties where they affect visible placement.  #92 and
#87 satisfy their acceptance intent and may close after this audit is merged.
