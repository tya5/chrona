"""#927: completed figure text reaches real period and annotation SVG labels."""
from copy import deepcopy

import pytest

from chrona.presentation.model.closure import ClosureError
from chrona.usecases.render_review import RenderFailed
from tests.integration import test_axis_band_color_scales as axis_bands
from tests.integration import test_named_periods as periods
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr


def _period_parts(*, template=None, text=None, figure=True):
    parts = periods._labelled(periods._parts())
    label = parts["view"]["body"]["periods"][0]["label"]
    if template is not None:
        label["template"] = template
    if text is not None:
        label["text"] = text
    if figure:
        parts["view"]["body"]["figures"] = [{"id": "n", "kind": "daysIn", "period": "window"}]
    return parts


def test_period_template_resolves_before_label_measurement_and_svg(tmp_path):
    rendered = periods._render(tmp_path, parts=_period_parts(template="WINDOW {figure:n} DAYS"))
    assert periods._labels(rendered)[0].text == "WINDOW 28 DAYS"
    assert b"WINDOW 28 DAYS" in rendered.artifact.content


def test_literal_period_text_never_interprets_figure_notation(tmp_path):
    rendered = periods._render(tmp_path, parts=_period_parts(text="{figure:n}", figure=False))
    assert periods._labels(rendered)[0].text == "{figure:n}"
    assert b"{figure:n}" in rendered.artifact.content


@pytest.mark.parametrize(("template", "code"), [
    ("{figure:unknown}", "E_VIEW_FIGURE_UNKNOWN"), ("{title}", "E_VIEW_FIGURE_TEMPLATE"),
    ("{figure:n", "E_VIEW_FIGURE_TEMPLATE"),
])
def test_period_template_refusals_name_the_consumer(tmp_path, template, code):
    with pytest.raises(ClosureError) as failure:
        periods._render(tmp_path, parts=_period_parts(template=template))
    assert failure.value.diagnostic_id == code
    assert failure.value.source_ref == "/body/periods/0/label/template"


def test_period_label_chooses_literal_or_template_not_both(tmp_path):
    with pytest.raises(ClosureError) as failure:
        periods._render(tmp_path, parts=_period_parts(template="{figure:n}", text="Literal"))
    assert failure.value.diagnostic_id == "E_VIEW_PERIOD_LABEL_SOURCE"


def test_period_template_has_no_implicit_current_group(tmp_path):
    parts = _period_parts(template="{figure:n}")
    parts["view"]["body"]["figures"] = [{"id": "n", "kind": "count", "source": "selected", "scope": "group"}]
    with pytest.raises(ClosureError) as failure:
        periods._render(tmp_path, parts=parts)
    assert failure.value.diagnostic_id == "E_FIGURE_SCOPE_UNAVAILABLE"


def _annotation_parts(source, title="{label} {figure:n}"):
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    kinds = deepcopy(ak.KINDS)
    kinds["risk"]["title"] = title
    ak.with_kind_theme(parts, kinds=kinds)
    parts["view"]["body"]["figures"] = [{"id": "n", "kind": "count", "source": "selected"}]
    return parts


def test_annotation_kind_title_reads_global_figures_before_layout_and_svg(tmp_path):
    source = ak.project(kinds=("risk",))
    rendered = sr.render(tmp_path, source, presentation=_annotation_parts(source))
    title = next(item for item in rendered.surface.primitives if item.scene_id == "annotation-kind-text:view-n0:0")
    assert title.text == "RISK 3"
    assert b"RISK 3" in rendered.artifact.content


def test_figure_annotation_and_axis_scale_complete_together_before_scene(tmp_path):
    source = ak.project(kinds=("risk",))
    parts = axis_bands._parts(tiers=axis_bands._alternating_tiers(),
                             scales={"alternating": axis_bands.SLOTS["parity"]})
    ak.with_view_notes(parts, source)
    kinds = deepcopy(ak.KINDS)
    kinds["risk"]["title"] = "{label} {figure:n}"
    ak.with_kind_theme(parts, kinds=kinds)
    parts["view"]["body"]["figures"] = [{"id": "n", "kind": "count", "source": "selected"}]
    rendered = sr.render(tmp_path, source, presentation=parts)
    title = next(item for item in rendered.surface.primitives
                 if item.scene_id == "annotation-kind-text:view-n0:0")
    assert title.text == "RISK 3"
    assert b"RISK 3" in rendered.artifact.content
    bands, svg_bands = axis_bands._bands(rendered), axis_bands._svg_bands(rendered)
    expected = tuple(axis_bands.COLORS[axis_bands.SLOTS["parity"][str(index % 2)]]
                     for index in range(6))
    assert tuple(item.paint.fill for item in bands.values()) == expected
    assert tuple(node.attrib["fill"] for node in svg_bands.values()) == expected


def test_annotation_kind_unknown_figure_names_the_theme_consumer(tmp_path):
    source = ak.project(kinds=("risk",))
    with pytest.raises(RenderFailed) as failure:
        sr.render(tmp_path, source, presentation=_annotation_parts(source, "{label} {figure:missing}"))
    assert failure.value.code == "E_VIEW_FIGURE_UNKNOWN"
    assert failure.value.source_ref == "/body/annotationKinds/risk/title"


def test_annotation_kind_has_no_implicit_current_group(tmp_path):
    source = ak.project(kinds=("risk",))
    parts = _annotation_parts(source)
    parts["view"]["body"]["figures"][0]["scope"] = "group"
    with pytest.raises(RenderFailed) as failure:
        sr.render(tmp_path, source, presentation=parts)
    assert failure.value.code == "E_FIGURE_SCOPE_UNAVAILABLE"
    assert failure.value.source_ref == "/body/annotationKinds/risk/title"


def test_unused_annotation_kind_does_not_demand_view_figure_facts(tmp_path):
    source = ak.project(kinds=("note",))
    rendered = sr.render(tmp_path, source, presentation=_annotation_parts(source, "{figure:missing}"))
    assert any(item.text == "NOTE" for item in rendered.surface.primitives if hasattr(item, "text"))


def test_annotation_separate_heading_resolves_the_same_global_figure(tmp_path):
    source = ak.project(kinds=("risk",))
    parts = _annotation_parts(source)
    body = parts["theme"]["body"]
    body["annotationKinds"]["risk"]["heading"] = "SELECTED {figure:n}"
    body["roles"]["annotation-heading"] = deepcopy(body["roles"]["annotation-kind-label"])
    body["colorBindings"]["annotation-heading.fill"] = "text"
    rendered = sr.render(tmp_path, source, presentation=parts)
    heading = next(item for item in rendered.surface.primitives if item.scene_id == "annotation-heading:view-n0")
    assert heading.text == "SELECTED 3"
    assert b"SELECTED 3" in rendered.artifact.content
