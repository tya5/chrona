"""Matrix-driven closure checks for schema-owned presentation settings."""
from pathlib import Path
import json

import pytest


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
MATRIX = json.loads((ROOT / "conformance/presentation-setting-consumption-matrix-v0.1.json").read_text())


@pytest.mark.parametrize("row", MATRIX["rows"], ids=lambda row: row["id"])
def test_every_consumption_matrix_row_has_closed_evidence(row):
    """No exact-path inert allow-list may replace conditional trigger/observer evidence."""
    assert row["disposition"] in {"implemented", "validation-only", "superseded"}
    assert row["classification"] in {"unconditional", "conditional", "validation-only", "superseded"}
    assert row["trigger"] and row["observer"]
    if row["classification"] == "validation-only":
        assert row["disposition"] == "validation-only"
    else:
        assert row["disposition"] in {"implemented", "superseded"}
