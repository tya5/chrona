"""Reject implicit platform-default text I/O in executable repository roots."""
from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROOTS = (ROOT / "src", ROOT / "tools", ROOT / "conformance")


def violations(roots: tuple[Path, ...] = ROOTS) -> list[str]:
    found: list[str] = []
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                if node.func.attr not in {"read_text", "write_text"}:
                    continue
                if not any(keyword.arg == "encoding" for keyword in node.keywords):
                    try:
                        label = path.relative_to(ROOT).as_posix()
                    except ValueError:
                        label = str(path)
                    found.append(f"{label}:{node.lineno}:{node.func.attr}")
    return found


def main() -> None:
    missing = violations()
    if missing:
        raise SystemExit("E_TEXT_ENCODING_IMPLICIT\n" + "\n".join(missing))


if __name__ == "__main__":
    main()
