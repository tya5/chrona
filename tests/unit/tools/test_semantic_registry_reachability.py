from pathlib import Path

from tools.check_semantic_registry_reachability import missing_semantic_ids, reachable_semantic_ids


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def test_every_semantic_registry_binding_has_a_layout_or_scene_lookup_path():
    assert missing_semantic_ids(_root()) == ()


def test_mark_icon_is_reachable_but_corpus_evidence_is_a_separate_question():
    assert "iconMark" in reachable_semantic_ids(_root())
