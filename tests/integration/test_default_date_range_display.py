"""Live View admission and actual init/default-render acceptance (#1293)."""
from hashlib import sha256
import json
import sys

import jsonschema
import pytest

from chrona.app.cli import main
from chrona.presentation.contracts import ClosureIdentity, ViewContract, parse_contract
from chrona.resources import safe_load, schema_validator
from chrona.usecases import preset_library


def _default_view():
    entry = next(item for item in preset_library._library()
                 if item["id"] == preset_library.DEFAULT_PRESET_ID)
    return safe_load(preset_library._read_member(preset_library._member(entry, "view")))


@pytest.mark.parametrize("mode", ["inclusive", "exclusive", None])
def test_live_view_accepts_endpoint_display_and_runtime_default(mode):
    document = _default_view()
    column = document["body"]["tableColumns"][1]
    column.pop("endDisplay", None)
    if mode is not None:
        column["endDisplay"] = mode
    schema_validator("view-v0.28.schema.yaml").validate(document)
    contract = parse_contract(ClosureIdentity("view", document["id"], "test",
                              "sha256:" + sha256(repr(document).encode()).hexdigest()), document)
    assert isinstance(contract, ViewContract)
    assert contract.view.table_columns[1].end_display == (mode or "exclusive")


@pytest.mark.parametrize("value", ["last-working-day", "", True, 1, None, {}])
def test_live_view_rejects_invalid_endpoint_modes(value):
    document = _default_view()
    document["body"]["tableColumns"][1]["endDisplay"] = value
    with pytest.raises(jsonschema.ValidationError):
        schema_validator("view-v0.28.schema.yaml").validate(document)


@pytest.mark.parametrize("formatter", [None, "signedDays", {"kind": "presence", "whenTrue": "yes", "whenFalse": "no"}])
def test_endpoint_mode_is_rejected_outside_date_range(formatter):
    document = _default_view()
    column = document["body"]["tableColumns"][1]
    if formatter is None:
        column.pop("format")
    else:
        column["format"] = formatter
    with pytest.raises(jsonschema.ValidationError):
        schema_validator("view-v0.28.schema.yaml").validate(document)


def test_init_starter_default_scene_uses_inclusive_plan_cells(tmp_path, monkeypatch, capsys):
    project = tmp_path / "starter"
    monkeypatch.setattr(sys, "argv", ["chrona", "init", str(project)])
    main()
    original = (project / "project.yaml").read_bytes()
    scene, svg = tmp_path / "review.json", tmp_path / "review.svg"
    monkeypatch.setattr(sys, "argv", ["chrona", "render", str(project / "project.yaml"),
                                      "--emit-scene", str(scene), "--output", str(svg)])
    main()
    document = json.loads(scene.read_text())
    cells = {item["id"]: item["text"] for item in document["surfaces"][0]["primitives"]
             if item["id"].startswith("cell:") and item["id"].endswith(":Plan")}
    assert cells == {"cell:design:Plan": "01 Oct – 30 Oct", "cell:build:Plan": "03 Nov – 14 Dec",
                     "cell:release:Plan": "18 Dec 2026"}
    assert (project / "project.yaml").read_bytes() == original
    assert "01 Oct – 30 Oct" in svg.read_text()


def test_all_builtin_date_range_columns_explicitly_use_inclusive_mode():
    found = []
    for entry in preset_library._library():
        document = safe_load(preset_library._read_member(preset_library._member(entry, "view")))
        for column in document["body"].get("tableColumns", ()):
            if column.get("format") == "dateRange":
                assert column["endDisplay"] == "inclusive", entry["id"]
                found.append((entry["id"], column["id"]))
    assert found == [(preset_library.DEFAULT_PRESET_ID, "Plan")]
