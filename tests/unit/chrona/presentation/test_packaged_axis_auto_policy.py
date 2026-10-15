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
    policy_tiers = [tier for tier in tiers if tier["role"] != "band"]
    assert policy_tiers == [
        {"unit": "quarter", "every": 1, "role": "grid-major"},
        {
            "unit": "auto",
            "every": 1,
            "role": "labels",
            "typographyRole": "axis" if document["id"] in {"chrona-preset-technical-print", "chrona-preset-wallboard-dark"} else "axisQuarter",
            "label": {
                "forms": ({"day": "localized-date", "week": "start-day-month", **EXPECTED_FORMS}
                          if document["id"] == "chrona-preset-editorial-readable-default" else EXPECTED_FORMS),
                "align": "center",
                "overflow": "thin-with-record",
                "orientation": "horizontal",
            },
        },
        {"unit": "month", "every": 1, "role": "grid-minor"},
    ], source
    bands = [tier for tier in tiers if tier["role"] == "band"]
    expected_bands = [
        {"unit": "year", "every": 1, "role": "band", "typographyRole": "axisQuarter"},
    ]
    if document["id"] == "chrona-preset-technical-print":
        expected_bands.append(
            {"unit": "month", "every": 1, "role": "band", "typographyRole": "axisMonth"},
        )
    if document["id"] == "chrona-preset-wallboard-dark":  # a fill per interval needs its own band tiers (#490; gap 3 of wallboard-dark-vocabulary-gaps.md)
        expected_bands = [
            {"unit": "quarter", "every": 1, "role": "band", "typographyRole": "axisQuarter",
             "fillScale": {"scale": "axis-quarter", "key": "alternating"}},
            {"unit": "month", "every": 1, "role": "band", "typographyRole": "axisMonth",
             "fillScale": {"scale": "axis-month", "key": "alternating", "containingTier": 0}},
        ]
    assert bands == expected_bands, source


def test_technical_pattern_and_label_ink_retain_the_declared_band_paint():
    path = ROOT / "src/chrona/resources/presets/bundles/technical-print/theme.yaml"
    body = safe_load(path.read_bytes())["body"]
    assert body["roles"]["axis-band-decoration2"]["pattern"] == "starter-halftone"
    assert body["colorBindings"]["axis-band-decoration.fill"] == "text"
    assert body["colorBindings"]["axis-band-decoration2.fill"] == "surfaceRaised"
    assert body["colorBindings"]["axis-label2.fill"] == "surface"


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
    paths = sorted(path for path in (ROOT / "src/chrona/resources/presets/bundles").glob("*/view.yaml")
                   if path.parent.name != "design-default")  # its axis is the selected design's `viewDefaults` (#429)
    paths.append(ROOT / "src/chrona/resources/presets/bundles/editorial/view-lanes.yaml")
    assert len(paths) == 11

    for path in paths:
        _assert_axis_policy(safe_load(path.read_bytes()), source=path.relative_to(ROOT).as_posix())


def test_every_builtin_preset_resolves_to_the_declared_auto_axis_policy():
    entries = preset_library._library()
    assert entries
    for entry in entries:
        if entry["members"]["layout"]["sourceRoot"].startswith("designs/"):
            continue  # a packaged design owns its axis in its Layout profile's `viewDefaults` (#429)
        contract, source = _resolved_builtin_view(entry)
        _assert_axis_policy(source, source=entry["id"])
        axis = contract.view.axis
        expected = ({"day": "localized-date", "week": "start-day-month", **EXPECTED_FORMS}
                    if source["id"] == "chrona-preset-editorial-readable-default" else EXPECTED_FORMS)
        assert axis["tiers"][2]["label"]["forms"] == expected
        assert axis["tiers"][2]["label"]["overflow"] == "thin-with-record"
