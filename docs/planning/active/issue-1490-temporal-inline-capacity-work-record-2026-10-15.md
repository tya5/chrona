# Issue 1490: temporal inline capacity

Status: design plan; no product changes. Public baseline: `ea602a91b`.
Owner: dev A / Codex. [Issue and acceptance](https://github.com/tya5/chrona/issues/1490).
This is the living work record; specifications remain normative.

## Literal scope and acceptance

1. Decide the rule before any code: either a growable temporal host completes
   from its natural demand (span days × `timeline.dayWidth`, plus point insets)
   with visible overflow and a warning, or the refusal stays, with a diagnostic
   that names the slot and the inline width it needed.
2. Carry the capacity facts typed into Layout composition. Do not guess
   growability downstream.

Use no epsilon and no numeric floor taken from the cases.

- Synthetic bounded and unbounded tests cover the chosen rule.
- #1474's 21 recorded refusal cases either render or still refuse with the
  chosen diagnostic, and the matrix expectations are updated to match.
- Do not edit `examples/**`.

## Verified baseline

PR1507 completed only four additional roadmap ledger cases. The original21
comprise13 point-mark,6 lane-frame and2 open-span refusals; the current ledger
contains25 cases, not a geometric threshold or waiver. The source is
`tools/draft_viewport_expected_refusals.yaml` and its matrix checker.

The allocator deliberately permits a zero minimum for `fr`/`fill`. Timeline
measurement already supplies `span_days × timeline.dayWidth` as preferred,
not minimum, width. `dayWidth` is validated positive. Mark insets are measured
only after a provisional temporal scale; zero allocation currently fails
before a useful capacity diagnostic. The final manifest loses host ancestry.

## Design slices and review questions

1. Choose completion or refusal against Spec33 §§5/6/13, Spec50's positive
   usable scale and ADR0031, including fixed/capped/anchored hosts.
2. Define typed allocated/natural/point-inset demand and its Layout-owned
   handoff; reuse the exact native mark/visual footprint producers.
3. Review ownership, whole-profile effects, diagnostics and migration; publish
   the normative correction before finalizing implementation or changing code.

Questions: can inline growth be closed without overlapping sibling content or
violating a cap? Can point demand be measured without a circular zero scale?
Which host facts are actually needed by the selected policy? What width is
reported without claiming an arbitrary epsilon or a mathematically minimal
positive real number?

## Planned verification and publication

Use synthetic row/column and capped/anchored hosts, zero/narrow-positive
allocation, span/point/icon demands and a typed-handoff integration test.
Batch the original21 and the4 additional recorded outcomes; preserve exact
diagnostics rather than broadening expected-refusal matching. Inspect public
materializer/SVG evidence as a batch. Focused tests are local; full/release
evidence comes from CI. Publish the selected design/architecture review and
implementation plan before product code; keep one coherent implementation PR
unless a real dependency requires a separate publication.
