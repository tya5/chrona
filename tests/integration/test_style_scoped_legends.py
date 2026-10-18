"""Real Style resource → final Layout legend → Scene and SVG evidence."""
from copy import deepcopy
from datetime import date

import pytest

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.model.font_metrics import FontMetricsError
from chrona.presentation.layout import surface_legend
from chrona.presentation.scene.serialization import scene_document, validate_scene_document
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderRequest, render_review
from tests.support import synthetic_review as sr


def _render(tmp_path, *, show_scope=False, glyph=None, shape=None, table=False,
            duplicate_column=False, wide_legend=False, mode="ordinary", legacy=False):
    parts = sr.bundle()
    theme = parts["theme"]["body"]
    theme["colorScales"] = {"owners": {"slots": {"a": "owner-a"}}}
    parts["scheme"]["body"]["categories"]["owner-a"] = "#28c7b8"
    if glyph is not None:
        theme["values"]["style-symbol"] = {"type": "symbol", "value": glyph}
        theme["roles"]["planned"]["symbol"] = "style-symbol"
        theme["roles"]["milestoneSymbol"]["symbol"] = "style-symbol"
        source = sr.project({"one": sr.point("one", date(2026, 1, 5))})
    elif mode == "folded":
        source = sr.project({"one": sr.point("one", date(2026, 1, 5))})
    else:
        source = sr.project({"one": sr.span("one", date(2026, 1, 5), 5)})
    if legacy:
        source = sr.project({"one": sr.span("one", date(2026, 1, 5), 5, owner="a"),
                             "two": sr.span("two", date(2026, 1, 10), 5, owner="b")})
        source["objects"]["one"]["fields"]["phase"] = "c"
        source["objects"]["two"]["fields"]["phase"] = "d"
        theme["colorScales"]["owners"] = {"palette": ["owner-a"]}
        parts["view"]["body"]["colorEncoding"] = {
            "target": "planned", "source": {"field": "owner"}, "scale": "owners", "domain": "firstAppearance"}
    if mode == "lane":
        parts["view"] = sr.lane_view(parts["view"], packing=("explicit",))
    elif mode == "folded":
        parts["view"]["body"]["rows"] = {"mode": "automatic", "points": "group-header"}
    else:
        parts["view"]["body"]["rows"] = {"mode": "automatic"}
    if table:
        columns = [{
            "id": "Owner", "source": {"field": "owner"}, "missing": "em-dash",
            "align": "start", "width": "content", "headerOrientation": "horizontal"}]
        if duplicate_column:
            columns.append({**columns[0], "id": "Owner copy"})
        parts["view"]["body"]["tableColumns"] = columns
    if shape is not None:
        theme["roles"].setdefault("legend-swatch", {})["swatchShape"] = shape
    if wide_legend:
        sr.fix_inline(parts, "legend", 800)
    rules = [{"id": "owner-fill", "when": {"semantic": "tableCell" if table else "planned"},
              "then": {"encode": {"channel": "fill", "source": {"field": "phase" if legacy else "owner"},
                                  "scale": "owners", "domain": "firstAppearance" if legacy else ["a"],
                                  "legend": {"title": "Owner", "showScope": show_scope}}}}]
    parts["style"] = {"version": "chrona/style/v0.2", "kind": "style", "id": "scoped",
                      "body": {"rules": rules}}
    parts["project"] = source
    paths = {kind: sr._write(tmp_path / f"{kind}.yaml", value) for kind, value in parts.items()}
    draft = resolve_draft_render(project_path=paths["project"], view_path=paths["view"],
        style_path=paths["style"], theme_path=paths["theme"], scheme_path=paths["scheme"], layout_path=paths["layout"])
    return render_review(RenderRequest(draft.closure, draft.asset_root, ReferenceScheduler(),
        renderer=V05SvgRenderer(), asset_root=draft.asset_root, require_all_inputs_read=True))


@pytest.mark.parametrize("shape", [None, "circle", "rule-pair"])
def test_real_encoding_legend_has_completed_colour_scope_and_svg(tmp_path, shape):
    rendered = _render(tmp_path, shape=shape)
    document = scene_document(rendered.scene)
    validate_scene_document(document)
    swatches = [node for node in rendered.surface.primitives if node.legend_scope is not None]
    assert len(swatches) == 1
    swatch = swatches[0]
    assert swatch.legend_scope.style_id == "scoped"
    assert swatch.legend_scope.rule_id == "owner-fill"
    assert swatch.legend_scope.selector == '{"semantic":"planned"}'
    assert (swatch.paint.stroke if shape == "rule-pair" else swatch.paint.fill) == "#28c7b8"
    assert any(node.text == "Owner: a" for node in rendered.surface.primitives)
    assert b"Owner: a" in rendered.artifact.content
    assert b"#28c7b8" in rendered.artifact.content
    altered = deepcopy(document)
    altered["provenance"]["resources"] = [item for item in altered["provenance"]["resources"] if item["kind"] != "style"]
    with pytest.raises(ValueError):
        validate_scene_document(altered)


def test_optional_scope_is_visible_when_it_fits_without_changing_primary_identity(tmp_path):
    rendered = _render(tmp_path, show_scope=True, wide_legend=True)
    assert any(node.text == 'Owner: a when {"semantic":"planned"}' for node in rendered.surface.primitives)


def test_optional_scope_omits_itself_without_room_but_retains_scope_provenance(tmp_path):
    rendered = _render(tmp_path, show_scope=True)
    assert any(node.text == "Owner: a" for node in rendered.surface.primitives)
    assert not any(node.text is not None and " when " in node.text for node in rendered.surface.primitives)
    assert any(node.legend_scope is not None and node.legend_scope.show_scope for node in rendered.surface.primitives)


def test_unmeasurable_optional_scope_does_not_reject_the_primary_key(tmp_path, monkeypatch):
    original = surface_legend.measure_text_width

    def width(text, **kwargs):
        if " when " in text:
            raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE", "optional qualifier glyph")
        return original(text, **kwargs)

    monkeypatch.setattr(surface_legend, "measure_text_width", width)
    rendered = _render(tmp_path, show_scope=True, wide_legend=True)
    assert any(node.text == "Owner: a" for node in rendered.surface.primitives)


@pytest.mark.parametrize("mode", ["ordinary", "lane", "folded"])
def test_source_occurrence_survives_final_mark_projection_and_legend_selection(tmp_path, mode):
    rendered = _render(tmp_path, mode=mode)
    treated = [node for node in rendered.surface.primitives if node.source_ref == "one" and node.style_match is not None]
    assert treated
    assert all(node.style_match.rule_ids == ("owner-fill",) for node in treated)
    assert any(node.legend_scope is not None for node in rendered.surface.primitives)


def test_table_only_fill_has_its_actual_visible_value_legend(tmp_path):
    rendered = _render(tmp_path, table=True)
    assert any(node.legend_scope is not None for node in rendered.surface.primitives)
    assert any(node.kind == "Text" and node.style_match is not None and node.paint.fill == "#28c7b8"
               for node in rendered.surface.primitives)


def test_repeated_same_object_field_in_distinct_columns_keeps_one_legend_and_both_occurrences(tmp_path):
    rendered = _render(tmp_path, table=True, duplicate_column=True)
    document = scene_document(rendered.scene)
    validate_scene_document(document)
    cells = [node for node in rendered.surface.primitives
             if node.kind == "Text" and node.style_match is not None
             and node.table_column_id in {"Owner", "Owner copy"}]
    assert {node.table_column_id for node in cells} == {"Owner", "Owner copy"}
    assert all(node.paint.fill == "#28c7b8" for node in cells)
    assert len({node.style_match for node in cells}) == 1
    assert sum(node.legend_scope is not None for node in rendered.surface.primitives) == 1


def test_suppressed_table_cell_does_not_keep_its_potential_style_legend(tmp_path, monkeypatch):
    from dataclasses import replace

    from chrona.presentation.layout import surface_composer

    compose_table = surface_composer.compose_table
    suppressed_keys = []

    def suppress_style_cells(*args, **kwargs):
        batch = compose_table(*args, **kwargs)
        style_cells = [item for item in batch.text if item.style_occurrence_key is not None]
        assert style_cells
        assert all(item.bounds.inline_size > 0 and item.bounds.block_size > 0 for item in style_cells)
        suppressed_keys.extend(item.style_occurrence_key for item in style_cells)
        return replace(batch, text=tuple(
            replace(item, overflow="suppressed") if item.style_occurrence_key is not None else item
            for item in batch.text
        ))

    monkeypatch.setattr(surface_composer, "compose_table", suppress_style_cells)
    rendered = _render(tmp_path, table=True)
    assert suppressed_keys
    assert not any(node.legend_scope is not None for node in rendered.surface.primitives)


def test_legacy_and_style_domain_union_reports_one_completed_folding_diagnostic(tmp_path):
    rendered = _render(tmp_path, table=True, legacy=True)
    folded = [item for item in rendered.info_diagnostics if item.code == "I_PRESENTATION_SCALE_FOLDED"
              and item.scale_id == "owners"]
    assert len(folded) == 1
    assert folded[0].values == ("b", "c", "d")


@pytest.mark.parametrize("part", [
    {"d": "M 10 10 L 90 10 L 90 90 L 10 90 Z", "paint": "fill", "color": "#123456"},
    {"d": "M 10 10 L 90 90", "paint": "stroke"},
])
def test_nonconsuming_glyph_parts_do_not_manufacture_a_fill_legend(tmp_path, part):
    glyph = {"shape": "glyph", "viewBox": [100, 100], "parts": [part]}
    rendered = _render(tmp_path, glyph=glyph)
    assert not any(node.legend_scope is not None for node in rendered.surface.primitives)
    assert not any(node.text is not None and node.text.startswith("Owner:") for node in rendered.surface.primitives)
