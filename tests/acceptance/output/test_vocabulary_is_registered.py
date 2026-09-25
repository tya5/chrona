"""Nothing may introduce a purpose, a slot or a primitive kind outside the registry.

These are the invariants that make `semantic_registry` authoritative rather than
merely complete: whatever the surface emits, and whatever a Layout Profile may
declare, has to be a semantic someone wrote down.
"""
from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree

import pytest
import yaml

from chrona.presentation.model.semantic_registry import (
    PrimitiveKind, REQUIRED_SLOTS, Slot, purposes, semantic_binding, semantic_ids,
)
from chrona.resources import schema_resource

ROOT = Path(__file__).resolve().parents[3]
SVG = "{http://www.w3.org/2000/svg}"
GENERATED = sorted(ROOT.glob("examples/*/generated/*.svg"))


@pytest.mark.parametrize("svg_path", GENERATED, ids=lambda path: f"{path.parents[1].name}/{path.stem}")
def test_every_emitted_purpose_is_a_registered_semantic(svg_path):
    emitted = {node.get("data-purpose") for node in ElementTree.fromstring(svg_path.read_text(encoding="utf-8")).iter()}
    unregistered = sorted(purpose for purpose in emitted - purposes() if purpose)
    assert not unregistered, f"purposes emitted but not declared in semantic_registry: {unregistered}"


def test_layout_profile_declares_exactly_the_registered_slots():
    schema = yaml.safe_load(schema_resource("layout-profile-v0.7.schema.yaml").read_text(encoding="utf-8"))
    declared = set(re.findall(r"[a-z-]+", str(_slot_enum(schema))))
    assert declared == {slot.value for slot in Slot}


def test_required_slots_are_slots():
    assert set(REQUIRED_SLOTS) <= set(Slot)


def test_every_semantic_resolves_and_is_unique():
    bindings = [semantic_binding(semantic_id) for semantic_id in semantic_ids()]
    assert len({(binding.purpose, binding.scene_role) for binding in bindings}) == len(bindings), "two semantics share one render-facing identity"
    assert all(binding.primitive_kind for binding in bindings)
    assert all(binding.theme_role for binding in bindings)


def test_dependency_variants_share_the_subject_but_not_the_scene_role():
    regular, critical = semantic_binding("dependency"), semantic_binding("dependency-critical")
    assert regular.purpose == critical.purpose == "dependency"
    assert regular.scene_role != critical.scene_role


@pytest.mark.parametrize("svg_path", GENERATED, ids=lambda path: f"{path.parents[1].name}/{path.stem}")
def test_the_renderer_draws_only_the_registered_primitive_kinds(svg_path):
    """Every rendered primitive is a supported SVG element or an icon path group."""
    drawn = {node.tag.removeprefix(SVG) for node in ElementTree.fromstring(svg_path.read_text(encoding="utf-8")).iter()
             if node.get("data-purpose") is not None}
    # A vector Icon is one Scene primitive projected as a semantic ``g`` that
    # owns its normalized fill/stroke paths; the paths themselves deliberately
    # do not duplicate the primitive's provenance attributes.
    assert drawn <= {"rect", "text", "polygon", "path", "image", "g"}
    assert {kind.value for kind in PrimitiveKind} == {"Rect", "Text", "Symbol", "Path", "Icon"}


def _slot_enum(node):
    if isinstance(node, dict):
        if node.get("title") == "slot source" or ("enum" in node and "timeline-axis" in (node.get("enum") or ())):
            return node["enum"]
        for value in node.values():
            found = _slot_enum(value)
            if found is not None:
                return found
    elif isinstance(node, list):
        for value in node:
            found = _slot_enum(value)
            if found is not None:
                return found
    return None
