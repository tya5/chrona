"""One completion receives the single actual annotation batch (#1841)."""
from chrona.presentation.layout import surface_annotations, surface_completion, surface_composer
from tests.integration.test_surface_annotation_phase_wiring import render_wiring_fixture


def test_completion_runs_once_after_annotations_with_every_batch(tmp_path, monkeypatch):
    trials, active = [], {}
    annotations = surface_annotations.place_annotations
    completion = surface_composer.complete_surface_layout

    def annotations_spy(context):
        trial = {"events": ["annotations"]}
        trials.append(trial)
        active["trial"] = trial
        trial["batch"] = annotations(context)
        return trial["batch"]

    def completion_spy(context):
        trial = active["trial"]
        trial["events"].append("completion")
        trial["context"] = context
        return completion(context)

    monkeypatch.setattr(surface_annotations, "place_annotations", annotations_spy)
    monkeypatch.setattr(surface_composer, "complete_surface_layout", completion_spy)
    render_wiring_fixture(tmp_path)
    assert len(trials) in {1, 2}
    assert all(trial["events"] == ["annotations", "completion"] for trial in trials)
    for trial in trials:
        context, batch = trial["context"], trial["batch"]
        assert isinstance(context, surface_completion.SurfaceCompletionContext)
        placed_ids = {item.placement_id for item in context.text} | {item.placement_id for item in context.shapes}
        assert {item.placement_id for item in batch.text} <= placed_ids
        assert {item.placement_id for item in batch.shapes} <= placed_ids


def test_the_composer_keeps_its_public_surface():
    assert surface_composer.SurfaceLayoutComposition is surface_completion.SurfaceLayoutComposition
    assert callable(surface_composer.compose_surface_layout)
    assert callable(surface_composer.timeline_content_block_requirement)
