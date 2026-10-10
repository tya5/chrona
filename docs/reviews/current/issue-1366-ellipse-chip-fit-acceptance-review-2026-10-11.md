<!-- chrona:literal-acceptance/v1 -->

# Ellipse chip fit acceptance (#1366)

Implementation: `f0e300d978a9196bc9869d53bc49420fbbd52b83`. [Current design/architecture/implementation record](https://github.com/tya5/chrona/issues/1366#issuecomment-6099168189); normative Spec07 in `a332edd1`.

## Literal issue acceptance

### Issue #1366

- Source: [Issue #1366](https://github.com/tya5/chrona/issues/1366)
- Observed: 2026-10-11

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | In a Scene test, a 20-character label with `fit: ellipse` gives a burst whose block extent is at most the text block plus the inset times a stated ratio, with every label corner inside it. | met | [Actual Scene/SVG test](../../../tests/integration/test_label_chip_shapes.py), `test_ellipse_burst_contains_twenty_character_label_in_scene_and_actual_svg`: exactly20characters, nominal block extent ≤sqrt(2)/f times padded text block; independent polygon inclusion for all corners, affine inradius, and actual SVG outline equality. [Geometry tests](../../../tests/unit/chrona/presentation/layout/test_chip_shape_geometry.py) cover both inradius branches and width-independent height. | — |
| 2 | Existing outputs are byte-identical. | met | [Exact-head derived preview](https://github.com/tya5/chrona/actions/runs/38084545441/job/114308253248): artifact `derived-snapshot-7b172497b7f2fafd9b150ecef504128643380d17` before/after paths match READY `26e9db96`; all46 Scene and all46 SVG files are raw-byte identical. Snapshot SHA256 `286a78c3bb1e7fc5192a8706cfcf65a9fd5f44e2bcc4331f734870a1d667c661`; only diagnostic inventory and coverage reports change. [Circle characterization fixtures](../../../tests/unit/chrona/presentation/layout/test_chip_shape_geometry.py) independently preserve absent-input/explicit-circle behavior. | — |
| 3 | Do not edit `examples/**`. Refs #1269 (Sunday Strip). | met | [PR #1384 file diff](https://github.com/tya5/chrona/pull/1384/files): `git diff --name-only 26e9db96...7b172497 -- examples` is empty. | — |

## Programme-level criteria (optional)

**Release pending:** ordinary adoption of #1367 READY main `26e9db96805ace211ad8aa0c8eeafa3a44996a02` is complete; joined token/geometry/measurement/Scene/SVG/period tests: **119 passed** (28.72s). Publish this item's single PR; fresh exact-head snapshot/gates and acceptance-containing exact-main three-OS release remain required before closure.

## Architecture conclusion

Root and independent Luna review: Theme declares optional burst-only fit, runtime default circle; shared Layout completes affine geometry using true inradius and actual asymmetric envelope. All four chip roles share it. Scene/adapters never fit shapes, and authored identity is not normalized away. Rectangle/catalog closed contracts, circle operation order, padding/stroke distinction and existing selected-role failures remain unchanged. No project-specific rule or unresolved design gap.

Focused geometry/Scene/SVG join on ordinary adopted READY `f890cea6`: **47 passed** (22.50s). Prior token/geometry/measurement/Scene batch **111 passed** (20.43s); schema/member/period/finish **64 passed** (9.29s, overlapping); both-fit nonfinite **2 passed**; schema parts **83 passed**. Tests exercise both fit branches, odd/even peaks, q=1/N=2, corner clearance, all four roles, actual SVG and closed-schema/default behavior.

Changed-code schema-equivalence: **PASS**, Theme additive=1/equal=37,482documents/739probes; four known invalid fixtures unchanged, L2+L3=57.5s within60s. Incoming #1367 owns stale View delta retirement. Full local pytest is not duplicated.
