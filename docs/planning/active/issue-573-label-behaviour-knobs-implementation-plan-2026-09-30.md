# Implementation Plan — Knobs for Hard-Coded Label Behaviour (#573)

Design: [design](../../design/issue-573-label-behaviour-knobs-design-2026-09-30.md), amended by the findings in the
[architecture review](../../reviews/current/issue-573-label-behaviour-knobs-architecture-review-2026-09-30.md).
The review's amendments (A1-A3) are part of the current design; this plan is the authority for their mechanics.

## Baseline (main `22ea2c1c`)

- One call site places associated member names: `src/chrona/presentation/layout/surface_member_labels.py`
  (`place_member_name(..., maximum_end_gap=2 * float(font_size), full_band=(lane_row_id is not None and row_distribution == "fill"))`).
  The issue text names `surface_composer.py` and two call sites; both are stale.
- The same function builds `MemberNameAssociation(..., 2 * float(font_size))`, a second hard-coded two-em bound (A1).
- `layout-profile-v0.9` `reviewSurface` has `additionalProperties: false`; `profile.py` copies a derived profile's
  `reviewSurface` whole.

## Literal acceptance (issue rows)

1. A declared metric (Theme or Layout equivalent), default 2, replaces the constant at the call sites; a synthetic test
   shows two values giving two bounds.
2. A declared search policy replaces the implicit coupling; defaults keep today's output byte-identical; a synthetic test
   covers both values on lane and non-lane rows.
3. Spec 50 states the default and the knob, not a fixed number.

## Slice I573-1: knobs, schema, tests (code PR)

Owned files: `schemas/layout-profile-v0.9.schema.yaml`, its packaged mirror if the schema inventory requires one,
`src/chrona/presentation/layout/engine.py` and `model.py` (carry `memberNames` into `LayoutManifest`; serialize it only when
declared, so an absent knob leaves manifest bytes unchanged), `surface_member_labels.py` (the one call site).

Behavior:
- `reviewSurface.memberNames` is optional: `{maxEndGapEm: number 0..100, search: side-band | full-band}`, both optional,
  `additionalProperties: false`. Added in place, no version bump (Spec 56 §3.2).
- Absent: `maxEndGapEm = 2`, `search` derived from `rowDistribution` as today.
- `reach = maxEndGapEm * font_size` replaces both `2 * font_size` occurrences (the end-gap bound and the association
  distance, A1). The item's last-own-mark slip extension of design decision 3 is NOT part of I573-1: see A2, where
  measurement showed it changes five public slides, contradicting the byte-identical acceptance row. It waits on an owner decision.
- `search` present applies to every associated member name; absent keeps the lane-and-fill coupling.

Focused tests (synthetic, `tests/unit/chrona/presentation/layout/`):
- default: no `memberNames` renders byte-identically to an explicit `{maxEndGapEm: 2}` (and `search` equal to the derived value).
- `maxEndGapEm`: two values give two different bounds on a fixture (smaller value rejects the end candidate and falls to the
  next declared side; larger accepts it). `0` never uses `end`.
- `search`: both values on a lane row under `fill`, a lane row under `pack`, and an automatic row.
- derived profile copy carries `memberNames`; a derived profile that omits it gets the defaults even if its base declares it.
- schema: unknown key under `memberNames`, `maxEndGapEm` negative / non-number / above 100, `search` outside the enum are rejected.

Local checks: the focused tests, `tests/unit/tools`, `python -m tools.schema_annotations`, `tools.schema_inventory`,
`tools.validate_schema_references`, `python -m tools.derived_evidence --check`, `python -m tools.regenerate_public_examples --check`.
Full pytest is left to PR CI.

Gate: any derived-evidence change in this slice is a stop-and-report condition, not something to regenerate past. Verified: zero
changed public slides with the knobs alone.

## Slice I573-2: Spec 50 (docs PR, after I573-1)

Spec 50 §3.2 (and the association paragraph that says "two-em") state the default (2 em, `search` coupled to
`rowDistribution: fill` on lane rows), the knob names, and that the association bound follows the same value. The last-own-mark wording is added only if the slip decision is taken. Byte-identity evidence from I573-1 is cited as evidence of no default
change only. No derived output is hand edited; derived outputs are regenerated on main by CI.

## Slice I679-1: measure the member-name reach from the item's last own drawn mark (code PR; issue #679)

Background. #573 decision 3 (measure from the last own drawn mark) was deferred by review A2 because the prototype changed five
public slides. #679 (found by #575 I575-4) shows why it cannot stay deferred: with the original `attached-milestones` data (readiness
planned `2027-09-30`, actual `2027-10-01`, `asOf 2027-10-15`) the `readiness` name starts 3.7 px after the planned mark and covers
its own actual mark in every packaged preset, with `W_LAYOUT_LABEL_OVERFLOW` and `W_LAYOUT_LABEL_SUPPRESSED`; `maxEndGapEm` 4 or 6
and `search: full-band` do not move it. Owner rule (#575): byte identity proves only that nothing changed; a behaviour change is
judged against the general rule (synthetic tests) and the approved targets (PR #461, HALCYON target mock), and the current corpus
output is not an oracle.

Rule (amended after the first measurement: final rung only). A mark-associated member name has a set of own drawn marks: the
item's `planned:` mark (which also carries the baseline and snapshot facets) and its `actual:` mark, when each exists.
`missing-actual:` is an absence indicator, not an observation, and is not an own mark for reach (the Scene acceptance check accepts
only `planned`, `actual`, `snapshot` hosts).
1. The declared side ladder and every host-measured candidate stay exactly as today, including the association bound (within the
   reach of the requested host) and the `hostPlacementId`. A name that has a legal candidate today keeps its position, host and
   geometry byte for byte.
2. "End after the rightmost own mark" is added only as a FINAL rung, tried after every existing candidate has failed and before the
   visible-overflow fallback, and only when `end` is on the declared ladder and an own mark ends past the host. It starts at the
   right edge of the rightmost own mark plus the declared gap and is bounded by `maxEndGapEm * font_size` from that edge.
   When no rung is legal and the visible-overflow fallback side is `end`, that fallback is measured from the same edge, so an
   overflowing name (an attached milestone over its parent bar) does not cover the item's own actual mark.
3. Only a name placed by the final rung is associated through "within reach of at least one own mark", and only its
   `hostPlacementId` names the own mark nearest its Text, so the existing Scene acceptance check (host gap within two em) stays true.
4. The default stays `maxEndGapEm = 2`; `search` is untouched.

Why final-rung-only. The first variant made the end side legal in the ordinary ladder, so names that had a legal position (above,
below, start) moved to the end. Regenerated evidence lost three dependency routes (`bustest-integration` on `02-programme-board`
and `12-glyph-gates`, `structure-avionics` on `16-gallery-editorial-lanes`, each now `W_LAYOUT_RELATION_SUPPRESSED`), because in lane
mode names are placed before routes and an end-side name can block a route exit. A legal placement must not move because a new rung
became legal; losing a dependency line is worse than the design targets. Names placed before routes is a separate router question,
not solved here. The final rung changes only names that are suppressed or drawn by visible-overflow today.

Owned files: `src/chrona/presentation/layout/labels.py` (`place_member_name` gains `own_mark_right`; `MemberNameAssociation`
gains `also_marks`), `src/chrona/presentation/layout/surface_member_labels.py` (the one call site collects own marks and picks
the host), Spec 50 §3.2, and tests. No schema, Theme, View, Scene or adapter change.

Tests (synthetic, no `examples/` input, `tests/support/synthetic_review.py`):
- `tests/unit/chrona/presentation/layout/test_member_names_profile_knobs.py`-style unit tests on `place_member_name` /
  `MemberNameAssociation` for the geometry (end gap from `own_mark_right`; association through `also_marks`).
- A test that a name with a legal ladder candidate is unchanged (same position and host with and without the final rung).
- `tests/integration/test_synthetic_surface_rules.py`: a project with a gate whose actual sits past its plan and a span whose
  actual and baseline extend past the plan, rendered through a packaged bundle, asserts for every member name: no overlap with
  any own mark, the name sits within `maxEndGapEm` of its last own mark, and with a smaller declared `maxEndGapEm` the name
  is not placed detached beyond the reach (the reach still bounds detached text). A negative test pins the old rule by
  running the same render with the reach measured from the host (monkeypatched `own_mark_right`) and asserting the old
  behaviour violates the new assertion. Quick mutation check, stated in the PR: reverting the call site to pass no
  `own_mark_right` makes the rule test fail.

Evidence procedure (local, nothing derived is committed): regenerate with `python -m tools.regenerate_public_examples` and
`python -m tools.derived_evidence` on the branch, list every changed scene JSON and SVG (`git status`, `git diff --stat`),
then per changed slide diff the Scene primitives by id (bounds, text, selected rung, diagnostics) against main, classify each
changed primitive (member label moved, suppressed label emitted, diagnostic gone or added, anything else), and explain each
against the rule and against the PR #461 targets / HALCYON target mock. Then restore the derived files (`git checkout -- .`)
before committing, since PRs carry source only and `derived-sync` regenerates on main. The PR body carries the table.

Stop conditions: any changed primitive that is not a member-name position/suppression/diagnostic consequence of the rule; any
name that ends up detached from every own mark by more than the reach; a new `W_LAYOUT_LABEL_OVERFLOW` or new suppression on a
public slide; any slide that reads worse than its target. Then do not merge: report.

Expected evidence with the final rung: changes only where a name was suppressed or fell back to visible-overflow (`aster-ssd/overview`
`ftl`; `attached-milestones` with the original data in a temporary copy). Any other changed slide, or any lost route, dependency or
annotation, is a stop condition.

Not in this slice: restoring `examples/attached-milestones` (the lead, after the PR, as I575-4), start-side measurement from the
first own mark (symmetric, not needed by the observed case; the association through `also_marks` already lets a start name clear an
early actual), closing #679, the acceptance review.

## Status

I573-1 merged as #663 (`8c590276`): knobs, schema, tests; zero public slides changed. I573-2 (Spec 50 §3.2) is this change. Decision 3 is taken by I679-1 (below, issue #679). Still open for the
owner: whether `maxEndGapEm` should be split from the association reach (review F1, A2).

## Publication

Docs PR (this plan and the review) first; I573-1 code PR; I573-2 spec PR. Every commit and PR: `Refs #573`, no closing
keywords, PR titles end with the slice id. The acceptance review and issue closure are separate, later work.
