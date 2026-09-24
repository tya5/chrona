from pathlib import Path

from tools.check_text_encoding import violations


def test_checker_reports_implicit_text_encoding(tmp_path):
    source = tmp_path / "src"; source.mkdir()
    (source / "bad.py").write_text("from pathlib import Path\nPath('x').read_text()\n", encoding="utf-8")
    assert violations((source,)) == [f"{source / 'bad.py'}:2:read_text"]


def test_checker_accepts_explicit_utf8(tmp_path):
    source = tmp_path / "src"; source.mkdir()
    (source / "good.py").write_text("from pathlib import Path\nPath('x').write_text('x', encoding='utf-8')\n", encoding="utf-8")
    assert not violations((source,))
