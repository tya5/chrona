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
