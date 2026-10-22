"""Forward point-target arrivals cannot use the backward-facing right port (#1627)."""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.ports import ConnectorEgress
from chrona.presentation.layout.surface_quality import MarkPlacement
import chrona.presentation.layout.surface_routes as surface_routes


@pytest.mark.parametrize(
    ("shape", "source_endpoint", "target_endpoint", "source_x", "expected_sides"),
    [
        ("point", "end", "at", 40.0, {"start", "above", "below"}),
        ("point", "finish", "start", 40.0, {"start", "above", "below"}),
        ("point", "end", "at", 50.0, {"start", "end", "above", "below"}),
        ("point", "end", "at", 60.0, {"start", "end", "above", "below"}),
        ("point", "start", "at", 40.0, {"start", "end", "above", "below"}),
        ("point", "end", "end", 40.0, {"start", "end", "above", "below"}),
        ("span", "end", "at", 40.0, {"start", "end", "above", "below"}),
    ],
)
@pytest.mark.parametrize("recovery_domain", (False, True))
def test_forward_point_arrival_filters_right_port_at_shared_candidate_seam(
        monkeypatch, shape, source_endpoint, target_endpoint, source_x, expected_sides, recovery_domain):
    mark = MarkPlacement("planned:target", "target", Rect(Decimal(40), Decimal(40), Decimal(20), Decimal(20)),
        (50.0, 50.0), (50.0, 50.0), mark_shape=shape)
    relation = SimpleNamespace(semantic_id="dependency", source_endpoint=source_endpoint)
    candidates = tuple(ConnectorEgress(side, (50.0, 50.0), (50.0, 50.0), ())
        for side in ("start", "end", "above", "below"))
    monkeypatch.setattr(surface_routes, "semantic_binding", lambda _: SimpleNamespace(theme_role="dependency"))
    monkeypatch.setattr(surface_routes, "marker_geometry", lambda *args, **kwargs: object())
    monkeypatch.setattr(surface_routes, "terminal_length", lambda _: 0.0)
    monkeypatch.setattr(surface_routes, "connector_egress_candidates",
        lambda *args, **kwargs: candidates)
    context = SimpleNamespace(
        marks=(mark,), timeline_bounds=(0.0, 0.0, 100.0, 100.0), metric_values={},
        request=SimpleNamespace(theme_tokens=SimpleNamespace(number=lambda *_: 2.0, marker=lambda *_: None)),
        obstacles=object(),
    )
    domain = SimpleNamespace(obstacles=object()) if recovery_domain else None

    resolved = surface_routes._entry_candidates(context, mark, target_endpoint,
        (source_x, 50.0), (), relation, entry="side-when-free", domain=domain)

    assert {item.side for item in resolved} == expected_sides
