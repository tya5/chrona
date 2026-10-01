import pytest

from tools.vocabulary_inventory import VocabularyEntry, VocabularyInventoryError, declared_values, render, validate


def _schema(tmp_path, values=("one", "two")):
    (tmp_path / "schemas").mkdir()
    (tmp_path / "schemas" / "sample.yaml").write_text(
        "properties:\n  value:\n    enum: [" + ", ".join(values) + "]\n", encoding="utf-8"
    )


def _entry(*, accepted=("one", "two"), disposition="finite"):
    return VocabularyEntry("schemas/sample.yaml", "/properties/value", "chrona.sample.owner", disposition, accepted,
                           "intentionally open" if disposition == "open-ended" else None)


def test_finite_schema_vocabulary_must_not_exceed_owner_acceptance(tmp_path):
    _schema(tmp_path)
    with pytest.raises(VocabularyInventoryError, match="E_VOCABULARY_DECLARATION_WIDER:.*:two"):
        validate(tmp_path, (_entry(accepted=("one",)),))


def test_schema_pointer_and_string_vocabulary_are_required(tmp_path):
    _schema(tmp_path)
    with pytest.raises(VocabularyInventoryError, match="E_VOCABULARY_POINTER"):
        declared_values(tmp_path, VocabularyEntry("schemas/sample.yaml", "/missing", "owner", "finite", ("one",)))


def test_open_ended_entry_is_explicit_in_generated_report(tmp_path):
    _schema(tmp_path)
    report = render(tmp_path, (_entry(disposition="open-ended", accepted=()),))
    assert "open-ended: intentionally open" in report


def test_the_theme_marker_shape_policy_names_the_function_that_accepts_exactly_those_shapes():
    """#715: the policy owner of the marker `shape` set must really accept every value the policy lists, and no other."""
    from pathlib import Path

    from chrona.presentation.layout.relation_terminals import marker_geometry
    from tools.vocabulary_inventory import load_policy

    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    (entry,) = [item for item in load_policy(root / "conformance/declared-vocabulary-policy-v0.1.yaml")
                if item.schema == "schemas/theme-v0.13.schema.yaml" and item.pointer.endswith("/allOf/1/then/properties/value/properties/shape")]
    assert entry.owner == "chrona.presentation.layout.relation_terminals.marker_geometry"
    token = {"headLength": 8.0, "headWidth": 6.0, "attachmentOffset": 0.0}
    for shape in entry.accepted:
        marker_geometry({"shape": shape, **token})
    for shape in ("square", "diamond", "Triangle", ""):
        with pytest.raises(ValueError, match="E_THEME_TOKEN_TYPE"):
            marker_geometry({"shape": shape, **token})
