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
| 2 | Do not edit `examples/**`. Refs #1283, #1269. | met | [Implementation commit](https://github.com/tya5/chrona/commit/dbd88829) changes six schema, Layout/consumer and synthetic-test files only; `git diff --name-only ff749b0b...dbd88829 -- examples` is empty. | — |

## Programme-level criteria (optional)

**Release pending:** ordinarily adopted READY main `02ac93ab` containing #1367/#1366. Plain/mixed-role Scene/SVG tests prove the independent strip and every non-caption primitive remain unchanged. Fresh public snapshot, exact-head gates and acceptance-containing exact-main three-OS release must succeed before closure. Local completion is not published release acceptance.

## Architecture conclusion

Layout carries completed per-header band padding separately from measured content; only positive-width nonsuppressed text activates it. Background composition consumes it only for the text-sized caption and table-clamps the completed Rect. Scene/adapters do not measure or select geometry. Leading/tab/ellipsis, folded block completion, other extents and authored resource identity remain unchanged. Root and independent Luna review found no ownership or contract gap.

Own-venv caption/text-extent integration: **39 passed** (44.10s), including plain/mixed-role independent-strip joins. Broader integration/strip join77 and adjacent leading-inset/run/builder90 passed. No full release claim.

Schema-equivalence against source main `39d6cc9a`: **PASS**, live Theme additive=1/equal=37; 482 documents/739 probes, four known invalid fixtures unchanged. L2+L3=58.8s within the60s budget. #1367 owns the stale View delta retirements; this item does not repeat them.
