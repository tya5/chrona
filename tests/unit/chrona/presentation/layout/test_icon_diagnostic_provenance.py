"""Hosted Layout icon provenance follows its typed semantic owner, never its drawing ID."""
from decimal import Decimal
from types import SimpleNamespace

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_quality import IconPlacement, MarkPlacement, TextPlacement, VisualRequest
from chrona.presentation.layout.surface_visuals import place_mark_visuals, place_text_visuals
from chrona.presentation.layout.surface_annotations import _annotation_icon_subjects
from chrona.presentation.model.diagnostic_sources import DiagnosticSubject


class _Metric:
    def width(self, value, size, **_kwargs):
        return len(value) * size

    def cap_height_at(self, size):
        return size * .7


def _icon():
    return SimpleNamespace(icon_id="icon", kind="vector", content_identity="sha256:icon",
                           viewport=(10, 10), payload=(), alternative="owner icon")


def test_table_row_text_icon_uses_exact_table_subject_not_row_or_colliding_project_id():
    subject_item = SimpleNamespace(object_id="project-owner-42", item_id="row-42", title="Selected owner")
    row = SimpleNamespace(row_id="row-42", table_subject_id="row-42", items=(subject_item,))
    request = SimpleNamespace(
        visual_requests=(VisualRequest("title", (), ref="icon", side="leading"),),
        icon_assets={"icon": _icon()}, font_metrics=_Metric(),
        theme_tokens=SimpleNamespace(icon_ratios=lambda _role: (Decimal(1), Decimal("0.2"))),
        surface_content=SimpleNamespace(table_cells=(SimpleNamespace(object_id="row-42"),)),
        projection=SimpleNamespace(rows=(row,), items=(subject_item,)),
    )
    text = TextPlacement("title", "row-42", "Owner", Rect(Decimal(0), Decimal(0), Decimal(50), Decimal(12)),
                         "text", baseline=(0, 10), lines=("Owner",), font_family="Test", font_weight=400,
                         font_size=10, line_height=1.2, available_inline_start=0, available_inline_size=50)

    icon = place_text_visuals((text,), request).icons[0]

    assert icon.source_ref == "row-42"  # retained drawing/source identity
    assert icon.subjects == (DiagnosticSubject.project_object("project-owner-42", "Selected owner"),)
    assert icon.subjects[0].source_ref != icon.source_ref


def test_mark_icon_inherits_host_subject_and_ownerless_host_stays_unattributed():
    owner = DiagnosticSubject.project_object("project/17", "Exact mark owner")
    request = SimpleNamespace(
        visual_requests=(VisualRequest("mark", (("object", "project/17"), ("facet", "planned")), ref="icon"),),
        icon_assets={"icon": _icon()},
        theme_tokens=SimpleNamespace(icon_ratios=lambda _role: (Decimal("0.5"), Decimal("0.2"))),
    )
    host = MarkPlacement("planned:project/17", "project/17", Rect(Decimal(0), Decimal(0), Decimal(20), Decimal(10)),
                         (0, 5), (20, 5), subjects=(owner,))
    icon = place_mark_visuals((host,), request).icons[0]
    assert icon.subjects == (owner,)

    ownerless = MarkPlacement("planned:shared-source", "shared-source", host.bounds, host.start_port, host.end_port)
    request.visual_requests = (VisualRequest("mark", (("object", "shared-source"), ("facet", "planned")), ref="icon"),)
    ownerless_icon = place_mark_visuals((ownerless,), request).icons[0]
    assert ownerless_icon.subjects == ()


def test_annotation_icon_ownership_uses_normalized_subject_not_colliding_annotation_id():
    annotation = SimpleNamespace(annotation_id="same-id", subject_id="project-owner", subject="The project subject")
    assert _annotation_icon_subjects(annotation) == (
        DiagnosticSubject.project_object("project-owner", "The project subject"),
    )

    ownerless = SimpleNamespace(annotation_id="project-owner", subject_id=None, subject=None)
    assert _annotation_icon_subjects(ownerless) == ()
