# Acceptance Review: Presentation evidence and inspection (#390)

**Decision:** Accept pending CI.

## Delivered evidence boundary

The Scene delivery gate inventories every public Scene dataclass field and
requires a checked-in adapter, inspection, or derived delivery owner. It does
not parse SVG, reopen rendering policy, or make serialized inspection facts
pretend to be adapter fields.

The prior-art matrix imports its rows from the #391 typed ceiling. It now
contains a Chrona disposition and one explicit observation column for each
named primary source. `documented`, `unknown`, and `not-applicable` have fixed
meanings; missing capability rows, source cells, stale rows, and unreasoned
`not-applicable` values fail the generator tests. The research table remains
tool-local and cannot configure rendering.

The corpus policy and visual acceptance-record template establish the required
human review record for future visual changes. #390 itself changes evidence
infrastructure rather than a rendered corpus artifact; it preserves every
public materialized SVG byte. #384's acceptance review is the first existing
corpus presentation-change record governed by the same materializer and gallery
boundaries.

## Architecture review

| Concern | Result |
| --- | --- |
| Scene ownership | Every public field has a named delivery class and live consumer; renderer-neutral inspection remains legitimate. |
| Capability ownership | #391 remains the only owner of capability identity and Chrona disposition. |
| External research | Source observations are complete, explicit, primary-source-linked, and never runtime input. |
| Visual review | The record template supplements reproducible generated evidence; it cannot become a golden-image policy. |

## Verification

* Focused matrix and Scene delivery tests: `6 passed`.
* Public materializer byte checks: `24 passed`; generated SVG and gallery diffs
  are empty.
* Conformance, import direction, module reachability, Scene delivery, matrix,
  documented command, and installed-wheel smoke checks: pass.
* Full regression: `780 passed, 19 skipped`.

The release is limited to quality evidence. It admits no new Scene primitive,
renderer option, presentation schema value, or external-product dependency.
