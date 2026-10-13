"""Where a committed Render Context reference points on disk, for tests that read a Context's files directly.

A reference is either a file of the Context's own example (`store.provider: local`) or a shared design in the
packaged store (`store: {provider: package, identity: chrona.resources}`, Spec 13 "Shared designs", #1342).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

PACKAGE_ROOT = Path(__file__).resolve().parents[2] / "src/chrona/resources"


def reference_path(example: Path, reference: Mapping[str, Any]) -> Path:
    """The file ``reference`` names for a Context of ``example``."""
    store = reference.get("store")
    if isinstance(store, Mapping) and store.get("provider") == "package":
        assert store.get("identity") == "chrona.resources", store
        return PACKAGE_ROOT / reference["address"]
    return example / reference["address"]
