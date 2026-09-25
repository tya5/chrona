from pathlib import Path

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
