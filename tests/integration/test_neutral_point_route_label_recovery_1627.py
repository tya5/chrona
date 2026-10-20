"""Neutral-ID, mixed-language fixture derived from public trial geometry (#1627).

Synthetic identities prevent project-name branching; the iOS label is generic,
while other labels preserve measured mixed-language geometry. The fixture keeps
the full relation inventory and checks permitted point-terminal approaches;
optional names may be omitted only with measured route-contact evidence.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

import chrona.presentation.layout.surface_composer as surface_composer
from chrona.presentation.layout.obstacles import ObstacleSegment, obstacles_intersect
from chrona.presentation.scene.serialization import serialize_scene
from chrona.core.relation_identity import relation_identities
from chrona.usecases.draft_render import DraftRenderRequest, render_draft


_OBJECTS = (
    ("item-00", "gate", "Kickoff", None, {"mode": "fixed-point", "at": "2026-11-02"}, None, "pm"),
    ("group-00", "group", "Design", None, {"mode": "rollup"}, None, None),
    ("item-01", "task", "UXリサーチ", "group-00", {"mode": "scheduled", "amount": "4wd", "anchor": {"start": "2026-11-02"}}, None, "佐藤"),
    ("item-02", "task", "Wireframes", "group-00", {"mode": "scheduled", "amount": "5wd"}, None, "Mika"),
    ("item-03", "task", "ビジュアルデザイン", "group-00", {"mode": "scheduled", "amount": "6wd"}, None, "Mika"),
    ("item-04", "task", "Design system tokens", "group-00", {"mode": "scheduled", "amount": "4wd"}, None, "Ken"),
    ("item-05", "task", "コピーライティング (日本語/English)", "group-00", {"mode": "scheduled", "amount": "3wd"}, None, "田中"),
    ("item-06", "gate", "Design freeze", "group-00", {"mode": "fixed-point", "at": "2026-11-27"}, "2026-12-04", "pm"),
    ("group-01", "group", "Build", None, {"mode": "rollup"}, None, None),
    ("item-07", "task", "Auth API (OAuth2 + SSO)", "group-01", {"mode": "scheduled", "amount": "6wd"}, None, "Raj"),
    ("item-08", "task", "決済API", "group-01", {"mode": "scheduled", "amount": "8wd"}, None, "Raj"),
    ("item-09", "task", "Mobile app shell", "group-01", {"mode": "scheduled", "amount": "10wd"}, None, "Lena"),
    ("item-10", "task", "Mobile clients", "group-01", {"mode": "scheduled", "amount": "10wd"}, None, "鈴木"),
    ("item-11", "task", "Push notifications", "group-01", {"mode": "scheduled", "amount": "4wd"}, None, "Lena"),
    ("item-12", "task", "オフライン同期", "group-01", {"mode": "scheduled", "amount": "7wd"}, None, "鈴木"),
    ("item-13", "task", "Analytics SDK integration", "group-01", {"mode": "scheduled", "amount": "3wd"}, None, "Ken"),
    ("item-14", "task", "Localization (ja/en)", "group-01", {"mode": "scheduled", "amount": "4wd"}, None, "田中"),
    ("group-02", "group", "Release", None, {"mode": "rollup"}, None, None),
    ("item-15", "task", "QA regression", "group-02", {"mode": "scheduled", "amount": "8wd"}, None, "QA team"),
    ("item-16", "task", "TestFlight / 社内ベータ", "group-02", {"mode": "scheduled", "amount": "5wd"}, None, "Lena"),
    ("item-17", "task", "Performance tuning", "group-02", {"mode": "scheduled", "amount": "4wd"}, None, "Raj"),
    ("item-18", "task", "ストア掲載素材", "group-02", {"mode": "scheduled", "amount": "3wd"}, None, "Mika"),
    ("item-19", "task", "App Store / Google Play review", "group-02", {"mode": "scheduled", "amount": "5wd"}, None, "pm"),
    ("item-20", "task", "Marketing launch campaign", "group-02", {"mode": "scheduled", "amount": "5wd"}, None, "田中"),
    ("item-21", "gate", "Public launch", "group-02", {"mode": "scheduled-point"}, "2027-02-26", "pm"),
)

_EDGES = (
    ("item-00", "at", "item-01", "start", "0d"),
    ("item-01", "end", "item-02", "start", "0d"),
    ("item-02", "end", "item-03", "start", "0d"),
    ("item-02", "end", "item-04", "start", "0d"),
    ("item-02", "end", "item-05", "start", "0d"),
    ("item-03", "end", "item-06", "at", "0d"),
    ("item-04", "end", "item-06", "at", "0d"),
    ("item-05", "end", "item-06", "at", "0d"),
    ("item-00", "at", "item-07", "start", "3wd"),
    ("item-07", "end", "item-08", "start", "0d"),
    ("item-04", "end", "item-09", "start", "0d"),
    ("item-04", "end", "item-10", "start", "0d"),
    ("item-09", "end", "item-11", "start", "0d"),
    ("item-10", "end", "item-11", "start", "0d"),
    ("item-08", "end", "item-12", "start", "0d"),
    ("item-09", "end", "item-13", "start", "0d"),
    ("item-05", "end", "item-14", "start", "0d"),
    ("item-09", "end", "item-14", "start", "0d"),
    ("item-11", "end", "item-15", "start", "0d"),
    ("item-12", "end", "item-15", "start", "0d"),
    ("item-13", "end", "item-15", "start", "0d"),
    ("item-15", "start", "item-16", "start", "3wd"),
    ("item-15", "start", "item-17", "start", "2wd"),
    ("item-03", "end", "item-18", "start", "0d"),
    ("item-14", "end", "item-18", "start", "0d"),
    ("item-15", "end", "item-19", "start", "0d"),
    ("item-18", "end", "item-19", "start", "0d"),
    ("item-16", "end", "item-19", "start", "0d"),
    ("item-19", "start", "item-20", "start", "0d"),
    ("item-19", "end", "item-21", "at", "0d"),
    ("item-17", "end", "item-21", "at", "0d"),
)


def _project() -> dict:
    objects = {}
    for identity, kind, title, parent, schedule, deadline, owner in _OBJECTS:
        item = {"type": kind, "title": title, "schedule": schedule}
        if parent is not None:
            item["parent"] = parent
        if deadline is not None:
            item["deadline"] = deadline
        if owner is not None:
            item["fields"] = {"owner": owner}
        objects[identity] = item
    relations = []
    for index, (source, source_end, target, target_end, lag) in enumerate(_EDGES):
        relations.append({"id": f"edge-{index:02d}", "type": "dependency",
                          "from": {"object": source, "endpoint": source_end},
                          "to": {"object": target, "endpoint": target_end}, "lag": lag})
    return {
        "version": "timeline/v0.7",
        "project": {"id": "neutral-point-route", "title": "Neutral point-route schedule", "calendar": "standard"},
        "calendars": {"standard": {"working_days": ["mon", "tue", "wed", "thu", "fri"],
                                     "exceptions": [{"date": "2026-12-25", "working": False},
                                                    {"date": "2026-12-28", "working": False},
                                                    {"date": "2026-12-29", "working": False},
                                                    {"date": "2026-12-30", "working": False},
                                                    {"date": "2026-12-31", "working": False},
                                                    {"date": "2027-01-01", "working": False}]}},
        "objects": objects, "relations": relations, "fieldRoles": {"responsible": "owner"},
    }


def test_neutral_identity_render_keeps_routes_and_left_point_ports_with_measured_blocked_names(
        tmp_path: Path, monkeypatch):
    captured = []
    compose = surface_composer.compose_routes_and_member_labels

    def capture_options(context):
        options = compose(context)
        captured.append((context, options))
        return options

    monkeypatch.setattr(surface_composer, "compose_routes_and_member_labels", capture_options)
    project_path = tmp_path / "neutral-point-route.yaml"
    project_path.write_text(yaml.safe_dump(_project(), sort_keys=False, allow_unicode=True), encoding="utf-8")
    result = render_draft(DraftRenderRequest(project=project_path, target_kind="png", preset="editorial",
                                             viewport="1600xauto"))
    assert result.rendered.artifact.content.startswith(b"\x89PNG\r\n\x1a\n")
    scene = json.loads(serialize_scene(result.rendered.scene))
    primitives = scene["surfaces"][0]["primitives"]
    labels = [item for item in primitives if item.get("purpose") == "member-label"]
    expected_members = {identity for identity, kind, *_ in _OBJECTS if kind != "group"}
    suppressed = {item.removeprefix("W_LAYOUT_LABEL_SUPPRESSED:member-label:")
                  for item in result.rendered.scene.diagnostics
                  if item.startswith("W_LAYOUT_LABEL_SUPPRESSED:member-label:")}
    expected_suppressions = {
        'review-lane:["generated","","item-05"]:item-05',
        'review-lane:["generated","","item-17"]:item-17',
    }
    assert suppressed == expected_suppressions
    assert {item["sourceRef"] for item in labels} == expected_members - {"item-05", "item-17"}
    assert len(labels) == 20
    assert result.rendered.scene.diagnostics.count(
        "I_LAYOUT_PLOT_LABELS_SUPPRESSED:surface=table-timeline;count=2") == 1

    # The actual candidate boxes are measured by Layout. The retry's completed
    # routes intersect those boxes, documenting why these optional names remain
    # suppressed without reimplementing rung selection or route search here.
    assert len(captured) == 1
    context, options = captured[0]
    assert options.retry is not None
    proposals = {item.text.content: item for item in options.first.members.route_blocked_candidates}
    assert set(proposals) == {"Design / コピーライティング (日本語/English)",
                              "Release / Performance tuning"}
    edge_ids = dict(zip(relation_identities(_project()["relations"]),
                        (item["id"] for item in _project()["relations"])))
    retries = {item.source_ref: item for item in options.retry.routes.relations
               if not item.suppressed and len(item.points) >= 2}
    expected_blocked_edges = {
        "Design / コピーライティング (日本語/English)": ("item-05", ("edge-07", "edge-16")),
        "Release / Performance tuning": ("item-17", ("edge-30",)),
    }
    marks = {item.placement_id: item for item in context.member_labels.marks}
    for content, (source_ref, relation_ids) in expected_blocked_edges.items():
        proposal = proposals[content]
        mark_id = proposal.text.host_placement_id
        assert mark_id in marks and marks[mark_id].source_ref == source_ref
        footprint = next(item for item in proposal.obstacles if item.obstacle_class == "text")
        intersecting = set()
        for route in retries.values():
            edge_id = edge_ids.get(route.source_ref)
            if edge_id not in relation_ids:
                continue
            segments = (ObstacleSegment(start, end) for start, end in zip(route.points, route.points[1:]))
            if any(obstacles_intersect(segment, footprint.geometry, footprint.clearance) for segment in segments):
                intersecting.add(edge_id)
        assert intersecting == set(relation_ids)

    routes = [item for item in primitives
              if item.get("kind") == "Path" and item.get("purpose") == "dependency"
              and item.get("toInstanceId") is not None]
    assert len({item["sourceRef"] for item in routes}) == len(_EDGES) == 31
    point_targets = {target for _, _, target, endpoint, _ in _EDGES if endpoint == "at"}
    marks = {item["id"]: item for item in primitives
             if item.get("purpose") == "planned" and item.get("sourceRef") in point_targets}
    # Use the typed endpoint identity and the established primary-mark namespace;
    # do not recover relation indices by parsing opaque source/instance IDs.
    arrivals = [item for item in routes if f"planned:{item.get('toInstanceId')}" in marks]
    assert len(arrivals) == sum(endpoint == "at" for _, _, _, endpoint, _ in _EDGES) == 5
    bad_ports = []
    for route in arrivals:
        mark = marks[f"planned:{route['toInstanceId']}"]["bounds"]
        endpoint = route["points"][-1]
        before = route["points"][-2]
        left, top = mark["inline"], mark["block"]
        right, bottom = left + mark["inlineSize"], top + mark["blockSize"]
        left_entry = endpoint[0] == left and top <= endpoint[1] <= bottom and before[0] <= left
        top_entry = endpoint[1] == top and left <= endpoint[0] <= right and before[1] <= top
        bottom_entry = endpoint[1] == bottom and left <= endpoint[0] <= right and before[1] >= bottom
        if not (left_entry or top_entry or bottom_entry):
            bad_ports.append((route["sourceRef"], marks[f"planned:{route['toInstanceId']}"]["sourceRef"],
                              endpoint, before, (left, top, right, bottom)))
    assert not bad_ports, "\n".join(map(str, bad_ports))
