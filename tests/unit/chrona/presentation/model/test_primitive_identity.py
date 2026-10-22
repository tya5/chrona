from types import SimpleNamespace

from chrona.presentation.model.primitive_identity import (
    completed_symbol_part_group,
    completed_symbol_part_groups,
    completed_symbol_primitive_ids,
    parse_symbol_part_id,
)


def _part(identifier, *, source="task", purpose="planned", bounds=None):
    return {"id": identifier, "kind": "Symbol", "sourceRef": source, "purpose": purpose,
            "bounds": bounds or {"inline": 2, "block": 3, "inlineSize": 7, "blockSize": 9}}


def test_symbol_parts_use_the_one_canonical_explicit_paint_grammar():
    parts = (SimpleNamespace(paint_mode="fill"), SimpleNamespace(paint_mode=None))
    assert completed_symbol_primitive_ids("planned:task:task", parts) == (
        "planned:task:task:part0", "planned:task:task")
    assert parse_symbol_part_id("planned:task:task:part0") == ("planned:task:task", 0)
    assert parse_symbol_part_id("planned:task:task:part11") == ("planned:task:task", 11)
    assert parse_symbol_part_id("planned:task:task:part:0") is None
    assert parse_symbol_part_id("planned:task:task:part00") is None
    assert parse_symbol_part_id("planned:task:task:part١") is None


def test_oversized_part_index_is_not_an_ingress_exception():
    assert parse_symbol_part_id("planned:task:task:part" + "9" * 5000) is None


def test_completed_symbol_parts_resolve_only_as_one_exact_contiguous_identity():
    base = "planned:task:task"
    parts = [_part(base + ":part0"), _part(base + ":part1"), _part(base + ":part2")]
    assert completed_symbol_part_group(parts, base) == tuple(parts)
    assert completed_symbol_part_groups(parts) == ({base: tuple(parts)}, frozenset())


def test_single_explicitly_painted_part_resolves_but_implicit_paint_keeps_base():
    base = "planned:task:task"
    part = _part(base + ":part0")
    assert completed_symbol_part_group([part], base) == (part,)
    implicit = _part(base)
    assert completed_symbol_part_group([implicit], base) is None


def test_symbol_sibling_group_fails_closed_on_noncanonical_or_mixed_ids():
    base = "planned:task:task"
    canonical = _part(base + ":part0")
    legacy_spelling = _part(base + ":part:1")
    assert completed_symbol_part_group([canonical, legacy_spelling], base) is None
    assert completed_symbol_part_group([legacy_spelling], base) is None


def test_symbol_sibling_group_requires_unique_contiguous_parts_and_no_base_collision():
    base = "planned:task:task"
    part0, part1, part2 = (_part(base + suffix) for suffix in (":part0", ":part1", ":part2"))
    assert completed_symbol_part_group([part0, part2], base) is None
    assert completed_symbol_part_group([part0, dict(part0)], base) is None
    assert completed_symbol_part_group([_part(base), part0], base) is None


def test_symbol_sibling_group_requires_matching_source_purpose_and_full_bounds():
    base = "planned:task:task"
    first = _part(base + ":part0")
    assert completed_symbol_part_group([first, _part(base + ":part1", source="other")], base) is None
    assert completed_symbol_part_group([first, _part(base + ":part1", purpose="actual")], base) is None
    assert completed_symbol_part_group([first, _part(base + ":part1", bounds={
        "inline": 2, "block": 3, "inlineSize": 8, "blockSize": 9})], base) is None
