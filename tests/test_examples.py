from pathlib import Path

import pytest

from chrona.scheduler import schedule
from chrona.validation import load_yaml, validate_project


EXAMPLES = Path(__file__).resolve().parents[1] / "timeline-design" / "docs" / "examples"
PROJECT_EXAMPLES = ("calendar.yaml", "controller-x.yaml", "dependencies.yaml", "minimal.yaml", "semiconductor.yaml")


@pytest.mark.parametrize("filename", PROJECT_EXAMPLES)
def test_canonical_project_example_validates_and_schedules(filename):
    project = load_yaml(EXAMPLES / filename)
    assert validate_project(project) == [], filename
    assert schedule(project).ok, filename
