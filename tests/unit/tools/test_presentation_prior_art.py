import pytest

import tools.presentation_prior_art as prior_art


def test_prior_art_matrix_is_deterministic_and_complete():
    matrix = prior_art.render()
    assert matrix == prior_art.render()
    assert "`decoration.row-band`" in matrix
    assert "deliberately-rejected" in matrix
    assert "[Microsoft Project Gantt]" in matrix
    assert "| Chrona |" in matrix
    assert "| Mermaid Gantt" not in matrix
    assert "unknown" in matrix


def test_prior_art_matrix_rejects_a_missing_capability_observation(monkeypatch):
    incomplete = dict(prior_art.OBSERVATIONS)
    incomplete.pop("mark.treatment")
    monkeypatch.setattr(prior_art, "OBSERVATIONS", incomplete)
    with pytest.raises(ValueError, match="E_PRIOR_ART_CAPABILITY_MISSING:mark.treatment"):
        prior_art.validate_observations()


def test_prior_art_matrix_rejects_an_incomplete_source_row(monkeypatch):
    incomplete = dict(prior_art.OBSERVATIONS)
    row = dict(incomplete["mark.treatment"])
    row.pop("mermaid")
    incomplete["mark.treatment"] = row
    monkeypatch.setattr(prior_art, "OBSERVATIONS", incomplete)
    with pytest.raises(ValueError, match="E_PRIOR_ART_OBSERVATION_MISSING:mark.treatment:mermaid"):
        prior_art.validate_observations()


def test_prior_art_matrix_requires_a_reason_for_not_applicable(monkeypatch):
    incomplete = dict(prior_art.OBSERVATIONS)
    row = dict(incomplete["mark.treatment"])
    row["mermaid"] = prior_art.SourceObservation(prior_art.Observation.NOT_APPLICABLE)
    incomplete["mark.treatment"] = row
    monkeypatch.setattr(prior_art, "OBSERVATIONS", incomplete)
    with pytest.raises(ValueError, match="E_PRIOR_ART_NOT_APPLICABLE_REASON:mark.treatment"):
        prior_art.validate_observations()
