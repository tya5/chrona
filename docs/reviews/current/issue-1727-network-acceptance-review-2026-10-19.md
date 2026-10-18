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

Pending: final-head PR CI and official batched SVG/Scene delta review, followed
by the exact-main three-OS pytest/conformance/wheel and materializer gate.
Local literal acceptance is not release acceptance; keep issue1727 open.

Initial PR run39140856471 artifact12141478084 covers109 safe paths with no
retirements. Only slide05 SVG/Scene and their contrast/source inventory reports
change:44 primitives remain44 (0 added/removed;43 changed:16 nodes,16 labels,
11 routes). All11 routes and their terminals remain; no other slide changes.
The one conformance failure is the intended valid Scene v0.6→v0.7 transition,
not invalid geometry. Spec08 records this impact at `140ae489f`; one precise
L2 expected transition and synthetic serialized-schema/endpoint assertions
cover it. Focused tests pass38, and L2/L3 with all50 official Scene payloads
overlaid in memory passes without modifying tracked generated output.
The superseded run's pytest shards were cancelled, not accepted as green.
