"""The read side of a configured Store, shared by the command line and the tool core (#812)."""
from __future__ import annotations

import pytest
import yaml

from chrona.core.ports import SnapshotReadError
from chrona.operational.baselines import compare_baseline
from chrona.operational.resources import parse_command
from chrona.operational.store_commands import open_store_reader, run_store_command
from chrona.operational.store_config import load_store_config
from chrona.operational.store_reads import compare_store_baseline, load_reference, snapshot_reader_for
from chrona.usecases.failure_report import StableFailure
from tests.support.store_workspace import PROJECT, STORE_IDENTITY, StoreWorkspace


def _config(work: StoreWorkspace, integrity: str):
    text = yaml.safe_load(work.config.read_text(encoding="utf-8"))
    text["stores"][0]["integrity"] = integrity
    work.config.write_text(yaml.safe_dump(text), encoding="utf-8")
    return load_store_config(str(work.config))


def _unpinned(reference: dict) -> dict:
    return {key: value for key, value in reference.items() if key != "contentIdentity"}


def _baseline(work: StoreWorkspace) -> dict:
    """A named baseline of ``project-r1`` published through the engine's own capture command."""
    command = parse_command(yaml.safe_dump(work.capture("capture-1", "q2")))
    result = run_store_command("command-apply", command, open_store_reader(work.config))
    assert result["status"] == "accepted", result
    return result["resultTarget"]


def _candidate(work: StoreWorkspace) -> dict:
    changed = {**PROJECT, "objects": {**PROJECT["objects"], "gate": {
        "type": "milestone", "schedule": {"mode": "fixed-point", "at": "2026-02-01"}}}}
    return work.write_resource("project-r2", "project.yaml", changed, "project", "p")


def test_the_reader_is_the_one_of_the_store_the_reference_names(tmp_path):
    work = StoreWorkspace(tmp_path)

    reader, root = snapshot_reader_for(load_store_config(str(work.config)), work.project_ref)

    assert root == work.store.resolve() and reader.identity == STORE_IDENTITY
    assert reader.read(work.project_ref) == (work.store / "revision-project-r1" / "project.yaml").read_bytes()


@pytest.mark.parametrize("reference", [
    {"store": {"provider": "local", "identity": "elsewhere"}}, {"store": "local"}, {}, [], None, "text",
])
def test_a_store_the_configuration_does_not_declare_is_a_typed_failure(tmp_path, reference):
    work = StoreWorkspace(tmp_path)

    with pytest.raises(StableFailure) as raised:
        snapshot_reader_for(load_store_config(str(work.config)), reference)

    assert (raised.value.code, raised.value.component, raised.value.exit_code) == ("E_STORE_CONFIG_REQUIRED", "store-config", 2)


def test_a_required_store_demands_a_content_identity_and_verifies_a_given_one(tmp_path):
    work = StoreWorkspace(tmp_path)
    reader, _ = snapshot_reader_for(_config(work, "required"), work.project_ref)

    with pytest.raises(SnapshotReadError) as missing:
        reader.read(_unpinned(work.project_ref))
    with pytest.raises(SnapshotReadError) as wrong:
        reader.read({**work.project_ref, "contentIdentity": "sha256:" + "0" * 64})

    assert (missing.value.diagnostic_id, wrong.value.diagnostic_id) == ("E_CONTENT_IDENTITY_REQUIRED", "E_CONTENT_IDENTITY")


def test_an_optional_store_reads_an_unpinned_reference_but_still_verifies_a_given_identity(tmp_path):
    work = StoreWorkspace(tmp_path)
    reader, _ = snapshot_reader_for(_config(work, "optional"), work.project_ref)

    assert reader.read(_unpinned(work.project_ref)) == reader.read(work.project_ref)
    with pytest.raises(SnapshotReadError) as wrong:
        reader.read({**work.project_ref, "contentIdentity": "sha256:" + "0" * 64})
    assert wrong.value.diagnostic_id == "E_CONTENT_IDENTITY"


def test_the_command_lines_explicit_opt_out_is_the_only_way_to_lower_a_required_store(tmp_path):
    work = StoreWorkspace(tmp_path)

    strict, _ = snapshot_reader_for(_config(work, "required"), work.project_ref)
    lowered, _ = snapshot_reader_for(_config(work, "required"), work.project_ref, allow_missing_content_identity=True)

    with pytest.raises(SnapshotReadError):
        strict.read(_unpinned(work.project_ref))
    assert lowered.read(_unpinned(work.project_ref))


def test_the_comparison_is_compare_baseline_over_one_reader(tmp_path):
    work = StoreWorkspace(tmp_path)
    baseline, candidate = _baseline(work), _candidate(work)
    config = load_store_config(str(work.config))

    result = compare_store_baseline(config, baseline, candidate)

    assert result == compare_baseline(config, baseline, config, candidate)
    assert (result["operation"], result["status"]) == ("baseline-compare", "accepted")
    assert result["comparison"]["changes"] == [{"kind": "object", "id": "gate", "change": "added"}]


def test_load_reference_reads_a_yaml_mapping(tmp_path):
    path = tmp_path / "ref.yaml"
    path.write_text(yaml.safe_dump({"id": "x", "kind": "project"}), encoding="utf-8")

    assert load_reference(path) == {"id": "x", "kind": "project"}
    assert load_reference(str(path)) == {"id": "x", "kind": "project"}
    with pytest.raises(OSError):
        load_reference(tmp_path / "missing.yaml")
