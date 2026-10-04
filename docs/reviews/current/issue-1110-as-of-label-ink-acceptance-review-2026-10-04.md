<!-- chrona:literal-acceptance/v1 -->

# Issue #1110: as-of label ink and typography, acceptance review

Source: [Issue #1110](https://github.com/tya5/chrona/issues/1110), re-fetched 2026-10-04 after the merges (body unchanged, 1696 characters; three comments: the reviewer's addendum asking for the label's own typography, and this work's two status blocks). The rows below are the four literal bullets of the body's acceptance list plus the reviewer's addendum. Work record: [issue-1110-asof-label-ink-2026-10-04.md](../../planning/active/issue-1110-asof-label-ink-2026-10-04.md); living contract [Specification 07](../../specification/07-style-and-theme.md) (as-of label ink and typography).

Slices: ink [PR #1118](https://github.com/tya5/chrona/pull/1118) (`1bd683a4`); typography [PR #1136](https://github.com/tya5/chrona/pull/1136) (`fcb501de`). Each had conformance, three pytest shards, newest-Python reproduction and derived-ready green on its final head before merge. The general successor, [#1117](https://github.com/tya5/chrona/issues/1117) (every declared Theme role needs a consumer), is merged apart from one conformance registration.

## Literal issue acceptance

### Issue #1110

- Source: [Issue #1110](https://github.com/tya5/chrona/issues/1110)
- Observed: 2026-10-04

| # | Literal acceptance criterion | Disposition | Evidence | Successor |
| ---: | --- | --- | --- | --- |
| 1 | With `as-of-label.fill` declared, the `as-of-label` Text carries that colour and is gated against the chip. | met | [`test_as_of_label_ink.py`](../../../tests/integration/test_as_of_label_ink.py) `test_a_declared_fill_paints_the_label_and_the_gate_judges_it_against_the_chip`: the published Text has `visualRole` `as-of-label` and the declared colour, its bounds unchanged, and the contrast gate judges it on the chip's fill (white passes on the amber chip, the default dark ink does not); `test_an_ink_that_cannot_be_read_on_the_chip_is_reported` reports an unreadable ink. The role is registered in [`capabilities.py`](../../../src/chrona/presentation/scene/capabilities.py). | none |
| 2 | Without it, the output is byte-identical. | met | [`test_as_of_label_ink.py`](../../../tests/integration/test_as_of_label_ink.py) `test_without_the_binding_the_label_keeps_the_text_colour_byte_for_byte`; `regenerate_public_examples --write` on the PR left every slide but target B unchanged (only `21-target-b`, which declares the binding, changed), and the typography slice changes no slide (no corpus Theme declares a size for the role). | none |
| 3 | A fixture declaring a binding no primitive reads (for example `as-of-label.stroke`) produces the chosen diagnostic. | met | [`test_as_of_label_ink.py`](../../../tests/integration/test_as_of_label_ink.py) `test_a_binding_no_primitive_reads_fails_at_its_pointer` (`as-of-label.stroke`, `as-of-label.gradientStart`): the closure fails with `E_THEME_ROLE_PROPERTY_UNSUPPORTED` at the binding's pointer, because the role admits only the properties the label reads (`fill`, `opacity`, the text measurement). For a role name nothing registers or names, the general case is the successor [#1117](https://github.com/tya5/chrona/issues/1117): [`test_theme_role_consumers.py`](../../../tests/integration/test_theme_role_consumers.py) shows the warning `W_THEME_ROLE_UNREAD` at the pointer. Mutations of the registration, the admitted property set and the builder branch each fail a test. | none |
| 4 | Target B: the as-of label is white on the amber chip. | narrowed | The knob exists and is documented, and white on `#B8761F` (contrast 3.717 against 4.5) is now one warning rather than a blocking error, since [#1126](https://github.com/tya5/chrona/issues/1126) made a Theme's contrast policy decide it and target B is not held to the floors. Whether target B keeps the white ink is the reviewer's decision in the target-B YAML (reviewer PR #1061, which drops `as-of-label.fill`), not an edit of this work. | [#987](https://github.com/tya5/chrona/issues/987) |
| 5 | Addendum (reviewer): give `asOfLabel` a Theme text role for size, weight and ink, defaulting to today's `text` binding, with a fixture where the chip's block size follows that role. | met | The `as-of-label` role now admits the text measurement properties; with a `fontSize` it measures and sets the label (`as_of_label_typography_role` in [`asof_foot_reserve.py`](../../../src/chrona/presentation/layout/asof_foot_reserve.py)), without one the label is measured in `text`, and a role that binds only a colour keeps `text`. [`test_as_of_label_ink.py`](../../../tests/integration/test_as_of_label_ink.py) `test_a_role_with_its_own_size_sets_the_label_and_its_chip_follows` (chip block size and padding follow the role: 9 px text gives a 15.3 px chip against 23.8), `test_a_role_that_only_binds_a_colour_keeps_the_text_size` and `test_the_space_reserved_below_the_plot_follows_the_role_size` (the `below-plot` reservation of #1063 equals the placed gap plus chip from the role's size). Five of five mutations fail a test. | none |

## Programme-level criteria (optional)

None.

## Architecture and release conclusion

Theme declares the role (ink and optional typography); Layout owns the typography role choice in one function shared by the label request, the chip padding and gap and the below-plot reservation; Scene paints with the role only when a fill is bound; adapters are unchanged. No schema property is added (role properties are open per role contract).

Disclosures:

- No image was read for the typography slice: no corpus slide declares the role, so every Scene is unchanged. The ink slice changed only `21-target-b`'s label colour, which the reviewer owns.
- The mock chip size (68 x 16, 10.5 px) is reachable by a Theme declaring `as-of-label` with that size and `chipPadding`; whether target B does is the reviewer's adoption (#987).
- Target B's remaining dead role lines (`annotation-text`, `table-header`, `range`) are the reviewer's to drop; #1117's conformance registration waits for that.

Exact review-bearing-main three-OS CI must pass before closing #1110; that run is recorded in the closing comment.
