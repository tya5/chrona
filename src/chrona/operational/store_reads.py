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
from typing import Any

from chrona.core.validation import load_yaml
from chrona.operational.baselines import compare_baseline
from chrona.operational.store_config import ConfiguredStoreReader
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.usecases.failure_report import StableFailure


def load_reference(path: str | Path) -> dict[str, Any]:
    """Load one resource-reference YAML file, as ``--context-reference`` and ``--baseline-reference`` do."""
    return load_yaml(path)


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
    return LocalSnapshotReader(root, key[1], require_content_identity=required), root


def compare_store_baseline(
    config: ConfiguredStoreReader, baseline_reference: dict[str, Any], candidate_reference: dict[str, Any],
) -> dict[str, Any]:
    """The Automation Result of ``chrona baseline-compare``: a named baseline against a candidate Project in one Store."""
    return compare_baseline(config, baseline_reference, config, candidate_reference)
