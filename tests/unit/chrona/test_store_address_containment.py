"""Store address containment (#710).

Every rejection below is decided by `PurePosixPath` and `PureWindowsPath` inside
`chrona.core.store_address`, never by the host path flavour, so these tests mean the
same thing on Linux, macOS and Windows. The only host-dependent vector is a symlink,
which skips where the OS refuses to create one.
"""
from __future__ import annotations

import json
import os
from hashlib import sha256
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest
import yaml

from chrona.commands.actual_commands import LocalActualStore
from chrona.core.ports import SnapshotReadError
from chrona.core.store_address import (
    StoreAddressError, _has_anchor, _has_bad_segment, _has_forbidden_character,
    check_store_address, check_store_segment, resolve_store_address,
)
from chrona.core.identity import content_identity
from chrona.operational.authoring_commands import OperationalResourceError, _recover_incomplete_aggregate, _transaction_marker
from chrona.operational.command_engine import apply_actual_command
from chrona.operational.authoring_commands import _relative as _operational_relative
from chrona.presentation.model.closure import ClosureError, _declared_child, _safe_icon_address
from chrona.usecases.authoring_materialization import _child as _authoring_child, _relative as _authoring_relative
from chrona.presentation.model.font_resources import FontResourceError, resolve_font_resource
from chrona.presentation.model.theme_inheritance import ThemeInheritanceError, _safe_relative
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.storage.snapshot_paths import snapshot_directory
from chrona.storage.snapshots import LocalBaselineRegistry
from chrona.usecases.materialize import _inside, _package_resource

REPO = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())

# The owner's row-3 vectors (both spellings of the double backslash), then the rest of the family.
OWNER_VECTORS = [
    "C:/x", "C:x", "\\\\server\\share\\x", "a\x00b", "a\nb", "a\\b", "a\\\\b", "./a", "a/../b",
]
OTHER_VECTORS = [
    "", ".", "..", "...", "a/.../b", ". ", "/x", "//srv/share/x", "\\x", "C:\\x", "a:b", "a/C:/x",
    "a//b", "a/", "a/./b", "a/..", "../a", "a\tb", "a\x7fb", "a\x85b", "a\rb", "a\n", "\na", "snapshots/..\\..\\x.yaml",
    # The schema's `storeAddress` character rule (#731): a space, a trailing-space segment, a non-ASCII letter, `+`.
    "a b", "a /b", "a/b ", "é", "計画.yaml", "a+b",
]
REJECTED = OWNER_VECTORS + OTHER_VECTORS
ACCEPTED = [
    "a", "project.yaml", "resources/project.yaml", "layouts/base.yaml", "font_metrics/acme-regular.json",
    "icons/sample.png", "snapshots/baseline-q2.yaml", "a.b/c-d_e", "a/.hidden", "x/y.z.w", "v1..2/a", "a-b/c",
]


def _ids(values):
    return [repr(value) for value in values]


# --------------------------------------------------------------------------------------------
# The pure decision
# --------------------------------------------------------------------------------------------

@pytest.mark.parametrize("address", REJECTED, ids=_ids(REJECTED))
def test_check_store_address_refuses_on_every_os(address):
    with pytest.raises(StoreAddressError) as error:
        check_store_address(address)
    assert error.value.kind == "syntax"


@pytest.mark.parametrize("address", [None, 3, b"a", ["a"]])
def test_check_store_address_refuses_a_non_string(address):
    with pytest.raises(StoreAddressError):
        check_store_address(address)


@pytest.mark.parametrize("address", ACCEPTED, ids=_ids(ACCEPTED))
def test_check_store_address_accepts_legitimate_addresses(address):
    assert check_store_address(address) == tuple(address.split("/"))


def test_the_decision_does_not_depend_on_the_host_path_flavour():
    # The drive and anchor forms are seen through both flavours: PurePosixPath alone cannot see a drive.
    assert PurePosixPath("C:/x").drive == "" and PureWindowsPath("C:/x").drive == "C:"
    assert PureWindowsPath("C:/store/rev") / "C:/Users/x/secret.yaml" == PureWindowsPath("C:/Users/x/secret.yaml")
    assert ".." in (PureWindowsPath("C:/store/rev") / "snapshots" / "..\\..\\x.yaml").parts
    for address in ("C:/x", "C:x", "\\\\server\\share\\x", "/x", "\\x"):
        with pytest.raises(StoreAddressError):
            check_store_address(address)


def test_each_syntax_guard_decides_on_its_own():
    """The guards overlap (a drive also has a colon), so each is pinned alone; breaking one fails here."""
    for address in ("a\\b", "a:b", "C:x", "a\x00b", "a\nb", "a\x7fb", "a\x85b"):
        assert _has_forbidden_character(address), address
    for address in ACCEPTED:
        assert not _has_forbidden_character(address), address
    # The anchor guard sees the path flavours, with the colon and backslash rules out of the way.
    for address in ("C:/x", "C:x", "\\\\server\\share\\x", "\\x", "/x", "//srv/share/x", "D:"):
        assert _has_anchor(address), address
    for address in ACCEPTED + ["a/b", "a/../b", "./a"]:
        assert not _has_anchor(address), address
    for segments in [("",), ("a", ""), ("a", "", "b"), (".",), ("..",), ("...",), ("a", ". "), ("a", " ")]:
        assert _has_bad_segment(segments), segments
    for segments in [("a",), ("a", ".hidden"), ("a..b",), ("a.",), ("..a",)]:
        assert not _has_bad_segment(segments), segments


def test_check_store_segment_accepts_one_segment_only():
    assert check_store_segment("supplier-observed") == "supplier-observed"
    for name in ("a/b", "../x", "", ".", "a\\b"):
        with pytest.raises(StoreAddressError):
            check_store_segment(name)


def test_every_committed_and_packaged_address_is_accepted():
    """Owner row 4, made permanent: only the named negative fixtures are refused."""
    negative_fixtures = {"conformance/revision-store/invalid-address.yaml"}
    roots = ("examples", "conformance", "src/chrona/resources", "docs/examples", "packages")
    seen, refused = 0, []

    def visit(value, where):
        nonlocal seen
        if isinstance(value, dict):
            for key, item in value.items():
                if key == "address" and isinstance(item, str):
                    seen += 1
                    try:
                        check_store_address(item)
                    except StoreAddressError:
                        refused.append((where, item))
                else:
                    visit(item, where)
        elif isinstance(value, list):
            for item in value:
                visit(item, where)

    for root in roots:
        for path in sorted((REPO / root).rglob("*")):
            if path.suffix not in {".yaml", ".yml", ".json"} or not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            if "address" not in text:
                continue
            documents = [json.loads(text)] if path.suffix == ".json" else list(yaml.safe_load_all(text))
            for document in documents:
                visit(document, path.relative_to(REPO).as_posix())
    assert seen > 300, "the survey must actually find the committed addresses"
    assert {where for where, _ in refused} == negative_fixtures, refused


# --------------------------------------------------------------------------------------------
# Containment
# --------------------------------------------------------------------------------------------

def _symlink(link: Path, target: Path) -> None:
    try:
        os.symlink(target, link, target_is_directory=True)
    except (OSError, NotImplementedError) as error:
        pytest.skip(f"this platform cannot create a symlink here ({error})")


def test_resolve_store_address_returns_the_resolved_path_inside_the_root(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "b.yaml").write_text("x: 1\n")
    assert resolve_store_address(tmp_path, "a/b.yaml") == (tmp_path / "a" / "b.yaml").resolve()
    assert resolve_store_address(tmp_path, "not/yet/there.yaml") == (tmp_path / "not" / "yet" / "there.yaml").resolve()


def test_resolve_store_address_refuses_the_root_itself_and_a_symlink_out_of_the_root(tmp_path):
    root, outside = tmp_path / "store", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "secret.yaml").write_text("secret: 1\n")
    _symlink(root / "link", outside)
    with pytest.raises(StoreAddressError) as error:
        resolve_store_address(root, "link/secret.yaml")
    assert error.value.kind == "containment"
    with pytest.raises(StoreAddressError) as error:
        resolve_store_address(root, "link")
    assert error.value.kind == "containment"


def test_resolve_store_address_refuses_a_link_back_to_the_root(tmp_path):
    root = tmp_path / "store"
    root.mkdir()
    _symlink(root / "self", root)
    with pytest.raises(StoreAddressError) as error:
        resolve_store_address(root, "self")
    assert error.value.kind == "containment"


def test_resolve_store_address_turns_an_os_failure_into_the_typed_error(tmp_path, monkeypatch):
    def broken(self, strict=False):
        raise OSError("boom")

    monkeypatch.setattr(Path, "resolve", broken)
    with pytest.raises(StoreAddressError) as error:
        resolve_store_address(tmp_path, "a/b.yaml")
    assert error.value.kind == "containment"


def test_resolve_store_address_with_a_revision_base_still_bounds_by_the_store_root(tmp_path):
    root = tmp_path / "store"
    (root / "revision-a").mkdir(parents=True)
    (root / "revision-b").mkdir()
    (root / "revision-b" / "x.yaml").write_text("x: 1\n")
    _symlink(root / "revision-a" / "sibling", root / "revision-b")
    # A link that stays inside the Store is allowed; containment is against the Store root.
    assert resolve_store_address(root / "revision-a", "sibling/x.yaml", root=root) == (root / "revision-b" / "x.yaml").resolve()
    outside = tmp_path / "outside"
    outside.mkdir()
    _symlink(root / "revision-a" / "escape", outside)
    with pytest.raises(StoreAddressError):
        resolve_store_address(root / "revision-a", "escape/x.yaml", root=root)


# --------------------------------------------------------------------------------------------
# LocalSnapshotReader (storage/revision_store.py)
# --------------------------------------------------------------------------------------------

def _store(tmp_path) -> tuple[Path, LocalSnapshotReader, dict]:
    root = tmp_path / "store"
    directory = snapshot_directory(root, "rev-1")
    (directory / "resources").mkdir(parents=True)
    payload = b"id: project\n"
    (directory / "resources" / "project.yaml").write_bytes(payload)
    (directory / "a-b").mkdir()
    (directory / "a-b" / "c.yaml").write_bytes(payload)
    reference = {"id": "project", "kind": "project", "store": {"provider": "local", "identity": "s"},
                 "address": "resources/project.yaml", "revision": {"token": "rev-1"},
                 "contentIdentity": "sha256:" + sha256(payload).hexdigest()}
    return root, LocalSnapshotReader(root, "s"), reference


@pytest.mark.parametrize("address", REJECTED, ids=_ids(REJECTED))
def test_snapshot_reader_refuses_with_the_existing_typed_error(tmp_path, address):
    _, reader, reference = _store(tmp_path)
    with pytest.raises(SnapshotReadError) as error:
        reader.read(reference | {"address": address})
    assert error.value.diagnostic_id == "E_IMMUTABLE_SNAPSHOT_REQUIRED"


@pytest.mark.parametrize("address", ["resources/project.yaml", "a-b/c.yaml"])
def test_snapshot_reader_still_reads_a_legitimate_address(tmp_path, address):
    _, reader, reference = _store(tmp_path)
    assert reader.read(reference | {"address": address}) == b"id: project\n"
    unpinned = {key: value for key, value in (reference | {"address": address}).items() if key != "contentIdentity"}
    # An omitted identity is refused by default (#723); the explicit opt-out still reads the address.
    opted_out = LocalSnapshotReader(reader.root, reader.identity, require_content_identity=False)
    assert opted_out.read(unpinned) == b"id: project\n"


def test_snapshot_reader_still_reports_a_missing_file_and_an_identity_mismatch(tmp_path):
    _, reader, reference = _store(tmp_path)
    with pytest.raises(SnapshotReadError) as error:
        reader.read(reference | {"address": "resources/absent.yaml"})
    assert error.value.diagnostic_id == "E_STORE_REFERENCE"
    with pytest.raises(SnapshotReadError) as error:
        reader.read(reference | {"contentIdentity": "sha256:" + "0" * 64})
    assert error.value.diagnostic_id == "E_CONTENT_IDENTITY"


def test_snapshot_reader_refuses_a_symlink_that_leaves_the_store(tmp_path):
    root, reader, reference = _store(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.yaml").write_text("secret: 1\n")
    _symlink(snapshot_directory(root, "rev-1") / "link", outside)
    without_identity = {key: value for key, value in reference.items() if key != "contentIdentity"}
    with pytest.raises(SnapshotReadError) as error:
        reader.read(without_identity | {"address": "link/secret.yaml"})
    assert error.value.diagnostic_id == "E_STORE_REFERENCE"


def test_snapshot_reader_maps_an_os_error_on_open_to_the_typed_error(tmp_path, monkeypatch):
    _, reader, reference = _store(tmp_path)

    def unreadable(self):
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "read_bytes", unreadable)
    with pytest.raises(SnapshotReadError) as error:
        reader.read(reference)
    assert error.value.diagnostic_id == "E_STORE_REFERENCE"


def test_baseline_read_maps_an_os_error_on_open_to_the_typed_error(tmp_path, monkeypatch):
    registry = LocalBaselineRegistry(tmp_path, "s")
    reference = registry.publish("baseline-a", _project_ref())

    def unreadable(self):
        raise PermissionError("denied")

    monkeypatch.setattr(Path, "read_bytes", unreadable)
    with pytest.raises(ValueError, match="E_BASELINE_REFERENCE"):
        registry.read(reference)


def test_snapshot_reader_never_leaks_an_os_error(tmp_path):
    _, reader, reference = _store(tmp_path)
    for address in ("resources", "a-b"):  # directories
        with pytest.raises(SnapshotReadError):
            reader.read(reference | {"address": address})
    for token in ("", None, "Draft"):
        with pytest.raises(SnapshotReadError):
            reader.read(reference | {"revision": {"token": token}})


# --------------------------------------------------------------------------------------------
# LocalBaselineRegistry (storage/snapshots.py): read and publish
# --------------------------------------------------------------------------------------------

def _project_ref():
    return {"id": "p", "kind": "project", "store": {"provider": "local", "identity": "s"}, "address": "p.yaml",
            "revision": {"token": "main"}}


@pytest.mark.parametrize("address", ["snapshots/" + value for value in REJECTED] + ["other/x.yaml", "C:/x", ""],
                         ids=lambda value: repr(value))
def test_baseline_read_refuses_with_the_existing_typed_error(tmp_path, address):
    registry = LocalBaselineRegistry(tmp_path, "s")
    reference = registry.publish("baseline-a", _project_ref())
    assert reference is not None
    with pytest.raises(ValueError, match="E_BASELINE_REFERENCE"):
        registry.read(reference | {"address": address})


def test_baseline_publish_and_read_still_work_for_a_legitimate_id(tmp_path):
    registry = LocalBaselineRegistry(tmp_path / "store", "s")
    reference = registry.publish("baseline-q2.v1", _project_ref())
    assert reference["address"] == "snapshots/baseline-q2.v1.yaml"
    assert registry.read(reference).startswith(b"body:")
    assert registry.publish("baseline-q2.v1", _project_ref()) is None  # still append-only


@pytest.mark.parametrize("snapshot_id", ["", ".", "..", "...", "a/b", "../x", "..\\..\\x", "a\\b", "C:x", "C:/x", "a:b", "a\x00b", "a\nb", "/x", None])
def test_baseline_publish_refuses_an_unsafe_id_and_writes_nothing(tmp_path, snapshot_id):
    store = tmp_path / "store"
    registry = LocalBaselineRegistry(store, "s")
    before = sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*"))
    assert registry.publish(snapshot_id, _project_ref()) is None
    assert sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*")) == before


def test_baseline_publish_and_read_refuse_a_registry_directory_that_is_a_symlink_out(tmp_path):
    store, outside = tmp_path / "store", tmp_path / "outside"
    store.mkdir()
    outside.mkdir()
    _symlink(store / "snapshots", outside)
    registry = LocalBaselineRegistry(store, "s")
    assert registry.publish("baseline-a", _project_ref()) is None
    assert list(outside.iterdir()) == []
    (outside / "x.yaml").write_text("x: 1\n")
    with pytest.raises(ValueError, match="E_BASELINE_REFERENCE"):
        registry.read({"store": {"provider": "local", "identity": "s"}, "address": "snapshots/x.yaml", "revision": {"token": "baseline:x"}})


# --------------------------------------------------------------------------------------------
# materialize, fonts, themes, icons, actual stores
# --------------------------------------------------------------------------------------------

@pytest.mark.parametrize("address", REJECTED, ids=_ids(REJECTED))
def test_materializer_paths_refuse(tmp_path, address):
    with pytest.raises(ValueError, match="E_MATERIALIZER_PATH"):
        _inside(tmp_path, address)
    with pytest.raises(ValueError, match="E_MATERIALIZER_PATH"):
        _package_resource(address)


def test_materializer_inside_refuses_a_symlink_out_and_keeps_legitimate_paths(tmp_path):
    root, outside = tmp_path / "example", tmp_path / "outside"
    (root / "contexts").mkdir(parents=True)
    outside.mkdir()
    _symlink(root / "link", outside)
    with pytest.raises(ValueError, match="E_MATERIALIZER_PATH"):
        _inside(root, "link/x.yaml")
    assert _inside(root, "contexts/a.yaml") == (root / "contexts" / "a.yaml").resolve()


@pytest.mark.parametrize("address", REJECTED, ids=_ids(REJECTED))
@pytest.mark.parametrize("locator", [{"provider": "context"}, {"provider": "package", "identity": "chrona.resources"}], ids=["context", "package"])
def test_font_locators_refuse(tmp_path, locator, address):
    with pytest.raises(FontResourceError):
        resolve_font_resource(locator | {"address": address}, asset_root=tmp_path)


def test_font_context_locator_refuses_a_symlink_out(tmp_path):
    root, outside = tmp_path / "example", tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "f.ttf").write_bytes(b"font")
    _symlink(root / "link", outside)
    with pytest.raises(FontResourceError):
        resolve_font_resource({"provider": "context", "address": "link/f.ttf"}, asset_root=root)
    (root / "fonts").mkdir()
    (root / "fonts" / "f.ttf").write_bytes(b"font")
    assert resolve_font_resource({"provider": "context", "address": "fonts/f.ttf"}, asset_root=root).name == "f.ttf"


@pytest.mark.parametrize("address", REJECTED, ids=_ids(REJECTED))
def test_theme_inheritance_and_icon_addresses_refuse(address):
    with pytest.raises(ThemeInheritanceError, match="E_THEME_INHERITANCE_PATH"):
        _safe_relative(address)
    assert _safe_icon_address(address) is False


@pytest.mark.parametrize("address", ACCEPTED, ids=_ids(ACCEPTED))
def test_theme_inheritance_and_icon_addresses_accept_legitimate(address):
    assert _safe_relative(address) == PurePosixPath(address)
    assert _safe_icon_address(address) is True


@pytest.mark.parametrize("address", REJECTED, ids=_ids(REJECTED))
def test_authoring_paths_refuse_on_every_os(tmp_path, address):
    with pytest.raises(ValueError, match="E_AUTHORING_MATERIALIZE_PATH"):
        _authoring_relative(address)
    with pytest.raises(ValueError, match="E_AUTHORING_MATERIALIZE_PATH"):
        _authoring_child(tmp_path, address)
    with pytest.raises(ClosureError, match="E_AUTHORING_PRESET_PATH"):
        _declared_child(tmp_path, address)
    assert _operational_relative(address) is False


def test_authoring_paths_refuse_a_symlink_out_and_keep_plain_relative_names(tmp_path):
    root, outside = tmp_path / "ws", tmp_path / "outside"
    (root / "presentation").mkdir(parents=True)
    outside.mkdir()
    (root / "presentation" / "view.yaml").write_text("a: 1\n")
    _symlink(root / "link", outside)
    with pytest.raises(ValueError, match="E_AUTHORING_MATERIALIZE_PATH"):
        _authoring_child(root.resolve(), "link/x.yaml")
    with pytest.raises(ClosureError, match="E_AUTHORING_PRESET_PATH"):
        _declared_child(root, "link/x.yaml")
    for name in ("presentation", "presentation/view.yaml", "out/deeper", "Out_1"):
        _authoring_relative(name)
        assert _operational_relative(name) is True
    assert _authoring_child(root.resolve(), "presentation/view.yaml") == (root / "presentation" / "view.yaml").resolve()
    assert _declared_child(root, "presentation/view.yaml") == (root / "presentation" / "view.yaml").resolve()


@pytest.mark.parametrize("actual_id", ["../x", "a/b", "..\\x", "C:x", "a\x00b", "", "."])
def test_actual_store_refuses_an_id_that_is_not_one_safe_segment(tmp_path, actual_id):
    with pytest.raises(ValueError, match="E_STORE_REFERENCE"):
        LocalActualStore(tmp_path, {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": actual_id, "body": {"observations": []}})
    assert not (tmp_path / "actual-tips").exists()


def test_actual_command_target_id_cannot_walk_out_of_the_tip_directory(tmp_path):
    root = tmp_path / "store"
    (root / "actual-tips").mkdir(parents=True)
    (tmp_path / "x.json").write_text('{"token": "actual:1", "counter": 1}')  # where `actual-tips/../../x.json` lands

    class Reader:
        roots = {("local", "s"): root}

        def read(self, reference):
            if reference["kind"] == "project":
                return b"project: {id: p}\nobjects: {}\n"
            return b"version: chrona/actual-set/v0.3\nkind: actual-set\nid: ../../x\nbody: {observations: []}\n"

    command = {"version": "chrona/command/v0.3", "commandId": "c1", "type": "resolveActualObservation",
               "target": {"id": "../../x", "kind": "actual-set", "store": {"provider": "local", "identity": "s"},
                          "address": "actuals/x.yaml", "revision": {"token": "actual:1"}},
               "baseRevision": "actual:1", "payload": {"observationId": "o", "projectObjectId": "p", "project": _project_ref()}}
    result = apply_actual_command(Reader(), command)
    assert result["status"] == "rejected"
    assert [row["code"] for row in result["diagnostics"]] == ["E_AUTOMATION_TARGET_CLOSURE"]
    assert "'../../x'" in result["diagnostics"][0]["message"]


@pytest.mark.parametrize("directory", ["C:/x", "C:x", "\\x", "/x", "a/../b", "..", "link"])
def test_aggregate_recovery_refuses_a_marker_directory_that_is_not_a_contained_name(tmp_path, directory):
    """The recovery path ends in `rmtree`, so the marker's `directory` is a document-supplied address."""
    (tmp_path / "ws").mkdir()
    workspace = tmp_path / "ws" / "workspace.yaml"
    workspace.write_text("id: w\n")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.yaml").write_text("keep: 1\n")
    if directory == "link":
        _symlink(tmp_path / "ws" / "link", outside)
    marker = _transaction_marker(workspace)
    marker.write_text(json.dumps({"workspaceIdentity": content_identity({"id": "w"}), "directory": directory, "resources": {}}))
    with pytest.raises(OperationalResourceError) as error:
        _recover_incomplete_aggregate(workspace)
    assert error.value.code == "E_AUTHORING_AGGREGATE_RECOVERY"
    assert str(error.value).startswith("E_AUTHORING_AGGREGATE_RECOVERY: ")
    assert "transaction marker '.workspace.yaml.authoring-transaction.json'" in error.value.detail
    assert "cannot be validated or recovered" in error.value.detail
    assert (outside / "keep.yaml").exists()
