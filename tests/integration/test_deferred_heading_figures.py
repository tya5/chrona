"""Defer only Layout-owned note counts; reject every unsupported early read (#1346)."""
import pytest

from chrona.usecases.render_review import RenderFailed, RenderRejected
from tests.integration.test_derived_figures import _parts, _source, _summary, _metric
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr

LATE = {"id": "notes", "kind": "count", "source": "placedNotes"}


def test_projection_never_passes_a_guessed_layout_count_to_core(tmp_path, monkeypatch):
    from chrona.usecases import render_review as usecase
    resolve = usecase.resolve_figures
    seen = []
    def observe(*args, **kwargs):
        seen.extend(args[0] if args else kwargs["specs"])
        assert kwargs["counts"].placed_notes is None
        return resolve(*args, **kwargs)
    monkeypatch.setattr(usecase, "resolve_figures", observe)
    parts = _parts(LATE, {"id": "items", "kind": "count", "source": "selected"}, slot=False)
    sr.render(tmp_path, _source(), presentation=parts)
    assert seen and {item.figure_id for item in seen} == {"items"}


def test_unavailable_date_figures_are_not_deferred_with_layout_counts(tmp_path):
    parts = _parts(LATE, {"id": "days", "kind": "daysUntil", "to": "asOf"}, slot=False)
    with pytest.raises(RenderRejected) as caught:
        sr.render(tmp_path, _source(), presentation=parts)
    assert {item.id for item in caught.value.diagnostics} == {"E_FIGURE_ASOF_MISSING"}


def test_summary_layout_count_read_is_rejected_at_its_actual_source_pointer(tmp_path):
    with pytest.raises(RenderFailed) as caught:
        sr.render(tmp_path, _source(), presentation=_parts(LATE), summary=_summary(_metric("notes")))
    assert caught.value.code == "E_FIGURE_LAYOUT_SCOPE"
    assert caught.value.source_ref == "/body/panels/0/metrics/0/source/figure"


@pytest.mark.parametrize("member", ["title", "heading"])
def test_annotation_kind_layout_count_read_is_rejected_before_layout(tmp_path, member):
    source = ak.project()
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    ak.with_kind_theme(parts)
    if member == "heading":
        parts["theme"]["body"]["roles"]["annotation-heading"] = dict(parts["theme"]["body"]["roles"]["annotation-kind-label"])
        parts["theme"]["body"]["colorBindings"]["annotation-heading.fill"] = "text"
    parts["view"]["body"]["figures"] = [LATE]
    parts["theme"]["body"]["annotationKinds"]["risk"][member] = "{figure:notes}"
    with pytest.raises(RenderFailed) as caught:
        sr.render(tmp_path, source, presentation=parts)
    assert caught.value.code == "E_FIGURE_LAYOUT_SCOPE"
    assert caught.value.source_ref == f"/body/annotationKinds/risk/{member}"
