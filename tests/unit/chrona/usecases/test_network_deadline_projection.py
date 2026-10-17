from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.profile import resolve_layout_profile
from chrona.presentation.model.projection import (
    DependencyNetworkNode,
    DependencyNetworkProjection,
    NetworkDeadlineContent,
    ReviewDeadline,
)
from chrona.presentation.layout.surface_source_inputs import network_deadline_source_input
from chrona.usecases.render_review import _network_deadline_projection


def test_network_deadline_projection_attaches_view_selected_iso_and_caption_to_primary_nodes_only():
    network = DependencyNetworkProjection((
        DependencyNetworkNode("primary", "Primary", ("primary",), False, "primary"),
        DependencyNetworkNode("scenario", "Scenario", ("scenario",), False, "scenario"),
        DependencyNetworkNode("no-deadline", "No deadline", ("no-deadline",), False, "primary"),
    ), ())
    deadlines = (
        ReviewDeadline("primary", date(2026, 10, 1), date(2026, 10, 4), True, 3, "3 days late"),
        ReviewDeadline("scenario", date(2026, 10, 2), date(2026, 10, 5), True, 3, "3 days late"),
    )

    result = _network_deadline_projection(network, deadlines)

    primary, scenario, absent = result.nodes
    assert primary.deadline is not None
    assert (primary.deadline.object_id, primary.deadline.label, primary.deadline.slipped) == (
        "primary", "2026-10-01 3 days late", True)
    assert scenario.deadline is None
    assert absent.deadline is None
    assert all(node.deadline is None for node in network.nodes)


def test_network_deadline_projection_keeps_network_identity_when_no_deadlines_are_selected():
    network = DependencyNetworkProjection((
        DependencyNetworkNode("primary", "Primary", ("primary",), False, "primary"),
    ), ())

    assert _network_deadline_projection(network, ()) is network
    assert _network_deadline_projection(None, ()) is None


def test_network_deadline_measurement_is_a_private_run_group_with_theme_text_role_fallback():
    network = DependencyNetworkProjection((
        DependencyNetworkNode("primary", "Primary", ("primary",), False, "primary",
                              deadline=NetworkDeadlineContent("primary", "2026-10-01 3 days late", True)),
    ), ())
    projection = SimpleNamespace(network=network)
    def theme(roles):
        return {"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
                "body": {"values": {}, "roles": roles}}

    with_caption_role = network_deadline_source_input(
        projection, theme({"deadline-caption": {}}))
    without_caption_role = network_deadline_source_input(projection, theme({}))

    assert with_caption_role.typography_role == "deadline-caption"
    assert without_caption_role.typography_role == "text"
    assert with_caption_role.text_runs()[0].source_ref == "primary"
    assert with_caption_role.text_runs()[0].content == "2026-10-01 3 days late"


def test_network_deadline_measurement_group_is_not_an_authorable_layout_source():
    root = Path(__file__).parents[4]
    profile = yaml.safe_load((root / "conformance/layout-profile-intent-v0.2.yaml").read_text())

    def replace_timeline_source(node):
        if node.get("kind") == "slot" and node.get("source") == "timeline":
            node["source"] = "network-deadlines"
        for child in node.get("children", ()):
            replace_timeline_source(child)

    replace_timeline_source(profile["root"])
    theme_values = {name: {"type": "number", "value": value} for name, value in {
        "spacing.none": 0, "spacing.s": 8, "spacing.m": 16, "spacing.l": 24,
        "panel.minimum": 180,
    }.items()}
    # Authored Layout profiles validate against the closed public-source schema
    # before admission; this private measurement group is not in that vocabulary.
    with pytest.raises(LayoutError, match="E_LAYOUT_SCHEMA"):
        resolve_layout_profile(
            profile,
            available_sources={"title", "table", "timeline", "timeline-axis", "legend", "notes"},
            theme={"body": {"values": theme_values}},
        )
