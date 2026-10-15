from datetime import date
from decimal import Decimal

import pytest

from chrona.presentation.layout.mark_aware_scale import PointMarkFootprint, point_facet_insets
from chrona.presentation.layout.model import LayoutDecision, LayoutError, LayoutManifest, Measurement, Rect
from chrona.presentation.layout.sources import MeasuredSources
from chrona.presentation.layout.surface_quality import ScalePlacement
from chrona.presentation.layout.temporal_capacity import TemporalInlineCapacity


def _manifest(allocated: str) -> LayoutManifest:
    return LayoutManifest("layout", "sha256:test", "block", "inline", Rect(
        Decimal(0), Decimal(0), Decimal(600), Decimal(340)),
        (LayoutDecision("timeline-slot", "slot", Rect(Decimal(100), Decimal(0),
                                                        Decimal(allocated), Decimal(200)),
                        source="timeline"),))


def _measured(natural: str = "120") -> MeasuredSources:
    return MeasuredSources({"timeline": Measurement(Decimal(0), Decimal(natural), None,
                                                       Decimal(0), Decimal(0), None)}, {}, {})


def _capacity(allocated: str, natural: str = "120") -> TemporalInlineCapacity:
    return TemporalInlineCapacity.from_manifest(_manifest(allocated), _measured(natural))


def test_manifest_closes_timeline_slot_and_existing_preferred_natural_demand():
    capacity = _capacity("0")
    assert (capacity.source_id, capacity.slot_id) == ("timeline", "timeline-slot")
    assert capacity.allocated_inline == Decimal(0)
    assert capacity.natural_inline == Decimal(120)


def test_repeated_timeline_uses_the_manifest_canonical_last_source_decision():
    manifest = _manifest("20")
    first = manifest.decisions[0]
    last = LayoutDecision("timeline-later", "slot", Rect(Decimal(275), Decimal(0),
                                                          Decimal(35), Decimal(200)),
                          source="timeline")
    repeated = LayoutManifest(manifest.profile_id, manifest.profile_hash, manifest.flow_direction,
                              manifest.dependency_network_flow_direction, manifest.viewport,
                              (first, last))

    capacity = TemporalInlineCapacity.from_manifest(repeated, _measured())
    assert repeated.source_decisions()["timeline"] == last
    assert (capacity.slot_id, capacity.allocated_inline) == ("timeline-later", Decimal(35))


def test_missing_timeline_retains_the_existing_missing_primitive_diagnostic():
    manifest = _manifest("20")
    missing = LayoutManifest(manifest.profile_id, manifest.profile_hash, manifest.flow_direction,
                             manifest.dependency_network_flow_direction, manifest.viewport, ())
    with pytest.raises(LayoutError, match="E_PRESENTATION_PRIMITIVE_MISSING"):
        TemporalInlineCapacity.from_manifest(missing, _measured())


def test_prototype_uses_natural_scale_only_for_zero_allocation():
    window = (date(2026, 1, 1), date(2026, 1, 11))
    zero = _capacity("0").prototype_scale(window, inline_origin=100)
    narrow = _capacity("30").prototype_scale(window, inline_origin=100)
    assert (zero.range_start, zero.range_end, zero.unit_ratio) == (100, 220, 12)
    assert (narrow.range_start, narrow.range_end, narrow.unit_ratio) == (100, 130, 3)


def test_prototype_preserves_domain_and_uses_explicit_slot_origin():
    scale = _capacity("0", "99").prototype_scale(
        (date(2026, 1, 1), date(2026, 1, 11)), inline_origin=Decimal("17.5"))
    assert (scale.domain_start, scale.domain_end) == (date(2026, 1, 1), date(2026, 1, 11))
    assert (scale.range_start, scale.range_end, scale.origin, scale.unit_ratio) == (17.5, 116.5, 17.5, 9.9)


def test_point_inset_extraction_reports_the_existing_exact_edge_protrusions():
    scale = ScalePlacement("surface", "primary", date(2026, 1, 1), date(2026, 1, 11),
                           0, 100, 0, 10)
    facets = (PointMarkFootprint(date(2026, 1, 1), -4, 3),
              PointMarkFootprint(date(2026, 1, 11), 97, 105))
    assert point_facet_insets(scale, facets) == (4, 5)
    assert _capacity("0").required_inline(*point_facet_insets(scale, facets)) == Decimal(129)


def test_usable_check_refuses_zero_host_with_natural_demand_and_point_insets():
    capacity = _capacity("0")
    with pytest.raises(LayoutError, match="E_LAYOUT_TEMPORAL_INLINE_CAPACITY") as error:
        capacity.require_usable(4, 5)
    assert error.value.path == "/layoutManifest/sources/timeline"
    assert error.value.node_id == "timeline-slot"
    assert error.value.detail == (
        "slot=timeline-slot; allocated_inline=0; required_inline=129; "
        "natural_inline=120; point_insets=4+5")


def test_usable_check_keeps_finite_positive_scale_even_below_natural_demand():
    _capacity("30").require_usable(4, 5)


def test_usable_check_refuses_when_resolved_insets_consume_the_positive_host():
    with pytest.raises(LayoutError, match="E_LAYOUT_TEMPORAL_INLINE_CAPACITY"):
        _capacity("9").require_usable(4, 5)


def test_usable_check_matches_existing_float_inset_mapping_at_rounding_boundary():
    capacity = _capacity("0.3", "120")
    # The native mapping computes range_end - right_inset; this exact float
    # pair collapses its range even though Decimal(str(inset)) addition is
    # slightly below 0.3.
    with pytest.raises(LayoutError, match="E_LAYOUT_TEMPORAL_INLINE_CAPACITY"):
        capacity.require_usable(0.1, 0.19999999999999998)


def test_capacity_slot_detail_survives_public_render_diagnostic_transport(monkeypatch):
    import importlib

    from chrona.usecases.failure_report import report_failure
    from chrona.usecases.render_review import RenderFailed

    usecase = importlib.import_module("chrona.usecases.render_review")
    capacity = _capacity("0")

    def fail(_request):
        capacity.require_usable(4, 5)

    monkeypatch.setattr(usecase, "_render_review", fail)
    with pytest.raises(RenderFailed) as error:
        usecase.render_review(object())
    report = report_failure(error.value)
    diagnostic = report.diagnostics[0]
    assert diagnostic["code"] == "E_LAYOUT_TEMPORAL_INLINE_CAPACITY"
    assert diagnostic["sourceRef"] == "/layoutManifest/sources/timeline"
    assert "slot=timeline-slot" in diagnostic["message"]
    assert "(timeline-slot)" in diagnostic["message"]


@pytest.mark.parametrize(("allocated", "natural"), [("-1", "120"), ("0", "0")])
def test_invalid_capacity_facts_are_rejected(allocated, natural):
    with pytest.raises(LayoutError, match="E_LAYOUT_TEMPORAL_CAPACITY_INVALID"):
        _capacity(allocated, natural)
