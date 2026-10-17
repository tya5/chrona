"""Independent heading slots retain Layout's exact per-glyph face closure (#1612)."""
import pytest

from chrona.presentation.fonts.installed import InstalledFontIndex, use_installed_fonts
from tests.integration.test_heading_part_slots import (
    PNG, _parts, _primitive_by_id, _render_parts, _theme_for_split,
)
from tests.integration.test_heading_templates import _source
from tests.support.text_treatments import cjk_available


@pytest.mark.skipif(not cjk_available(), reason="requires optional Noto CJK provider")
def test_independent_heading_slot_carries_measured_japanese_and_latin_faces(tmp_path):
    parts = _parts(heading={"title": "日本語 Team"}, split=("title",))
    _theme_for_split(parts)
    source = _source()
    source["project"]["title"] = "日本語 Team"

    with use_installed_fonts(InstalledFontIndex([])):
        rendered = _render_parts(tmp_path / "independent", parts, source=source, target="png", profile=PNG)
        whole_parts = _parts(heading={"title": "日本語 Team"}, split=("title",))
        whole_parts["layout"]["root"]["children"][0]["source"] = "title"
        _theme_for_split(whole_parts)
        whole = _render_parts(tmp_path / "whole", whole_parts, source=source, target="png", profile=PNG)

    placement = _primitive_by_id(rendered)["title"].text_layout
    control = _primitive_by_id(whole)["title"].text_layout
    runs = placement.runs[0]
    assert [(run.text, run.family, run.weight) for run in runs] == [
        ("日本語", "Noto Sans JP", 700), (" Team", "Noto Sans", 700)]
    assert all(run.asset_identity.startswith("sha256:") and run.inline_size > 0 for run in runs)
    assert placement.lines == ("日本語 Team",)
    assert placement.runs == control.runs
    assert placement.bounds == pytest.approx(control.bounds)


def test_latin_independent_heading_does_not_gain_fallback_runs(tmp_path):
    parts = _parts(heading={"title": "Programme Team"}, split=("title",))
    _theme_for_split(parts)
    source = _source()
    source["project"]["title"] = "Programme Team"
    rendered = _render_parts(tmp_path, parts, source=source, target="png", profile=PNG)
    placement = _primitive_by_id(rendered)["title"].text_layout
    assert placement.runs == ()


@pytest.mark.skipif(not cjk_available(), reason="requires optional Noto CJK provider")
def test_network_title_and_node_keep_the_same_completed_fallback_faces(tmp_path):
    from tests.integration.test_title_ink import _network_parts, _source as network_source
    from tests.support import synthetic_review as sr
    source = network_source()
    source["project"]["title"] = "日本語 Team"
    source["objects"]["alpha"]["title"] = "日本語 Team"
    with use_installed_fonts(InstalledFontIndex([])):
        rendered = sr.render(tmp_path, source, presentation=_network_parts())
    texts = {item.scene_id: item for item in rendered.surface.primitives if item.kind == "Text"}
    for identity in ("title", "network-label:alpha"):
        runs = texts[identity].text_layout.runs[0]
        assert [(run.text, run.family) for run in runs] == [
            ("日本語", "Noto Sans JP"), (" Team", "Noto Sans")]
        assert all(run.asset_identity.startswith("sha256:") for run in runs)
