"""Generic object-reference diagnostics survive the public Core/render entrypoints (#344)."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from chrona.core.validation import validate_project
from chrona.extensions.profiles import PACKAGE_ID, validate_profiles
from chrona.scheduling.scheduler import schedule
from chrona.usecases import render_review


PACKAGE = {
    "version": "chrona/profile/v0.3",
    "packageId": "acme-reference",
    "contentIdentity": "sha256:" + "1" * 64,
    "requires": {"projectFormat": "timeline/v0.7"},
    "profiles": {
        "acme-reference.work": {
            "extends": "task",
            "fields": {
                "owner": {"type": "objectReference", "targetProfiles": ["acme-reference.team"]},
                "reviewers": {"type": "objectReference", "targetProfiles": ["acme-reference.team"], "cardinality": "many"},
            },
        },
        "acme-reference.team": {"extends": "entity"},
        "acme-reference.other": {"extends": "entity"},
    },
}

IDP_PACKAGE = {
    "version": "chrona/profile/v0.3",
    "packageId": PACKAGE_ID,
    "contentIdentity": "sha256:" + "2" * 64,
    "requires": {"projectFormat": "timeline/v0.7"},
    "profiles": {
        "implementation-delivery.work-item": {
            "extends": "task",
            "fields": {
                "assignees": {"type": "objectReference", "cardinality": "many",
                              "targetProfiles": ["implementation-delivery.person", "implementation-delivery.team"]},
                "workflowState": {"type": "enum", "cardinality": "one", "required": True,
                                  "enumValues": ["planned", "active", "blocked", "completed", "cancelled"]},
                "reuseClassification": {"type": "enum", "cardinality": "one", "required": True,
                                        "enumValues": ["core", "shared-service", "adapter", "experimental"]},
            },
        },
        "implementation-delivery.delivery-gate": {"extends": "milestone"},
        "implementation-delivery.person": {"extends": "entity"},
        "implementation-delivery.team": {"extends": "entity"},
    },
}


def _project(*, owner="team-a", reviewers=None):
    return {
        "version": "timeline/v0.7",
        "project": {"id": "object-reference-test"},
        "extensions": [{"packageId": "acme-reference", "path": "extensions/acme-reference.yaml",
                        "revision": "git:" + "1" * 40}],
        "entities": {"team-a": {"type": "acme-reference.team", "title": "Team A"}},
        "objects": {
            "work": {
                "type": "acme-reference.work",
                "title": "Work",
                "schedule": {"mode": "fixed-span", "start": "2026-10-01", "end": "2026-10-03"},
                "fields": {"owner": owner, "reviewers": ["team-a"] if reviewers is None else reviewers},
            },
            "other": {
                "type": "acme-reference.other",
                "title": "Other",
                "schedule": {"mode": "fixed-span", "start": "2026-10-03", "end": "2026-10-05"},
            },
        },
    }


class _RenderScheduler:
    def schedule(self, project, *, extension_diagnostics=()):
        return schedule(project, extension_diagnostics=extension_diagnostics)


class _ReachedProjection(Exception):
    pass


@pytest.mark.parametrize(("project", "pointer"), [
    (_project(owner="missing"), "/objects/work/fields/owner"),
    (_project(owner="other"), "/objects/work/fields/owner"),
    (_project(reviewers="team-a"), "/objects/work/fields/reviewers"),
    (_project(reviewers=["team-a", "missing"]), "/objects/work/fields/reviewers/1"),
])
def test_reference_failures_keep_the_same_pointer_through_validate_schedule_and_render(project, pointer):
    package = deepcopy(PACKAGE)
    manifests = {"acme-reference": package}
    profile_diagnostics = validate_profiles(project, manifests)
    expected = [("E_PROFILE_FIELD_TYPE", pointer)]
    assert [(item.id, item.path) for item in profile_diagnostics] == expected

    core_diagnostics = validate_project(project, extension_diagnostics=profile_diagnostics)
    assert [(item.id, item.path) for item in core_diagnostics if item.id == "E_PROFILE_FIELD_TYPE"] == expected

    scheduled = schedule(project, extension_diagnostics=profile_diagnostics)
    assert not scheduled.ok
    assert [(item.id, item.path) for item in scheduled.diagnostics] == expected

    with pytest.raises(render_review.RenderRejected) as caught:
        render_review._project_review(project, None, None, manifests, _RenderScheduler())
    assert [(item.id, item.path) for item in caught.value.diagnostics] == expected


def test_valid_reference_passes_validate_schedule_and_render_source_closure(monkeypatch):
    project = _project()
    manifests = {"acme-reference": deepcopy(PACKAGE)}
    diagnostics = validate_profiles(project, manifests)
    assert diagnostics == []
    assert validate_project(project, extension_diagnostics=diagnostics) == []
    assert schedule(project, extension_diagnostics=diagnostics).ok

    class _Closure:
        context = SimpleNamespace(forecast=False, environment=SimpleNamespace(locale="en-US"))
        actual_set = None
        snapshot_project = None
        profile_packages = ()

    view = SimpleNamespace(
        comparison=SimpleNamespace(baseline="planned", scenario_id=None),
        rows=SimpleNamespace(items=()),
        wording=None,
    )

    def reached_projection(*_args, **_kwargs):
        raise _ReachedProjection

    monkeypatch.setattr(render_review, "build_review_projection", reached_projection)
    with pytest.raises(_ReachedProjection):
        render_review._project_review(project, view, _Closure(), manifests, _RenderScheduler())


def _idp_shared_id_project(*, include_actor_entity=True):
    return {
        "version": "timeline/v0.7",
        "project": {"id": "idp-shared-id"},
        "extensions": [{"packageId": PACKAGE_ID, "resource": deepcopy(IDP_PACKAGE)}],
        "entities": ({"actor": {"type": "implementation-delivery.person", "title": "Actor"}}
                     if include_actor_entity else {}),
        "objects": {
            "actor": {
                "type": "implementation-delivery.person", "title": "Scheduled object",
                "schedule": {"mode": "fixed-span", "start": "2026-10-01", "end": "2026-10-02"},
            },
            "work": {
                "type": "implementation-delivery.work-item",
                "schedule": {"mode": "fixed-span", "start": "2026-10-02", "end": "2026-10-03"},
                "fields": {"assignees": ["actor"], "workflowState": "planned",
                           "reuseClassification": "core"},
            },
        },
    }


def test_idp_assignee_remains_valid_when_same_id_is_an_allowed_profile_object():
    project = _idp_shared_id_project()
    manifests = {PACKAGE_ID: deepcopy(IDP_PACKAGE)}

    profile_diagnostics = validate_profiles(project, manifests)
    assert profile_diagnostics == []
    assert validate_project(project, extension_diagnostics=profile_diagnostics) == []
    assert schedule(project, extension_diagnostics=profile_diagnostics).ok


def test_idp_assignee_still_rejects_actor_profile_object_without_entity():
    project = _idp_shared_id_project(include_actor_entity=False)
    diagnostics = validate_profiles(project, {PACKAGE_ID: deepcopy(IDP_PACKAGE)})

    assert [(item.id, item.path) for item in diagnostics] == [
        ("IDP-PROFILE-003", "/objects/work/fields/assignees"),
    ]


def _messages(project):
    return [item.message for item in validate_profiles(project, {"acme-reference": deepcopy(PACKAGE)})]


def test_missing_reference_names_value_field_constraint_and_nearest_ids():
    project = _project(owner="team-aa")
    for extra in ("team-b", "team-ab", "unrelated-long-name"):
        project["entities"][extra] = {"type": "acme-reference.team", "title": extra}
    project["entities"]["other-entity"] = {"type": "acme-reference.other", "title": "Other"}
    (message,) = _messages(project)
    assert message == ("owner must name one object or entity of profile ['acme-reference.team']; "
                       "'team-aa' is not a declared id; nearest ids: team-a, team-ab, team-b")


def test_nearest_ids_are_capped_at_three_and_skip_far_and_wrong_profile_ids():
    project = _project(owner="team-x")
    for extra in ("team-b", "team-c", "team-d"):
        project["entities"][extra] = {"type": "acme-reference.team", "title": extra}
    project["entities"]["team-z"] = {"type": "acme-reference.other", "title": "wrong profile"}
    (message,) = _messages(project)
    assert message.endswith("nearest ids: team-a, team-b, team-c")
    far = _project(owner="completely-different")
    (message,) = _messages(far)
    assert "nearest" not in message and "'completely-different' is not a declared id" in message


def test_wrong_profile_reference_says_the_constraint_is_not_met():
    (message,) = _messages(_project(owner="other"))
    assert "'other' does not satisfy the profile constraint" in message


def test_non_string_reference_reports_the_found_value():
    (message,) = _messages(_project(owner=7))
    assert message.endswith("found 7, which is not a non-empty id")
