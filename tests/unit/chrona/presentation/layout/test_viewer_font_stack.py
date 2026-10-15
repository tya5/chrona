"""Layout completes viewer alternatives without changing its measured face."""
from types import SimpleNamespace

import pytest

from chrona.presentation.layout.text import _resolved_family


@pytest.mark.parametrize("requested,selected,expected", [
    ("A, B, sans-serif", "A", "A, B, sans-serif"),
    ("A, B, sans-serif", "B", "B, A, sans-serif"),
    ("Missing, sans-serif", "Noto Sans", "Noto Sans, Missing, sans-serif"),
    ('"A Face", B, sans-serif', "A Face", '"A Face", B, sans-serif'),
    ('Missing, "A Face", sans-serif', "A Face", '"A Face", Missing, sans-serif'),
    ("Noto Sans, sans-serif", "Noto Sans", "Noto Sans, sans-serif"),
])
def test_completed_family_list_keeps_selected_face_first_and_remaining_order(requested, selected, expected):
    assert _resolved_family(requested, SimpleNamespace(family=selected)) == expected
