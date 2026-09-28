"""Completed catalogue pattern facts never require Scene asset lookup."""
from decimal import Decimal

import jsonschema

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.pattern_placement import complete_pattern_placement
from chrona.presentation.scene.pattern_geometry import project_pattern_placement
from chrona.presentation.scene.serialization import _pattern
from chrona.resources import schema_document


def test_layout_pattern_projects_to_scene_v07_with_fixed_phase_and_clip() -> None:
    asset = {"tile": {"inlineSize": 8, "blockSize": 8}, "angle": 45,
             "densityBasisPoints": 1250,
             "primitives": [{"kind": "circle", "cx": 2, "cy": 2, "radius": 1}]}
    region = Rect(Decimal(14), Decimal(25), Decimal(30), Decimal(12))
    completed = complete_pattern_placement(asset, region, 3)
    result = _pattern(project_pattern_placement(completed))
    assert result["origin"] == [14.0, 25.0]
    assert result["regionBounds"] == result["clipBounds"] == {
        "inline": 14.0, "block": 25.0, "inlineSize": 30.0, "blockSize": 12.0}
    assert result["cornerRadius"] == 3
    assert result["densityBasisPoints"] == 1250
    schema = schema_document("scene-v0.7.schema.yaml")
    jsonschema.Draft202012Validator({"$ref": "#/$defs/catalogPattern",
                                      "$defs": schema["$defs"]}).validate(result)
