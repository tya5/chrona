"""CLI readability is independent of canonical Scene identity and geometry."""
import json

import pytest

from chrona.app.scene_inspection import format_inspection_scene


@pytest.mark.parametrize("surface_count", [0, 1, 2])
@pytest.mark.parametrize("primitive_count", [0, 1, 3])
def test_readable_scene_preserves_all_data_and_keeps_each_primitive_on_one_line(surface_count, primitive_count):
    document = {
        "version": "chrona/scene/v0.7",
        "surfaces": [{"id": f"s{index}", "primitives": [
            {"id": f"s{index}-p{number}", "kind": "Text", "text": "設計\nReview ⚙",
             "bounds": {"inline": -0.0, "block": 12.345678901234567},
             "textLayout": {"lines": ["設計", "Review ⚙"], "baseline": [1.0, 2.5]},
             "paint": {"pattern": {"primitives": [{"kind": "Path", "points": [[1, 2], [3, 4]]}]}},
             "optional": None, "enabled": False}
            for number in range(primitive_count)]} for index in range(surface_count)],
        "diagnostics": [], "provenance": {"resources": []},
    }
    canonical = (json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n").encode()

    readable = format_inspection_scene(canonical)

    assert json.loads(readable) == document
    assert list(json.loads(readable)) == list(document)
    assert readable == format_inspection_scene(canonical)
    assert readable.endswith(b"\n") and not readable.endswith(b"\n\n")
    for surface in document["surfaces"]:
        for primitive in surface["primitives"]:
            expected = json.dumps(primitive, ensure_ascii=False, separators=(",", ":")).encode()
            assert sum(line.strip().removesuffix(b",") == expected for line in readable.split(b"\n")) == 1


def test_changing_one_primitive_changes_only_its_inspection_line():
    document = {"surfaces": [{"primitives": [
        {"id": "first", "bounds": {"inline": 1.0}},
        {"id": "second", "bounds": {"inline": 2.0}},
    ]}]}
    before = format_inspection_scene(json.dumps(document).encode()).splitlines()
    document["surfaces"][0]["primitives"][0]["bounds"]["inline"] = 3.0
    after = format_inspection_scene(json.dumps(document).encode()).splitlines()
    assert len(before) == len(after)
    assert sum(old != new for old, new in zip(before, after, strict=True)) == 1
