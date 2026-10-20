import pytest

from chrona.core.object_references import (
    ObjectReferenceCatalog,
    ObjectReferenceConstraint,
    ObjectReferenceError,
)


def _project():
    return {
        "project": {"id": "demo"},
        "entities": {
            "shared": {"type": "acme.team", "title": "Team A"},
            "blank": {"type": "acme.team", "title": "  "},
        },
        "objects": {
            "shared": {"type": "acme.work", "title": "Work A"},
            "task": {"type": "task", "title": "Task"},
        },
    }


def test_resolves_a_unique_bare_id_with_detached_namespaced_identity_and_title_fallback():
    project = _project()
    catalog = ObjectReferenceCatalog.from_project(project)
    project["entities"]["blank"]["title"] = "Changed after snapshot"

    target = catalog.resolve("blank", target_profiles=("acme.team",))
    assert target.identity == ("demo", "entities", "blank")
    assert target.display_title == "blank"
    assert target.profile_id == "acme.team"


def test_declared_target_profiles_filter_same_id_before_uniqueness():
    catalog = ObjectReferenceCatalog.from_project(_project())
    target = catalog.resolve("shared", target_profiles=("acme.team",))
    assert target.identity == ("demo", "entities", "shared")
    assert target.display_title == "Team A"

    target = catalog.resolve("shared", target_profiles=("acme.work",))
    assert target.identity == ("demo", "objects", "shared")


def test_omitted_constraint_is_unconstrained_but_requires_unique_target():
    catalog = ObjectReferenceCatalog.from_project(_project())
    with pytest.raises(ObjectReferenceError, match="ambiguous") as caught:
        catalog.resolve("shared")
    assert caught.value.reason == "ambiguous"
    assert catalog.resolve("task").identity == ("demo", "objects", "task")


def test_missing_incompatible_and_invalid_references_are_distinct():
    catalog = ObjectReferenceCatalog.from_project(_project())
    for value, profiles, reason in (
        ("missing", (), "missing"),
        ("task", ("acme.work",), "incompatible"),
        (None, (), "invalid"),
    ):
        with pytest.raises(ObjectReferenceError) as caught:
            catalog.resolve(value, target_profiles=profiles)
        assert caught.value.reason == reason


def test_namespace_constraint_filters_same_profile_identity_without_changing_default_scope():
    project = _project()
    project["entities"]["same-profile"] = {"type": "acme.team", "title": "Entity"}
    project["objects"]["same-profile"] = {"type": "acme.team", "title": "Object"}
    catalog = ObjectReferenceCatalog.from_project(project)

    constraint = ObjectReferenceConstraint(
        target_profiles=("acme.team",), target_namespaces=("entities",),
    )
    assert catalog.resolve(
        "same-profile",
        target_profiles=constraint.target_profiles,
        target_namespaces=constraint.target_namespaces,
    ).identity == ("demo", "entities", "same-profile")
    with pytest.raises(ObjectReferenceError) as caught:
        catalog.resolve("same-profile", target_profiles=("acme.team",))
    assert caught.value.reason == "ambiguous"
