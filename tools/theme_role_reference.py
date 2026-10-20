#!/usr/bin/env python3
"""Generate the Theme-authoring reference page from the vocabulary the renderer enforces (#1827 row 1).

The page answers what an author needs to design a look without reading other designs: which Theme role paints what,
which colour bindings and which role properties it takes, what a token may hold, and which legend keys the renderer adds
on its own. Every table is derived from a resource the code reads:

* the Theme role registry (`chrona.presentation.scene.capabilities`), the table that admits a property on a role;
* the semantic vocabulary resource (`semantic-vocabulary.yaml`), which says what each role paints;
* `schemas/theme-v0.15.schema.yaml` (property descriptions, Scheme intents, token types and value forms);
* `schemas/review-detail-profile-v0.1.schema.yaml` (`unkeyedLegendRoles`) and the wording table (legend keys).

The few hand-written sentences name things the vocabulary also defines; `_require` stops generation when one of them
disappears, so the prose cannot outlive its subject. `--check` fails when the committed page differs; the same check
runs as a unit test.

    python tools/theme_role_reference.py            # write skills/chrona/references/theme-roles.md
    python tools/theme_role_reference.py --check    # exit 1 when the committed page is stale
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chrona.presentation.model.semantic_registry import semantic_binding, semantic_ids  # noqa: E402
from chrona.presentation.scene.capabilities import generated_role_prefixes, registered_role_contracts  # noqa: E402
from chrona.resources import safe_load  # noqa: E402

OUTPUT = Path("skills/chrona/references/theme-roles.md")
THEME_SCHEMA = Path("schemas/theme-v0.15.schema.yaml")
DETAIL_SCHEMA = Path("schemas/review-detail-profile-v0.1.schema.yaml")
LAYOUT_SCHEMA = Path("schemas/layout-profile-v0.10.schema.yaml")
WORDING = Path("src/chrona/resources/wording-tables-v0.1.yaml")

# A colour binding is `<role>.<paint>`; these paints are the colour half of a role's properties.
COLOUR_PAINTS = ("fill", "stroke", "gradientStart", "gradientEnd", "shadowColor", "glowColor")
EFFECT_PREFIXES = ("gradient", "shadow", "glow", "wobble", "strokeLine", "strokeFinish")
LEGEND_ROLES = ("planned", "actual", "milestone", "dependency", "asOf", "calendar-closed", "critical-edge",
                "forecast", "progressFill", "snapshot", "deadlineMark")
GENERATED_PREFIX_NOTES = {
    "group:": "one colour per group, chosen by the View's group colouring",
    "period-band:": "a named period's band, one role per period slug",
    "period-label:": "a named period's label, one role per period slug",
    "region-frame-": "a region frame painted by `frame.paint` (the slug after the dash)",
    "frame-glyph": "a catalogue border run on a region frame",
    "annotation-artwork": "an annotation container's artwork layer",
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(f"E_THEME_ROLE_REFERENCE_DRIFT: {message}")


def _load(root: Path, relative: Path) -> Any:
    return safe_load((root / relative).read_bytes())


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("<", "&lt;").replace("\n", " ").strip()


def _first_sentence(description: str) -> str:
    text = re.sub(r"\s*\(#\d+(?:, #\d+)*\)", "", description).strip()
    match = re.search(r"(?<=[a-z0-9`)])\.(?:\s|$)", text)
    return (text[: match.start() + 1] if match else text).strip()


def _code(names: list[str] | tuple[str, ...]) -> str:
    return " ".join(f"`{name}`" for name in names)


def _is_effect(name: str) -> bool:
    return name.startswith(EFFECT_PREFIXES)


def _paints(role: str) -> str:
    """What the semantic vocabulary says this role paints (by Theme role, else by Scene role)."""
    by_theme: list[str] = []
    by_scene: list[str] = []
    for semantic_id in semantic_ids():
        binding = semantic_binding(semantic_id)
        label = f"{binding.primitive_kind} `{binding.purpose}`"
        if binding.theme_role == role:
            by_theme.append(label)
        elif binding.scene_role == role:
            by_scene.append(label)
    return "; ".join(dict.fromkeys(by_theme + by_scene))


def _role_table() -> list[str]:
    lines = ["| Role | Paints | Colour (`<role>.<paint>`) | Tokens (`roles.<role>.<property>`) | Effects |",
             "| --- | --- | --- | --- | --- |"]
    for role, contract in sorted(registered_role_contracts().items()):
        colours = [name for name in COLOUR_PAINTS if name in contract.properties and not _is_effect(name)]
        tokens = sorted(name for name in contract.properties
                        if name not in COLOUR_PAINTS and not _is_effect(name))
        effects = sorted(name for name in contract.properties if _is_effect(name))
        effect_kinds = [kind for kind in ("gradient", "shadow", "glow", "wobble") if any(n.startswith(kind) for n in effects)]
        if any(n.startswith("strokeLine") or n.startswith("strokeFinish") for n in effects):
            effect_kinds.append("stroke cap/join")
        lines.append("| " + " | ".join((
            f"`{role}`",
            _cell(_paints(role) or contract.consumer),
            _code([f".{name}" for name in colours]) or "-",
            _code(tokens) or "-",
            ", ".join(effect_kinds) or "-")) + " |")
    return lines


def _property_table(theme: Mapping[str, Any]) -> list[str]:
    properties = theme["properties"]["body"]["properties"]["roles"]["additionalProperties"]["properties"]
    used = {name for contract in registered_role_contracts().values() for name in contract.properties}
    lines = ["| Property | Value | Meaning |", "| --- | --- | --- |"]
    for name in sorted(used - set(COLOUR_PAINTS)):
        schema = properties.get(name)
        if schema is None:
            continue
        if "enum" in schema:
            value = _code([str(item) for item in schema["enum"]])
        elif schema.get("type") == "integer":
            value = "integer"
        elif "$ref" in schema:
            value = "closed set (see the Theme schema)"
        else:
            value = "a token name from `values`"
        lines.append(f"| `{name}` | {_cell(value)} | {_cell(_first_sentence(schema.get('description', '')))} |")
    return lines


def _scheme_intents(theme: Mapping[str, Any]) -> list[str]:
    patterns = theme["properties"]["body"]["properties"]["colorBindings"]["patternProperties"]
    intents: list[str] = []
    for schema in patterns.values():
        for option in schema["anyOf"]:
            for item in option.get("enum", ()):
                if item not in intents:
                    intents.append(item)
    return intents


def _token_forms(theme: Mapping[str, Any]) -> tuple[list[str], dict[str, Any]]:
    token = theme["properties"]["body"]["properties"]["values"]["additionalProperties"]
    types = token["properties"]["type"]["enum"]
    forms: dict[str, Any] = {}

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            condition, outcome = node.get("if"), node.get("then")
            if condition and outcome:
                const = condition.get("properties", {}).get("type", {}).get("const")
                if const:
                    forms[const] = outcome["properties"]["value"]
            for item in node.values():
                walk(item)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(token)
    return list(types), forms


def _symbol_shapes(forms: Mapping[str, Any]) -> list[str]:
    return list(forms["symbol"]["oneOf"][0]["properties"]["shape"]["enum"])


def _legend_keys(wording: Mapping[str, Any]) -> list[tuple[str, str]]:
    table = wording["tables"]["en-US"]
    return [(key, str(text)) for key, text in table.items() if key.startswith("legend.")]


def render(root: Path = ROOT) -> str:
    theme = _load(root, THEME_SCHEMA)
    detail = _load(root, DETAIL_SCHEMA)
    layout = _load(root, LAYOUT_SCHEMA)
    wording = safe_load((root / WORDING).read_bytes())
    contracts = registered_role_contracts()

    def takes(role: str) -> frozenset[str]:
        return contracts[role].properties if role in contracts else frozenset()

    types, forms = _token_forms(theme)
    shapes = _symbol_shapes(forms)
    intents = _scheme_intents(theme)
    transforms = list(forms["textTransform"]["enum"])
    unkeyed = detail["properties"]["body"]["properties"]["unkeyedLegendRoles"]["items"]["enum"]
    legend_keys = dict(_legend_keys(wording))

    # The prose below names these; it must stop being generated when one disappears.
    _require("stroke" in takes("as-of") and {"dash", "strokeWidth"} <= takes("asOf"),
             "the as-of line is painted by role `as-of` and shaped by role `asOf`")
    _require(all("fill" in takes(name) for name in ("milestone", "gate", "actual")),
             "milestone, gate and actual take a fill")
    _require("fill" in takes("progress-fill"), "role `progress-fill` takes a fill")
    _require("progressFill" in layout["properties"]["viewDefaults"]["properties"], "Layout viewDefaults.progressFill")
    _require("smallCapsScale" in takes("legend") and "small-caps" in transforms,
             "smallCapsScale and the small-caps transform")
    _require("circle" in shapes and "symbol" in takes("milestoneSymbol"),
             "symbol tokens with a circle shape")
    _require({"snapshot", "deadlineMark"} == set(unkeyed), "unkeyedLegendRoles admits snapshot and deadlineMark")
    _require({f"legend.{name}" for name in LEGEND_ROLES} <= set(legend_keys), "wording keys for the legend roles")
    _require({"legend.forecast", "legend.progressFill", "legend.snapshot", "legend.deadlineMark"} <= set(legend_keys),
             "default legend wording keys")
    _require(set(generated_role_prefixes()) == set(GENERATED_PREFIX_NOTES), "the generated role prefixes")

    out: list[str] = []
    out += [
        "<!-- Generated by tools/theme_role_reference.py from chrona's role registry, semantic vocabulary and",
        "     Theme schema; do not edit. Regenerate with `python tools/theme_role_reference.py`. -->",
        "# Theme roles: what each role paints and what it takes",
        "",
        "Use this when you edit a Theme (a `theme.yaml` from `chrona preset copy`) to change how a plan looks.",
        "A Theme has three parts:",
        "",
        "- `values`: named tokens, each `{type: ..., value: ...}` (a size, a dash pattern, a symbol, a font family).",
        "- `roles`: per role, properties that **name a token** (`roles.planned.cornerRadius: radius.bar`).",
        "- `colorBindings`: per role, a colour **paint** bound to a Colour Scheme intent",
        "  (`planned.fill: accent`). Concrete colours live in the Scheme, not here.",
        "",
        "A property a role does not take is rejected (`E_THEME_ROLE_PROPERTY_UNSUPPORTED`). A declared role that no",
        "table row, View, Detail Profile or Layout Profile names is reported as unread (`W_THEME_ROLE_UNREAD`).",
        "",
        "## Look-affecting switches that are easy to miss",
        "",
        "- **Today line.** Its colour is the binding `as-of.stroke`; its dash and width are the properties of the",
        "  **different** role `asOf` (`dash`, `strokeWidth`). A dash needs positive numbers: for a solid line remove",
        "  `dash` from the role rather than writing `[1, 0]`.",
        "- **Planned and actual points.** Planned milestones paint with `milestone.fill`, gates with `gate.fill` (when the",
        "  Theme declares a `gate` role), and actual points with `actual.fill`.",
        "- **Progress.** Progress fill appears only when the View asks for it (`progressFill: {source: actual}` or",
        "  `planned`, which a Layout Profile can supply as `viewDefaults.progressFill`). It is painted by role",
        "  `progress-fill` (`progress-fill.fill`) and adds a Progress key to the legend (see Legend keys).",
        "  Remove that member from the View and the Layout Profile defaults to draw finished actuals without it.",
        f"- **Small caps.** A text role with `textTransform` set to a token of value `small-caps` also needs",
        f"  `smallCapsScale`, a number token above 0.5 and below 1. Text transforms: {_code(transforms)}.",
        f"- **Circles.** A `symbol` token takes `{{shape: circle}}`; the other shapes are {_code([s for s in shapes if s != 'circle'])}",
        "  or a `glyph` whose path parts use only move, line, quadratic and close commands (no arcs: draw a circle with",
        "  the shape, not with `A` commands).",
        "",
        "## Colour bindings",
        "",
        "A binding key is `<role>.<paint>` where the paint is one of " + _code(COLOUR_PAINTS) + ". Its value is a Scheme intent:",
        "",
        _code(intents) + ", or `category:<slot>` for a named category slot of the Scheme.",
        "",
        "## Roles",
        "",
        f"{len(contracts)} registered roles. *Paints* is the meaning the semantic vocabulary gives the role. *Colour* lists",
        "the paints that take a Scheme intent. *Tokens* lists the properties that name a token (see the property table).",
        "*Effects* says the role also takes gradient, shadow, glow, wobble or stroke cap and join properties.",
        "",
    ]
    out += _role_table()
    out += ["", "### Generated role names", "",
            "A Theme may also declare names under these prefixes.", ""]
    out += [f"- `{prefix}...`: {GENERATED_PREFIX_NOTES[prefix]}" for prefix in generated_role_prefixes()]
    out += ["", "## Role properties", ""]
    out += _property_table(theme)
    out += ["", "## Tokens", "",
            "A token is `{type: T, value: V}` in `values`; a role property names it. Token types: "
            + _code(types) + ".", ""]
    out += [
        f"- `symbol`: `{{shape: S}}` with S one of {_code(shapes)}, or a `glyph`.",
        f"- `textTransform`: one of {_code(transforms)}.",
        f"- `radius`: a number of at least 0, or `capsule`.",
        f"- `dashPattern`: a list of positive numbers.",
        "",
        "## Legend keys",
        "",
        "A Detail Profile `legend` lists the keys you want, in order, each `{role, label}`; `label` is a literal or",
        "`{wording: <key>}`. Role names include " + _code(LEGEND_ROLES) + "; each has a default label under the",
        "wording key `legend.<role>`. The renderer then **adds** keys for meanings that are drawn, so the legend can",
        "show more than you listed:",
        "",
        "| Key | Added when | How to leave it out |",
        "| --- | --- | --- |",
        "| `snapshot` (Baseline) | a baseline is drawn | `unkeyedLegendRoles: [snapshot]` |",
        "| `deadlineMark` (Deadline) | a deadline is drawn | `unkeyedLegendRoles: [deadlineMark]` |",
        "| `forecast` | an item has a forecast | do not draw forecasts |",
        "| `progressFill` (Progress) | a positive progress fill is drawn and its ink differs from its mark | do not set `progressFill` in the View, or give `progress-fill` the colour of its mark |",
        "",
        f"`unkeyedLegendRoles` is a Detail Profile member (a sibling of `legend`) that takes only {_code(unkeyed)}.",
        "Naming the same role in both `legend` and `unkeyedLegendRoles` is `E_DETAIL_LEGEND_POLICY`. An explicit",
        "`legend` entry for a defaulted role replaces the default and sets its label and order. Keys for colour",
        "scales (`scale:...`) follow the entries.",
        "",
        "Built-in wording keys for legend labels (en-US text; `--locale ja-JP` has its own):",
        "",
    ]
    out += [f"- `{key}`: {text}" for key, text in legend_keys.items()]
    out.append("")
    return "\n".join(out)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", dir=path.parent, delete=False) as temporary:
        temporary.write(content)
        name = Path(temporary.name)
    name.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    content = render(root)
    if args.check:
        if not output.is_file() or output.read_bytes().decode("utf-8") != content:
            raise SystemExit(f"E_THEME_ROLE_REFERENCE_STALE: {output}; run python tools/theme_role_reference.py")
        return
    write(output, content)


if __name__ == "__main__":
    main()
