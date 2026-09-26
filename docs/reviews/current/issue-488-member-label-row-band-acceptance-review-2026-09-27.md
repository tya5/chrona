<!-- chrona:literal-acceptance/v1 -->

# Release Review — Member Labels Stay in Their Own Row (#488)

**Reviewed product:** I488-1 `bac5a6c7` ([slice review](issue-488-member-label-row-band-i488-1-review-2026-09-27.md)). **Design:** [design](../../design/issue-488-member-label-row-band-design-2026-09-27.md), [architecture review](issue-488-member-label-row-band-architecture-review-2026-09-27.md).

## Literal issue acceptance

### Issue #488

- Source: [Issue #488](https://github.com/tya5/chrona/issues/488)
- Observed: 2026-09-27

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A member label placed in the plot never leaves its own row band. If no candidate fits inside it, it takes the declared fallback (start, then suppress), and the suppression is counted. | met | The row band is the label request's `bounds` for every candidate, including the side search ([`surface_composer.py`](../../../src/chrona/presentation/layout/surface_composer.py)). The counted suppression is covered by [suppression-count tests](../../../tests/integration/test_render.py). | — |
| 2 | The HALCYON-1 default draft places every member label at its bar's end or start inside its own row, or reports it suppressed. | met | [Default-draft test](../../../tests/integration/test_readable_defaults.py): 24 visible, all at end or start inside their rows; 4 counted as suppressed; 29 items in all. | — |

## Programme-level criteria (optional)

- CI: [four-job CI run](https://github.com/tya5/chrona/actions/runs/36269962926) on `bac5a6c7`, green.

## Architecture conclusion

- The change is one Layout region input, and it reuses `place_label`'s existing bounds check.
- View, Theme, Scene and adapters are unchanged.
- Seven slides' label positions change; the slice review attributes each one.

Release disposition: both rows met.
