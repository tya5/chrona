from datetime import date

import pytest

from chrona.presentation.contracts import ClosureIdentity, parse_contract
from chrona.presentation.contracts.resources import ReviewDetailProfileContract, SchemaContractError, ThemeContract
from chrona.presentation.model.projection import ReviewPeriod, ReviewProjection
from chrona.presentation.review.v05_content import legend_entries


def _detail(entries):
    value = {
        "version": "chrona/review-detail-profile/v0.1",
        "id": "legend-detail",
        "body": {"legend": entries},
    }
    return parse_contract(
        ClosureIdentity("review-detail-profile", value["id"], "r", "sha256:" + "a" * 64), value,
    )


@pytest.mark.parametrize("shape", ("circle", "rule-pair"))
def test_closed_detail_swatch_shape_is_typed_and_threaded_with_period_source(shape):
    detail = _detail([{"role": "period-band", "label": "Launch", "sourceRef": "launch",
                       "swatchShape": shape}])
    assert isinstance(detail, ReviewDetailProfileContract)
    entry, = detail.detail.legend
    assert entry.swatch_shape == shape

    period = ReviewPeriod("launch", "Launch", date(2026, 1, 1), date(2026, 2, 1))
    projection = ReviewProjection((), (date(2026, 1, 1), date(2026, 2, 1)), (), (), periods=(period,))
    result, = legend_entries(detail.detail, {}, projection, None, closed_days_drawn=False)
    assert (result.role, result.label, result.source_ref, result.swatch_shape) == (
        "period-band", "Launch", "launch", shape,
    )
    assert result.swatch_placement_id == "legend-period-swatch:launch"


def test_absent_detail_swatch_shape_retains_typed_default_and_existing_identity():
    detail = _detail([{"role": "planned", "label": "Planned"}])
    entry, = detail.detail.legend
    assert entry.swatch_shape is None

    projection = ReviewProjection((), (date(2026, 1, 1), date(2026, 2, 1)), (), ())
    result, = legend_entries(detail.detail, {}, projection, None, closed_days_drawn=False)
    assert result.swatch_shape is None
    assert result.swatch_placement_id == "legend-swatch:planned"


def test_detail_swatch_shape_rejects_values_outside_the_shared_closed_vocabulary():
    with pytest.raises(SchemaContractError) as raised:
        _detail([{"role": "planned", "label": "Planned", "swatchShape": "triangle"}])
    assert raised.value.violation is not None
    assert raised.value.violation.pointer == "/body/legend/0/swatchShape"


def test_theme_default_swatch_shape_uses_the_shared_closed_vocabulary():
    theme = {"version": "chrona/theme/v0.15", "kind": "theme", "id": "shape-theme",
             "body": {"values": {}, "roles": {"legend-swatch": {"swatchShape": "rule-pair"}},
                      "colorBindings": {"text.fill": "text"}}}
    contract = parse_contract(ClosureIdentity("theme", theme["id"], "r", "sha256:" + "a" * 64), theme)
    assert isinstance(contract, ThemeContract)
    assert contract.theme_input["body"]["roles"]["legend-swatch"]["swatchShape"] == "rule-pair"

    theme["body"]["roles"]["legend-swatch"]["swatchShape"] = "triangle"
    with pytest.raises(SchemaContractError) as raised:
        parse_contract(ClosureIdentity("theme", theme["id"], "r", "sha256:" + "a" * 64), theme)
    assert raised.value.violation is not None
    assert raised.value.violation.pointer == "/body/roles/legend-swatch/swatchShape"
