<!-- chrona:literal-acceptance/v1 -->

# Group caption trailing inset acceptance (#1368)

Implementation: `dbd88829`. [Current design/architecture/implementation record](https://github.com/tya5/chrona/issues/1368#issuecomment-6099192641); normative Spec50 section3.4 in `93ea75fd`.

## Literal issue acceptance

### Issue #1368

- Source: [Issue #1368](https://github.com/tya5/chrona/issues/1368)
- Observed: 2026-10-11

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | In a Scene test, band end = drawn text end + the trailing inset, clamped to the column. | met | [Scene/SVG integration tests](../../../tests/integration/test_group_header_trailing_inset.py) assert plain/mixed-role actual drawn end plus header-font-size ratio, independently computed clamp, genuine ellipsis, unchanged text/content and block bounds. | — |
| 2 | Do not edit `examples/**`. Refs #1283, #1269. | met | Implementation `dbd88829` changes six schema, Layout/consumer and synthetic-test files only; `git diff --name-only ff749b0b...dbd88829 -- examples` is empty. | — |

## Programme-level criteria (optional)

**Release pending:** adopt the ready main containing #1367/#1366 before final publication; verify the independent strip remains unchanged. Fresh public snapshot, exact-head gates and acceptance-containing exact-main three-OS release must succeed before closure. Local completion is not published release acceptance.

## Architecture conclusion

Layout carries completed per-header band padding separately from measured content; only positive-width nonsuppressed text activates it. Background composition consumes it only for the text-sized caption and table-clamps the completed Rect. Scene/adapters do not measure or select geometry. Leading/tab/ellipsis, folded block completion, other extents and authored resource identity remain unchanged. Root and independent Luna review found no ownership or contract gap.

Own-venv focused integration batch: **37 passed** (29.37s), including existing text-extent replay; adjacent leading-inset, marked-run and Scene-builder regressions: **90 passed** (19.57s). These overlap no claimed full release. Initial missing property-owner registration and test-only tuple/string assumptions were corrected before acceptance.

Schema-equivalence against ready `ff749b0b`: **PASS**, live Theme additive=1/equal=37; 482 documents/739 probes, four known invalid fixtures unchanged, L2+L3=40.4s within 60s. Incoming #1367 already owns the five stale View delta retirements; this item does not repeat them.
