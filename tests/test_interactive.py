from chrona.interactive import InteractiveScene, apply_scene_delta


def _scene():
    return InteractiveScene("eval-1", 1, {"a": {"title": "A"}}, {}, {})


def test_scene_delta_is_atomic_and_preserves_scene_on_mismatch():
    scene = _scene()
    delta = {"baseEvaluationFingerprint": "eval-1", "baseGeneration": 1, "targetEvaluationFingerprint": "eval-2", "targetGeneration": 2, "reason": "actual-observation-change", "replaceScope": None, "operations": [{"op": "upsert", "sceneId": "b", "node": {"title": "B"}}, {"op": "tokenUpdate", "token": "accent", "value": "red"}]}
    result = apply_scene_delta(scene, delta)
    assert result.status == "applied" and set(result.scene.nodes) == {"a", "b"}
    mismatch = apply_scene_delta(scene, delta | {"baseGeneration": 0})
    assert mismatch.status == "resync-required" and mismatch.scene is scene


def test_scene_delta_rejects_local_whole_scene_replacement():
    scene = _scene()
    result = apply_scene_delta(scene, {"baseEvaluationFingerprint": "eval-1", "baseGeneration": 1, "targetEvaluationFingerprint": "eval-2", "targetGeneration": 2, "reason": "project-change", "replaceScope": "scene", "operations": []})
    assert result.diagnostics == ("E_SCENE_DELTA_SCOPE",)
