from pathlib import Path

import pytest

from tools.check_layout_float_accumulation import violations


def test_live_layout_has_no_unclassified_builtin_float_sum() -> None:
    assert not violations()


def test_checker_accepts_reviewed_decimal_and_count_sums_but_rejects_geometry_sum(tmp_path: Path) -> None:
    (tmp_path / "engine.py").write_text(
        "def _allocate(values):\n    return sum(values, ZERO)\n",
        encoding="utf-8",
    )
    (tmp_path / "presentation.py").write_text(
        "def count(items):\n    return sum(item.enabled is True for item in items)\n"
        "def geometry(values):\n    return sum(item.width for item in values)\n",
        encoding="utf-8",
    )
    assert violations(tmp_path) == ("presentation.py:4:E_LAYOUT_FLOAT_SUM_UNCLASSIFIED",)


@pytest.mark.parametrize("filename,owner", [
    ("presentation.py", "_bounded_column_widths"),
    ("surface_base.py", "prepare_surface_inline"),
    ("table_measurement.py", "measure_bounded_table"),
    ("tracks.py", "resolve_flexible_tracks"),
    ("surface_legend.py", "complete_legend_layout"),
    ("surface_legend.py", "legend_source_input"),
    ("surface_source_inputs.py", "_annotation_source_input"),
])
def test_new_decimal_owners_require_an_explicit_decimal_seed(tmp_path, filename, owner):
    path = tmp_path / filename
    for seed in ("Decimal(0)", "ZERO"):
        path.write_text(f"from decimal import Decimal\nZERO = Decimal(0)\ndef {owner}(values):\n"
                        f"    return sum(values, {seed})\n", encoding="utf-8")
        assert not violations(tmp_path)
    for arguments in ("values", "values, 0.0", "values, 0", "values, UNKNOWN"):
        path.write_text(f"def {owner}(values):\n    return sum({arguments})\n", encoding="utf-8")
        assert violations(tmp_path) == (f"{filename}:2:E_LAYOUT_FLOAT_SUM_UNCLASSIFIED",)


@pytest.mark.parametrize("expression", [
    "sum(map(len, edges))",
    "sum(len(neighbors) for neighbors in edges)",
])
def test_checker_accepts_integer_length_counts_in_any_owner(tmp_path, expression):
    (tmp_path / "unrelated_owner.py").write_text(
        f"def retained_records(edges):\n    return {expression}\n", encoding="utf-8")
    assert not violations(tmp_path)


@pytest.mark.parametrize("expression", [
    "sum(map(float, edges))",
    "sum(map(custom_length, edges))",
    "sum(map(len, edges), 0.0)",
    "sum((len(neighbors) for neighbors in edges), start=0.0)",
    "sum((len(neighbors) for neighbors in edges), 0.0)",
    "sum(neighbor.width for neighbor in edges)",
    "sum(len(neighbor) + neighbor.width for neighbor in edges)",
])
def test_integer_count_classification_does_not_admit_float_geometry(tmp_path, expression):
    (tmp_path / "unrelated_owner.py").write_text(
        f"def geometry(edges):\n    return {expression}\n", encoding="utf-8")
    assert violations(tmp_path) == ("unrelated_owner.py:2:E_LAYOUT_FLOAT_SUM_UNCLASSIFIED",)
