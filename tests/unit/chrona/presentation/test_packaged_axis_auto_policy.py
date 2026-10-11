from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from chrona.presentation.contracts import ClosureIdentity, ViewContract, parse_contract
from chrona.resources import safe_load
from chrona.usecases import preset_library


ROOT = Path(__file__).resolve().parents[4]
EXPECTED_FORMS = {
    "month": "short-month-year",
    "quarter": "year-quarter",
    "half": "half-year",
    "year": "year",
}


def _assert_axis_policy(document: dict, *, source: str) -> None:
    tiers = document["body"]["axis"]["tiers"]
    assert tiers == [
        {"unit": "year", "every": 1, "role": "band", "typographyRole": "axisQuarter"},
        {"unit": "quarter", "every": 1, "role": "grid-major"},
        {
            "unit": "auto",
            "every": 1,
            "role": "labels",
            "typographyRole": "axisQuarter",
            "label": {
                "forms": EXPECTED_FORMS,
                "align": "center",
                "overflow": "thin-with-record",
                "orientation": "horizontal",
            },
        },
        {"unit": "month", "every": 1, "role": "grid-minor"},
    ], source


def _resolved_builtin_view(entry: dict) -> tuple[ViewContract, dict]:
    member = preset_library._member(entry, "view")
    raw = preset_library._read_member(member)
    source = safe_load(raw)
    contract = parse_contract(
        ClosureIdentity("view", member["id"], "builtin", "sha256:" + sha256(raw).hexdigest()),
        source,
    )
    assert isinstance(contract, ViewContract)
    return contract, source


def test_all_packaged_axis_views_declare_thinning_and_automatic_forms():
    paths = sorted((ROOT / "src/chrona/resources/presets/bundles").glob("*/view.yaml"))
    paths.append(ROOT / "src/chrona/resources/presets/bundles/editorial/view-lanes.yaml")
    assert len(paths) == 9

    for path in paths:
        _assert_axis_policy(safe_load(path.read_bytes()), source=path.relative_to(ROOT).as_posix())


def test_every_builtin_preset_resolves_to_the_declared_auto_axis_policy():
    entries = preset_library._library()
    assert entries
    for entry in entries:
        contract, source = _resolved_builtin_view(entry)
        _assert_axis_policy(source, source=entry["id"])
        axis = contract.view.axis
        assert axis["tiers"][2]["label"]["forms"] == EXPECTED_FORMS
        assert axis["tiers"][2]["label"]["overflow"] == "thin-with-record"
