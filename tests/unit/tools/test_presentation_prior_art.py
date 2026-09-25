from tools.presentation_prior_art import render


def test_prior_art_matrix_is_deterministic_and_complete():
    matrix = render()
    assert matrix == render()
    assert "`decoration.row-band`" in matrix
    assert "deliberately-rejected" in matrix
    assert "Microsoft Project" in matrix
