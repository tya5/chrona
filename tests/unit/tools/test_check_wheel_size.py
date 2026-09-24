from pathlib import Path

import pytest

from tools.check_wheel_size import MAX_PRIMARY_WHEEL_BYTES, WheelSizeError, validate


def test_primary_wheel_within_budget_is_accepted(tmp_path: Path):
    wheel = tmp_path / "chrona-0.1.0-py3-none-any.whl"
    wheel.write_bytes(b"x" * 8)
    assert validate([wheel]) == wheel


def test_primary_wheel_at_budget_is_rejected(tmp_path: Path):
    wheel = tmp_path / "chrona-0.1.0-py3-none-any.whl"
    wheel.write_bytes(b"x" * MAX_PRIMARY_WHEEL_BYTES)
    with pytest.raises(WheelSizeError, match="E_PRIMARY_WHEEL_SIZE.*5000000"):
        validate([wheel])


def test_wheel_budget_requires_one_primary_wheel(tmp_path: Path):
    first = tmp_path / "chrona-0.1.0-py3-none-any.whl"; first.write_bytes(b"x")
    second = tmp_path / "other-0.1.0-py3-none-any.whl"; second.write_bytes(b"x")
    with pytest.raises(WheelSizeError, match="E_PRIMARY_WHEEL_SELECTION"):
        validate([first, second])
