from pathlib import Path

import tools.check_semantic_registry_reachability as reachability
from tools.check_semantic_registry_reachability import missing_semantic_ids, reachable_semantic_ids


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def test_every_semantic_registry_binding_has_a_layout_or_scene_lookup_path():
    assert missing_semantic_ids(_root()) == ()


def test_missing_identifiers_traverses_production_syntax_once(monkeypatch):
    calls = 0
    original = reachability.reachable_semantic_ids

    def counted(root):
        nonlocal calls
        calls += 1
        return original(root)

    monkeypatch.setattr(reachability, "reachable_semantic_ids", counted)

    assert reachability.missing_semantic_ids(_root()) == ()
    assert calls == 1


def test_mark_icon_is_reachable_but_corpus_evidence_is_a_separate_question():
    assert "iconMark" in reachable_semantic_ids(_root())


def test_table_state_semantics_are_reachable_from_the_normalized_content_producer():
    assert {"tableVarianceAhead", "tableVarianceOnTrack", "tableVarianceBehind", "missingActualCell"} <= reachable_semantic_ids(_root())
