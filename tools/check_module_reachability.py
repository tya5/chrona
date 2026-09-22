"""Report chrona modules that no product entry point can reach."""
from __future__ import annotations
import ast, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src"
ENTRY_POINTS = ("chrona.app.cli",)
ENTRY_SCRIPTS = ("conformance/*.py", "tools/*.py")

def modules() -> dict[str, Path]:
    """Every chrona module. Package ``__init__`` files are structure, not code."""
    found = {}
    for path in (SOURCE / "chrona").rglob("*.py"):
        name = str(path.relative_to(SOURCE)).replace("/", ".")[:-3]
        found[name.removesuffix(".__init__")] = path
    return found


def is_package(path: Path) -> bool:
    return path.name == "__init__.py"

def imports(path: Path, package: str, known: set[str]) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                base = package if node.level == 1 else package.rsplit(".", node.level - 1)[0]
                target = f"{base}.{node.module}" if node.module else base
            elif node.module and node.module.startswith("chrona"):
                target = node.module
            else:
                continue
            out.add(target)
            out.update(f"{target}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Import):
            out.update(alias.name for alias in node.names if alias.name.startswith("chrona"))
    return {name for name in out if name in known}

def main() -> int:
    found = modules()
    known = set(found)
    graph = {
        name: imports(path, name if path.name == "__init__.py" else name.rsplit(".", 1)[0], known)
        for name, path in found.items()
    }
    roots = set(ENTRY_POINTS)
    for pattern in ENTRY_SCRIPTS:
        for script in sorted(ROOT.glob(pattern)):
            roots |= imports(script, "", known)
    reached: set[str] = set()
    stack = [name for name in roots if name in found]
    while stack:
        name = stack.pop()
        if name in reached:
            continue
        reached.add(name)
        stack.extend(graph[name])
    staged = {
        line.split("#", 1)[0].strip()
        for line in (ROOT / "tools/staged_modules.txt").read_text(encoding="utf-8").splitlines()
    } - {""}
    orphans = sorted(name for name in set(found) - reached - staged if not is_package(found[name]))
    revived = sorted(name for name in staged if name in reached)
    for name in orphans:
        print(f"unreachable: {name} ({len(found[name].read_text().splitlines())} lines)")
    for name in revived:
        print(f"listed as staged but now reachable: {name}")
    if orphans or revived:
        print("\nEvery module is product code or is listed in tools/staged_modules.txt with a reason.")
        return 1
    print(f"{len(reached)} modules reachable, {len(staged)} staged, none orphaned")
    return 0

if __name__ == "__main__":
    sys.exit(main())
