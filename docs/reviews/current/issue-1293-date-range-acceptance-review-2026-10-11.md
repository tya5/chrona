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
| 3 | Existing Views that declare `dateRange` keep their current output unless the PR lists the changed corpus cells and states why. | met | [Live admission/default and formatter tests](../../../tests/integration/test_default_date_range_display.py) prove absent mode is exclusive. Batched public audit at `3a51cfdb` passes all46 materializers: every declared Scene/SVG is byte-identical, hence zero changed corpus cells. The packaged default Plan column intentionally opts into inclusive display and is covered by actual init/Scene/SVG tests. | — |
| 4 | Do not edit `examples/**`. | met | [Implementation commit](https://github.com/tya5/chrona/commit/5d7dedae): authored WIP diff `git diff --name-only origin/main...HEAD -- examples` is empty. | — |

## Programme-level criteria (optional)

Focused formatter/live schema/init/corpus-mirror batch: 24 passed (6.86s).
Full schema-equivalence at `16ddae45` against trusted READY `95b2fddc`: PASS;
one changed View schema (two exact endpoint property/constraint paths),
37 equal schemas, 482 documents/739 probes, four known-invalid fixtures
unchanged; L2+L3=57.3s within60s. Final READY/public snapshot and review-containing
exact-main three-OS release remain pending; issue stays open.
After ordinary integration of main `b05b09bf`, date-range/default-axis
tests pass:28 (5.27s). Public audit at `3a51cfdb`:46/46 PASS, all declared
Scene/SVG bytes identical. Retained outputs: `chrona-1293-public-audit-7kiya4vl`.
Subsequent `512ae424` adds only #1294's acceptance-review lines, not product code.

## Architecture conclusion

View owns the explicit display choice; normalization applies it once before
Layout measures text. Domain dates, schedules, bars and routes are unchanged.
Existing authored Views default to exclusive; only the packaged default Plan
column explicitly adopts inclusive. Layout/Scene/adapters do not reinterpret
scheduled endpoints. No corpus, working-day or preset-ID branch was added.
