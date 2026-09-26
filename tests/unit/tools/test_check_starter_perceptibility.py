from copy import deepcopy

from tools import check_starter_perceptibility as gate


def test_real_bundled_starter_has_no_perceptibility_error(capsys):
    assert gate.main() == 0
    assert "Starter perceptibility: PASS (0 errors)" in capsys.readouterr().out


def test_starter_gate_fails_a_serialized_text_intersection(monkeypatch, capsys):
    scene = deepcopy(gate.starter_scene_document())
    text = [item for item in scene["surfaces"][0]["primitives"] if item["kind"] == "Text"]
    assert len(text) >= 2
    text[1]["bounds"] = dict(text[0]["bounds"])
    monkeypatch.setattr(gate, "starter_scene_document", lambda: scene)

    assert gate.main() == 1
    output = capsys.readouterr().out
    assert "E_SCENE_TEXT_INTERSECTION" in output
    assert "Starter perceptibility: FAIL" in output
