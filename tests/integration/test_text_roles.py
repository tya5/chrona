"""A View `tableColumns[].textRole` and a Theme `legend.fill` set text apart per column and per legend (#1062).

Every table cell shared the `text` role and every legend label the `text` ink, so a muted, smaller Phase column or a
muted legend could not be declared. Synthetic Project through the packaged `executive-light` bundle; no test reads
`examples/`.
"""
from __future__ import annotations

from datetime import date

import pytest

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr

DETAIL = {"version": "chrona/review-detail-profile/v0.1", "id": "legend-detail", "body": {"legend": [
    {"role": "planned", "label": "Planned"}, {"role": "actual", "label": "Actual"}]}}


def _column(column_id, source, **extra):
    return {"id": column_id, "source": source, "missing": "em-dash", "align": "start", "width": "content",
            "headerOrientation": "horizontal", **extra}


def _render(tmp_path, *, text_role=None, declare=True, fill="textMuted", legend_fill=None, columns=None, actual=None):
    source = sr.project({"a": sr.span("a", date(2026, 2, 2), 30, title="Alpha"),
                         "b": sr.span("b", date(2026, 3, 9), 20, title="Beta")})
    for key, owner in (("a", "Build"), ("b", "Verify")):
        source["objects"][key]["fields"] = {"phase": owner} if "fields" not in source["objects"][key] else {
            **source["objects"][key]["fields"], "phase": owner}
    parts = sr.bundle("executive-light")
    body = parts["theme"]["body"]
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    parts["view"]["body"]["tableColumns"] = columns or [
        _column("Work package", "title"),
        _column("Phase", {"field": "phase"}, **({"textRole": text_role} if text_role else {}))]
    if declare:
        body["values"]["secondary-size"] = {"type": "number", "value": 9}
        # A View-named role declares text measurement properties (and a fill); the icon properties are the text role's.
        measure = {key: value for key, value in body["roles"]["text"].items() if key not in {"iconScale", "iconGap"}}
        body["roles"]["table-cell-secondary"] = {**measure, "fontSize": "secondary-size"}
        if fill:
            body["colorBindings"]["table-cell-secondary.fill"] = fill
    if legend_fill:
        body["colorBindings"]["legend.fill"] = legend_fill
    return sr.render(tmp_path, source, presentation=parts, detail=DETAIL, actual=actual)


def _sub(tmp_path, name):
    path = tmp_path / name
    path.mkdir()
    return path


def _cells(rendered, column):
    return [item for item in rendered.surface.primitives if item.purpose == "table-cell" and item.table_column_id == column]


def test_the_named_role_sets_the_size_and_colour_of_that_column_only(tmp_path):
    plain = _render(_sub(tmp_path, "plain"), declare=False)
    named = _render(_sub(tmp_path, "named"), text_role="table-cell-secondary")

    phase = _cells(named, "Phase")
    assert len(phase) == 2
    assert {item.text_layout.font_size for item in phase} == {9}
    assert {item.visual_role for item in phase} == {"table-cell-secondary"}
    assert {item.paint.fill for item in phase} != {item.paint.fill for item in _cells(plain, "Phase")}
    # The other column, and the header, are unchanged.
    for before, after in zip(_cells(plain, "Work package"), _cells(named, "Work package")):
        assert (before.text_layout.font_size, before.paint.fill, before.visual_role) == (
            after.text_layout.font_size, after.paint.fill, after.visual_role)
    assert all(item.visual_role == "text" for item in _cells(plain, "Phase"))


def test_a_role_without_a_fill_changes_the_type_and_keeps_the_text_ink(tmp_path):
    plain = _render(_sub(tmp_path, "plain"), declare=False)
    named = _render(_sub(tmp_path, "named"), text_role="table-cell-secondary", fill=None)
    phase = _cells(named, "Phase")
    assert {item.text_layout.font_size for item in phase} == {9} and {item.visual_role for item in phase} == {"text"}
    assert {item.paint.fill for item in phase} == {item.paint.fill for item in _cells(plain, "Phase")}


def test_absent_declarations_are_byte_identical(tmp_path):
    first = _render(_sub(tmp_path, "a"), declare=False)
    second = _render(_sub(tmp_path, "b"), declare=True)  # a declared but unused role changes nothing
    assert scene_document(first.scene)["surfaces"] == scene_document(second.scene)["surfaces"]


def test_a_state_coloured_cell_keeps_its_ink_and_takes_the_role_type(tmp_path):
    columns = [_column("Work package", "title"),
               _column("Delta", {"comparisonFacet": "finishDelta"}, format="signedDays", textRole="table-cell-secondary")]
    observed = {"id": "a-observed", "sequence": 1, "projectObjectId": "a",
                "actual": {"start": "2026-02-02", "finish": "2026-03-10", "progress": 1.0}}
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "synthetic-observed",
              "body": {"asOf": "2026-04-30", "observations": [observed]}}
    rendered = _render(_sub(tmp_path, "state"), text_role="table-cell-secondary", columns=columns, actual=actual)
    cells = [item for item in _cells(rendered, "Delta") if item.source_ref == "a"]
    assert cells and all(item.visual_role == "variance-behind" for item in cells)
    assert {item.text_layout.font_size for item in cells} == {9}


def test_an_unknown_role_fails_at_the_view_pointer(tmp_path):
    with pytest.raises(RenderFailed) as raised:
        _render(_sub(tmp_path, "unknown"), text_role="no-such-role", declare=False)
    assert (raised.value.code, raised.value.source_ref) == ("E_THEME_ROLE_REQUIRED", "/body/tableColumns/1/textRole")
    assert "/body/roles/no-such-role" in raised.value.message


def test_a_muted_ink_that_fails_text_contrast_is_reported_and_a_passing_one_is_not(tmp_path):
    def phase_findings(rendered):
        return [item for item in evaluate_scene_contrast(scene_document(rendered.scene))
                if item.purpose == "table-cell" and item.visual_role == "table-cell-secondary"]

    good = phase_findings(_render(_sub(tmp_path, "good"), text_role="table-cell-secondary"))
    assert good and all(item.severity != "error" and item.floor == 4.5 for item in good)
    bad = phase_findings(_render(_sub(tmp_path, "bad"), text_role="table-cell-secondary", fill="surface"))
    assert bad and all(item.severity == "error" and item.code == "E_SCENE_STATE_TEXT_CONTRAST" for item in bad)


def test_the_legend_labels_all_carry_the_declared_ink(tmp_path):
    plain = _render(_sub(tmp_path, "plain"), declare=False)
    muted = _render(_sub(tmp_path, "muted"), declare=False, legend_fill="textMuted")
    labels = [item for item in muted.surface.primitives if item.purpose == "legend-label"]
    base = [item for item in plain.surface.primitives if item.purpose == "legend-label"]
    assert len(labels) == 2 == len(base)
    assert {item.visual_role for item in labels} == {"legend"} and {item.visual_role for item in base} == {"text"}
    assert {item.paint.fill for item in labels} != {item.paint.fill for item in base}
    assert [item.bounds for item in labels] == [item.bounds for item in base]  # colour moves nothing


def test_a_legend_ink_that_fails_text_contrast_is_reported(tmp_path):
    bad = _render(_sub(tmp_path, "bad"), declare=False, legend_fill="surface")
    findings = [item for item in evaluate_scene_contrast(scene_document(bad.scene))
                if item.purpose == "legend-label" and item.visual_role == "legend"]
    assert findings and all(item.severity == "error" and item.floor == 4.5 for item in findings)


def test_every_adapter_serialises_the_role_size_and_ink_of_the_column_and_the_legend(tmp_path):
    """No adapter reads a role name: SVG, Typst and TikZ all carry the completed size and ink."""
    from chrona.presentation.renderers.v05_svg import V05SvgRenderer
    from chrona.presentation.renderers.v05_typeset import V05TikzRenderer, V05TypstRenderer

    rendered = _render(_sub(tmp_path, "adapters"), text_role="table-cell-secondary", legend_fill="textMuted")
    phase = _cells(rendered, "Phase")[0]
    legend = next(item for item in rendered.surface.primitives if item.purpose == "legend-label")
    plain = next(item for item in _cells(rendered, "Work package"))
    assert legend.paint.fill == phase.paint.fill and plain.paint.fill != phase.paint.fill
    ink = phase.paint.fill

    svg = V05SvgRenderer().render(rendered.surface).content.decode()
    typst = V05TypstRenderer().render(rendered.surface).content.decode()
    tikz = V05TikzRenderer().render(rendered.surface).content.decode()
    assert svg.count(f'fill="{ink}"') >= 3 and 'font-size="9"' in svg  # two phase cells and the legend labels
    # The phase cell is 9 pt in the muted ink; a legend label keeps the legend size in the same ink.
    assert f'size: 9pt, number-width: "proportional", fill: rgb("{ink}"))[Build]' in typst
    assert f'size: 12pt, number-width: "proportional", fill: rgb("{ink}"))[Planned]' in typst
    assert f"text={ink}, text opacity=1, font=\\fontsize{{9pt}}" in tikz and "Build}" in tikz
    assert f"text={ink}, text opacity=1, font=\\fontsize{{12pt}}" in tikz and "Planned}" in tikz
