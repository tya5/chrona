from __future__ import annotations

from pathlib import Path

import pytest

from tools.check_documented_commands import discover, discover_prerequisites
from tools.wheel_doc_check import PREREQUISITES, prerequisite_installs

ROOT = Path(__file__).resolve().parents[3]


def test_the_locale_guide_declares_the_cjk_font_prerequisite_before_its_japanese_example():
    assert "cjk-font" in discover_prerequisites(ROOT)
    text = (ROOT / "docs" / "guides" / "locale-and-wording.md").read_text(encoding="utf-8")
    marker = text.index("<!-- chrona:doc-check prerequisite: cjk-font -->")
    assert marker < text.index("--locale ja-JP --output")
    assert "fonts-noto-cjk" in text and "chrona-fonts-noto-cjk" in text and "#1281" in text


def test_the_japanese_command_stays_checked_not_skipped():
    commands = [c for c in discover(ROOT) if "ja-JP" in c.tokens and c.path.name == "locale-and-wording.md"]
    assert commands and all(c.skip_reason is None for c in commands)


def test_a_declared_prerequisite_installs_the_provider_from_the_clone():
    (install,) = prerequisite_installs(ROOT, frozenset({"cjk-font"}))
    assert install == ["install", "--quiet", str(ROOT / "packages" / "chrona-fonts-noto-cjk")]
    assert (ROOT / "packages" / "chrona-fonts-noto-cjk" / "pyproject.toml").is_file()
    assert PREREQUISITES["cjk-font"]


def test_no_declaration_installs_nothing_and_an_unknown_one_is_rejected():
    assert prerequisite_installs(ROOT, frozenset()) == []
    with pytest.raises(SystemExit, match="E_WHEEL_DOC_CHECK_PREREQUISITE_UNKNOWN"):
        prerequisite_installs(ROOT, frozenset({"nope"}))


def test_the_marker_is_ignored_by_the_repository_command_check(tmp_path):
    guide = tmp_path / "docs" / "guides" / "g.md"
    guide.parent.mkdir(parents=True)
    (tmp_path / "README.md").write_text("", encoding="utf-8")
    guide.write_text("<!-- chrona:doc-check prerequisite: cjk-font -->\n\n```sh\nchrona --help\n```\n", encoding="utf-8")
    assert [c.skip_reason for c in discover(tmp_path)] == [None]
    assert discover_prerequisites(tmp_path) == {"cjk-font"}
