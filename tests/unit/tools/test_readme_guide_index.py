"""Every guide in docs/guides is reachable from the README, and the README's local links resolve (#1813)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
README = ROOT / "README.md"
LINK = re.compile(r"\]\((?P<target>[^)\s]+)\)")


def _local_targets() -> list[tuple[str, Path]]:
    found = []
    for match in LINK.finditer(README.read_text(encoding="utf-8")):
        target = match["target"]
        if re.match(r"[a-z][a-z0-9+.-]*:", target) or target.startswith("#"):
            continue
        found.append((target, (ROOT / target.split("#")[0]).resolve()))
    return found


def test_every_guide_is_linked_from_the_readme():
    linked = {path for _, path in _local_targets()}
    missing = sorted(p.name for p in (ROOT / "docs/guides").glob("*.md") if p.resolve() not in linked)
    assert not missing, f"README.md does not link these guides: {missing}"


def test_the_how_do_i_table_is_in_the_quick_start():
    text = README.read_text(encoding="utf-8")
    quick, how, after = (text.index(marker) for marker in ("## Quick start", "### How do I", "## Presentation slides"))
    assert quick < how < after


def test_readme_local_links_resolve():
    broken = [target for target, path in _local_targets() if not path.exists()]
    assert not broken, f"README.md links to missing paths: {broken}"
