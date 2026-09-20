"""Validate the design-owned conditional presentation-setting consumption matrix."""
from pathlib import Path
import json
from jsonschema import Draft202012Validator

REPO = Path(__file__).resolve().parents[1]
schema = json.loads((REPO / "schemas/presentation-setting-consumption-matrix-v0.1.schema.json").read_text())
matrix = json.loads((REPO / "conformance/presentation-setting-consumption-matrix-v0.1.json").read_text())
errors = list(Draft202012Validator(schema).iter_errors(matrix))
assert not errors, "\n".join(error.message for error in errors)
rows = matrix["rows"]
assert len({row["id"] for row in rows}) == len(rows)
assert len({row["settingPattern"] for row in rows}) == len(rows)
for row in rows:
    if row["classification"] == "conditional":
        assert row["trigger"] not in {"none", "single-sample"}
        assert "observer" in row and row["observer"]
    if row["classification"] == "validation-only":
        assert row["disposition"] == "validation-only"
assert any(row["settingPattern"] == "theme.bar.radius" and row["issue"] == 11 for row in rows)
assert any(row["settingPattern"] == "layout.routing.enabled" for row in rows)
assert not any("KNOWN_INERT" in row["observer"] or "known-inert" in row["observer"] for row in rows)
print(f"Presentation setting consumption matrix: PASS ({len(rows)} rows)")
