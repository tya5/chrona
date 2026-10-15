"""A preset declares the font set it needs, so it renders without an installed CJK face (#429).

The font-poor machine is simulated with an empty installed-font index; no test reads the host's fonts.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest
import yaml

from chrona.presentation.contracts.font_sets import draft_font_metrics
from chrona.presentation.fonts.installed import InstalledFontIndex, use_installed_fonts
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from chrona.usecases.failure_report import StableFailure
from chrona.usecases.preset_library import copy_builtin_preset, list_builtin_presets
from chrona.usecases.render_review import RenderFailed
from tests.support import text_treatments as tt

DECLARING = ("titlecard", "yuya")
NO_FONTS = InstalledFontIndex((), files=())
needs_cjk = pytest.mark.skipif(not tt.cjk_available(), reason="requires the chrona-fonts-noto-cjk package")


@pytest.fixture(scope="module")
def starter(tmp_path_factory):
    root = tmp_path_factory.mktemp("fontsets")
    done = subprocess.run([sys.executable, "-c", "from chrona.app.cli import main; main()", "init", "p"], cwd=root,
                          capture_output=True, text=True, timeout=300)
    assert done.returncode == 0, done.stdout + done.stderr
    return root / "p"


def _render(starter: Path, preset: str):
    return render_draft(DraftRenderRequest(project=starter / "project.yaml", actual=starter / "actual.yaml",
                                           target_kind="svg", preset=preset))


def _copy_without_font_sets(tmp_path: Path, identifier: str) -> Path:
    target = copy_builtin_preset(identifier, tmp_path / identifier)
    document = yaml.safe_load(target.read_text(encoding="utf-8"))
    del document["body"]["resources"]["fontSets"]
    target.write_text(yaml.safe_dump(document), encoding="utf-8")
    return target


def test_the_catalogue_entries_that_need_cjk_declare_the_font_set():
    from chrona.usecases.preset_library import _library

    declared = {entry["id"]: entry["members"].get("fontSets") for entry in _library()}
    assert {name for name, value in declared.items() if value} == set(DECLARING)
    assert all(declared[name] == ["chrona.noto-sans+jp"] for name in DECLARING)
    assert set(DECLARING) <= {item["id"] for item in list_builtin_presets()}


@pytest.mark.parametrize("identifier", DECLARING)
def test_preset_copy_carries_the_declaration_and_no_font_bytes(tmp_path, identifier):
    target = copy_builtin_preset(identifier, tmp_path / "copy")
    document = yaml.safe_load(target.read_text(encoding="utf-8"))
    assert document["body"]["resources"]["fontSets"] == ["chrona.noto-sans+jp"]
    assert not [path for path in (tmp_path / "copy").rglob("*") if path.suffix in {".ttf", ".otf", ".ttc"}]


def test_other_presets_declare_nothing(tmp_path):
    target = copy_builtin_preset("editorial", tmp_path / "copy")
    assert "fontSets" not in yaml.safe_load(target.read_text(encoding="utf-8"))["body"]["resources"]


@needs_cjk
@pytest.mark.parametrize("identifier", DECLARING)
def test_a_declaring_preset_renders_on_a_machine_without_a_cjk_face(starter, identifier):
    with use_installed_fonts(NO_FONTS):
        rendered = _render(starter, identifier)
    assert rendered.artifact.content


@needs_cjk
def test_the_same_preset_without_the_declaration_refuses(starter, tmp_path):
    path = _copy_without_font_sets(tmp_path, "titlecard")
    with use_installed_fonts(NO_FONTS), pytest.raises(RenderFailed) as caught:
        render_draft(DraftRenderRequest(project=starter / "project.yaml", actual=starter / "actual.yaml",
                                        target_kind="svg", preset=str(path)))
    assert "E_FONT_GLYPH_UNAVAILABLE" in caught.value.code + caught.value.message


def test_the_descriptor_is_the_deduplicated_union_of_the_named_sets():
    base = {"algorithm": "declared-metrics-v3", "missingFont": "diagnose", "assets": []}
    union = draft_font_metrics(("chrona.noto-sans", "chrona.noto-sans+jp"), base)
    keys = [(item["family"], item["weight"]) for item in union["assets"]]
    assert len(keys) == len(set(keys)) and ("Noto Sans JP", 400) in keys and ("Noto Sans", 700) in keys
    assert union["algorithm"] == "declared-metrics-v3" and "fontSet" not in union


def test_without_the_cjk_package_a_declaring_preset_fails_loudly(starter, monkeypatch):
    from chrona.presentation.model import font_resources

    monkeypatch.setattr(font_resources, "entry_points", lambda **_kwargs: ())
    with use_installed_fonts(NO_FONTS), pytest.raises((RenderFailed, StableFailure, Exception)) as caught:
        _render(starter, "titlecard")
    text = str(caught.value) + getattr(caught.value, "code", "") + getattr(caught.value, "message", "") + str(getattr(caught.value, "detail", ""))
    assert "E_FONT_METRICS_UNAVAILABLE" in text and "chrona-fonts-noto-cjk" in text


@needs_cjk
def test_yuya_renders_the_halcyon_slip_suffix_without_an_installed_cjk_face():
    root = Path(__file__).resolve().parents[2] / "examples" / "halcyon-1"
    with use_installed_fonts(NO_FONTS):
        rendered = render_draft(DraftRenderRequest(project=root / "project.yaml", actual=root / "actual.yaml",
                                                   target_kind="svg", preset="yuya"))
    assert rendered.artifact.content
