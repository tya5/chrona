"""The runtime guard refuses exactly what the schema's `storeAddress` refuses (#731, item 4).

Every verdict is decided from data and the JSON Schema validator, never from the host path flavour, so the file means
the same on Linux, macOS and Windows. The two callers that join an identifier or an operator's file name (not an address)
use `charset="file-name"` and must keep their wider character set; both modes are pinned here, end to end.
"""
from __future__ import annotations

import itertools
from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from chrona.commands.actual_commands import LocalActualStore
from chrona.core.identity import content_identity
from chrona.core.store_address import (
    StoreAddressError, _has_foreign_segment, check_store_address, check_store_segment, resolve_store_address,
)
from chrona.operational.authoring_commands import (
    OperationalResourceError, _relative as _operational_relative, cas_write_authoring_aggregate,
)
from chrona.operational.command_engine import apply_actual_command
from chrona.operational.store_config import ConfiguredStoreReader
from chrona.resources import validator_for_schema
from chrona.storage.snapshot_paths import snapshot_directory

STORE_ADDRESS = validator_for_schema({"$ref": "urn:chrona:common-v0.1#/$defs/storeAddress"})
# One character from every class that matters: a letter, a digit, the three punctuation marks the grammar allows, the
# separator, the line break the old `$` patterns let through, a space, the characters that were already refused,
# a non-ASCII letter and a punctuation mark outside the set.
ALPHABET = ("a", "0", ".", "-", "_", "/", "\n", " ", ":", "\\", "\x00", "é", "+")


def _accepts(address: object, **options: object) -> bool:
    try:
        check_store_address(address, **options)
    except StoreAddressError:
        return False
    return True


def test_the_guard_accepts_exactly_what_the_schema_accepts_on_every_short_string():
    """Both directions over 30,941 strings (length 0 to 4): the guard is neither stricter nor weaker than `storeAddress`."""
    disagreements = [text for length in range(0, 5) for tuple_ in itertools.product(ALPHABET, repeat=length)
                     if STORE_ADDRESS.is_valid(text := "".join(tuple_)) is not _accepts(text)]
    assert disagreements == []


@pytest.mark.parametrize("address", [
    "a b", " a", "a ", "a /b", "a/ b", "a/b ", "é", "計画.yaml", "a/é", "a+b", "a%20b", "a;b", "a*b", "a?b", "a<b", "a>b", "a|b",
    'a"b', "a'b", "a@b", "a~b", "a#b", "a=b", "a,b", "a\u00a0b", "a\u200bb", "a\u2028b", "\ufeffa", "a\u0661b",
    "a/...", "a/.../b", "...", "a/..", "a/.", "a/", "/a", "a//b",
], ids=repr)
def test_the_guard_refuses_what_the_schema_refuses(address):
    assert not STORE_ADDRESS.is_valid(address)
    with pytest.raises(StoreAddressError) as error:
        check_store_address(address)
    assert error.value.kind == "syntax"


@pytest.mark.parametrize("address", [
    "a", ".hidden", "a..b", "a./b", "a/..b", "..a", "a.", "_a", "-a", "A_b-c.0/d", "snapshots/baseline-2027-06.yaml", "0", "a" * 300,
], ids=lambda value: repr(value)[:40])
def test_the_guard_accepts_what_the_schema_accepts(address):
    assert STORE_ADDRESS.is_valid(address)
    assert check_store_address(address) == tuple(address.split("/"))


def test_the_character_rule_decides_on_its_own():
    """The structural guards overlap with the character set; this one is pinned alone, so breaking it fails here."""
    for segments in [("a b",), ("é",), ("a", "b+c"), ("a\n",), ("a", " "), ("a ",), ("...",), ("a", "..."), (".",), ("..",), ("a", ""), ("",)]:
        assert _has_foreign_segment(segments), segments
    for segments in [("a",), ("a-b_c.d",), (".hidden",), ("a..b",), ("a.", "b."), ("0", "Z", "z")]:
        assert not _has_foreign_segment(segments), segments


def test_a_trailing_newline_is_not_an_address_in_either_mode():
    """The old `$` patterns accepted `a\\n`; the guard never did, and still does not, in any mode."""
    for charset in ("address", "file-name"):
        assert not _accepts("a\n", charset=charset)


# --------------------------------------------------------------------------------------------
# The file-name mode: the callers that join an identifier or a file name, not an address
# --------------------------------------------------------------------------------------------

WIDE_NAMES = ["my plan.yaml", "計画.yaml", "作業 1", "a b/c", "é", "plan (2).yaml", "a+b", "a ", " a", "a\u00a0b"]


@pytest.mark.parametrize("name", WIDE_NAMES, ids=repr)
def test_the_file_name_mode_keeps_the_wider_set_and_the_address_mode_refuses_it(name):
    assert check_store_address(name, charset="file-name") == tuple(name.split("/"))
    with pytest.raises(StoreAddressError):
        check_store_address(name)
    if "/" not in name:
        assert check_store_segment(name, charset="file-name") == name
        with pytest.raises(StoreAddressError):
            check_store_segment(name)


@pytest.mark.parametrize("name", [
    "a\\b", "a:b", "C:x", "C:/x", "\\\\server\\share\\x", "/x", "//srv/x", "", ".", "..", "...", ". ", "a/../b", "../x", "a//b", "a/",
    "a\x00b", "a\nb", "a\n", "a\tb", "a\x7fb", "a\x85b",
], ids=repr)
def test_the_file_name_mode_still_refuses_every_unsafe_form(name):
    with pytest.raises(StoreAddressError):
        check_store_address(name, charset="file-name")


def test_the_file_name_mode_is_still_one_segment_for_a_segment():
    for name in ("a/b", "../x", "a b/c"):
        with pytest.raises(StoreAddressError):
            check_store_segment(name, charset="file-name")


def test_resolve_takes_the_mode_and_still_checks_containment(tmp_path):
    assert resolve_store_address(tmp_path, "作業 1.json", charset="file-name") == (tmp_path / "作業 1.json").resolve()
    with pytest.raises(StoreAddressError):
        resolve_store_address(tmp_path, "作業 1.json")
    with pytest.raises(StoreAddressError):
        resolve_store_address(tmp_path, "../x", charset="file-name")


def test_the_operational_path_check_takes_the_mode():
    assert _operational_relative("計画.yaml", charset="file-name") is True
    assert _operational_relative("計画.yaml") is False
    assert _operational_relative("a:b.yaml", charset="file-name") is False
    assert _operational_relative("a\\b.yaml", charset="file-name") is False
    assert _operational_relative("presentation/view.yaml") is True


# --------------------------------------------------------------------------------------------
# End to end: the two file-name callers keep working, and an address-shaped resource name does not widen
# --------------------------------------------------------------------------------------------

def _workspace() -> dict:
    return {"version": "chrona/authoring-workspace/v0.1", "kind": "authoring-workspace", "id": "w", "body": {}}


@pytest.mark.parametrize("workspace_name", ["workspace.yaml", "my plan.yaml", "計画.yaml"])
def test_the_aggregate_writer_accepts_a_workspace_file_name_of_any_valid_kind(tmp_path, workspace_name):
    path = tmp_path / workspace_name
    workspace = _workspace()
    path.write_text(yaml.safe_dump(workspace), encoding="utf-8")
    candidates = {workspace_name: yaml.safe_dump(workspace).encode(), "presentation/view.yaml": b"view"}
    assert cas_write_authoring_aggregate(path, content_identity(workspace), candidates) == content_identity(workspace)
    assert (tmp_path / "presentation" / "view.yaml").read_bytes() == b"view"


@pytest.mark.parametrize("resource", ["presentation/view file.yaml", "présentation/view.yaml", "presentation/計画.yaml", "presentation/view+1.yaml"])
def test_the_aggregate_writer_holds_a_resource_name_to_the_address_rule(tmp_path, resource):
    path = tmp_path / "my plan.yaml"
    workspace = _workspace()
    path.write_text(yaml.safe_dump(workspace), encoding="utf-8")
    candidates = {path.name: yaml.safe_dump(workspace).encode(), resource: b"x"}
    with pytest.raises(OperationalResourceError) as error:
        cas_write_authoring_aggregate(path, content_identity(workspace), candidates)
    assert error.value.code == "E_AUTHORING_AGGREGATE_PATH"
    assert str(error.value).startswith("E_AUTHORING_AGGREGATE_PATH: ")
    assert "workspace 'my plan.yaml'" in error.value.detail
    assert "safe relative paths" in error.value.detail
    assert not (tmp_path / resource.split("/")[0]).exists()


@pytest.mark.parametrize("actual_id", ["作業 1", "a b", "plan (2)", "é"])
def test_the_actual_store_keeps_an_identifier_with_spaces_or_non_ascii(tmp_path, actual_id):
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": actual_id, "body": {"observations": []}}
    store = LocalActualStore(tmp_path, actual)
    revision, loaded = store.read()
    assert loaded == actual
    assert (tmp_path / "actual-tips" / f"{actual_id}.json").is_file()
    assert LocalActualStore(tmp_path, actual).read()[0] == revision  # reopened through the same tip


def _write(root: Path, token: str, address: str, value: dict, kind: str, identifier: str) -> dict:
    payload = yaml.safe_dump(value, sort_keys=True).encode()
    path = snapshot_directory(root, token) / address
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"id": identifier, "kind": kind, "store": {"provider": "local", "identity": "test"}, "address": address,
            "revision": {"token": token}, "contentIdentity": "sha256:" + sha256(payload).hexdigest()}


def test_the_command_engine_applies_to_an_actual_set_whose_id_is_not_address_shaped(tmp_path):
    """The tip file name follows the id; the pinned reference keeps its own, address-shaped, address."""
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "作業 1", "body": {"observations": []}}
    revision, _ = LocalActualStore(tmp_path, actual).read()
    target = _write(tmp_path, revision, "actuals/ws.yaml", actual, "actual-set", "作業 1")
    project = {"version": "timeline/v0.7", "project": {"id": "p"}, "extensions": [], "relations": [],
               "objects": {"firmware": {"type": "milestone", "schedule": {"mode": "fixed-point", "at": "2026-01-01"}}}}
    project_ref = _write(tmp_path, "project-r1", "project.yaml", project, "project", "p")
    batch = {"version": "chrona/actual-intake-batch/v0.2", "kind": "actual-intake-batch", "id": "batch",
             "body": {"source": {"system": "supplier", "contentIdentity": "sha256:" + "a" * 64},
                      "records": [{"externalKey": "42", "projectObjectId": "firmware", "actual": {"finish": "2026-01-02"}}]}}
    batch_ref = _write(tmp_path, "batch-r1", "batch.yaml", batch, "actual-intake-batch", "batch")
    reader = ConfiguredStoreReader({"stores": [{"provider": "local", "identity": "test", "root": str(tmp_path)}]})
    command = {"version": "chrona/command/v0.3", "commandId": "c1", "type": "applyActualIntakeBatch", "target": target,
               "baseRevision": revision, "expectedContentIdentity": target["contentIdentity"],
               "payload": {"batch": batch_ref, "project": project_ref}}
    result = apply_actual_command(reader, command)
    assert result["status"] == "accepted", result
    assert result["actualIntake"]["dispositions"] == ["inserted"]
