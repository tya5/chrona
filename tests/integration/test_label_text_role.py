"""#1141: `visibility.labels.textRole` separates the plot member (bar) labels from table cells.

Synthetic Projects through the packaged `executive-light` bundle; no `examples/` input. The default (no `textRole`)
keeps the shared `text` role byte for byte; a named role carries typography, `viewerFit` and a bound fill to the
member labels only, and an undeclared role fails at the View pointer.
"""
from __future__ import annotations

import re
from datetime import date

import pytest

from tests.support import synthetic_review as sr

FIT = "text-follows-box"


def _parts(*, label_role=None, roles=None, declare=True, fill=None):
    parts = sr.bundle("executive-light")
    body = parts["theme"]["body"]
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    parts["view"]["body"]["tableColumns"] = [{"id": "Work package", "source": "title", "missing": "em-dash",
                                              "align": "start", "width": "content", "headerOrientation": "horizontal"}]
    labels = parts["view"]["body"]["visibility"]["labels"]
    if label_role is not None:
        assert isinstance(labels, dict), labels
        labels["textRole"] = label_role
        if declare:
            body["roles"][label_role] = {key: value for key, value in body["roles"]["text"].items()
                                         if key not in {"iconScale", "iconGap"}}
    for role, declaration in (roles or {}).items():
        body["roles"].setdefault(role, {}).update(declaration)
    if fill is not None:
        body["colorBindings"][f"{label_role}.fill"] = fill
    return parts


def _render(tmp_path, name="r", **kwargs):
    directory = tmp_path / name
    directory.mkdir()
    source = sr.project({"a": sr.span("a", date(2026, 2, 2), 30, title="Alpha"),
                         "b": sr.span("b", date(2026, 3, 9), 20, title="Beta Release Candidate")})
    return sr.render(directory, source, presentation=_parts(**kwargs))


def _texts(rendered, purpose):
    found = [item for item in rendered.surface.primitives if item.kind == "Text" and item.purpose == purpose]
    assert found
    return found


def test_a_named_role_that_restates_the_shared_one_renders_exactly_as_before(tmp_path):
    base = _render(tmp_path, "a")
    same = _render(tmp_path, "b", label_role="bar-label", roles={"bar-label": {"viewerFit": "raw"}})
    assert same.artifact.content == base.artifact.content
    assert b"textLength" not in base.artifact.content


def test_a_named_role_pins_the_bar_labels_and_not_the_table_cells(tmp_path):
    rendered = _render(tmp_path, label_role="bar-label", roles={"bar-label": {"viewerFit": FIT}})
    svg = rendered.artifact.content.decode("utf-8")
    for item in _texts(rendered, "member-label"):
        assert item.text_layout.fit is not None and item.text_layout.fit.mode == FIT
        assert re.search(rf'<text data-scene-id="{re.escape(item.scene_id)}"[^>]*textLength=', svg)
    assert all(item.text_layout.fit is None for item in _texts(rendered, "table-cell"))


def test_the_shared_text_role_still_pins_cells_and_bar_labels_without_the_property(tmp_path):
    rendered = _render(tmp_path, roles={"text": {"viewerFit": FIT}})
    assert all(item.text_layout.fit is not None for item in _texts(rendered, "member-label"))
    assert all(item.text_layout.fit is not None for item in _texts(rendered, "table-cell"))


def test_pinning_the_named_role_leaves_the_table_cells_untouched(tmp_path):
    shared = _render(tmp_path, "a")
    named = _render(tmp_path, "b", label_role="bar-label", roles={"bar-label": {"viewerFit": FIT}})

    def cells(rendered):
        return [(i.scene_id, i.bounds, i.paint) for i in _texts(rendered, "table-cell")]
    assert cells(named) == cells(shared)


def test_a_named_role_sets_the_bar_label_size_only(tmp_path):
    shared = _render(tmp_path, "a")
    bigger = _render(tmp_path, "b", label_role="bar-label", roles={"bar-label": {"fontSize": "axis-size"}})

    def sizes(rendered, purpose):
        return {i.text_layout.font_size for i in _texts(rendered, purpose)}
    assert sizes(bigger, "table-cell") == sizes(shared, "table-cell")
    assert sizes(bigger, "member-label") == {12.0}


def test_a_bound_fill_colours_the_bar_labels_and_not_the_cells(tmp_path):
    rendered = _render(tmp_path, label_role="bar-label", fill="surfaceRaised")
    assert {i.visual_role for i in _texts(rendered, "member-label")} == {"bar-label"}
    assert {i.visual_role for i in _texts(rendered, "table-cell")} == {"text"}


def test_an_undeclared_role_fails_at_the_view_pointer(tmp_path):
    with pytest.raises(Exception) as raised:
        _render(tmp_path, label_role="no-such-role", declare=False)
    error = raised.value
    assert (getattr(error, "code", None) or getattr(error, "diagnostic_id", "")) == "E_THEME_ROLE_REQUIRED"
    assert error.source_ref == "/body/visibility/labels/textRole"


def test_lane_rows_measure_and_set_the_labels_in_the_same_named_role(tmp_path):
    parts = _parts(label_role="bar-label", roles={"bar-label": {"fontSize": "axis-size", "viewerFit": FIT}})
    parts["view"] = sr.lane_view(parts["view"])
    roles = parts["theme"]["body"]["roles"]
    roles.setdefault("numeric", dict(roles["text"]))
    parts["view"]["body"]["visibility"]["labels"] = {"placement": "plot", "textRole": "bar-label",
                                                     "content": ["title"], "side": "end"}
    directory = tmp_path / "lanes"
    directory.mkdir()
    source = sr.project({"a": sr.span("a", date(2026, 2, 2), 30, title="Alpha"),
                         "b": sr.span("b", date(2026, 3, 9), 20, title="Beta")})
    rendered = sr.render(directory, source, presentation=parts)
    labels = _texts(rendered, "member-label")
    assert {i.text_layout.font_size for i in labels} == {12.0}
    assert all(i.text_layout.fit is not None for i in labels)
