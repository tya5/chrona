# Implementation Plan: Named Periods, Labelled and Patternable Bands (#582)

**Status:** Proposed. Design: [design](../../design/issue-582-named-periods-design-2026-10-02.md); review:
[architecture review](../../reviews/current/issue-582-named-periods-architecture-review-2026-10-02.md); plan:
[design plan](issue-582-named-periods-design-plan-2026-10-02.md).
**Base:** `main` at `324d1aca` (the plan, design and review are merged). Findings F1 to F5 of the review are slice
conditions; F6 to F10 are slice-review items. Files named below that the review did not list (the ledger test, the
module ownership table, the id-site allowlist, the decoration-role list) were found by prototyping each slice against the
repository's own guards; each guard is part of its slice's definition of done.

## Rules for every slice

- One PR per slice, `Refs #582` only, the two trailers, and a branch cut from the derived bot commit
  (`newbranch.sh`, which waits for a green `derived-main` on the tip).
- A schema slice runs `python -m tools.schema_equivalence --base-rev origin/main` and pastes the output in the PR.
- Default behaviour is unchanged: a Project and a View without `periods` give identical Scene and SVG, shown by a
  focused test and by the conformance and `regenerate_public_examples --check` runs.
- Every new test is synthetic (no `examples/` input), is mutation-checked (the rule removed or inverted makes it
  fail), and names the rule it protects. Corpus output is evidence, never an oracle; no corpus value is edited to
  pass a criterion.
- `src/chrona/scheduling/`, the axis lane files, the legend lane files and `src/chrona/resources/presets/` are not
  edited. The PR states this.
- Merge procedure: merge lock, rebase on `origin/main`, all checks including `derived-ready`, merge, release.

## S1: the Project fact (no presentation change)

| Item | Detail |
| --- | --- |
| Rows | Acceptance 1 (schema, ordering, unknown refs, diagnostics) |
| Schema | `schemas/project-v0.7.schema.yaml`: optional `periods` map and `$defs` `period`, `periodBoundary` (`oneOf` the `date` definition and `endpointRef`); descriptions and examples on every author-facing node (`tools/schema_annotations`) |
| Core | New `src/chrona/core/periods.py`: `period_diagnostics(project, endpoints_of)` returning `E_PROJECT_PERIOD_ORDER` (both literal), `E_PROJECT_PERIOD_OBJECT_UNKNOWN`, `E_PROJECT_PERIOD_ENDPOINT_UNAVAILABLE`; calendar-date check through `as_date` reported as `E_SCHEMA`; called from `validate_project` after the object checks, reusing the existing endpoint-availability rule rather than copying it |
| Terse | `src/chrona/terse/ledger.py`: `top.periods` and the member paths as `YAML_ONLY` with the scope-rule reason (F5); `tests/unit/chrona/terse/test_ledger.py` also walks the `period` definition so a later member is forced into a decision |
| Specification | 05: new section "Periods" (shape, half-open convention with the "22 Oct to 5 Nov" example, validation table, never schedules) and the §16 note that the member is additive in `timeline/v0.7`; `docs/specification/supplemental/core-v0.1-diagnostics.md`: the three codes |
| Tests | `tests/unit/chrona/core/test_periods.py`: valid literal and reference forms; each code with its pointer; non-calendar date; unknown member rejected (closed object); a Project without `periods` yields the same diagnostics as before; a period never changes `schedule` output; ledger test green |
| Generated | None committed; derived-sync regenerates `docs/diagnostics/inventory.md` |
| Gate | Schema equivalence (L1 delta entry only if the gate asks for one), conformance, unit tests for `core`, `terse`, `schemas` |
| Boundary | Merges alone: no View, Theme, Layout or Scene change; no Scene or SVG byte changes |

## S2: resolution and the post-placement check (no presentation change)

| Item | Detail |
| --- | --- |
| Rows | Acceptance 1 (ordering after scheduling); prerequisite of S3 and of #586 |
| Core | `core/periods.py`: `ResolvedPeriod(period_id, title, start, end)`, `resolve_periods(project, placements)` (Project order; literal date, or `placements[object][endpoint]`), `period_range_diagnostics(project, placements)` (`E_PROJECT_PERIOD_ORDER` when a reference makes the range empty or inverted, message naming both resolved dates) |
| Use cases | `usecases/project_checks.py` (`schedule_project_mapping` returns a rejected `ProjectSchedule`) and `usecases/render_review.py` (`_project_review` raises `RenderRejected`) call it once each (F4); `review_projects` unchanged |
| Specification | 05: the post-placement rule and the `validate` limitation |
| Tests | resolution for a span `start`/`end`, a fixed point, a scheduled point and a rollup; a reference that moves with a re-plan; inverted and empty ranges rejected at both sites with the pointer; literal-only periods unaffected; `chrona schedule` JSON unchanged for a Project without periods (CLI characterization golden untouched); mutation: remove each call |
| Boundary | `scheduling/` untouched; no Scene or SVG byte changes |

## S3: View selection, Theme paint, Layout band, Scene primitive, corpus evidence

| Item | Detail |
| --- | --- |
| Rows | Acceptance 2 (selection, Theme paint, pattern), 3 (band primitive, sourceRef, contrast and perceptibility), 4 (corpus slide through YAML) |
| View | `schemas/view-v0.28.schema.yaml`: optional `periods` (`id` only in this slice) and `periods` added to the dependency-network prohibition (one L1 delta); `presentation/contracts/resources.py`: `ViewInput.periods`, `E_VIEW_PERIOD_DUPLICATE`; `usecases/render_review.py`: select resolved periods in View order, `E_VIEW_PERIOD_UNKNOWN` with the declared ids |
| Model | `ReviewProjection.periods`, `SurfaceContentInput.periods` (typed `PeriodBandIntent`), defaulting to `()`; `review/v05_content.py` copies them |
| Registry and Theme | `model/semantic_registry.py`: `periodBand` (decoration, `ContrastClass.DECORATION`); `scene/capabilities.py`: role `period-band` (patterned Rect paint plus `backgroundTreatment`, `backgroundPaintOrder`) and its catalogue-pattern admission; `layout/surface_completion.py`: `_RECT_PATTERN_THEME_ROLES` |
| Layout | New `layout/surface_periods.py` (geometry, clipping, `I_LAYOUT_PERIOD_OUTSIDE_WINDOW`); `surface_composer.py` one call; `surface_backgrounds.py`: `BACKGROUND_SEMANTIC_IDS` and the widened overlay relation (F3) |
| Scene | `scene/v05_builder.py`: background purpose list, emission of the Rect with `sourceRef` the period id |
| Specification | 06 (§7.1 View `periods`), 49 (registry row), 50 (§3.4 band, overlap relation, window rule), 07 (pattern-admission list), 33 (§8.3 module ownership table row for `surface_periods`) |
| Guards that change with the slice | `tests/unit/tools/test_schema_identifiers_and_license.py` (the View id-site count: the new `id` keeps the sibling `minLength: 1` form), `tests/unit/chrona/presentation/model/test_semantic_registry_contrast.py` (the decoration role list), `tests/acceptance/output/test_generated_output_properties.py` (the timeline slot purposes), `tests/support/synthetic_review.py` (an optional `icon_catalogs` argument so a synthetic render can resolve a catalogue pattern) |
| Synthetic tests | geometry from dates through the scale; clipping and outside-window omission with the diagnostic; fill, outline and `none` (absent disposition); a catalogue pattern (Scene `catalogPattern`); paint order beneath marks and above bands; reference-resolved dates; unknown id, duplicate id, missing Theme role (`E_THEME_ROLE_REQUIRED`); the overlay relation (each allowed pair, each reversed pair, equal order); contrast gate fails a too-faint band and passes a sufficient one; perceptibility runs; a View without `periods` is byte-identical |
| Evidence | HALCYON-1: `project.yaml` `periods.launch-window` (`start` referencing `launch`, `end: 2027-11-06`); `themes/wallboard.yaml` `period-band` (pattern if one fits, opacity 1 where a pattern is used) with colour bindings; `views/02-programme-board.yaml` `periods`; contexts re-pinned by the materializer tool; the README sentence. Rendered PNG of slide 02 inspected; batch diff shows fifteen unchanged SVGs and provenance-only Scene changes (F6) |
| Gate | Schema equivalence, conformance (including the decoration witness and `check_semantic_registry_reachability`), `regenerate_public_examples --check`, focused and affected unit tests, three-OS matrix after merge |
| Boundary | The only slice that changes a committed example; the only slice that registers a classified role |

## S4: the label

| Item | Detail |
| --- | --- |
| Rows | Acceptance 2 (label placement options), 3 (label primitive, contrast, perceptibility), completes 4 |
| View | `periods[].label` (`placement`, `overflow`) added in place |
| Registry and Theme | `periodLabel` (label, `ContrastClass.STATE_TEXT`) and `periodLabelChip`; roles `period-label` (text measurement and paint, `contrastTreatment`) and `period-label-chip`; `label_chip_semantic` entry; `_CATALOG_PATTERN_ROLES` if a chip may carry a pattern (decided in the slice) |
| Layout | The label request to the shared label engine in the pre-route phase (anchors `top`, `bottom`, `inside`; overflow `suppress` or `visible-overflow`), the placed label registered as an obstacle for later phases, the chip through the existing mechanism |
| Scene | Text primitive `period-label:<id>` with `sourceRef` the period id; chip Rect |
| Specification | 06, 49, 50 (label rule, obstacle, overflow) |
| Synthetic tests | each placement; shift inside the plot; a collision with a mark moves it or applies each overflow policy with the existing warnings; a following member label avoids it; chip present and absent; title and id fallback; text contrast gated at both floors; missing `period-label` role error; mutation: stop registering the obstacle |
| Evidence | The slide 02 label through `wallboard.yaml` and the View; inspected as an image |
| Boundary | Changes slide 02 only (and any slide whose View selects a labelled period) |

## S5: acceptance

A single review in `docs/reviews/current/` with the marker and one row per literal acceptance item, re-fetching
the issue body and comments first, a `tools/check_issue_acceptance_reviews.py` run, then the exact-main
three-OS conformance run on the review commit before closing the issue. The successor issue for the items of
design D11 is linked from every narrowed row (none is an acceptance row).

## Order and dependencies

S1, then S2, then S3, then S4, then S5; S1 and S2 share a file but not behaviour, so each rebases on the
previous merge. S3 needs S2's `resolve_periods`. #586 needs S2 only.
