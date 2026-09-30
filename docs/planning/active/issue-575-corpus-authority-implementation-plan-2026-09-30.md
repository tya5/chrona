# Implementation Plan — Corpus Used as Authority for the Core (#575)

**Status:** In progress (I575-1 to I575-3 planned here; I575-4 and I575-5 wait for #573)  
**Design:** [design](../../design/issue-575-corpus-authority-design-2026-09-30.md)  
**Review:** [architecture review](../../reviews/current/issue-575-corpus-authority-architecture-review-2026-09-30.md)  
**Depends on:** #573 (label behaviour knobs) for I575-4 only.

This is the one work record for the issue's baseline, plan and progress. The
design plan is folded into it: the design's baseline is the issue text plus the
published `main`, and there is no separate design-plan file.

## Baseline (published `main`, verified 2026-09-30)

- `examples/halcyon-1/project.yaml` `avionics-bustest` lag is `4wd` (`63f86e6a`,
  made to satisfy the #467 chain row). All 15 contexts pin the Project as
  `example-v2` with `contentIdentity` `sha256:e196a21b...`.
- `examples/attached-milestones/actual.yaml` was edited by `a3bd7c57` (#518).
- Item 2 tests: the fixed-host shortage is asserted only under
  `context_name == "11-overlay-briefing"` in
  `tests/unit/chrona/usecases/test_render_review.py`; fill/name counting only on
  the HALCYON scenes in `tests/integration/test_readable_defaults.py`; the rail
  fallback only in `tests/integration/test_issue_466_c3_fallback.py`;
  `tests/unit/chrona/presentation/layout/test_intent_engine.py` reads three
  example Layout Profiles (`print-portrait`, `overlay-briefing`, `briefing`).
- Acceptance rows 3, 4 and 5 (Spec 50 neutral text, byte-identity rule, AGENTS.md
  principle) are already met on `main`: Spec 50 no longer names HALCYON as
  authority (§5 says tests use synthetic fixtures; the corpus "demonstrates").
  The acceptance review cites this evidence; no text change is planned.

## Literal acceptance

| # | Criterion | Slice |
| --- | --- | --- |
| 1 | Each corpus data edit restored (look reached by YAML/knob) or README records why the data was wrong | I575-3 (HALCYON lag), I575-4 (attached-milestones) |
| 2 | Each item-2 core rule has a synthetic fixture test loading no `examples/` project | I575-1, I575-2 |
| 3 | Spec 50 neutral, HALCYON only as example | met on main; verified in I575-5 |
| 4 | Byte identity is a no-change proof only | met on main; verified in I575-5 |
| 5 | AGENTS.md states the principle | met on main; verified in I575-5 |

## Slices

### I575-1 Synthetic support and frozen layout profiles

- New `tests/support/synthetic_review.py`: small builders returning plain
  dictionaries / tmp-dir files for a Project (tasks, milestones, dependencies,
  as-of, actuals) and Views. It imports no `examples/` path and no corpus data.
- Freeze `print-portrait`, `overlay-briefing` and `briefing` into
  `tests/fixtures/layout-profiles/`. A guard test validates each against the live
  layout-profile schema and resolves it through `resolve_layout_profile`, so a
  schema move forces a deliberate fixture migration.
- `test_intent_engine.py` reads only those fixtures (and `conformance/`), never
  `examples/`.
- Gate: focused tests; a grep shows `test_intent_engine.py` has no `examples/`.
  Behaviour: none (tests only).

### I575-2 Synthetic tests for the four core rules

New synthetic test module(s) (no corpus). Each test gets a mutation check
recorded in its PR body.

1. Fixed timeline host with more lane rows than fit: `W_LAYOUT_ROW_DENSITY`,
   `required_block > available_block`, behaviour `visible-overflow`, rows inside
   the canvas.
2. Fill lanes: `laneMembers == shown member labels + W_LAYOUT_LABEL_SUPPRESSED`,
   no `member-label-leader` primitive, no name under an annotation box.
3. Member label stays in its row band (today's default; #573 changes only the
   end-gap bound and search knob, which this test does not pin).
4. Crowded plot falls back to a declared rail with
   `W_LAYOUT_ANNOTATION_CANDIDATE_FALLBACK:<id>:<rung>`.

The HALCYON tests stay as evidence and are not edited in this slice.

### I575-3 Restore `avionics-bustest` to `2wd`

- Source change: `project.yaml` lag `4wd` to `2wd`; re-pin the 15 contexts to the
  restored bytes (new token and `contentIdentity`); update the HALCYON tests that
  hard-code the 4wd data (review findings 2 and 3), each re-derived from a
  synthetic test that already exists or reduced to evidence.
- Evidence: regenerate locally (`tools/regenerate_public_examples.py`) and read
  the Scene/SVG diff against the general rules and the approved targets (PR #461,
  HALCYON target mock). Expected: the `structure -> avionics -> bus-test` chain
  no longer shares one lane on `02` (avionics' actual finish 2027-04-30 overlaps
  the 2wd bus-test start 2027-04-29). This is a rule consequence, not a defect,
  unless the diff shows a side effect. Generated files are not committed:
  `derived-sync` regenerates them on `main`; locally `--check` shows exactly what
  CI will regenerate.
- A real core defect found here stops the slice and is reported.

### I575-4 Restore `attached-milestones` data (after #573)

Restore the original `actual.yaml` values; the label reads correctly through the
#573 knob or the README records a declared value in YAML. Lead-owned.

### I575-5 Acceptance review (after I575-4)

`docs/reviews/current/` acceptance review with a row per literal criterion and
the exact-main three-OS run. Lead-owned.

## Publication units

Docs PR (this file and the review), then one PR per slice I575-1, 2, 3, each
"Refs #575", none closing the issue, all source-only.
