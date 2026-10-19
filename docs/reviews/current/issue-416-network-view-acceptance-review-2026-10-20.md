# Issue 416 — network View acceptance

Implementation `8240e85c0`; design/architecture/plan published at `2e2117331`
and shared-role clarification `e7fb83df7`, before affected code. Current
[work record](../../planning/active/issue-416-network-view-work-record-2026-10-19.md);
normative Specs 06/07/50. Status: locally verified, **not release accepted**.

| Literal acceptance criterion | Status and direct evidence |
| --- | --- |
| A View can select and label network nodes without borrowing the timeline's vocabulary by accident. | Met locally: `test_network_view_projection.py`, `test_network_view_intent_render.py`; closed `network.nodeLabel.source`, shared field reference, title/id/default/role/null/empty-string cases and actual SVG text. |
| Rank spacing and member spacing are set independently. | Met locally: `test_dependency_network.py` and `test_network_group_bands.py`; independent primary/cross-axis geometry, containers, horizontal/vertical flows, zero and absent→rank-gap behavior. Invalid metric values reject. |
| Member order within a rank is declared rather than incidental. | Met locally: existing global View ordering becomes projection ordinals, including direction/tie-break and explicit-row Views. Timeline explicit-row order remains unchanged; no private parallel ordering resolver survives. |
| A View selects a subset of objects and a label source for the network; a synthetic test and a PNG. | Met locally: actual SVG/Scene integration test and [inspected PNG](assets-416/opted-in.png): only a/b selected, custom labels, descending order and member gap 48. |
| The same View vocabulary is accepted or refused with a pointed diagnostic on the timeline surface where it does not apply, never silently ignored. | Met locally: schema/contract tests accept network intent on the network and refuse the same member, including `{}`, on timeline with structured `E_RESOURCE_SCHEMA` at `/body/network`. Real-render non-string field tests preserve `E_VIEW_NETWORK_LABEL_SOURCE`, source pointer and object subject, not `E_TOOL_FAILURE`. Unbound roles preserve existing declaration info while falling back to title. |
| HALCYON slide 05 is unchanged unless its View opts in (count table). | Met locally: unchanged public single materializer succeeds; Scene and SVG are byte-identical. [Inspected PNG](assets-416/halcyon05.png); counts below. No corpus input was edited. |

## Unopted public output

Command: `.venv/bin/python tools/materialize_example.py examples/halcyon-1/manifest.yaml --slide dependency-network --output <scratch>` (without `--write`).
Compared with the ready-main `d0dc06f6b` committed evidence:

| HALCYON 05 item | Before | After | Changed / added / removed |
| --- | ---: | ---: | --- |
| Nodes | 16 | 16 | 0 / 0 / 0 |
| Node labels | 16 | 16 | 0 / 0 / 0 |
| Edges | 11 | 11 | 0 / 0 / 0 |
| All primitives | 44 | 44 | 0 / 0 / 0 |

SVG SHA256 `552452e30666cf389686be003ade536b84ea3ce742075ce18d44237e8d405951`;
Scene SHA256 `0c4d1ebbd434307bcd695316c156c8f125387b265a5ac7259503f96683023dde`.
Opted-in synthetic SVG SHA256
`9ba3ffc47ffdddf2f2dac0c55b5c44690d1333e2affcdab840bf093bf1e4dd5b`.
Both actual adapter rasterizations were inspected without new clipping/overlap.

## Verification and architecture

Combined schema/contract/projection/Layout/real-render/semantic-field-role
focused batch: **266 passed**. Full schema equivalence against `origin/main`
passes (L1: one changed schema, 42 equal; three precise expected pointers;
L2/L3 preserve the existing recorded invalid fixtures). Schema annotations,
shared references, import direction, View dispatch and Scene delivery checks
pass. No full local pytest or repeated full public corpus run is needed.
The combined 416/1756 candidate passes **452 focused tests**, including two
additional primary-descending order regressions (`ffb5f6ef4`); one integration
PR will preserve both issues' source commits and separate literal reviews.

View carries closed content intent; Projection reads source-local field/default
bindings and closes selected labels/order; Layout alone measures and completes
nodes, groups, spacing, ports and routes. The existing application error
transport preserves typed model failures. Theme metrics retain one channel;
no parallel Layout Profile override, scheduler change, Scene/adapter placement
logic, corpus tuning or new layout algorithm is introduced.

Release pending: exact-ready-main PR, CI-generated inventory/public snapshot
and all full checks, then the exact published review-containing main's
three-OS/conformance/wheel/newest-Python run. Keep issue416 open until these pass.
