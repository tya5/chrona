"""A kind's `colorAlso` carries its colour to the note header text and the leader line (#991).

The kind colour reached only the bar, accent and stamp. Synthetic Projects through the packaged `executive-light`
bundle with the shared annotation-kind Theme helpers; no `examples/` input.
"""
from __future__ import annotations

from copy import deepcopy

import pytest

from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr


def _render(tmp_path, *, also: dict | None = None):
    kinds = deepcopy(ak.KINDS)
    for kind, value in (also or {}).items():
        kinds[kind]["colorAlso"] = value
    source = ak.project(("risk", "note"))
    parts = sr.bundle()
    ak.with_view_notes(parts, source, connector="leader")
    ak.with_kind_theme(parts, kinds=kinds, bar=False, border_side="start", label_fill="text")
    return ak.render(tmp_path, source, parts) if hasattr(ak, "render") else sr.render(tmp_path, source, presentation=parts)


def _by_prefix(rendered, prefix: str) -> dict[str, object]:
    return {item.scene_id: item for item in rendered.surface.primitives if item.scene_id.startswith(prefix)}


def _sub(tmp_path, name):
    path = tmp_path / name
    path.mkdir()
    return path


def test_without_color_also_the_header_and_leader_keep_their_own_paint(tmp_path):
    plain = _render(_sub(tmp_path, "a"))
    accents = _by_prefix(plain, "annotation-border:")
    labels = _by_prefix(plain, "annotation-kind-text:")
    assert accents and labels
    kind_colours = {item.paint.fill for item in accents.values()}
    assert all(item.paint.fill not in kind_colours for item in labels.values())


def test_color_also_paints_the_header_text_and_the_leader_in_the_kind_colour_for_that_kind_only(tmp_path):
    rendered = _render(_sub(tmp_path, "b"), also={"risk": ["header", "leader"]})
    accent = next(item for key, item in _by_prefix(rendered, "annotation-border:").items() if key.split(":")[1] == "view-n0")
    other_accent = next(item for key, item in _by_prefix(rendered, "annotation-border:").items() if key.split(":")[1] == "view-n1")
    risk_text = [item for key, item in _by_prefix(rendered, "annotation-kind-text:").items() if ":view-n0" in key or "n0" in key.split(":")[1]]
    note_text = [item for key, item in _by_prefix(rendered, "annotation-kind-text:").items() if "n1" in key.split(":")[1]]
    assert risk_text and note_text
    assert all(item.paint.fill == accent.paint.fill for item in risk_text)
    assert all(item.paint.fill != other_accent.paint.fill for item in note_text)  # the unlisted kind is unchanged
    leaders = {key: item for key, item in _by_prefix(rendered, "annotation-leader:").items()}
    risk_leader = next(item for key, item in leaders.items() if key.split(":")[1] == "view-n0")
    note_leader = next(item for key, item in leaders.items() if key.split(":")[1] == "view-n1")
    assert risk_leader.paint.stroke == accent.paint.fill
    assert note_leader.paint.stroke != other_accent.paint.fill


def test_header_alone_leaves_the_leader_alone(tmp_path):
    plain = _render(_sub(tmp_path, "p"))
    rendered = _render(_sub(tmp_path, "h"), also={"risk": ["header"]})
    plain_leader = next(item for key, item in _by_prefix(plain, "annotation-leader:").items() if key.split(":")[1] == "view-n0")
    leader = next(item for key, item in _by_prefix(rendered, "annotation-leader:").items() if key.split(":")[1] == "view-n0")
    assert leader.paint.stroke == plain_leader.paint.stroke


@pytest.mark.parametrize("bad", [[], ["body"], ["header", "header"], "header"])
def test_a_malformed_color_also_is_rejected(tmp_path, bad):
    with pytest.raises(Exception) as caught:
        _render(_sub(tmp_path, "x"), also={"risk": bad})
    assert "E_" in str(caught.value)


def test_a_header_colour_too_close_to_the_note_box_fails_the_kind_contrast_gate(tmp_path):
    # The kind colour is now the header's ink, so it is judged against the note box like any header text.
    kinds = deepcopy(ak.KINDS)
    kinds["risk"]["colorAlso"] = ["header"]
    source = ak.project(("risk", "note"))
    parts = sr.bundle()
    ak.with_view_notes(parts, source, connector="leader")
    ak.with_kind_theme(parts, kinds=kinds, bar=False, border_side="start", label_fill="text")
    parts["scheme"]["body"]["categories"]["kind-alert"] = "#F4F7FB"  # nearly the note box fill
    with pytest.raises(Exception) as caught:
        sr.render(_sub(tmp_path, "gate"), source, presentation=parts)
    assert "E_SCHEME_ANNOTATION_KIND_CONTRAST" in str(caught.value)
