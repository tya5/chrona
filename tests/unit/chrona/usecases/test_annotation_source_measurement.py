"""Natural measurement and placement share the same closed narrative input."""
from datetime import date
from types import SimpleNamespace

import pytest

from chrona.presentation.contracts.resources import ViewRowMode
from chrona.presentation.model.surface_content import AnnotationIntent, SummaryContent
from chrona.usecases.render_review import _annotation_source_input, _source_inputs
from tests.unit.chrona.presentation.layout.test_sources import theme


@pytest.mark.parametrize("number,prefix", [(None, ""), (7, "7. ")])
def test_annotation_measurement_uses_resolved_content_identity_and_number(number, prefix):
    view = SimpleNamespace(visibility=SimpleNamespace(annotations={"mode": "presentation"}),
                           annotations=({"id": "raw", "text": "wrong narrative"},))
    annotation = AnnotationIntent("closed", "note", {}, "end", "center", "Resolved Project note", number)
    source = _annotation_source_input(view, SimpleNamespace(annotations=(annotation,)),
                                      (), {}, theme())
    assert len(source.runs) == 1
    assert source.runs[0].content == prefix + "Resolved Project note"
    assert source.runs[0].source_ref == "annotation-text:closed"


def test_notes_measurement_excludes_consumed_project_narrative():
    view = SimpleNamespace(rows=SimpleNamespace(mode=ViewRowMode.AUTOMATIC), table_columns=())
    projection = SimpleNamespace(lane_rows=(), rows=(), items=(),
                                 window=(date(2027, 1, 1), date(2027, 2, 1)), network=None)
    content = SimpleNamespace(notes=(("remaining", "Unconsumed narrative"),), axis_tiers=(),
                              group_details=(), milestones=(), observation_columns=(), observation_rows=())
    sources = _source_inputs({"project": {"title": "Project"},
                             "annotations": {"consumed": {"text": "Consumed narrative"}}},
                            view, projection, SummaryContent(()), content=content)
    assert sources["notes"].lines == ("Unconsumed narrative",)
