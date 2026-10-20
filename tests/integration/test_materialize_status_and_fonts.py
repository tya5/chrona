"""`chrona materialize` reports like `render` and resolves fonts like `render` (#1842 row 3, #1281 policy)."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml

from chrona.usecases.draft_render import warning_payloads
from chrona.usecases.materialize import materialize
from tests.support.text_treatments import CJK_DESCRIPTOR


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/controller-z-ja"

pytestmark = pytest.mark.skipif(not CJK_DESCRIPTOR.is_file(), reason="requires the optional Noto CJK font provider")


def _example(tmp_path: Path, *, declare_cjk: bool) -> Path:
    """A copy of the ja-JP fixture; `declare_cjk=False` keeps only the bundled Latin faces in its font descriptor,
    as a Context does when it relies on the resolution policy for Japanese text."""
    example = tmp_path / "ja"
    shutil.copytree(FIXTURE, example)
    path = example / "contexts/executive.yaml"
    context = yaml.safe_load(path.read_text(encoding="utf-8"))
    metrics = context["body"]["environment"]["fontMetrics"]
    if not declare_cjk:
        metrics["assets"] = [asset for asset in metrics["assets"] if asset["family"] != "Noto Sans JP"]
    path.write_text(yaml.safe_dump(context, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return example


def _cli(example: Path, output: Path) -> subprocess.CompletedProcess:
    program = "from chrona.app import cli; cli.main()"
    return subprocess.run([sys.executable, "-c", program, "materialize", str(example / "manifest.yaml"),
                           "--slide", "executive", "--output", str(output), "--write"],
                          capture_output=True, text=True, check=False)


@pytest.mark.parametrize("declare_cjk", [True, False], ids=["cjk-declared", "latin-declared-only"])
def test_materialize_prints_the_render_status_and_warnings_json(tmp_path, declare_cjk):
    example = _example(tmp_path, declare_cjk=declare_cjk)
    done = _cli(example, tmp_path / "out")
    assert done.returncode == 0, done.stdout + done.stderr
    payload = json.loads(done.stdout)
    assert set(payload) == {"status", "diagnostics", "warnings"}
    assert payload["status"] == "ok" and payload["diagnostics"] == []
    # the same records `render` would print for this result
    result = materialize(example / "manifest.yaml", "executive", tmp_path / "again", write=True)
    assert payload["warnings"] == json.loads(json.dumps(warning_payloads(result.rendered), ensure_ascii=False))


def test_materialize_resolves_japanese_text_without_a_declared_cjk_face(tmp_path):
    """A Context that declares only Noto Sans renders Japanese text through the #1281 stack, as `render` does.

    The SVG target stages metrics but not font files, so the declared-file lookup used to abandon the whole
    resolution and the first Japanese glyph failed with E_FONT_GLYPH_UNAVAILABLE.
    """
    for name, declare_cjk in (("a", True), ("b", False)):
        (tmp_path / name).mkdir()
        done = _cli(_example(tmp_path / name, declare_cjk=declare_cjk), tmp_path / f"out-{name}")
        assert done.returncode == 0, done.stdout + done.stderr
        assert (tmp_path / f"out-{name}" / "review.svg").read_bytes()
