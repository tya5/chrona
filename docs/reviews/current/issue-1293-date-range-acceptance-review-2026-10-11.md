<!-- chrona:literal-acceptance/v1 -->

# Date-range endpoint acceptance (#1293)

Authority: Spec24 section1.1, published before code at `a5144289`. Implementation: `0d864b29`, `5d7dedae`, `c2251b07`. [Issue work record](https://github.com/tya5/chrona/issues/1293).

## Literal issue acceptance

### Issue #1293

- Source: [Issue #1293](https://github.com/tya5/chrona/issues/1293)
- Observed: 2026-10-11

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A unit test of the formatter: `[2027-01-04, 2027-01-05)` renders as a single day (`04 Jan`) in inclusive mode, and as `04 Jan – 05 Jan` in exclusive mode. A multi-day span renders `start – end−1` in inclusive mode. | met | [Formatter tests](../../../tests/unit/chrona/presentation/model/test_date_range_display.py) cover both modes, multi-day/year boundary, locales, open/nonpositive/point cases and Planned/Actual normalization. | — |
| 2 | A render test of `chrona init`'s starter project with the default preset asserts the `Plan` cell text from the Scene equals the inclusive range of each object. | met | [Actual CLI init/default render](../../../tests/integration/test_default_date_range_display.py) checks every Plan cell and SVG text; starter Project bytes remain unchanged. | — |
| 3 | Existing Views that declare `dateRange` keep their current output unless the PR lists the changed corpus cells and states why. | not met | [Live admission/default and formatter tests](../../../tests/integration/test_default_date_range_display.py) prove absent mode is exclusive; a fresh public snapshot/cell-delta audit is still required before this broad output criterion is accepted. | — |
| 4 | Do not edit `examples/**`. | met | [Implementation commit](https://github.com/tya5/chrona/commit/5d7dedae): authored WIP diff `git diff --name-only origin/main...HEAD -- examples` is empty. | — |

## Programme-level criteria (optional)

Focused formatter/live schema/init/corpus-mirror batch: 24 passed (6.86s).
Full schema-equivalence against `e19005d0`: PASS; two exact View deltas,
37 equal schemas, 482 documents/739 probes, four known-invalid fixtures
unchanged; L2+L3=48.7s. Final READY/public snapshot and review-containing
exact-main three-OS release remain pending; issue stays open.

## Architecture conclusion

View owns the explicit display choice; normalization applies it once before
Layout measures text. Domain dates, schedules, bars and routes are unchanged.
Existing authored Views default to exclusive; only the packaged default Plan
column explicitly adopts inclusive. Layout/Scene/adapters do not reinterpret
scheduled endpoints. No corpus, working-day or preset-ID branch was added.
