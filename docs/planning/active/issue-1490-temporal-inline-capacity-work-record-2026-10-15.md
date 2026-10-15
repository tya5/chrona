# Issue 1490: temporal inline capacity

Status: design and architecture review complete; no product changes.
Public ready baseline: `1deffc014` (normal merge, no rewritten history).
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

## Selected design and architecture review

Choose the issue's refusal option B. Do not change flex minima, reallocate the
whole profile or infer that an uncapped host can grow. A finite positive scale
continues existing rendering/overflow behavior; only a non-positive usable
temporal range gets `E_LAYOUT_TEMPORAL_INLINE_CAPACITY` at
`/layoutManifest/sources/timeline`.

Layout closes a narrow typed host-capacity record at the allocation-to-native
composition boundary: actual slot/source identity, allocated inline width and
the source's measured natural temporal width. The latter is the existing
preferred measurement, not a new minimum or a value recomputed in Scene.
Point insets are then closed by the existing representation-specific native
mark footprint producers and shared inset arithmetic. Icons remain inside
their host bounds; do not add a separate icon geometry estimator.

For zero allocation, measurement uses a positive prototype scale from natural
demand, never an epsilon. It is not a completed placement and cannot escape
into Scene. Native point composition supplies exact start/end protrusions;
the diagnostic reports allocated width and natural temporal width plus those
insets, naming the slot. This is a sufficient natural-demand width, not a
claimed smallest positive real width. Malformed source/Theme/domain errors
retain their owners. An empty admitted point set contributes zero insets.

Consistency: Spec33 flex allocation is untouched. Spec50's positive temporal
mapping invariant is retained. ADR0031/Spec33's blanket fit-completion rule
needs the published narrow distinction between degenerate temporal mapping
and otherwise valid finite geometry that can overflow. View still owns dates;
Layout owns demand, allocation and native measurement; Scene/adapters own no
new decision. No schema, CLI flag, project-specific threshold, ancestor
framework or unused growability flag is added. Capped and uncapped hosts obey
the same explicit refusal rule, so no lost ancestry is guessed downstream.

Rejected A for this slice: safe natural completion needs an inline counterpart
of whole-profile block growth, including cross-axis/anchored/grid/capped hosts
and a verified re-solve that preserves siblings. Mutating one slot or treating
preferred width as a flex minimum would not implement that contract. B is an
explicitly permitted final outcome, not a partial implementation of A.

Migration: the recorded degenerate-scale cases keep refusal but replace the
generic mark/lane/path failures with the named capacity diagnostic and measured
widths. Valid positive-scale output must remain unchanged. Keep exact matrix
outcomes; update the ledger rather than weakening its comparison.

## Verification and publication

Use synthetic row/column and capped/anchored hosts, zero/narrow-positive
allocation, span/point/icon demands and a typed-handoff integration test.
Batch the original21 and the4 additional recorded outcomes; preserve exact
diagnostics rather than broadening expected-refusal matching. Inspect public
materializer/SVG evidence as a batch. Focused tests are local; full/release
evidence comes from CI. Publish the selected design/architecture review and
implementation plan before product code; keep one coherent implementation PR
unless a real dependency requires a separate publication.
