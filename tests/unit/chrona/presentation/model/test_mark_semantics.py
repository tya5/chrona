import pytest

from chrona.presentation.model import mark_semantics
from chrona.presentation.model.semantic_registry import SemanticBinding


@pytest.mark.parametrize(("logical", "shape", "gate", "expected"), (
    ("planned", "span", False, "planned"),
    ("planned", "span", True, "planned"),
    ("planned", "point", False, "planned"),
    ("planned", "point", True, "gate"),
    ("forecast", "point", False, "forecast"),
    ("forecast", "point", True, "forecast"),
    ("actual", "point", True, "actual"),
    ("snapshot", "point", True, "snapshot"),
    ("missing-actual", "span", False, "missingActual"),
    ("missing-actual", "span", True, "missingActual"),
    ("gate", "point", True, "gate"),
))
def test_canonical_mark_semantic_preserves_existing_host_bindings(logical, shape, gate, expected):
    assert mark_semantics.canonical_mark_semantic(logical, shape, gate_declared=gate) == expected


def test_unknown_logical_semantic_keeps_existing_unknown_error():
    with pytest.raises(ValueError, match="E_PRESENTATION_SEMANTIC_UNKNOWN:not-a-mark"):
        mark_semantics.canonical_mark_semantic("not-a-mark", "point", gate_declared=True)


def test_ambiguous_legacy_theme_role_alias_keeps_existing_unknown_error(monkeypatch):
    def binding(name):
        if name == "legacy-mark-role":
            raise ValueError("E_PRESENTATION_SEMANTIC_UNKNOWN:legacy-mark-role")
        return SemanticBinding(name, "mark", "planned", "planned", "shared-mark-role")

    monkeypatch.setattr(mark_semantics, "semantic_ids", lambda: ("first", "second"))
    monkeypatch.setattr(mark_semantics, "semantic_binding", binding)
    with pytest.raises(ValueError, match="E_PRESENTATION_SEMANTIC_UNKNOWN:legacy-mark-role"):
        mark_semantics.canonical_mark_semantic("legacy-mark-role", "span", gate_declared=False)
