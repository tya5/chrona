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
- `reach = maxEndGapEm * font_size + slip`, where `slip = max(0, right edge of the item's rightmost own mark - right edge of
  the host mark)`. `reach` replaces `2 * font_size` in both the end-gap bound and the association distance (A1). `slip` is 0
  without an actual mark past the host, so the default stays byte-identical there (A2 says how that is proven and where it is not).
- `search` present applies to every associated member name; absent keeps the lane-and-fill coupling.

Focused tests (synthetic, `tests/unit/chrona/presentation/layout/`):
- default: no `memberNames` renders byte-identically to an explicit `{maxEndGapEm: 2}` (and `search` equal to the derived value).
- `maxEndGapEm`: two values give two different bounds on a fixture (smaller value rejects the end candidate and falls to the
  next declared side; larger accepts it). `0` never uses `end`.
- `search`: both values on a lane row under `fill`, a lane row under `pack`, and an automatic row.
- slip: an actual mark past the host by a known distance; the label clears it within `maxEndGapEm` beyond the slip.
- derived profile copy carries `memberNames`; a derived profile that omits it gets the defaults even if its base declares it.
- schema: unknown key under `memberNames`, `maxEndGapEm` negative / non-number / above 100, `search` outside the enum are rejected.

Local checks: the focused tests, `tests/unit/tools`, `python -m tools.schema_annotations`, `tools.schema_inventory`,
`tools.validate_schema_references`, `python -m tools.derived_evidence --check`, `python -m tools.regenerate_public_examples --check`.
Full pytest is left to PR CI.

Gate: any derived-evidence change beyond a slipped-actual label is a stop-and-report condition (A2), not something to
regenerate past.

## Slice I573-2: Spec 50 (docs PR, after I573-1)

Spec 50 §3.2 (and the association paragraph that says "two-em") state the default (2 em, `search` coupled to
`rowDistribution: fill` on lane rows), the knob names, that the bound is measured from the item's last own drawn mark, and
that the association bound follows the same value. Byte-identity evidence from I573-1 is cited as evidence of no default
change only. No derived output is hand edited; derived outputs are regenerated on main by CI.

## Publication

Docs PR (this plan and the review) first; I573-1 code PR; I573-2 spec PR. Every commit and PR: `Refs #573`, no closing
keywords, PR titles end with the slice id. The acceptance review and issue closure are separate, later work.
