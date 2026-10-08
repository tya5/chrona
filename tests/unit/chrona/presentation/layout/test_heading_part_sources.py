from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from chrona.presentation.contracts.resources import ViewRowMode
from chrona.presentation.layout.model import Measurement, Rect, SlotHeading
from chrona.presentation.layout.slot_heading import complete_slot_headings, reserve_slot_heading_blocks
from chrona.presentation.layout.sources import SourceInput, SourceTextRun, measure_sources
from chrona.presentation.layout.surface_quality import SlotPlacement
from chrona.presentation.model.surface_content import HeadingContent, SummaryContent
from chrona.presentation.model.theme_tokens import TextTreatment
from chrona.usecases.render_review import _source_inputs
from tests.unit.chrona.presentation.layout.test_sources import theme


class _Metrics:
    content_identity = "sha256:heading-parts"

    def width(self, value, size, **_kwargs):
        return len(value) * size / 2

    def baseline(self, top, size, _line_height):
        return top + size


def _source_map(*, surface="table-timeline", legacy_heading=None, view_heading=None):
    view = SimpleNamespace(rows=SimpleNamespace(mode=ViewRowMode.AUTOMATIC), table_columns=(), surface=surface)
    projection = SimpleNamespace(lane_rows=(), rows=(SimpleNamespace(label="Row"),), items=(),
                                 window=(date(2026, 1, 1), date(2026, 1, 2)), network=None)
    content = SimpleNamespace(axis_tiers=(), group_details=(), milestones=(),
                               observation_rows=(), observation_columns=())
    return _source_inputs(
        {"project": {"title": "Project title"}, "annotations": {}}, view, projection,
        SummaryContent(()), content=content,
        heading=legacy_heading, view_heading=view_heading)


def test_normalized_heading_parts_are_always_advertised_with_stable_ids_and_roles():
    normalized = HeadingContent("View title", "View subtitle", "View kicker")
    sources = _source_map(legacy_heading=normalized, view_heading=normalized)

    assert sources["heading.title"].text_runs() == (SourceTextRun("View title", "heading", "heading.title"),)
    assert sources["heading.kicker"].text_runs() == (SourceTextRun("View kicker", "kicker", "heading.kicker"),)
    assert sources["heading.subtitle"].text_runs() == (SourceTextRun("View subtitle", "subtitle", "heading.subtitle"),)
    assert all(sources[name].content_present for name in
               ("heading.title", "heading.kicker", "heading.subtitle"))
    assert sources["title"] == SourceInput(
        ("View kicker", "View title", "View subtitle"), typography_role="heading",
        runs=(SourceTextRun("View kicker", "kicker", "kicker"),
              SourceTextRun("View title", "heading", "title"),
              SourceTextRun("View subtitle", "subtitle", "subtitle")),
        run_flow="block")

    empty_parts = _source_map(legacy_heading=HeadingContent("", None, None),
                              view_heading=HeadingContent("", None, None))
    for part in ("heading.title", "heading.kicker", "heading.subtitle"):
        assert part in empty_parts
        assert not empty_parts[part].content_present and empty_parts[part].text_runs() == ()


def test_network_keeps_legacy_project_title_source_while_advertising_view_parts():
    normalized = HeadingContent("Templated title", "Templated subtitle", "Templated kicker")
    sources = _source_map(surface="dependency-network", view_heading=normalized)

    assert sources["title"] == SourceInput(("Project title",), typography_role="heading")
    assert sources["heading.title"].text_runs()[0].content == "Templated title"
    assert sources["heading.kicker"].text_runs()[0].typography_role == "kicker"
    assert sources["heading.subtitle"].text_runs()[0].typography_role == "subtitle"


def test_empty_declared_heading_part_has_zero_measurement_and_no_runs():
    resolved_theme = theme()
    measured = measure_sources({"heading.kicker": SourceInput(content_present=False)},
                               resolved_theme, font_metrics=_Metrics())

    assert measured.measurements["heading.kicker"] == Measurement(*(Decimal(0) for _ in range(6)))
    assert measured.run_measurements["heading.kicker"] == ()
    assert "heading.kicker" not in measured.block_stacks


def test_heading_part_measurement_honors_its_declared_numeric_spacing():
    normalized = HeadingContent("111")
    source = _source_map(view_heading=normalized)["heading.title"]
    resolved = theme()
    resolved["body"]["values"]["numeric-spacing"]["value"] = "tabular"
    seen = []

    class Metrics(_Metrics):
        def ensure_numeric_spacing(self, mode):
            assert mode in {"proportional", "tabular"}

        def width(self, value, size, **kwargs):
            if value == "111":
                seen.append(kwargs["numeric_spacing"])
            return super().width(value, size, **kwargs)

    measured = measure_sources({"heading.title": source}, resolved, font_metrics=Metrics())
    assert seen == ["tabular"]
    assert measured.run_measurements["heading.title"][0].numeric_spacing == "tabular"


def test_empty_heading_part_does_not_reserve_or_draw_a_slot_caption(monkeypatch):
    import chrona.presentation.layout.slot_heading as slot_heading

    resolved_theme = theme()
    measured = measure_sources({"heading.kicker": SourceInput(content_present=False)},
                               resolved_theme, font_metrics=_Metrics())
    root = {"kind": "slot", "source": "heading.kicker", "id": "kicker-slot",
            "blockSize": "content", "heading": {"text": "Caption"}}
    layout = SimpleNamespace(profile={"root": root})

    class Tokens:
        def slot_heading_role(self):
            return "slot-heading"

        def text_treatment(self, _role):
            return TextTreatment("Test", 400, Decimal(10), Decimal("1.5"), Decimal(0), "none", "proportional")

    baseline = measured.measurements["heading.kicker"]
    assert reserve_slot_heading_blocks(measured, layout, Tokens(), content=SimpleNamespace()).measurements[
        "heading.kicker"] == baseline

    monkeypatch.setattr(slot_heading, "metric_for_role", lambda *_args: _Metrics())
    decision = SimpleNamespace(node_id="kicker-slot", source="heading.kicker",
                               heading=SlotHeading("Caption", "start", "top"))
    request = SimpleNamespace(
        theme_tokens=Tokens(), font_metrics=_Metrics(), measured_sources=measured,
        surface_content=SimpleNamespace(slot_heading_text=()))
    slot = SlotPlacement("kicker-slot", "heading.kicker", Rect(Decimal(0), Decimal(0), Decimal(100), Decimal(40)))

    completed = complete_slot_headings(request=request, slots={"heading.kicker": slot},
                                       decisions={"kicker-slot": decision})
    assert completed.text == ()
    assert completed.reserved("heading.kicker") == 0
    assert completed.diagnostics == ("I_LAYOUT_SLOT_HEADING_OMITTED:kicker-slot:no-content",)
