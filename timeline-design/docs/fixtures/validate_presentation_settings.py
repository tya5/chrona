"""Validate design contracts only; does not implement the runtime resolver."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource


DOCS = Path(__file__).resolve().parents[1]


def read(relative):
    return json.loads((DOCS / relative).read_text())


def merge(base, override):
    result = deepcopy(base)
    for key, value in override.items():
        result[key] = merge(result[key], value) if isinstance(value, dict) else deepcopy(value)
    return result


def main():
    schemas = [read(f"schemas/{name}-v0.2.schema.json") for name in
               ("presentation-settings", "presentation-preset")]
    registry = Registry().with_resources((s["$id"], Resource.from_contents(s)) for s in schemas)
    for schema in schemas:
        Draft202012Validator.check_schema(schema)
    settings, preset = [Draft202012Validator(s, registry=registry) for s in schemas]
    fixture = read("fixtures/presentation-settings-executive-v0.2.json")
    override = yaml.safe_load((DOCS / "fixtures/presentation-preset-override-v0.2.yaml").read_text())
    settings.validate(fixture)
    preset.validate(override)
    m23_override = deepcopy(override)
    m23_override["overrides"].setdefault("layout", {}).setdefault("slots", {}).update({
        "groupDetails": {"region": "detail", "track": 0, "source": "group-details",
                         "priority": "required", "overflow": "diagnose", "align": "stretch"},
        "observations": {"region": "detail", "track": 1, "source": "observations",
                         "priority": "required", "overflow": "diagnose", "align": "stretch"},
        "milestones": {"region": "detail", "track": 2, "source": "milestones",
                       "priority": "required", "overflow": "diagnose", "align": "stretch"},
    })
    preset.validate(m23_override)
    base_bytes = (DOCS / "fixtures/presentation-settings-executive-v0.2.json").read_bytes()
    assert override["base"]["contentIdentity"] == f"sha256:{sha256(base_bytes).hexdigest()}"
    preset.validate({"version": "chrona/presentation-preset/v0.2", "id": "complete", "settings": fixture})
    settings.validate(merge(fixture, override["overrides"]))
    axis_slots = [slot for slot in fixture["layout"]["slots"].values()
                  if slot["source"] in {"timeline", "timeline-axis"}]
    assert len(axis_slots) == 2 and {slot["scaleId"] for slot in axis_slots} == {"primary"}

    inventory = read("planning/presentation-fixed-value-inventory-v0.2.json")
    paths = set()
    for entry in inventory["entries"]:
        path = (entry["owner"], *entry["path"].split("."))
        assert path not in paths, path
        paths.add(path)
        value = fixture
        for key in path:
            value = value[key]
        assert value == entry["value"], path

    cases = [
        (settings, fixture, ("theme", "bar", "radius"), -1),
        (settings, fixture, ("theme", "paints", "planned", "opacity"), 1.1),
        (settings, fixture, ("theme", "arrow", "shape"), "arbitrary-script"),
        (settings, fixture, ("output", "coordinateDecimals"), 1.5),
        (settings, fixture, ("layout", "unknown"), 1),
        (settings, fixture, ("layout", "labelPlacement", "maxCandidates"), 17),
        (settings, fixture, ("layout", "labelPlacement", "candidateSides"), ["above"] * 17),
        (settings, fixture, ("layout", "routing", "limit"), 0),
        (settings, fixture, ("theme", "facetPaints", "groups", "delivery", "actual", "opacity"), 1.1),
        (settings, fixture, ("detail", "legend"), [{"role": "unknown", "label": "x"}]),
        (preset, override, ("overrides", "theme", "bar", "radius"), None),
        (preset, override, ("overrides", "detail", "legend"), [{"role": "planned"}]),
        (preset, override, ("overrides", "layout", "unknown"), 1),
        (preset, override, ("settings",), fixture),
    ]
    for validator, original, path, value in cases:
        invalid = deepcopy(original)
        target = invalid
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        assert not validator.is_valid(invalid), path
    missing = deepcopy(fixture)
    del missing["theme"]["bar"]["radius"]
    assert not settings.is_valid(missing)
    print(f"PASS: 2 schemas, 5 positive fixtures, {len(cases) + 1} negative fixtures, {len(paths)} inventory groups")
    print("Design structure only: font assets, semantic closure and rendering remain implementation gates.")


if __name__ == "__main__":
    main()
