from copy import deepcopy
from pathlib import Path

import yaml

from chrona.commands import execute_set_typed_field, set_typed_field
from chrona.revision_store import MemoryRevisionStore
from chrona.scheduler import schedule
from chrona.validation import validate_project

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "timeline-design" / "docs" / "fixtures"


def _manifest():
    return {"implementation-delivery": yaml.safe_load((FIXTURES / "implementation-delivery-profile-v0.1.yaml").read_text())}


def _roadmap():
    project = yaml.safe_load((FIXTURES / "implementation-delivery-roadmap-v0.1.yaml").read_text())
    project.pop("expectedPlacements")
    return project


def test_resolved_delivery_profile_validates_and_schedules_through_core():
    project = _roadmap()
    assert validate_project(project, package_manifests=_manifest()) == []
    assert schedule(project, package_manifests=_manifest()).ok


def test_invalid_state_is_rejected_without_changing_project():
    project = _roadmap()
    original = deepcopy(project)
    result = set_typed_field(project, _manifest(), "idp-4", "workflowState", "done")
    assert result.status == "rejected"
    assert result.diagnostics == ("IDP-STATE-001",)
    assert project == original


def test_valid_typed_field_command_returns_a_new_candidate_only():
    project = _roadmap()
    result = set_typed_field(project, _manifest(), "idp-4", "workflowState", "active")
    assert result.status == "accepted"
    assert result.project is not project
    assert result.project["objects"]["idp-4"]["fields"]["workflowState"] == "active"
    assert project["objects"]["idp-4"]["fields"]["workflowState"] == "planned"


def test_typed_field_command_uses_cas_and_creates_immutable_snapshot():
    store = MemoryRevisionStore(_roadmap())
    base = store.read()
    result = execute_set_typed_field(store, base.revision, _manifest(), "idp-4", "workflowState", "active")
    assert result.status == "accepted"
    assert result.result_revision and result.result_revision != base.revision
    assert store.read().project["objects"]["idp-4"]["fields"]["workflowState"] == "active"
    conflict = execute_set_typed_field(store, base.revision, _manifest(), "idp-4", "workflowState", "blocked")
    assert conflict.status == "rejected"
    assert conflict.diagnostics == ("E_CONFLICT",)
