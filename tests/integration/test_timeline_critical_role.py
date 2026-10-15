"""Existing scheduler critical facts select optional paint before Layout (#1561)."""
from datetime import date

from tests.support import synthetic_review as sr


def _source():
    source = sr.project({"start": sr.span("start", date(2026, 10, 1), 1),
                         **{name: {"type": "task", "title": name.title(), "fields": {"owner": "a"},
                                   "schedule": {"mode": "scheduled", "amount": amount}}
                            for name, amount in (("long", "4d"), ("short", "2d"), ("finish", "1d"))}})
    source["relations"] = [
        {"id": name, "type": "dependency", "from": {"object": start, "endpoint": "end"},
         "to": {"object": end, "endpoint": "start"}}
        for name, start, end in (("start-long", "start", "long"), ("start-short", "start", "short"),
                                 ("long-finish", "long", "finish"), ("short-finish", "short", "finish"))]
    return source


def _parts(*, critical):
    parts = sr.bundle("executive-light")
    parts["view"]["body"]["visibility"]["relations"] = {"mode": "semantic", "overflow": "visible-overflow"}
    body = parts["theme"]["body"]
    body["roles"].pop("dependency-critical", None)
    body["colorBindings"].pop("dependency-critical.stroke", None)
    if critical:
        body["values"]["critical-width"] = {"type": "number", "value": 2}
        body["roles"]["dependency-critical"] = {"strokeWidth": "critical-width"}
        body["colorBindings"]["dependency-critical.stroke"] = "negative"
    return parts


def test_theme_role_is_wired_through_real_render_without_reclassifying_the_short_branch(tmp_path):
    (tmp_path / "plain").mkdir()
    (tmp_path / "critical").mkdir()
    before = sr.render(tmp_path / "plain", _source(), presentation=_parts(critical=False))
    after = sr.render(tmp_path / "critical", _source(), presentation=_parts(critical=True))
    def relations(result):
        return {item.scene_id: item for item in result.surface.primitives
                if item.kind == "Path" and item.visual_role in {"dependency", "dependency-critical"}}
    plain, themed = relations(before), relations(after)
    assert set(plain) == set(themed) and len(themed) == 4
    assert all(item.visual_role == "dependency" for item in plain.values())
    assert {item.source_ref for item in themed.values() if item.visual_role == "dependency-critical"} == {
        "relation:0:start-long", "relation:2:long-finish"}
    assert {item.paint.stroke_width for item in themed.values() if item.visual_role == "dependency-critical"} == {2}
