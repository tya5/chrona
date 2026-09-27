<!-- chrona:literal-acceptance/v1 -->

# Release Review — As-of Dash (#423)

**Reviewed product:** `1e7c2882` on `main`, slice I483-1 of the [#483 readable-defaults design](../../design/issue-483-readable-defaults-design-2026-09-26.md), which implements #423 jointly. Slice review: [I483-1](issue-483-readable-defaults-i483-1-review-2026-09-26.md).

## Literal issue acceptance

### Issue #423

- Source: [Issue #423](https://github.com/tya5/chrona/issues/423)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | At least one corpus slide renders a dashed stroke, and `stroke-dasharray` appears in committed output. | met | 16 committed SVGs under `examples/*/generated/` contain `stroke-dasharray` (the as-of line, `[4, 3]`); [I483-1 review](issue-483-readable-defaults-i483-1-review-2026-09-26.md). | — |
| 2 | The as-of line is visually distinct from the axis gridlines by more than colour. | met | Every shipped Theme dashes `as-of`/`asOf`, while gridlines stay solid; [`test_print_mono_separates_slips_and_as_of_in_greyscale`](../../../tests/integration/test_readable_defaults.py) asserts dash versus no dash on completed paint; PNG check in the [slice review](issue-483-readable-defaults-i483-1-review-2026-09-26.md). | — |
| 3 | `dashPattern` is reported as realized in the presentation coverage report. | met | [`docs/gallery/presentation-coverage.md`](../../gallery/presentation-coverage.md): `theme body.values.*.type "dashPattern"` is realized by 21 slides (was `—`). | — |

## Programme-level criteria (optional)

- CI: [run 36244923666](https://github.com/tya5/chrona/actions/runs/36244923666), green on all four jobs.

## Architecture conclusion

The existing Theme → Scene → adapter dash path is now used by the shipped Themes; no code changed. Release disposition: all rows met.
