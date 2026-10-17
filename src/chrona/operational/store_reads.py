"""The read side of a configured Store, shared by the command line and the agent tool core (#812).

``chrona render-review --store-config`` and ``chrona baseline-compare`` open a Store configuration and read immutable
references through it. This module owns the three steps both front ends take so that a second front end calls the same
code: loading a reference file, choosing the reader of the Store a reference names (with the integrity the configuration
declares), and comparing a named baseline with a candidate Project. ``open_store_reader`` of ``store_commands`` is still
the one way to open a workspace Store.

It writes nothing, prints nothing and exits nothing. No argument lowers integrity here: the only switch is the explicit
``allow_missing_content_identity`` of the command line, which the tool core never passes.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from chrona.core.validation import load_yaml
from chrona.operational.baselines import compare_baseline
from chrona.operational.store_config import ConfiguredStoreReader
from chrona.core.ports import SnapshotReadError
from chrona.storage.package_store import is_package_reference, read_package_reference
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.usecases.failure_report import StableFailure


def load_reference(path: str | Path) -> dict[str, Any]:
    """Load one resource-reference YAML file, as ``--context-reference`` and ``--baseline-reference`` do."""
    return load_yaml(path)


class PackageAwareReader(LocalSnapshotReader):
    """A local Store reader that also reads `package` references from the packaged store (#1342)."""

    def read(self, reference: dict[str, Any]) -> bytes:
        if is_package_reference(reference):
            return read_package_reference(reference)
        return super().read(reference)


class SharedDesignReader(PackageAwareReader):
    """The reader of the Context's own Store that also reads shared designs (#1342).

    A reference to the Context's Store is read as before. A reference to another Store the configuration declares is read
    from that Store under its own integrity; a `package` reference is read from the packaged store. Every Store is read-only,
    and nothing is copied: the same reference resolves the same bytes here and in `materialize`.
    """

    def __init__(self, config: ConfiguredStoreReader, key: tuple[str, str], root: Path, *, require_content_identity: bool,
                 allow_missing_content_identity: bool) -> None:
        super().__init__(root, key[1], require_content_identity=require_content_identity)
        self._config, self._key, self._allow_missing = config, key, allow_missing_content_identity

    def read(self, reference: dict[str, Any]) -> bytes:
        if is_package_reference(reference):
            return read_package_reference(reference)
        store = reference.get("store") if isinstance(reference, dict) else None
        other = (store.get("provider"), store.get("identity")) if isinstance(store, dict) else None
        if other is None or other == self._key:
            return super().read(reference)
        root = self._config.roots.get(other)
        if root is None:
            raise SnapshotReadError("E_STORE_CONFIG_REQUIRED", f"the Store config does not declare Store {other[0]}/{other[1]}, which "
                                    f"reference {reference.get('id')!r} names")
        required = self._config.integrity[other] == "required" and not self._allow_missing
        return LocalSnapshotReader(root, other[1], require_content_identity=required).read(reference)


class DraftExtensionPackageReader:
    """Read Draft Project package pins through their named immutable Store.

    The Store configuration is loaded only when a non-package reference is
    actually read. This keeps Drafts with no extension packages independent of
    workspace Store configuration while preserving the same routing and
    integrity rules as immutable Context closure.
    """

    def __init__(self, config_loader: Callable[[], ConfiguredStoreReader] | None = None) -> None:
        self._config_loader = config_loader
        self._config: ConfiguredStoreReader | None = None

    def read(self, reference: dict[str, Any]) -> bytes:
        if is_package_reference(reference):
            return read_package_reference(reference)
        if self._config_loader is None:
            raise SnapshotReadError(
                "E_STORE_CONFIG_REQUIRED",
                "Draft extension package references require a configured Store",
            )
        if self._config is None:
            self._config = self._config_loader()
        try:
            reader, _root = snapshot_reader_for(self._config, reference)
        except StableFailure as error:
            raise SnapshotReadError(error.code, error.message) from error
        return reader.read(reference)


def snapshot_reader_for(
    config: ConfiguredStoreReader, reference: Any, *, allow_missing_content_identity: bool = False,
) -> tuple[LocalSnapshotReader, Path]:
    """The reader and root of the Store ``reference`` names, with the integrity the configuration declares for it.

    A Store the configuration does not declare is ``E_STORE_CONFIG_REQUIRED``. The reader requires a ``contentIdentity``
    unless the Store's ``integrity`` is ``optional`` (an explicit setting of the configuration) or the caller passes the
    command line's explicit opt-out; it verifies a given identity against the stored bytes in every case.
    """
    store = reference.get("store") if isinstance(reference, dict) else None
    key = (store.get("provider"), store.get("identity")) if isinstance(store, dict) else None
    if key not in config.roots:
        raise StableFailure("E_STORE_CONFIG_REQUIRED",
                            "the Context reference names a Store that the Store config does not declare",
                            "store-config", "/", 2)
    root = config.roots[key]
    required = config.integrity[key] == "required" and not allow_missing_content_identity
    return SharedDesignReader(config, key, root, require_content_identity=required,
                              allow_missing_content_identity=allow_missing_content_identity), root


def compare_store_baseline(
    config: ConfiguredStoreReader, baseline_reference: dict[str, Any], candidate_reference: dict[str, Any],
) -> dict[str, Any]:
    """The Automation Result of ``chrona baseline-compare``: a named baseline against a candidate Project in one Store."""
    return compare_baseline(config, baseline_reference, config, candidate_reference)
