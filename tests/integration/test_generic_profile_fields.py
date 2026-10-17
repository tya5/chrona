"""Generic typed-field validation for every resolved profile package (#344)."""
from copy import deepcopy

from chrona.extensions.profiles import validate_profiles

MANIFEST = {
    "version": "chrona/profile/v0.3", "packageId": "acme-risk",
    "contentIdentity": "sha256:" + "1" * 64, "requires": {"projectFormat": "timeline/v0.7"},
    "profiles": {"acme-risk.item": {"extends": "task", "fields": {
        "risk": {"type": "enum", "required": True, "enumValues": ["low", "high"]},
        "cost": {"type": "number"}, "reviewed": {"type": "boolean"}, "due": {"type": "date"},
        "tags": {"type": "string", "cardinality": "many"},
    }}},
}


def _project(**fields):
    return {"version": "timeline/v0.7", "project": {"id": "p"},
            "extensions": [{"packageId": "acme-risk"}],
            "objects": {"a": {"type": "acme-risk.item", "fields": {"risk": "low", **fields}}}}


def _run(project, manifest=MANIFEST):
    return [(d.id, d.path) for d in validate_profiles(project, {"acme-risk": manifest})]


def test_valid_typed_fields_pass():
    assert _run(_project(cost=1.5, reviewed=False, due="2026-10-17", tags=["x"])) == []
    assert _run(_project(cost=None)) == []  # explicit null on an optional field


def test_unknown_field_is_pointed():
    assert _run(_project(**{"acme.rsk": "x"})) == [("E_PROFILE_FIELD_UNKNOWN", "/objects/a/fields/acme.rsk")]
    assert _run(_project(owner="x")) == []  # bare legacy keys stay free-form


def test_wrong_types_are_pointed():
    for name, bad in (("cost", "5"), ("cost", True), ("reviewed", "yes"), ("due", "2026-13-01"), ("tags", "x")):
        assert _run(_project(**{name: bad})) == [("E_PROFILE_FIELD_TYPE", f"/objects/a/fields/{name}")], (name, bad)


def test_out_of_enum_is_pointed():
    assert _run(_project(risk="severe")) == [("E_PROFILE_FIELD_ENUM", "/objects/a/fields/risk")]


def test_required_absent_vs_null():
    absent = _project(); del absent["objects"]["a"]["fields"]["risk"]
    assert _run(absent) == [("E_PROFILE_FIELD_REQUIRED", "/objects/a/fields")]
    null = _project(); null["objects"]["a"]["fields"]["risk"] = None
    assert _run(null) == [("E_PROFILE_FIELD_REQUIRED", "/objects/a/fields/risk")]


def test_invalid_package_and_untouched_objects():
    broken = deepcopy(MANIFEST); broken["profiles"]["acme-risk.item"]["fields"]["risk"]["type"] = "bogus"
    assert _run(_project(), broken)[0][0] == "E_PROFILE_PACKAGE_INVALID"
    other = _project(); other["objects"]["a"]["type"] = "task"; other["objects"]["a"]["fields"] = {"anything": 1}
    assert _run(other) == []
    assert validate_profiles(_project(), None) == []
