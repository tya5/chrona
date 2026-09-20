from pathlib import Path

import pytest

from chrona.scheduling.scheduler import schedule
from chrona.core.validation import load_yaml, validate_project


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
EXAMPLES = REPO_ROOT / "conformance"
PROJECT_EXAMPLES = ("calendar.yaml", "controller-x.yaml", "dependencies.yaml", "minimal.yaml", "semiconductor.yaml")


@pytest.mark.parametrize("filename", PROJECT_EXAMPLES)
def test_canonical_project_example_validates_and_schedules(filename):
    project = load_yaml(EXAMPLES / filename)
    assert validate_project(project) == [], filename
    assert schedule(project).ok, filename
