"""Real count-bound planning/composition and pure accepted Scene projection (#1346)."""
import pytest

from chrona.presentation.model.render_progress import RenderProgress, RenderProgressEvent
from tests.integration.test_annotation_list_status import _fixture
from tests.integration.test_slot_heading import HEADING, _by_id, _render
from tests.support import synthetic_review as sr


def _late(parts):
    parts["view"]["body"]["figures"] = [{"id": "notes", "kind": "count", "source": "placedNotes"}]
    parts["layout"]["viewDefaults"] = {"figureFormats": {"notes": {"form": "digits", "minimumDigits": 2}}}


def _capture(monkeypatch):
    from chrona.presentation import surface_pipeline as pipeline
    complete = pipeline.complete_surface_render_plan
    results = []
    def observe(*args, **kwargs):
        result = complete(*args, **kwargs)
        results.append(result)
        return result
    monkeypatch.setattr(pipeline, "complete_surface_render_plan", observe)
    return results


def test_completed_notes_flow_into_actual_slot_heading_scene_and_svg(tmp_path, monkeypatch):
    completed = _capture(monkeypatch)
    rendered = _render(tmp_path, heading={"template": "STATUS REPORTS : {figure:notes}"}, configure=_late)
    assert _by_id(rendered)[HEADING].text == "STATUS REPORTS : 03"
    assert b">STATUS REPORTS : 03<" in rendered.artifact.content
    assert len(completed) == 1
    assert dict(completed[0].projection.figures) == {"notes": 3}
    assert [(t.count, t.outcome, t.actual) for t in completed[0].trials] == [(3, "accepted", 3)]


def test_unused_late_figures_resolve_after_one_ordinary_completion_without_changing_copy(tmp_path, monkeypatch):
    completed = _capture(monkeypatch)
    plain = _render(tmp_path, name="plain", heading={"text": "Notes"})
    late = _render(tmp_path, name="late", heading={"text": "Notes"}, configure=_late)
    assert late.surface.primitives == plain.surface.primitives
    assert late.artifact.content == plain.artifact.content
    assert dict(completed[-1].projection.figures) == {"notes": 3}
    assert len(completed[-1].trials) == 1 and completed[-1].trials[0].outcome == "ordinary"


def test_absent_optional_caption_is_not_an_active_late_read(tmp_path, monkeypatch):
    completed = _capture(monkeypatch)
    rendered = _render(tmp_path, heading={"template": "{figure:notes}"}, notes=False, configure=_late)
    assert HEADING not in _by_id(rendered)
    assert dict(completed[0].projection.figures) == {"notes": 0}
    assert len(completed[0].trials) == 1 and completed[0].trials[0].outcome == "ordinary"


def test_literal_override_does_not_activate_count_trials(tmp_path, monkeypatch):
    completed = _capture(monkeypatch)
    def configure(parts):
        _late(parts)
        parts["view"]["body"]["slotHeadingText"] = {"annotations": "Literal reports"}
    rendered = _render(tmp_path, heading={"template": "{figure:notes}"}, configure=configure)
    assert _by_id(rendered)[HEADING].text == "LITERAL REPORTS"
    assert len(completed[0].trials) == 1 and completed[0].trials[0].outcome == "ordinary"


def test_unclaimed_heading_part_is_not_an_active_late_read(tmp_path, monkeypatch):
    completed = _capture(monkeypatch)
    def configure(parts):
        _late(parts)
        parts["view"]["body"]["heading"] = {"title": "{figure:notes}"}
        parts["layout"]["root"]["children"] = [node for node in parts["layout"]["root"]["children"]
                                                if node.get("source") not in {"title", "heading"}]
    rendered = _render(tmp_path, configure=configure)
    assert "title" not in _by_id(rendered)
    assert dict(completed[0].projection.figures) == {"notes": 3}
    assert len(completed[0].trials) == 1 and completed[0].trials[0].outcome == "ordinary"


def test_mismatched_trial_is_discarded_and_progress_is_published_only_for_accepted_trial(tmp_path, monkeypatch):
    from chrona.presentation.layout import surface_annotations, surface_count_closure as closure
    from chrona.presentation.layout import surface_lane_route_plan as lane_plan, surface_route_label_plan as label_plan, surface_routes
    from chrona.presentation.model.info_diagnostics import RelationSearchBudgetHit
    completed = _capture(monkeypatch)
    source, parts = _fixture()
    source["relations"] = [{"id": f"r{index}", "type": "dependency", "lag": "0d",
        "from": {"object": f"gate-{index}", "endpoint": "at"},
        "to": {"object": f"gate-{index + 1}", "endpoint": "at"}} for index in range(3)]
    _late(parts)
    parts["layout"]["relationRouting"] = {"maxBends": 4, "maxDetourRatio": 2, "searchBudget": 1}
    parts["view"]["body"]["heading"] = {"title": "{figure:notes} completed notes"}
    sr.with_note_rail(parts, width=300)
    visibility = parts["view"]["body"]["visibility"]
    visibility["annotations"]["marker"] = "none"
    visibility.setdefault("fallback", {})["annotations"] = ["end", "suppress"]
    annotation = parts["view"]["body"]["annotations"][2]
    annotation.pop("candidates")
    annotation["placement"] = {"side": "end", "alignment": "center"}
    original_box = surface_annotations.project_annotation_box
    def suppress(annotation, *args, **kwargs):
        return None if annotation.annotation_id == "note-2" else original_box(annotation, *args, **kwargs)
    monkeypatch.setattr(surface_annotations, "project_annotation_box", suppress)
    compose, requests = closure.compose_surface_layout, []
    def observe(request, **kwargs):
        requests.append(request)
        request.progress.emit(RenderProgressEvent("layout", dict(request.projection.figures)["notes"], 4, "count-trial"))
        return compose(request, **kwargs)
    monkeypatch.setattr(closure, "compose_surface_layout", observe)
    routed = {4: [], 3: []}
    routes = surface_routes.compose_surface_routes
    def observe_routes(context):
        batch = routes(context)
        routed[dict(context.request.projection.figures)["notes"]].extend(batch.routing_info)
        return batch
    monkeypatch.setattr(lane_plan, "compose_surface_routes", observe_routes)
    monkeypatch.setattr(label_plan, "compose_surface_routes", observe_routes)
    events = []
    progress = RenderProgress(events.append)
    request_type = sr.RenderRequest
    monkeypatch.setattr(sr, "RenderRequest", lambda **kwargs: request_type(**kwargs, progress=progress))
    rendered = sr.render(tmp_path, source, presentation=parts, viewport=(2400, 1400))
    assert _by_id(rendered)["title"].text == "03 completed notes"
    assert b"03 completed notes" in rendered.artifact.content
    assert [(t.count, t.outcome, t.actual) for t in completed[0].trials] == [(4, "mismatch", 3), (3, "accepted", 3)]
    assert len(requests) == 2 and requests[0] is not requests[1]
    assert requests[0].mark_visibility_index is not None
    assert requests[0].mark_visibility_index is not requests[1].mark_visibility_index
    assert [e.completed for e in events if e.pass_name == "count-trial"] == [3]
    facts = [item for item in rendered.info_diagnostics if isinstance(item, RelationSearchBudgetHit)]
    assert routed[4] and routed[3]
    assert facts == routed[3]  # all executed accepted-pass facts, not both whole-layout trials
    assert len(facts) < len(routed[4]) + len(routed[3])


@pytest.mark.parametrize("late", [False, True])
def test_unused_checkpoint_precedes_completion_and_defers_only_active_count_planning(tmp_path, monkeypatch, late):
    from chrona.usecases import render_review as usecase
    from chrona.usecases.render_review import RenderFailed
    order = []
    prepare = usecase.prepare_surface_render_plan
    def observe(value):
        order.append("prepare")
        return prepare(value)
    monkeypatch.setattr(usecase, "prepare_surface_render_plan", observe)
    def unused(self):
        order.append("unused")
        return ("controlled-unread-resource",)
    monkeypatch.setattr(usecase.ClosureReadLedger, "unused", unused)
    def forbidden(*args, **kwargs):
        raise AssertionError("completion must not occur after unused-input rejection")
    monkeypatch.setattr(usecase, "compose_resolved_review_surface", forbidden)
    request_type = sr.RenderRequest
    monkeypatch.setattr(sr, "RenderRequest", lambda **kwargs: request_type(**kwargs, require_all_inputs_read=True))
    with pytest.raises(RenderFailed) as caught:
        _render(tmp_path, heading={"template": "{figure:notes}"} if late else {"text": "Notes"},
                configure=_late if late else None)
    assert caught.value.code == "E_CLOSURE_INPUT_UNUSED"
    assert order == (["unused"] if late else ["prepare", "unused"])
