"""Project-independent period selection closes before Layout (#1560)."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path

import pytest
import yaml

from chrona.presentation.contracts.view_defaults import merge_view_defaults
from chrona.presentation.contracts import ClosureIdentity, parse_contract
from chrona.presentation.model.closure import ClosureError
from chrona.resources import schema_validator
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from tests.support import synthetic_review as sr
from chrona.presentation.review.annotation_expansion import expand_annotations
from chrona.presentation.model.projection import ReviewItem, ReviewProjection


def _source(period_ids):
    source = sr.project({"a": sr.span("a", date(2026, 2, 1), 40)})
    if period_ids:
        source["periods"] = {
            key: {"title": f"Window {key}",
                  "start": (date(2026, 2, 5) + timedelta(days=index * 7)).isoformat(),
                  "end": (date(2026, 2, 10) + timedelta(days=index * 7)).isoformat()}
            for index, key in enumerate(period_ids)}
    return source


def _parts(selection):
    parts = sr.bundle("executive-light")
    parts["view"]["body"]["window"] = {"mode": "explicit", "start": "2026-02-01", "end": "2026-04-01"}
    parts["view"]["body"]["periods"] = selection
    return parts


@pytest.mark.parametrize("period_ids", [(), ("only",), ("zulu", "alpha", "middle")])
def test_all_selects_zero_one_or_many_in_project_declaration_not_sorted_order(tmp_path, period_ids):
    source, parts = _source(period_ids), _parts({"select": "all"})
    originals = deepcopy((source, parts))
    result = sr.render(tmp_path, source, presentation=parts)
    bands = [item for item in result.surface.primitives if item.purpose == "period-band"]
    assert [item.source_ref for item in bands] == list(period_ids)
    assert not [item for item in result.surface.primitives if item.purpose == "period-label"]
    assert (source, parts) == originals


def test_all_reuses_declared_label_and_layout_defaults_with_view_precedence(tmp_path):
    parts = _parts({"select": "all", "label": {"overflow": "suppress"}})
    parts["layout"]["viewDefaults"] = {"periodLabelPresentation": {"placement": "top", "overflow": "visible-overflow"}}
    parts["view"] = merge_view_defaults(parts["view"], parts["layout"]["viewDefaults"])
    assert parts["view"]["body"]["periods"]["label"] == {"placement": "top", "overflow": "suppress"}
    # Prove shared label intent through actual rendering, not only raw dictionary normalization.
    source = _source(("zulu",))
    result = sr.render(tmp_path, source, presentation=parts)
    labels = [item for item in result.surface.primitives if item.purpose == "period-label"]
    assert [item.text.casefold() for item in labels] == ["window zulu"]


def test_all_on_a_project_without_periods_preserves_svg_and_surface_bytes(tmp_path):
    source, selected = _source(()), _parts({"select": "all"})
    control = deepcopy(selected)
    control["view"]["body"].pop("periods")
    (tmp_path / "all").mkdir()
    (tmp_path / "none").mkdir()
    after = sr.render(tmp_path / "all", source, presentation=selected)
    before = sr.render(tmp_path / "none", source, presentation=control)
    assert after.artifact.content == before.artifact.content
    assert after.surface == before.surface


@pytest.mark.parametrize("selection", [{"select": "unknown"}, {"select": "all", "ids": []},
                                        {"select": "all", "variant": "custom"}])
def test_all_selector_is_closed_and_rejects_unapproved_policy(selection):
    view = _parts(selection)["view"]
    assert not schema_validator("view-v0.28.schema.yaml").is_valid(view)


def test_explicit_period_list_retains_its_own_order(tmp_path):
    result = sr.render(tmp_path, _source(("zulu", "alpha")),
                       presentation=_parts([{"id": "alpha"}, {"id": "zulu"}]))
    assert [item.source_ref for item in result.surface.primitives if item.purpose == "period-band"] == ["alpha", "zulu"]


def test_all_reuses_label_text_and_global_figure_templates(tmp_path):
    parts = _parts({"select": "all", "label": {"placement": "top", "template": "COUNT {figure:count}"}})
    parts["view"]["body"]["figures"] = [{"id": "count", "kind": "count", "source": "selected"}]
    result = sr.render(tmp_path, _source(("window",)), presentation=parts)
    assert [item.text.casefold() for item in result.surface.primitives if item.purpose == "period-label"] == ["count 1"]


def test_all_label_cannot_mix_literal_text_and_template(tmp_path):
    parts = _parts({"select": "all", "label": {"placement": "top", "text": "Window", "template": "Window"}})
    with pytest.raises(ClosureError) as raised:
        sr.render(tmp_path, _source(("window",)), presentation=parts)
    assert raised.value.diagnostic_id == "E_VIEW_PERIOD_LABEL_SOURCE"
    assert raised.value.source_ref == "/body/periods/label"


def test_generic_note_bindings_do_not_require_optional_actual_geometry():
    root = Path(__file__).resolve().parents[2]
    raw = yaml.safe_load((root / "src/chrona/resources/presets/bundles/design-default/view.yaml").read_text(encoding="utf-8"))
    layout = yaml.safe_load((root / "src/chrona/resources/designs/target-b/layout.yaml").read_text(encoding="utf-8"))
    raw = merge_view_defaults(raw, layout["viewDefaults"])
    view = parse_contract(ClosureIdentity("view", raw["id"], "r", "sha256:" + "a" * 64), raw).view
    span = ReviewItem("task", "Task", "span", {"start": date(2026, 2, 1), "end": date(2026, 2, 8)},
                      None, None, (), source_kind="primary")
    point = ReviewItem("gate", "Gate", "point", {"at": date(2026, 2, 9)}, None, None, (), source_kind="primary")
    projection = ReviewProjection((span, point), (date(2026, 2, 1), date(2026, 3, 1)), (), (), folded_points=())
    notes = {"risk": {"kind": "risk", "text": "Risk", "anchor": {"object": "task"}},
             "note": {"kind": "note", "text": "Note", "anchor": {"object": "task"}},
             "point": {"kind": "note", "text": "Gate", "anchor": {"object": "gate"}}}
    expanded = expand_annotations(view, notes, projection)
    assert len(expanded) == 3
    assert {entry.value["anchor"]["facet"] for entry in expanded} == {"planned"}
    assert {entry.value["anchor"]["endpoint"] for entry in expanded} == {"at", "end"}


@pytest.mark.parametrize("preset", ["titlecard", "yuya"])
def test_generic_notes_close_named_preset_required_capabilities_for_png(tmp_path, preset):
    source = _source(())
    source["annotations"] = {"risk": {"kind": "risk", "text": "Synthetic risk", "anchor": {"object": "a"}}}
    project = tmp_path / "project.yaml"
    project.write_text(yaml.safe_dump(source), encoding="utf-8")
    result = render_draft(DraftRenderRequest(project=project, target_kind="png", preset=preset))
    assert result.artifact.content.startswith(b"\x89PNG")
    assert any(item.scene_id == "annotation-text:risk-note" for item in result.rendered.surface.primitives)
