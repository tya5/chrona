<!-- chrona:literal-acceptance/v1 -->

# Release Review — Progress Track Inset (#430)

**Reviewed product:** `dd8e5b0d` on `main`. **Design:** [design](../../design/issue-430-progress-track-inset-design-2026-09-26.md), [architecture review](issue-430-progress-track-inset-architecture-review-2026-09-26.md), Specification 61. The work was a single slice (I430-1), so this review also serves as its slice review.

## Evidence and byte review

- **Theme.** `progressInset` is an additive optional v0.11 role property; `markCornerRadius` is reused on `progress-fill`. Values out of range raise `E_THEME_TOKEN_TYPE` at the role pointer ([`test_progress_track_is_optional_and_range_checked`](../../../tests/unit/chrona/presentation/model/test_theme_tokens.py)).
- **Layout.** `progress_fill_bounds(host, fraction, inset)` deflates the host (the track) and measures the fraction against the inner width. [`test_inset_progress_track_measures_the_fraction_against_the_inner_track`](../../../tests/unit/chrona/presentation/layout/test_surface_quality.py) checks bar lengths of 4, 20, 58, 132 and 388 px:
  - 0 returns no fill;
  - 1 fills exactly the inner track;
  - ½ is half of it;
  - the inner track is never below half the bar.

  `test_zero_progress_inset_is_the_published_full_height_fill` checks that zero inset reproduces the old formula.
- **Scene.** The fill Rect carries its completed `cornerRadius` (half the fill height at a ratio of 0.5). The clip to the host is kept.
- **Public materializers:** `--write`, then `--check`: **22 slides**. The 21 existing slides are byte-identical, including the eight with progress fills. The new Controller Z `progress-track` slide, whose Theme is a v0.11 copy of `executive-light` plus the two tokens, renders three inset capsules 388, 132 and 58 px wide, each inside its host bar with rounded ends ([`test_committed_progress_track_example_draws_inset_capsules_at_several_lengths`](../../../tests/unit/chrona/presentation/layout/test_surface_quality.py)).
- **Deviation from the design:** the design proposed a v0.12 derived Theme. v0.12 inheritance may only replace existing tokens and roles (`E_THEME_INHERITANCE_OVERRIDE_UNKNOWN`), and `executive-light` has no 0.5 token, so the example Theme is a standalone v0.11 copy, as Controller Z's `material-icons-light` already is.
- **Hardcoded corpus counts updated for the new slide:**
  - public Scenes and SVGs 21 → 22;
  - axis labels 164 → 171;
  - hosted DVT labels 6 → 7.
- **Checks:** full `pytest` 1167 passed, 20 skipped; conformance PASS.
- **Visual check:** a PNG crop of the new slide shows the capsules inset from their bars with a visible gap all round.

## Literal issue acceptance

### Issue #430

- Source: [Issue #430](https://github.com/tya5/chrona/issues/430)
- Observed: 2026-09-26

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A theme can declare a progress track's padding, and a bar renders as a track with a visibly inset fill with rounded ends of its own. | met | `progressInset` plus `markCornerRadius` on `progress-fill`; [committed slide test](../../../tests/unit/chrona/presentation/layout/test_surface_quality.py); `examples/controller-z/generated/progress-track.svg`. | — |
| 2 | With a non-zero padding, a fraction of 1 fills the inner track edge to edge and a fraction of 0 renders nothing, at every bar length. | met | [Parametrized geometry test](../../../tests/unit/chrona/presentation/layout/test_surface_quality.py) at five lengths, including 4 px. | — |
| 3 | With the default padding of zero, the eight committed examples that render a progress fill reproduce byte-identically. | met | `tools.regenerate_public_examples --check` after the change, with no bytes changed in the 21 existing slides; [zero-inset formula test](../../../tests/unit/chrona/presentation/layout/test_surface_quality.py). | — |
| 4 | One committed example renders the inset treatment at more than one bar length, so the short-bar case is in the corpus rather than argued about. | met | [Controller Z `progress-track`](../../../examples/controller-z/manifest.yaml): 388, 132 and 58 px fills. | — |

## Programme-level criteria (optional)

- CI: the run on `dd8e5b0d` failed only the two generated-report checks (`presentation-contrast`, `presentation-font-identity`) because the reports were not refreshed for the new slide; fixed in `edf985f6`, whose [four-job CI run](https://github.com/tya5/chrona/actions/runs/36246975774) is green.

## Architecture conclusion

- The Theme declares ratios, and Layout completes geometry and radius in one function.
- Scene carries a completed radius on an existing Rect, and the adapters are unchanged.
- #478's role/property admission (the other session) must register `progressInset` and `markCornerRadius` on `progress-fill`.

Release disposition: all rows met.
