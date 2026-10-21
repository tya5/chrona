"""Explicit caption templates bind before Layout sizing; literal copy stays literal (#1346)."""
import pytest

from chrona.usecases.render_review import RenderFailed
from tests.integration.test_slot_heading import DETAIL, HEADING, _by_id, _render
from tests.support import synthetic_review as sr


def _counts(parts):
    parts["view"]["body"]["figures"] = [
        {"id": "n", "kind": "count", "source": "selected"},
        {"id": "groups", "kind": "count", "source": "groups"},
    ]
    parts["layout"]["viewDefaults"] = {"figureFormats": {
        "n": {"form": "english-words", "capitalize": True},
        "groups": {"form": "digits", "minimumDigits": 2},
    }}


@pytest.mark.parametrize("block", ["top", "header-row", "axis-tier"])
def test_explicit_caption_templates_use_selected_counts_and_formats_in_scene_and_svg(tmp_path, block):
    rendered = _render(tmp_path, heading={"template": "{figure:n} items in {figure:groups} groups", "block": block},
                       configure=_counts)
    assert _by_id(rendered)[HEADING].text == "TWELVE ITEMS IN 03 GROUPS"
    assert b">TWELVE ITEMS IN 03 GROUPS<" in rendered.artifact.content


def test_template_and_its_equivalent_literal_have_identical_completed_primitives(tmp_path):
    literal = _render(tmp_path, name="literal", heading={"text": "Twelve items in 03 groups"}, configure=_counts)
    template = _render(tmp_path, name="template", heading={"template": "{figure:n} items in {figure:groups} groups"},
                       configure=_counts)
    assert template.surface.primitives == literal.surface.primitives
    assert template.surface.slots == literal.surface.slots
    assert template.artifact.content == literal.artifact.content


def test_literal_text_is_not_interpreted_as_a_template(tmp_path):
    rendered = _render(tmp_path, heading={"text": "{figure:not-declared}"})
    assert _by_id(rendered)[HEADING].text == "{FIGURE:NOT-DECLARED}"


def test_literal_view_copy_wins_without_reading_or_reparsing_the_template(tmp_path, monkeypatch):
    from chrona.presentation.layout import slot_heading
    compile_text = slot_heading.compile_figure_text
    def closed_without_read(source, **options):
        program = compile_text(source, **options)
        class Closed:
            figure_ids = program.figure_ids
            def bind(self, *args):
                raise AssertionError("overridden caption must not read count names")
        return Closed()
    monkeypatch.setattr(slot_heading, "compile_figure_text", closed_without_read)
    def configure(parts):
        _counts(parts)
        parts["view"]["body"]["slotHeadingText"] = {"annotations": "{figure:still-literal}"}
    rendered = _render(tmp_path, heading={"template": "{figure:n}"}, configure=configure)
    assert _by_id(rendered)[HEADING].text == "{FIGURE:STILL-LITERAL}"


@pytest.mark.parametrize("notes", [True, False])
@pytest.mark.parametrize("template,code", [("{figure:missing}", "E_VIEW_FIGURE_UNKNOWN"),
                                           ("{figure:", "E_VIEW_FIGURE_TEMPLATE"),
                                           ("{project}", "E_VIEW_FIGURE_TEMPLATE")])
def test_bad_template_references_fail_even_on_absent_optional_slots(tmp_path, notes, template, code):
    with pytest.raises(RenderFailed) as caught:
        _render(tmp_path, heading={"template": template}, notes=notes)
    assert caught.value.code == code
    assert caught.value.component == "layout-profile"
    assert caught.value.source_ref.endswith("/heading/template")


def test_group_scoped_caption_reads_are_refused_at_the_reference(tmp_path):
    def configure(parts):
        parts["view"]["body"]["figures"] = [{"id": "n", "kind": "count", "source": "selected", "scope": "group"}]
    with pytest.raises(RenderFailed) as caught:
        _render(tmp_path, heading={"template": "{figure:n}"}, configure=configure)
    assert caught.value.code == "E_FIGURE_SCOPE_UNAVAILABLE"
    assert caught.value.source_ref.endswith("/heading/template")


def test_absent_optional_caption_has_no_bound_copy_or_completed_text(tmp_path, monkeypatch):
    from chrona.presentation.layout import surface_render_plan as planner
    original = planner.bind_slot_heading_templates
    bound = []
    def observe(*args, **kwargs):
        result = original(*args, **kwargs)
        bound.append(dict(result.slot_heading_text))
        return result
    monkeypatch.setattr(planner, "bind_slot_heading_templates", observe)
    rendered = _render(tmp_path, heading={"template": "{figure:n}"}, notes=False, configure=_counts)
    assert bound == [{}]
    assert HEADING not in _by_id(rendered)


def test_start_column_caption_uses_bound_copy_for_its_reserved_inline_width(tmp_path):
    def configured(heading):
        def configure(parts):
            _counts(parts)
            legend = sr.find_node(parts["layout"], "legend")
            legend.update(columns=2, heading=heading)
        return configure
    template = _render(tmp_path, name="template", detail=DETAIL,
                       configure=configured({"template": "{figure:n} items", "block": "start-column"}))
    literal = _render(tmp_path, name="literal", detail=DETAIL,
                      configure=configured({"text": "Twelve items", "block": "start-column"}))
    assert _by_id(template)["slot-heading:legend"].text == "TWELVE ITEMS"
    assert template.surface.primitives == literal.surface.primitives
    assert template.surface.slots == literal.surface.slots
    assert template.artifact.content == literal.artifact.content
