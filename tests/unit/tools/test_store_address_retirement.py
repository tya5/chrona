"""The record of what the #710 version bumps leave open (slice S-D): the predecessors, their removal slices, and the loose forms.

No predecessor is retired here: retirement needs one release of dual support (Spec 56 section 3.2). This test pins the
state a later removal slice starts from, so it cannot drift unnoticed. Every verdict is decided from data.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

import yaml

from chrona.operational.resources import AUTOMATION_RESULT_SCHEMAS, COMMAND_SCHEMAS
from chrona.presentation.contracts.resources import RENDER_CONTEXT_VERSION, RENDER_CONTEXT_VERSIONS, _SCHEMAS
from chrona.presentation.layout.profile import LAYOUT_SCHEMAS, LAYOUT_VERSION
from chrona.storage.snapshots import SNAPSHOT_REF_VERSIONS
from tools.schema_inventory import load_inventory


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
SCHEMAS = ROOT / "schemas"
ENTRIES = {entry["file"]: entry for entry in load_inventory(SCHEMAS / "schema-inventory-v0.1.yaml")}

# predecessor file -> (successor file, removal slice, what the removal slice must delete)
RETIREMENTS: dict[str, tuple[str, str, str]] = {
    "snapshot-ref-v0.2.schema.yaml": (
        "snapshot-ref-v0.3.schema.yaml", "issue-710-snapshot-ref-v0.2-authoring-retirement",
        "only the authoring fallback in `SNAPSHOT_REF_VERSIONS`; the schema and the `_SCHEMAS` entry stay for reads of stored baselines"),
}
# Loose forms that remain on purpose, each with its owner and what ends it.
OPEN_LOOSE_USERS: dict[str, str] = {
    "src/chrona/extensions/profiles.py":
        "checks the `resourceReference` fields (evidence and artifacts) of a Project's profile objects against `revision-store-resource-ref-v0.1`; "
        "nothing opens such a reference afterwards, so v0.2 would refuse a document accepted today: an owner decision (#731 design B3). "
        "`extensions[].resource` of project-v0.7 is an unconstrained object with no address pattern, and the reader guard covers its read",
}


def _walk(node: Any) -> Iterator[Any]:
    yield node
    if isinstance(node, dict):
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def _references(name: str) -> set[str]:
    schema = yaml.safe_load((SCHEMAS / name).read_bytes())
    return {node["$ref"] for node in _walk(schema) if isinstance(node, dict) and isinstance(node.get("$ref"), str)}


def test_the_transitioning_predecessors_of_710_are_exactly_the_recorded_ones():
    found = {name: entry for name, entry in ENTRIES.items()
             if entry["state"] == "transitioning" and str(entry.get("removalSlice", "")).startswith("issue-710-")}
    assert set(found) == set(RETIREMENTS)
    for name, (successor, slice_name, _) in RETIREMENTS.items():
        assert found[name]["successor"] == successor and found[name]["removalSlice"] == slice_name
        assert ENTRIES[successor]["state"] == "live" and ENTRIES[successor]["kind"] == found[name]["kind"]
        assert (SCHEMAS / name).is_file(), "a predecessor is retired only in its removal slice"


def test_every_predecessor_is_still_registered_in_the_reader_that_selects_it():
    """The removal slice deletes exactly these registrations; until then each predecessor is read."""
    registered = set(_SCHEMAS.values()) | set(LAYOUT_SCHEMAS.values()) | set(COMMAND_SCHEMAS.values()) \
        | set(AUTOMATION_RESULT_SCHEMAS.values()) | {schema for _, schema in SNAPSHOT_REF_VERSIONS}
    for name, (successor, _, _) in RETIREMENTS.items():
        assert name in registered and successor in registered, name


def test_a_retired_predecessor_is_unregistered_and_an_unsupported_version_to_every_reader():
    """Layout Profile v0.9 (C1), Render Context v0.16 (C2), Command Request v0.2 (C3) and Automation Result v0.1 (C4).
    The archive test already proves each file is out of
    `schemas/` and the inventory and unnamed; here the readers refuse the version and the kind has one live schema."""
    assert set(LAYOUT_SCHEMAS) == {LAYOUT_VERSION} == {"chrona/layout-profile/v0.10"}
    assert ("layout-profile", "chrona/layout-profile/v0.9") not in _SCHEMAS
    assert [name for name, entry in ENTRIES.items() if entry["kind"] == "layout-profile"] == ["layout-profile-v0.10.schema.yaml"]
    assert RENDER_CONTEXT_VERSIONS == ("chrona/render-context/v0.17",) and RENDER_CONTEXT_VERSION == RENDER_CONTEXT_VERSIONS[0]
    assert ("render-context", "chrona/render-context/v0.16") not in _SCHEMAS
    assert [name for name, entry in ENTRIES.items() if entry["kind"] == "render-context"] == ["render-context-v0.17.schema.yaml"]
    # Command Request v0.2 (C3): the CLI registers v0.3 only.
    assert set(COMMAND_SCHEMAS) == {"chrona/command/v0.3"}
    assert [name for name, entry in ENTRIES.items() if entry["kind"] == "command-request"] == ["command-request-v0.3.schema.yaml"]
    # Automation Result v0.1 (C4): one registered version, one live schema.
    assert set(AUTOMATION_RESULT_SCHEMAS) == {"chrona/automation-result/v0.2"}
    assert [name for name, entry in ENTRIES.items() if entry["kind"] == "automation-result"] == ["automation-result-v0.2.schema.yaml"]


def test_the_snapshot_ref_predecessor_is_the_one_that_is_never_retired_for_reads():
    assert "snapshot-ref-v0.2.schema.yaml" in _SCHEMAS.values()
    assert "authoring" in RETIREMENTS["snapshot-ref-v0.2.schema.yaml"][1]
    assert "stay for reads" in RETIREMENTS["snapshot-ref-v0.2.schema.yaml"][2]


def test_no_live_schema_references_the_loose_address_definitions():
    live = [name for name, entry in ENTRIES.items() if entry["state"] == "live"]
    for name in live:
        for reference in _references(name):
            assert not reference.endswith(("#/$defs/relativeAddress", "#/$defs/relativeAddressDotTolerant")), (name, reference)
    # Nothing references them any more (the last users, Layout Profile v0.9 and Render Context v0.16, are retired), so they
    # could be dropped with a new `common` part version; until then they stay frozen and unedited.
    transitioning = [name for name, entry in ENTRIES.items() if entry["state"] == "transitioning"]
    users = {name for name in transitioning if any(ref.endswith(("#/$defs/relativeAddress", "#/$defs/relativeAddressDotTolerant"))
                                                    for ref in _references(name))}
    assert users == set()


def test_no_live_kind_references_revision_store_v0_1_and_the_part_has_only_the_recorded_users():
    v1 = "urn:chrona:revision-store-resource-ref-v0.1"
    live_users = {name for name, entry in ENTRIES.items() if entry["state"] == "live"
                  and any(ref.partition("#")[0] == v1 for ref in _references(name))}
    assert live_users == set(), "no live schema names v0.1: every kind moved to v0.2 (the vocabulary part never referenced it)"
    in_source = {path.relative_to(ROOT).as_posix() for path in (ROOT / "src").rglob("*.py")
                 if "revision-store-resource-ref-v0.1" in path.read_text(encoding="utf-8")}
    assert in_source == {"src/chrona/resources/__init__.py", *OPEN_LOOSE_USERS}, in_source
    transitioning_users = {name for name, entry in ENTRIES.items() if entry["state"] == "transitioning"
                           and any(ref.partition("#")[0] == v1 for ref in _references(name))}
    assert transitioning_users == {"snapshot-ref-v0.2.schema.yaml"}


def test_the_frozen_loose_definitions_say_they_are_frozen():
    defs = yaml.safe_load((SCHEMAS / "common-v0.1.schema.yaml").read_bytes())["$defs"]
    for name in ("relativeAddress", "relativeAddressDotTolerant"):
        assert "#710" in defs[name]["description"] and "storeAddress" in defs[name]["description"], name
