#!/usr/bin/env python3
"""Generate the packaged Theme authoring reference from runtime role contracts (#1827)."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Iterable

from chrona.presentation.model.semantic_registry import semantic_ids, semantic_binding
from chrona.presentation.scene.capabilities import _ROLE_PROPERTY_CONTRACTS, theme_role_contract
from chrona.presentation.model.point_paint import resolve_point_paint_role


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "skills/chrona/references/theme-role-reference.md"


def _cell(value: str) -> str:
    return value.replace("|", "&#124;").replace("\n", "<br>")


def _semantic_rows() -> tuple[str, ...]:
    rows: list[str] = []
    for semantic_id in semantic_ids():
        binding = semantic_binding(semantic_id)
        rows.append("| " + " | ".join(map(_cell, (
            semantic_id, binding.primitive_kind, binding.purpose,
            binding.scene_role, binding.theme_role,
        ))) + " |")
    return tuple(rows)


def _role_rows() -> tuple[str, ...]:
    rows: list[str] = []
    for role in sorted(_ROLE_PROPERTY_CONTRACTS):
        contract = theme_role_contract(role)
        assert contract is not None
        properties = ", ".join(sorted(contract.properties)) or "—"
        paint_keys = tuple(f"{role}.{name}" for name in (
            "fill", "stroke", "gradientStart", "gradientEnd", "shadowColor", "glowColor",
        )
                           if name in contract.properties)
        paint_text = "<br>".join(f"`{key}`" for key in paint_keys) or "—"
        scene_kinds = "<br>".join(sorted(contract.scene_kinds)) or "—"
        rows.append("| " + " | ".join(map(_cell, (
            role, contract.consumer, scene_kinds, paint_text, properties,
        ))) + " |")
    return tuple(rows)


def render_reference() -> str:
    """Render the deterministic page from the packaged semantic vocabulary and consumer contract."""
    point_role = resolve_point_paint_role("planned", gate_declared=False)
    gate_role = resolve_point_paint_role("planned", gate_declared=True)
    lines = [
        "# Theme role reference",
        "",
        "Use this page while authoring a Theme; it describes the current renderer contract, not a palette.",
        "The semantic mapping below is generated from the packaged semantic vocabulary; the consumer",
        "and property table is generated from the finite Theme role contracts. Repository maintainers",
        "regenerate/check it with `python -m tools.theme_role_reference --write` / `--check`.",
        "",
        "## Roles, meanings, and consumed properties",
        "",
        "A semantic binding records a primitive family, purpose, Scene role and Theme role; these are",
        "distinct concepts. The Scene role identifies the completed primitive/paint use. A Theme role",
        "can instead supply geometry or measurement, and need not be the paint role. Theme role",
        "properties have property-specific value forms; they are not all token references. The table",
        "lists registered consumers and properties; color-binding paint keys are the",
        "properties that can address a color binding. Color-binding values select Color Scheme",
        "intents/slots, not Theme value-token IDs. For other role properties, the schema specifies",
        "whether a value is a token reference or an inline value; do not assume every property is a token.",
        "",
        "### Semantic-to-presentation mapping (packaged vocabulary)",
        "",
        "| Semantic ID | Primitive family | Purpose | Scene role | Theme role |",
        "| --- | --- | --- | --- | --- |",
        *_semantic_rows(),
        "",
        "### Theme role consumers (registered contracts)",
        "",
        "| Theme role | Consumer | Scene kinds | Color-binding paint keys | Consumed properties |",
        "| --- | --- | --- | --- | --- |",
        *_role_rows(),
        "",
        "Some consumers accept a bounded role family with a resource-selected suffix, such as",
        "`period-band:<slug>`, `period-label:<slug>`, `region-frame-<slug>`, `frame-glyph-<slug>` and",
        "`annotation-artwork-<slug>`; each uses its corresponding registered base contract.",
        "",
        "A Theme role can be shared by several meanings: `forecast` is distinct but reuses `planned`.",
        "`milestoneSymbol` is point-glyph geometry and has no fill paint key. Planned point milestones",
        f"and the Detail `milestone` key resolve to `{point_role}` paint by default; when `gate` is declared,",
        f"they resolve to `{gate_role}`. Actual marks use `actual` paint. The `asOf` Theme role provides",
        "as-of relation geometry/width; the Scene Path's paint role is `as-of`, for example",
        "`as-of.stroke`. Do not infer the milestone key's paint binding from its Detail role name:",
        f"its selected targets are `{point_role}.fill` / `{gate_role}.fill`, as the shared point resolver specifies.",
        "These distinctions keep paint bindings separate from geometry roles.",
        "",
        "## Authoring notes",
        "",
        "- A Layout Profile's top-level `viewDefaults.progressFill.source` supplies the default for a",
        "  View's `body.progressFill.source`; an explicit View value replaces that default. It selects",
        "  `planned` or `actual` as the source for a display-only submark on completed marks; the Theme",
        "  `progress-fill` role supplies its ink (including progress on completed Actual marks).",
        "- A Theme text role using `textTransform: small-caps` must also declare `smallCapsScale` (a named",
        "  number token greater than 0.5 and less than 1).",
        "- A point-symbol token may use a built-in shape such as `shape: circle`; legend entries may also",
        "  request the closed `swatchShape: circle` geometry. Neither syntax assigns a color token ID.",
        "- Common built-in Detail legend roles include `planned`, `actual`, `milestone`, `dependency`,",
        "  `asOf`, `calendar-closed`, `forecast`, `progressFill`, `actual-ahead`, `actual-on-track`,",
        "  `actual-behind`, `snapshot`, `deadlineMark` and `critical-edge`. These are role names, distinct",
        "  from localized `legend.*` wording keys. Detail entries may name other roles.",
        "",
        "Color Schemes provide the colors selected by Theme `colorBindings`. Theme roles select visual uses;",
        "they do not select project data or scheduling behavior.",
        "",
    ]
    return "\n".join(lines)


def write_reference(path: Path = OUTPUT) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_reference(), encoding="utf-8", newline="\n")


def check_reference(path: Path = OUTPUT) -> bool:
    try:
        return path.read_text(encoding="utf-8") == render_reference()
    except OSError:
        return False


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true", help="fail if the generated page is stale")
    action.add_argument("--write", action="store_true", help="write the generated page")
    args = parser.parse_args(argv)
    if args.write:
        write_reference()
        print(f"Wrote {OUTPUT.relative_to(ROOT).as_posix()}")
        return 0
    if not check_reference():
        print(f"E_THEME_ROLE_REFERENCE_STALE: run python -m tools.theme_role_reference --write ({OUTPUT})", file=sys.stderr)
        return 1
    print("Theme role reference: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
