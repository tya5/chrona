"""Scene acceptance for exact member-name/mark association (#554)."""

import json
from pathlib import Path


def _gap(left, right):
    inline = max(0.0, left["inline"] - right["inline"] - right["inlineSize"],
                 right["inline"] - left["inline"] - left["inlineSize"])
    block = max(0.0, left["block"] - right["block"] - right["blockSize"],
                right["block"] - left["block"] - left["blockSize"])
    return (inline * inline + block * block) ** 0.5


def _check_members(scene):
    checked = 0
    for surface in scene["surfaces"]:
        primitives = {item["id"]: item for item in surface["primitives"]}
        for label in surface["primitives"]:
            if label["purpose"] != "member-label":
                continue
            host_id = label.get("hostPlacementId")
            if host_id is None and label["id"].startswith("member-label:group-header:"):
                # Folded group-header points retain a canonical, same-source
                # mark identity across the table/timeline slot boundary.
                host_id = label["id"].replace("member-label:", "planned:", 1)
            host = primitives.get(host_id)
            assert host is not None, label["id"]
            assert host["sourceRef"] == label["sourceRef"], label["id"]
            assert host["purpose"] in {"planned", "actual", "snapshot"}, label["id"]
            if label.get("laneRowId") is not None:
                assert (host.get("laneRowId"), host.get("laneMemberId")) == (
                    label["laneRowId"], label["laneMemberId"]), label["id"]
            assert _gap(label["textLayout"]["bounds"], host["bounds"]) <= (
                2 * label["textLayout"]["fontSize"] + 0.01), label["id"]
            checked += 1
    return checked


def test_synthetic_scene_checks_both_sides_and_folded_point_identity():
    def bounds(x):
        return {"inline": x, "block": 40, "inlineSize": 10, "blockSize": 10}

    mark = {"id": "planned:a", "purpose": "planned", "sourceRef": "a", "bounds": bounds(50)}
    labels = [
        {"id": f"member-label:{side}", "purpose": "member-label", "sourceRef": "a",
         "hostPlacementId": "planned:a", "textLayout": {"bounds": bounds(x), "fontSize": 10}}
        for side, x in (("start", 30), ("end", 70))
    ]
    folded_mark = {"id": "planned:group-header:g:p", "purpose": "planned",
                   "sourceRef": "p", "bounds": bounds(50)}
    folded_label = {"id": "member-label:group-header:g:p", "purpose": "member-label",
                    "sourceRef": "p", "textLayout": {"bounds": bounds(70), "fontSize": 10}}
    assert _check_members({"surfaces": [{"primitives": [mark, *labels, folded_mark, folded_label]}]}) == 3


def test_every_public_scene_member_label_has_a_bounded_exact_mark():
    root = Path(__file__).resolve().parents[3]
    scenes = tuple(sorted((root / "examples").glob("*/generated/*.scene.json")))
    assert scenes
    checked = sum(_check_members(json.loads(path.read_text(encoding="utf-8"))) for path in scenes)
    assert checked > 0
