# Issue 145 Dependency-Network Release Review

## Result

Issue 145 is accepted. Chrona now materializes a deterministic
`dependency-network` (PERT) View through the existing closure, render-review
entry point, and SVG renderer. The public HALCYON Context is
`contexts/05-dependency-network.yaml`; its checked-in generated artifact is
`generated/05-dependency-network.svg`.

## Boundary audit

| Boundary | Evidence |
| --- | --- |
| View | v0.8 surface discriminator and network-only authoring validation select typed graph facts. `window` remains the common schedule envelope, but network Layout never reads it. |
| Layout | `DependencyNetworkProjection` is ranked, measured, placed, ported, routed, quality-checked, and returned as title/node-label/node/edge placement closure. Horizontal and vertical writing modes are covered. |
| Scene | A small dispatcher selects table/timeline or network adapter from typed projection intent. The network route consumes completed Layout records only and maps Rect/Path semantics through `networkNode`, `networkEdge`, and `criticalEdge`. |
| Use case / closure | No surface-selection branch, closure format, or renderer branch was added. The only render-review change is unconditional neutral registration of the already-typed `network` measurement source, required to retain a single measurement pipeline. |
| Renderer | Unchanged: the generic SVG renderer serializes existing Rect/Text/Path primitives and existing Theme roles. |

The review found and corrected two potential boundary violations before release:
the common `window` must remain a projection envelope, and the required title
placement must be completed by Layout rather than invented by Scene. The
corrections and their implementation amendments were published and merged
before the dependent slices resumed.

## Release evidence

* PRs #239–#241 publish the design plan, design review, and implementation
  plan; #244–#247 and #249–#251 publish/implement the required corrections.
* PR #248 closes measured network node/routing Layout; PR #252 delivers the
  registry Scene adapter and HALCYON materialization.
* The generated HALCYON SVG contains `network-node:*`, `network-edge:*`, and
  `critical-edge` primitive evidence. Existing table/timeline generated SVGs
  remain byte-characterized by the materializer tests.
* Focused Scene/Layout tests, public materializer/output-property tests,
  conformance, module reachability (55 reachable, 0 staged), import-direction
  checks, full pytest, wheel install smoke tests, and all Ubuntu/macOS CI jobs
  passed for PR #252.

## Follow-up boundary

Composite Gantt-plus-network output is intentionally not included. It needs a
future explicit composite View contract; it must not be synthesized by placing
two independently composed surfaces into the current single-surface closure.
