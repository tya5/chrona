"""Every native text-placement site closes the width of the text it draws (#1336)."""
from __future__ import annotations

from copy import deepcopy
import pytest

from chrona.presentation.layout.text import measure_text_width, metric_for_role, paint_text
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr
from tests.support.legacy_axis import use_legacy_six_tier_axis


DETAIL = {
    "version": "chrona/review-detail-profile/v0.1",
    "id": "transformed-placement-sites",
    "body": {"legend": [
        {"role": "planned", "label": "Planned work"},
        {"role": "actual", "label": "Observed work"},
    ]},
}


def _uppercase_compressed_theme(parts):
    body = parts["theme"]["body"]
    body["values"].update({
        "text-transform": {"type": "textTransform", "value": "uppercase"},
        "letter-spacing": {"type": "number", "value": 0.4},
        "numeric-spacing": {"type": "numericSpacing", "value": "tabular"},
        "text-horizontal-scale": {"type": "number", "value": 0.8},
        "slot-heading-size": {"type": "number", "value": 12},
    })
    for role in body["roles"].values():
        if isinstance(role, dict) and "textTransform" in role:
            role["textTransform"] = "text-transform"
            role["letterSpacing"] = "letter-spacing"
            role["numericSpacing"] = "numeric-spacing"
            if "fontSize" in role:
                role["horizontalScale"] = "text-horizontal-scale"
    # Exercise the slot-heading role separately from the text it captions.
    body["roles"]["slot-heading"] = {
        **deepcopy(body["roles"]["text"]),
        "fontSize": "slot-heading-size",
    }
    body["colorBindings"]["slot-heading.fill"] = "textMuted"


def _as_drawn_width(placement, tokens, font_metrics):
    treatment = tokens.text_treatment(placement.typography_role)
    metrics = metric_for_role(tokens, placement.typography_role, font_metrics)
    lines = placement.lines or (placement.content,)
    return max(measure_text_width(
        paint_text(line, text_transform=treatment.transform),
        font_size=placement.font_size,
        font_metrics=metrics,
        letter_spacing=float(treatment.letter_spacing),
        numeric_spacing=treatment.numeric_spacing,
    ) for line in lines)


@pytest.fixture(scope="module")
def _rendered_sites(tmp_path_factory, request):
    """One native synthetic render shared by each site-specific assertion."""
    import chrona.presentation.layout.surface_composer as composer
    import chrona.presentation.layout.surface_axis as axis
    import chrona.presentation.layout.surface_table as table
    import chrona.presentation.layout.surface_legend as legend
    import chrona.presentation.layout.slot_heading as slot_heading
    import chrona.presentation.layout.surface_annotations as annotations
    import chrona.presentation.layout.annotation_kind_frame as kind_frame
    import chrona.presentation.layout.surface_content as content
    import chrona.presentation.layout.group_header_runs as group_header_runs
    import chrona.presentation.layout.surface_observations as observations
    import chrona.presentation.layout.dependency_network as network

    from chrona.presentation.layout import text as text_layout

    original = text_layout.place_text
    placements = {}
    resources = {}
    sources = {}

    def checked_place_text(**kwargs):
        placement = original(**kwargs)
        placements[placement.placement_id] = placement
        resources[placement.placement_id] = (
            kwargs["theme_tokens"],
            metric_for_role(kwargs["theme_tokens"], kwargs["typography_role"], kwargs["font_metrics"]),
        )
        sources[placement.placement_id] = tuple(kwargs.get("lines") or (kwargs["content"],))
        return placement

    # Layout modules bind the shared function at import time; observe each real call site.
    patch = pytest.MonkeyPatch()
    request.addfinalizer(patch.undo)
    for module in (composer, axis, table, legend, slot_heading, annotations, kind_frame, content,
                   group_header_runs, observations, network):
        if hasattr(module, "place_text"):
            patch.setattr(module, "place_text", checked_place_text)

    parts = use_legacy_six_tier_axis(sr.bundle("executive-light"))
    source = ak.project(text="A short synthetic note.")
    ak.with_view_notes(parts, source)
    ak.with_kind_theme(parts)
    _uppercase_compressed_theme(parts)
    # A month label includes lowercase letters whose advances differ from their uppercase forms;
    # a numeric year/quarter label would not reliably exercise transformed measurement.
    parts["view"]["body"]["axis"]["tiers"][2].update({"unit": "month"})
    parts["view"]["body"]["axis"]["tiers"][2]["label"]["form"] = "short-month"

    # A real slot heading and note rail exercise the caption caller alongside the native content.
    sr.with_note_rail(parts, 300)
    sr.find_node(parts["layout"], "annotations")["heading"] = {
        "text": "Review notes", "block": "top", "align": "start",
    }
    render_dir = tmp_path_factory.mktemp("transformed-text")
    try:
        rendered = sr.render(
            render_dir,
            source,
            presentation=parts,
            detail=DETAIL,
            viewport=(1500, 900),
        )
    finally:
        patch.undo()

    primitives = {item.scene_id: item for item in rendered.surface.primitives}
    selected = {
        "axis": next(name for name in placements if name.startswith("axis-label:")),
        "table-header": next(name for name in placements if name.startswith("column:")),
        "table-cell": next(name for name in placements if name.startswith("cell:")),
        "legend": next(name for name in placements if name.startswith("legend:")),
        "slot-heading": "slot-heading:annotations",
        "kind-bar": next(name for name in placements if name.startswith("annotation-kind-text:")),
    }
    assert set(selected.values()) <= placements.keys()
    return rendered, placements, resources, sources, selected, primitives


@pytest.mark.parametrize("site", ["axis", "table-header", "table-cell", "legend", "slot-heading", "kind-bar"])
def test_each_text_site_transports_the_transformed_compressed_width(_rendered_sites, site):
    """Audit each caller separately while reusing the same synthetic render."""
    _rendered, placements, resources, sources, selected, primitives = _rendered_sites
    placement_id = selected[site]
    placement = placements[placement_id]
    tokens, font_metrics = resources[placement_id]
    primitive = primitives[placement_id]
    source_lines = sources[placement_id]

    treatment = tokens.text_treatment(placement.typography_role)
    assert placement.text_transform == "uppercase"
    assert float(treatment.horizontal_scale) == pytest.approx(0.8)
    assert float(treatment.letter_spacing) > 0
    assert placement.numeric_spacing == "tabular"
    assert primitive.bounds[2] == pytest.approx(float(placement.bounds.inline_size), abs=0.002)
    assert primitive.text == placement.content

    def width(lines):
        return max(measure_text_width(
            line,
            font_size=placement.font_size,
            font_metrics=font_metrics,
            letter_spacing=float(treatment.letter_spacing),
            numeric_spacing=treatment.numeric_spacing,
        ) for line in lines)

    source_width = width(source_lines)
    painted_lines = tuple(paint_text(line, text_transform=treatment.transform) for line in source_lines)
    painted_width = width(painted_lines)
    assert any(source != painted for source, painted in zip(source_lines, painted_lines)), (
        site, placement_id, source_lines, painted_lines)
    assert source_width != pytest.approx(painted_width, abs=0.002), (
        site, placement_id, source_lines, source_width, painted_width)
    assert float(placement.bounds.inline_size) == pytest.approx(
        _as_drawn_width(placement, tokens, font_metrics), abs=0.002), placement_id


def test_transformed_legend_grid_and_start_column_close_drawn_bounds(tmp_path, monkeypatch):
    """The new grid/caption path uses the same as-drawn placement contract."""
    import chrona.presentation.layout.surface_legend as legend
    import chrona.presentation.layout.slot_heading as headings
    from chrona.presentation.layout.text import place_text

    placements = {}
    resources = {}

    def capture(**kwargs):
        placement = place_text(**kwargs)
        placements[placement.placement_id] = placement
        resources[placement.placement_id] = (kwargs["theme_tokens"], kwargs["font_metrics"])
        return placement

    monkeypatch.setattr(legend, "place_text", capture)
    monkeypatch.setattr(headings, "place_text", capture)
    parts = sr.bundle("executive-light")
    _uppercase_compressed_theme(parts)
    sr.find_node(parts["layout"], "legend").update({
        "columns": 2,
        "heading": {"text": "Review key", "block": "start-column"},
    })
    rendered = sr.render(tmp_path, ak.project(text="A synthetic note."),
                         presentation=parts, detail=DETAIL, viewport=(1500, 900))
    primitives = {item.scene_id: item for item in rendered.surface.primitives}
    for identity in ("legend:planned", "legend:actual", "slot-heading:legend"):
        placement = placements[identity]
        tokens, metrics = resources[identity]
        assert placement.text_transform == "uppercase"
        assert float(placement.bounds.inline_size) == pytest.approx(
            _as_drawn_width(placement, tokens, metrics), abs=0.002)
        assert primitives[identity].bounds[2] == pytest.approx(
            float(placement.bounds.inline_size), abs=0.002)

    caption = primitives["slot-heading:legend"]
    first = next(item for item in rendered.surface.primitives
                 if item.scene_id.startswith("legend-swatch:planned"))
    second = next(item for item in rendered.surface.primitives
                  if item.scene_id.startswith("legend-swatch:actual"))
    label = primitives["legend:planned"]
    assert first.bounds[0] == pytest.approx(
        caption.bounds[0] + caption.bounds[2]
        + placements["slot-heading:legend"].font_size * 0.5, abs=0.002)
    assert second.bounds[0] > label.bounds[0] + label.bounds[2]
