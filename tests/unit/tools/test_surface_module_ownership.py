"""Spec 33 section 8.3 names each surface module; the code, the gates and the docstrings must agree (#592)."""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
LAYOUT = ROOT / "src/chrona/presentation/layout"
SPEC = ROOT / "docs/specification/33-intent-oriented-layout.md"


def _spec_modules() -> list[str]:
    section = SPEC.read_text(encoding="utf-8").split("### 8.3 Surface implementation ownership", 1)[1].split("\n## ", 1)[0]
    return re.findall(r"^\| `(surface_\w+)` \|", section, flags=re.MULTILINE)


def _reachability_modules() -> set[str]:
    spec = importlib.util.spec_from_file_location("check_module_reachability", ROOT / "tools/check_module_reachability.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return set(module.modules())


def test_the_ownership_table_names_only_real_modules_the_reachability_gate_covers() -> None:
    names = _spec_modules()
    assert len(names) >= 15  # the table is not silently empty
    covered = _reachability_modules()
    for name in names:
        assert (LAYOUT / f"{name}.py").is_file(), name
        assert f"chrona.presentation.layout.{name}" in covered, name


def test_every_surface_module_is_named_in_the_ownership_table_or_is_a_shared_value_module() -> None:
    named = set(_spec_modules())
    on_disk = {path.stem for path in LAYOUT.glob("surface_*.py")}
    # surface_quality holds immutable placement values shared by every phase; it owns no phase.
    assert on_disk - named == {"surface_quality"}


def test_each_surface_module_docstring_says_what_it_owns_and_what_it_reads() -> None:
    for name in _spec_modules():
        first = (LAYOUT / f"{name}.py").read_text(encoding="utf-8").splitlines()[0]
        assert first.startswith('"""') and "; reads " in first, (name, first)
        assert first.startswith(('"""Owns ', '"""Coordinates ')), (name, first)


def test_the_composer_is_orchestration_sized() -> None:
    lines = (LAYOUT / "surface_composer.py").read_text(encoding="utf-8").splitlines()
    assert len(lines) < 400
