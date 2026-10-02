# Implementation Plan — Guided annotations and the guided grouping subset (#709)

Design: [design](../../design/issue-709-guided-annotations-design-2026-10-01.md). This plan is the authority for mechanics.

**Status:** I709-D (#749) and I709-A (#752) merged; I709-B in review. The acceptance review is the lead's.

## Literal acceptance mapped to slices

| # | Row (short) | Slice | Evidence |
| ---: | --- | --- | --- |
| 1 | the guided annotation works or is rejected clearly | I709-A | defaulting rule (design D2); no frozen container reaches a source (D1); failures are `AuthoringError` |
| 2 | end-to-end: a guided annotation yields a valid View and a rendered Scene containing it | I709-A | `test_authoring.py` end-to-end test through View parse, Scene build and render |
| 3 | the guided `grouping` subset is named and tested | I709-B | `viewGroupingBy` and `guidedViewGroupingBy`, subset-of-superset test, site tests |

## Slices

| Slice | Content | Gate |
| --- | --- | --- |
| I709-D | design note and this plan (docs only) | `pr-title`, `derived-ready` |
| I709-A | `_apply_view_overrides`: plain-data copy of the override, default `facet: planned` and `endpoint: finish` for a guided anchor; tests: end-to-end, one per default, a kept explicit member, the original `RepresenterError` reproduction as a regression, sources are plain data; mutation check (remove each default, see its test fail, restore) | unit tests, `tests/unit`, conformance, import direction, derived evidence, public-example regeneration check; no committed Scene byte changes |
| I709-B | `viewGroupingBy` and `guidedViewGroupingBy` in `vocabulary-v0.1` (untyped enums, frozen digests, inventory entry), subset-of-superset test, packaged-resources test; adoption by the authoring-workspace `grouping` site and View `grouping.by` only if the S0 gate (`--base-rev origin/main`) shows L1 equal | S0 gate output in the PR, wheel build and `tools/wheel_smoke.py`; `KIND_COVERED_THROUGH` already maps `schema-part-vocabulary` to `render-context`, so no new kind is added |

## Stop conditions

A slice stops and reports when it would change a committed Scene byte, newly reject a committed document, or need an edit to authoring-workspace's accepted shape or a version bump.

## Derived documents

No slice edits a derived document. After merge CI's derived-sync regenerates `docs/diagnostics/inventory.md` (source line numbers shift with a source edit), `docs/declared-value-inventory.md`,
`docs/vocabulary-inventory.md` (I709-B adds two definitions) and the gallery coverage page where they change.
