"""Encoded-fill warnings preserve occurrences without repeating a realised pair."""
from dataclasses import replace

import pytest

from chrona.presentation.scene.contrast_policy import (
    DEFAULT_POLICY, EncodedFillPair, SceneContrastFinding, evaluate_scene_contrast,
)
from chrona.presentation.style import EncodingSource, EncodingWitness
from chrona.usecases.diagnostic_messages import collapse_warnings
from chrona.usecases.render_review import _contrast_warnings_from_findings
from chrona.usecases.warning_ledger import collect_render_warnings


def _finding(identity="a", **changes):
    witness = EncodingWitness("fill", "owners", "owner", "bus",
                              (EncodingSource("view", "view-a", "/body/colorEncoding"),))
    finding = SceneContrastFinding(
        "W_SCENE_ENCODING_CONTRAST", "warning", "/surfaces/0:plot", "planned", "planned", identity,
        1.2, 3.0, "required", "row-a", "#16213A", "fill", 5, 5, "flat",
        encoding=witness, encoding_pair=EncodedFillPair("#2C2138", 1.0, "#2C2138", "#16213A", 1.2, 3.0),
    )
    return replace(finding, **changes)


def _records(findings):
    return collect_render_warnings(
        surface_diagnostics=(), tabular_warnings=(), glyph_warnings=(), fit_warnings=(),
        perceptibility_warnings=(), scale_collisions=(), attachment_warnings=(),
        contrast_warnings=_contrast_warnings_from_findings(tuple(findings)),
    )


def test_pair_identity_does_not_depend_on_occurrence_count_or_row_identity():
    first = _finding()
    one, = _records([first])
    two, = _records([first, _finding("b", ground_id="row-b")])

    assert one.identity == two.identity
    assert two.payload["primitiveIds"] == ["a", "b"]
    assert two.payload["groundIds"] == ["row-a", "row-b"]
    assert two.payload["occurrenceCount"] == 2
    assert two.payload["encodingPair"]["fillColor"] == "#2C2138"
    assert "2 occurrences" in two.payload["message"]


def test_cli_keeps_distinct_pairs_and_all_occurrence_ids_beyond_its_generic_limit():
    findings = [_finding(f"mark-{i}") for i in range(30)]
    other = _finding("other", encoding=replace(findings[0].encoding, value="another owner"))
    records = _records([*findings, other])
    rows = collapse_warnings(record.payload for record in records)

    assert len(rows) == 2
    assert rows[0]["occurrenceCount"] == 30
    assert rows[0]["primitiveIds"] == [f"mark-{i}" for i in range(30)]
    assert rows[1]["primitiveIds"] == ["other"]
    assert all("occurrences" not in row for row in rows)


@pytest.mark.parametrize("dimension", ["source", "scale", "field", "value", "opacity", "sampledFill", "surface"])
def test_each_encoding_and_completed_sample_dimension_keeps_distinct_warnings(dimension):
    first = _finding()
    if dimension in {"scale", "field", "value"}:
        name = {"scale": "scale_id", "field": "field", "value": "value"}[dimension]
        second = _finding("b", encoding=replace(first.encoding, **{name: "different"}))
    elif dimension == "source":
        second = _finding("b", encoding=replace(first.encoding, sources=(
            EncodingSource("view", "other-view", "/body/colorEncoding"),)))
    elif dimension == "surface":
        second = _finding("b", scene_path="/surfaces/1:other")
    else:
        change = {"fill_opacity": 0.5} if dimension == "opacity" else {"sampled_fill": "#332244"}
        second = _finding("b", encoding_pair=replace(first.encoding_pair, **change))
    assert len(_records([first, second])) == 2


def test_observer_preserves_each_witness_and_captures_completed_pair_without_repainting():
    witness = _finding().encoding.as_mapping()
    primitives = [{"id": identity, "kind": "Rect", "purpose": "planned", "visualRole": "planned",
                   "bounds": {"inline": 0, "block": block, "inlineSize": 20, "blockSize": 10},
                   "paint": {"fill": "#2C2138", "stroke": "#FFFFFF", "strokeWidth": 1},
                   "encoding": witness}
                  for identity, block in (("a", 0), ("b", 20))]
    document = {"version": "chrona/scene/v0.7", "kind": "scene",
                "provenance": {"resources": [{"kind": "view", "id": "view-a"}]},
                "surfaces": [{"id": "plot", "canvasPaint": {"fill": "#16213A"},
                              "primitives": primitives}]}
    findings = evaluate_scene_contrast(document, policy=DEFAULT_POLICY)
    encoded = [item for item in findings if item.encoding is not None]
    warning, = _records(findings)

    assert len(encoded) == 2 and all(item.encoding.as_mapping() == witness for item in encoded)
    assert encoded[0].encoding_pair == encoded[1].encoding_pair
    assert warning.payload["occurrenceCount"] == 2
    assert [item["encoding"] for item in primitives] == [witness, witness]
    assert [item["paint"]["fill"] for item in primitives] == ["#2C2138", "#2C2138"]
