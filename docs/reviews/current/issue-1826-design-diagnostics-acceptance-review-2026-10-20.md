# Issue1826 — design self-checks

[Pre-code design, architecture review and implementation plan](https://github.com/tya5/chrona/issues/1826#issuecomment-6290560393).
Specs60 (`b12de2c7e`) and33/46/49 (`5a2fcaa8f`) were public before affected code.
One issue PR; no authored public-corpus adaptations or new schema, threshold,
tolerance, Scene geometry or adapter policy.

| Literal criterion | Status | Evidence |
| --- | --- | --- |
| every pair of drawn legend swatches is checked with the existing Spec 60 measure, under normal vision and the scheme's declared colour-vision types. A synthetic case warns for the ΔE 2.7 pair and for identical swatches with different meanings. | focused checks met; release pending | `test_legend_diagnostics.py` exercises the completed-placement path for ordinary keys, the specified colours under normal/protanopia/deuteranopia/tritanopia, identical different-meaning inks, both source subjects, and hidden/text-only controls. Existing final-ink and typed ScaleCollision dedup remain. |
| a halo is excluded from the decoration contrast check by its declared purpose (it is a separator, not a figure). target-b can then drop decoration: none (reviewer YAML follows). | focused checks met; release pending | `test_contrast_policy.py` checks canonical separator, arbitrary identity, wrong/absent purpose and Text misuse, while retaining ordinary bands, marks, Text and graphical legend floors. `test_semantic_vocabulary_closure.py` checks the fresh host identity and rejects stale styled Scene identity. Reviewer owns the target-b YAML follow-through. |
| content-width legends measure with the same rounding they place with (no false ellipsis), the one-row height is the measured row height, and a synthetic test covers both. | focused checks met; release pending | `test_legend_measurement_closure.py` checks exact natural widths at three origins in block/inline/grid, genuine shortage, and shared wrap offsets. `test_legend_known_width_completion.py` checks real fixed-parent rendering, wrapping/shortage, tall swatches and Draft auto; fixed outer dimensions stay fixed. |

Ownership review: Layout compares completed legend ink and owns shared finite
measurement/placement arithmetic and known-width row completion. The host
vocabulary declares the separator's contrast disposition; Scene contrast uses
an exact graphical role/purpose join with conservative fallback for misuse.
Existing classified role/Text precedence remains. Fresh closures bind current
host bytes; no Context pin or stale-identity compatibility alias is added.
Independent Luna review caught and corrected the Text misuse edge before
publication. General optional-decoration synthetic coverage remains; a halo
is no longer falsely required as a decoration witness.

Final PR head, focused command/count, batched official artifact changes,
CI links and exact-main three-OS release evidence remain to be recorded.
The issue stays open until those release gates pass.
