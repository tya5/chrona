"""Finalize one CI job after independently reported required steps."""
from __future__ import annotations

import argparse


KNOWN = frozenset({"success", "failure", "cancelled", "skipped"})


def _entry(value: str) -> tuple[str, str]:
    name, separator, status = value.partition("=")
    if not separator or not name or status not in KNOWN:
        raise ValueError("E_CI_OUTCOME_INPUT")
    return name, status


def assess(*, required: tuple[tuple[str, str], ...], dependent: tuple[tuple[str, str], ...]) -> tuple[str, ...]:
    """Return deterministic outcome violations without invoking a shell."""
    failures = tuple(name for name, status in required if status != "success")
    if failures:
        expected = "skipped"
        return tuple(f"E_CI_REQUIRED_STEP:{name}:{status}" for name, status in required if status != "success") + tuple(
            f"E_CI_DEPENDENT_STEP:{name}:{status}:expected={expected}" for name, status in dependent if status != expected)
    return tuple(f"E_CI_DEPENDENT_STEP:{name}:{status}:expected=success" for name, status in dependent if status != "success")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--required", action="append", default=[])
    parser.add_argument("--dependent", action="append", default=[])
    args = parser.parse_args()
    try:
        required = tuple(_entry(value) for value in args.required)
        dependent = tuple(_entry(value) for value in args.dependent)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    violations = assess(required=required, dependent=dependent)
    if violations:
        print("\n".join(violations))
        return 1
    print("CI outcomes: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
