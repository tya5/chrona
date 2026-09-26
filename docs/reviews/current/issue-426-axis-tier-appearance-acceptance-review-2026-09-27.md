<!-- chrona:literal-acceptance/v1 -->

# Release Review — Axis Tier Appearance (#426)

**Reviewed product:** `6e3b4529` on this branch (`0e75e9d6` View v0.24 + migration, `c55d6c05` lane/appearance implementation, `6e3b4529` public evidence). **Design:** [design](../../design/issue-426-axis-tier-appearance-design-2026-09-26.md), [architecture review](issue-426-axis-tier-appearance-architecture-review-2026-09-26.md), [Specification 39 §1.2](../../specification/39-axis-and-observation-clarity.md#12-axis-tier-appearance-426). **Slice review:** [I426-1](issue-426-axis-tier-appearance-i426-1-review-2026-09-27.md).

## Literal issue acceptance

### Issue #426

- Source: [Issue #426](https://github.com/tya5/chrona/issues/426)
- Observed: 2026-09-27

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | A view can declare two `band` tiers and both render, each in its own lane, neither covering the other. | met | [I426-1 review](issue-426-axis-tier-appearance-i426-1-review-2026-09-27.md): independent per-role lane cursors in `layout/surface_composer.py`; `test_two_band_tiers_each_render_in_their_own_non_overlapping_lane` fails before and passes after. | — |
| 2 | Two band tiers can take different fills from the Theme. | met | [I426-1 review](issue-426-axis-tier-appearance-i426-1-review-2026-09-27.md): per-ordinal semantic id (`axisBandDecoration`/`axisBandDecoration2`); `test_two_band_tiers_resolve_different_fills_from_the_theme` fails before and passes after. | — |
| 3 | Two labels tiers can take different sizes, weights and colours. | met | [I426-1 review](issue-426-axis-tier-appearance-i426-1-review-2026-09-27.md): per-tier `typographyRole` resolution and per-ordinal semantic id (`axisLabel`/`axisLabel2`/`axisLabel3`); `test_two_labels_tiers_resolve_different_sizes_weights_and_colours` fails before and passes after. | — |
| 4 | One committed example renders a two-tier date band whose tiers are visually distinct, and reproduces byte-identically. | met | [I426-1 review](issue-426-axis-tier-appearance-i426-1-review-2026-09-27.md): `examples/controller-z` slide `axis-tiers` (new View, derived Theme, context, manifest entry); `tools.regenerate_public_examples --check` PASS; rendered PNG crop inspected. | — |

## Non-literal fold-in

- Source: comment on [Issue #426](https://github.com/tya5/chrona/issues/426), folding in a criterion from the closed #405 ("a band tier can resolve alternating fills from a Theme, and a committed slide shows it").

| Item | Disposition | Evidence | Successor |
| --- | --- | --- | --- |
| A band tier can resolve a different fill per interval (alternating, or a wallboard-style per-coarser-interval domain) from a declared Theme colour scale. | deferred | Design §6: the band loop already resolves its Theme fill once per interval (not once per tier), so the lookup point exists; only the role/scale selection on each iteration would need to become data-driven. Specification 60's declared colour scales are currently eligible only for `planned` member marks with a Project-field-tagged domain, not axis bands keyed by interval ordinal — a genuinely new eligible-target case. | A new issue extending Specification 60's eligible-target list to axis bands, keyed by interval ordinal rather than a Project field. Not filed by this session, per the lead's direction (2026-09-26: "File nothing; I will record it."). |

## Programme-level criteria (optional)

- Focused tests: `.venv/bin/python -m pytest -q -n 6 -p no:cacheprovider tests/unit/chrona/presentation tests/integration tests/cli tests/acceptance` — 984 passed, 21 skipped.
- `conformance/run_conformance.py` — PASS, all 31 checks (including `semantic-registry-reachability`, `layout-float-accumulation` and `presentation-coverage`, each touched by this issue's implementation).
- `tools.regenerate_public_examples --write --jobs 6` then `--check` — PASS, 23 slides; every changed `generated/*.scene.json` differs from its prior committed version only in the View provenance resource's `contentIdentity` hash (the required View v0.24 migration), structurally verified by stripping that one field; no committed SVG changed; the new `controller-z/axis-tiers` slide is the only evidence that differs beyond that hash.
- CI: pending (the lead fills in the run link).

## Architecture conclusion

Layer ownership held: View states intent only (`typographyRole`, a Theme role name); Layout alone derives lane geometry, semantic-id selection, and host/contrast resolution from it; Theme states tokens under role keys the schema already left open; Scene/adapters read the same closed id sets Layout and surface-quality validation use, with no new dispatch policy. No Scene, ColorScheme, or Layout Profile contract changed. The one deliberately non-uniform rule — a View with exactly one band tier keeps its historical whole-axis-slot geometry — is recorded normatively in Specification 39 §1.2, not left implicit.

Out of scope, and not left silent: per-interval/alternating band fills (#405 fold-in, deferred above); #466/#467 (annotation placement and lane rows, owned by another session, untouched by this issue's files); a third band semantic-id ordinal (a one-line follow-up if a future View needs it).

Release disposition: all four literal rows are met; the non-literal fold-in is deferred with its extension point named.
