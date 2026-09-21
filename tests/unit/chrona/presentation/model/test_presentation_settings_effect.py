"""The removed Settings product surface cannot silently return."""
from importlib.util import find_spec


def test_presentation_settings_runtime_is_absent():
    assert find_spec("chrona.presentation.model.settings") is None
