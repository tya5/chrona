import pytest

from chrona.presentation.actual_intake import intake_actual_observations


def test_intake_keeps_explicit_mapping_and_unmatched_source_identity():
    result = intake_actual_observations(
        "supplier",
        [
            {"externalKey": "build-7", "projectObjectId": "firmware", "actual": {"finish": "2026-04-18"}},
            {"externalKey": 42, "title": "Firmware", "actual": {"finish": "2026-04-20"}},
        ],
        {"firmware"},
    )

    assert result.observations[0] == {
        "id": "supplier:build-7",
        "sequence": 1,
        "projectObjectId": "firmware",
        "actual": {"finish": "2026-04-18"},
    }
    assert result.observations[1] == {
        "id": "supplier:42",
        "sequence": 2,
        "externalIdentity": {"system": "supplier", "key": 42},
        "alignment": "unmatched",
        "actual": {"finish": "2026-04-20"},
    }
    assert result.resolved == ("supplier:build-7",)
    assert result.unmatched == ("supplier:42",)
    assert result.diagnostics == ("E_ACTUAL_UNMATCHED",)


def test_intake_never_guesses_alignment_from_text_or_unknown_id():
    result = intake_actual_observations(
        "supplier",
        [{"externalKey": "42", "projectObjectId": "unknown", "title": "firmware", "actual": {"progress": 0.75}}],
        {"firmware"},
    )
    assert result.observations[0]["alignment"] == "unmatched"
    assert "projectObjectId" not in result.observations[0]


def test_intake_rejects_missing_or_duplicate_stable_external_identity():
    with pytest.raises(ValueError, match="externalKey"):
        intake_actual_observations("supplier", [{"actual": {"finish": "2026-04-20"}}], set())
    with pytest.raises(ValueError, match="duplicate external identity"):
        intake_actual_observations(
            "supplier",
            [{"externalKey": "42", "actual": {"finish": "2026-04-20"}}, {"externalKey": "42", "actual": {"finish": "2026-04-21"}}],
            set(),
        )
