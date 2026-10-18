<!-- chrona:literal-acceptance/v1 -->

# Dependency-network defect acceptance

## Literal issue acceptance

### Issue #1727

- Source: [Issue #1727](https://github.com/tya5/chrona/issues/1727)
- Observed: 2026-10-19

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | Each of the three errors names what to change, with the pointer. | met | Error slice `a53303c9f`; [auto viewport](../../../tests/integration/test_auto_block_limit_render.py), [required slot](../../../tests/unit/chrona/presentation/layout/test_dependency_network.py), [sorted tokens](../../../tests/unit/chrona/presentation/layout/test_intent_profile.py); existing codes and pointers retained. | — |
| 2 | Synthetic network: group containers are not drawn as orphan nodes; edges carry direction; no edge passes through a node it does not connect (or the route records why); the critical role has a legend key when drawn; nothing is clipped; node text keeps the Theme padding. | met | Geometry slice `4b99df734`; [Project-to-SVG acceptance](../../../tests/integration/test_network_layout_acceptance.py), [container bands](../../../tests/unit/chrona/presentation/layout/test_network_group_bands.py), [route/terminal safety and explicit fallback](../../../tests/unit/chrona/presentation/layout/test_network_routes.py), [paint envelopes](../../../tests/unit/chrona/presentation/layout/test_network_ink.py), [measured legend](../../../tests/unit/chrona/presentation/layout/test_network_legend.py), [Theme padding](../../../tests/unit/chrona/presentation/layout/test_network_node_padding.py), [passive Scene](../../../tests/unit/chrona/presentation/scene/test_dependency_network_scene_projection.py). | — |
| 3 | The trial-7 Japanese network re-rendered as a PNG. | met | [Actual Japanese PNG](assets-1727/trial-7-japanese-network.png), rendered from public [trial-7 inputs](https://github.com/tya5/chrona/tree/3f234372863763efdf5d22a140d44da11355f610/trial-7), unchanged. Containers, directional arrows, critical-edge key and complete deadline date inspected in the raster output. | — |

## Architecture conclusion

Pre-code contracts: `cb3182eb4`, corrected actual network paint role
`4997433a4`, legend overflow `4cc3d0a31`, and completed relation bounds/text
identity `92ec3ca57`; [whole-architecture review and plan](https://github.com/tya5/chrona/issues/1727#issuecomment-6251204543)
and [closure correction](https://github.com/tya5/chrona/issues/1727#issuecomment-6251589934).
Model closes selected containment, visibility and scheduler-driving critical
facts. Layout owns measured insets, groups, terminals, ink bounds, factual
fallback and shared legend placement; Scene copies completed values. No
project-specific Core rule, new route search, required Theme migration or
authored example edit. Independent architecture review found no blocker.

Focused combined network/Model/content/Scene/SVG tests pass296; shared legend
unit/materializer tests pass33; heading/source/closure checks pass35.
Import direction and float accumulation guards pass. Error slice focused127
passed before geometry changes; CI supplies the full matrix and public corpus.

PNG command: `python -m chrona render trial-7/ja/project.yaml --view
trial-7/net/net-view.yaml --layout trial-7/net/net-layout.yaml --viewport
1600x900 --format png --output trial-7-japanese-network.png`, with packaged
Noto JP fonts. Natural canvas growth and eight explicit route-quality
fallback occurrences remain visible; this slice does not claim an improved
search algorithm or suppress those paths. The grouped warning names crossed
subjects instead of representing a direct crossing as a clear route.

## Programme-level criteria (optional)

[PR1732](https://github.com/tya5/chrona/pull/1732) merged at
`d14aabc7c63f0402f0ed4afef75d585bf7294252`. Final head
`3b409d001ffa11dd240d5936bf35cfe0b1398d41` passes all checks in
[CI39143120950](https://github.com/tya5/chrona/actions/runs/39143120950).
Final artifact12141738990 (SHA256
`c6d0546e49c50c05b6fb66dcefdb87ddc503c3dd40b237fcbc86374e64769019`)
covers109 safe paths, no retirements. Only slide05 SVG/Scene and associated
reports change:44→44 primitives (0 added/removed;43 changed:16 nodes,
16 labels,11 routes). All11 routes and terminals remain; the other49 SVG/Scene
pairs are unchanged. [Final artifact review](https://github.com/tya5/chrona/pull/1732#issuecomment-6252057784).

All earlier failures are resolved: the exact L2 valid Scene v0.6→v0.7
transition is recorded; typed node mocks, round-terminal centre assertions
and the schema-validated capability-free adapter fixture retain their intended
checks. No validator weakening or generated-file edits. Affected tests pass49;
final CI supplies conformance, all three pytest shards and reproduction.

Derived sync and the exact-SHA trusted gate pass on ready main
`a59fe7c68c094a970c2e1465e62bfa669c8c2f48`.
[native release39144628668](https://github.com/tya5/chrona/actions/runs/39144628668)
passes three-OS pytest/conformance/wheel, MCP floor and newest-Python public
reproduction. All three literal rows are met and issue1727 is
[closed](https://github.com/tya5/chrona/issues/1727#issuecomment-6252720230).
