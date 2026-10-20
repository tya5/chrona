# Issue 344 — Level 1 object-reference slice

**Disposition:** the reviewer-selected Level 1 slice is released; the wider
issue remains open. The [reviewer acceptance](https://github.com/tya5/chrona/issues/344#issuecomment-6290785975)
defines this slice. Normative Specs 06/07/17/60 and the namespace correction
preceded implementation.

**Review-containing main:** `53bbcc9900ebba3d6490ad0dfe1ccb81b84c7948`.
**Release:** [39444807924](https://github.com/tya5/chrona/actions/runs/39444807924)
passed full pytest, conformance and wheel on Ubuntu, macOS and Windows, plus
MCP-floor and newest-Python reproduction.

| Literal active-slice acceptance | Result and direct evidence |
| --- | --- |
| Synthetic plan: a valid reference passes; a missing target, a wrong target profile and a cardinality error each fail with a pointer through validate, schedule and render. | met — `test_object_reference_validation.py` checks source-closure validation and pointers through all three entry points; `test_object_references.py` and `test_generic_profile_fields.py` cover target/profile disambiguation and invalid cases. |
| A column over a reference shows the target title, en-US and ja-JP. | met — `test_object_reference_projection.py` checks actual English and Japanese SVG output, ordinary and lane tables, ordered many-target titles, and source-local primary/Snapshot/scenario bindings. The two SVG rasters were inspected. |
| Existing Projects unchanged (count table). | met — the [official artifact audit](https://github.com/tya5/chrona/pull/1834#issuecomment-6292534493) records all 50 public SVG and all 50 Scene files byte-identical, with no authored public-corpus changes. |

Core owns the immutable indexed target catalogue and canonical identity
`(logicalProjectID, namespace, targetID)`; extensions own package-specific
profile/namespace constraints; detached source bindings feed View and Style.
Reference display uses the target title, falling back to the ID, while raw
IDs remain encoding domains and legend identities. Layout, Scene and adapters
do not resolve references. The IDP actor-entity rule remains extension-owned;
generic object/entity ambiguity is rejected without changing the resource-
reference shape-only guard.

The broader #344 profile/field work remains outside this released slice; this
review does not claim the parent issue is closed.
