"""Completed fill-encoding witnesses survive the public View/Style render paths."""
from datetime import date

import pytest

from chrona.presentation.scene.serialization import scene_document
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr


_PALE = "#F5F5F5"
_OUTLINE = "#172033"


def _render(tmp_path, *, source_kind, policy=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    parts = sr.bundle()
    theme = parts["theme"]["body"]
    theme.setdefault("colorScales", {})["owner-ink"] = {"slots": {"bus": "owner-ink"}}
    theme["contrastPolicy"] = {"mark": policy} if policy else {}
    # The packaged planned role already has a readable Theme-bound outline.
    parts["scheme"]["body"]["categories"]["owner-ink"] = _PALE
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    if source_kind == "view":
        parts["view"]["body"]["colorEncoding"] = {
            "target": "planned", "source": {"field": "owner"}, "scale": "owner-ink", "domain": ["bus"]}
    style = None
    if source_kind == "style":
        style = {"version": "chrona/style/v0.2", "kind": "style", "id": "owner-style",
                 "body": {"rules": [{"id": "owner-encode", "when": {"semantic": "planned"},
                     "then": {"encode": {"channel": "fill", "source": {"field": "owner"},
                         "scale": "owner-ink", "domain": ["bus"]}}}]}}
    source = sr.project({"task": sr.span("task", date(2026, 1, 5), 5, owner="bus")})
    return sr.render(tmp_path, source, presentation=parts, style=style)


@pytest.mark.parametrize("source_kind", ["view", "style"])
def test_only_applied_encoded_mark_fill_carries_provenance_and_outline_does_not_discharge_it(
        tmp_path, source_kind):
    rendered = _render(tmp_path / source_kind, source_kind=source_kind)
    mark = next(item for item in rendered.surface.primitives if item.scene_id.startswith("planned:"))
    witness = mark.encoding
    assert witness is not None
    assert (witness.channel, witness.scale_id, witness.field, witness.value) == (
        "fill", "owner-ink", "owner", "bus")
    source = witness.sources[0]
    assert source.kind == source_kind
    assert source.resource_id == ("owner-style" if source_kind == "style" else "chrona-preset-executive-light")
    if source_kind == "style":
        assert source.rule_id == "owner-encode"
        assert source.source_ref.endswith("/then/encode")
    else:
        assert source.source_ref == "/body/colorEncoding"
    assert mark.paint.fill == _PALE
    assert mark.paint.stroke == _OUTLINE
    warning = next(record for record in rendered.warning_records
                   if record.payload["code"] == "W_SCENE_ENCODING_CONTRAST")
    assert warning.payload["primitiveIds"] == [mark.scene_id]
    assert warning.payload["encoding"] == witness.as_mapping()

    document = scene_document(rendered.scene)
    serialized = next(item for surface in document["surfaces"] for item in surface["primitives"]
                      if item["id"] == mark.scene_id)
    assert serialized["encoding"] == witness.as_mapping()
    svg = rendered.artifact.content
    if isinstance(svg, str):
        svg = svg.encode()
    assert _PALE.encode() in svg
    assert _OUTLINE.encode() in svg
    if source_kind == "style":
        swatch = next(item for item in rendered.surface.primitives if item.legend_scope is not None)
        assert swatch.paint.fill == mark.paint.fill == _PALE
        assert swatch.encoding is None


@pytest.mark.parametrize("source_kind", ["view", "style"])
def test_encoded_mark_contrast_obeys_existing_mark_error_opt_in(tmp_path, source_kind):
    with pytest.raises(RenderFailed) as caught:
        _render(tmp_path / source_kind, source_kind=source_kind, policy="error")
    assert caught.value.code == "E_SCENE_ENCODING_CONTRAST"
    assert "contrastPolicy.mark: error" in caught.value.message
