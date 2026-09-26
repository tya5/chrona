# Design Plan — Layout Fit Completion and Draft Host Fonts (#457, #447)

## Published baseline and questions

At `4b67be51`, #449 has completed-surface visible overflow and warnings, but
`solve_layout` can still reject valid narrow canvases before surface
composition. #448 has a multi-face draft catalog, but its fontconfig query
uses CSS weight numbers, opens collections without a face index, and treats
every Theme face as a host face. These are published facts from code and issue
reports; the full corpus/host reproduction and every raise-site disposition
remain to be verified.

Design slices, in order:

1. Inventory Layout Profile, axis, and remaining fit-related raises by
   reachable ingress and distinguish valid-fit failure from invalid input.
   Reproduce all reported HALCYON viewport cases and batch every public view
   at 1600x900, 800x450, and 600x340.
2. Specify Layout-owned normal-flow expansion, container overflow defaults,
   axis fallback, finite warning/canvas propagation, and exact required versus
   available extents. Review against ADR-0031, Specifications 08/50, #449,
   immutable reproducibility, and Scene/adapter projection.
3. Specify host face selection with correct fontconfig weights, collection
   index and byte/face identity, English family records, packaged/declared
   face priority, and exact PNG paint. Review against #411/#448, immutable
   font closure, SVG/PNG adapters, and platform dependency messaging.
4. Publish design and architecture review, then a sliced implementation plan.

## Literal acceptance and evidence

### #457

| Literal criterion | Planned evidence |
| --- | --- |
| Every corpus view drafts at 1600x900, 800x450 and 600x340 with exit code 0, drawing whatever does not fit visibly, with warnings. | Batch CLI matrix, generated Scene/SVG inspection, structured warnings. |
| No fit-related refusal remains reachable from the draft or immutable path. | Raise-site inventory with disposition and draft/immutable regression tests. |
| Any remaining layout error message names the placement and the required and available extents. | Negative diagnostic fixtures for genuinely invalid layout states. |

### #447

| Literal criterion | Planned evidence |
| --- | --- |
| On a host with fontconfig, `--system-fonts` resolves a single-file family at 400 and at 700 to its regular and bold faces. | Real `fc-match` Linux integration plus exact face assertions. |
| It resolves a face inside a `.ttc`, and the PNG is painted with that face. | Collection fixture/host test, metrics identity and PNG visual/byte check. |
| `Hiragino Sans` resolves by its English family name. | macOS conditional host integration or name-table fixture representing Japanese-first records. |
| CI exercises the real `fc-match` at least once. | CI-enabled real-host test without injected runner. |
| A host without fontconfig receives a message that says how to get it, or does not need it. | Missing-executable diagnostic test and guide check. |

## Boundary and release controls

The design must leave Layout as sole owner of geometry/fallback/warnings and
font closure as ingress-owned: Scene/adapter may only serialize completed
placements and exact assets. No compatibility branch may obscure that rule.
Publish each design, implementation-plan, implementation, and release-review
phase separately after checking remote `main`. Focused tests precede each
implementation slice; CI supplies full cross-platform pytest/conformance.
Do not close either issue before its literal acceptance review is complete.
