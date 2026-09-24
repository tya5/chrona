"""Enforce the compressed primary-wheel budget at release boundaries."""
from __future__ import annotations

import argparse
from pathlib import Path


MAX_PRIMARY_WHEEL_BYTES = 5_000_000


class WheelSizeError(ValueError):
    """The selected primary wheel does not meet the release budget."""


def validate(wheels: list[Path], maximum: int = MAX_PRIMARY_WHEEL_BYTES) -> Path:
    """Return the sole admitted primary wheel or raise a stable release error."""
    if len(wheels) != 1 or wheels[0].suffix != ".whl" or not wheels[0].name.startswith("chrona-"):
        raise WheelSizeError("E_PRIMARY_WHEEL_SELECTION")
    wheel = wheels[0]
    size = wheel.stat().st_size
    if size >= maximum:
        raise WheelSizeError(f"E_PRIMARY_WHEEL_SIZE: {wheel} is {size} bytes; limit is {maximum} bytes")
    return wheel


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("wheel", nargs="+", type=Path)
    parser.add_argument("--max-bytes", type=int, default=MAX_PRIMARY_WHEEL_BYTES)
    args = parser.parse_args()
    try:
        wheel = validate(args.wheel, args.max_bytes)
    except WheelSizeError as error:
        raise SystemExit(str(error)) from error
    print(f"Primary wheel size: PASS ({wheel.stat().st_size} < {args.max_bytes} bytes)")


if __name__ == "__main__":
    main()
