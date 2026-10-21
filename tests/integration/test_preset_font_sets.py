"""A preset declares the font set it needs, so it renders without an installed CJK face (#429).

The font-poor machine is simulated with an empty installed-font index; no test reads the host's fonts.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

import pytest
import yaml

from chrona.presentation.contracts.font_sets import draft_font_metrics
from chrona.presentation.fonts.installed import InstalledFontIndex, use_installed_fonts
from chrona.operational.store_config import load_store_config
from chrona.operational.store_reads import DraftExtensionPackageReader
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from chrona.usecases.failure_report import StableFailure
from chrona.usecases.preset_library import copy_builtin_preset, list_builtin_presets
from chrona.usecases.render_review import RenderFailed
from tests.support.draft_packages import stage_project_package_store
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


@pytest.fixture(scope="module")
def hiragino(tmp_path_factory):
    """An installed CJK face under the name a Mac has: a renamed copy of the packaged Noto Sans JP."""
    from tests.integration.test_installed_fonts import CJK_FONTS, renamed

    root = tmp_path_factory.mktemp("installed-cjk")
    for weight, name in ((400, "regular"), (700, "bold")):
        renamed(root / f"h-{weight}.ttf", CJK_FONTS / f"noto-sans-jp-{name}-v1.ttf", "Hiragino Sans", weight)
    return InstalledFontIndex([root])


@pytest.fixture
def no_provider(monkeypatch):
    """A plain `pip install chrona`: no `chrona.font-resource-provider` entry point is registered."""
    from chrona.presentation.model import font_resources

    monkeypatch.setattr(font_resources, "entry_points", lambda **_kwargs: ())


def _skipped(rendered) -> list[str]:
    return [item for item in rendered.rendered.scene.diagnostics if item.startswith("W_FONT_FAMILY_SKIPPED")]


@needs_cjk
@pytest.mark.parametrize("identifier", DECLARING)
def test_a_missing_provider_with_an_installed_cjk_face_renders_with_the_skip_warning(starter, no_provider, hiragino, identifier):
    with use_installed_fonts(hiragino):
        rendered = _render(starter, identifier)
    assert rendered.artifact.content
    assert any("role=font-set" in item and "requested=chrona.noto-sans+jp" in item and "skipped=chrona-fonts-noto-cjk" in item
               for item in _skipped(rendered))


@needs_cjk
@pytest.mark.parametrize("identifier", DECLARING)
def test_a_missing_provider_and_no_cjk_face_still_refuses_the_glyph(starter, no_provider, identifier):
    root = starter if identifier == "titlecard" else Path(__file__).resolve().parents[2] / "examples" / "halcyon-1"
    project_path = root / "project.yaml"
    if identifier == "yuya":
        project = yaml.safe_load(project_path.read_text(encoding="utf-8"))
        with TemporaryDirectory(prefix="chrona-fontset-package-store-") as directory:
            config = stage_project_package_store(Path(directory), project, root)
            reader = DraftExtensionPackageReader(lambda: load_store_config(str(config)))
            with use_installed_fonts(NO_FONTS), pytest.raises(RenderFailed) as caught:
                render_draft(DraftRenderRequest(project=project_path, actual=root / "actual.yaml",
                                                target_kind="svg", preset=identifier, package_reader=reader))
    else:
        with use_installed_fonts(NO_FONTS), pytest.raises(RenderFailed) as caught:
            render_draft(DraftRenderRequest(project=project_path, actual=root / "actual.yaml",
                                            target_kind="svg", preset=identifier))
    assert "E_FONT_GLYPH_UNAVAILABLE" in caught.value.code + caught.value.message


@needs_cjk
@pytest.mark.parametrize("identifier", DECLARING)
def test_a_present_provider_is_unchanged_and_not_reported_as_skipped(starter, hiragino, identifier):
    with use_installed_fonts(hiragino):
        rendered = _render(starter, identifier)
    assert not [item for item in _skipped(rendered) if "role=font-set" in item]
    with use_installed_fonts(NO_FONTS):
        assert _render(starter, identifier).artifact.content


def test_a_missing_provider_only_drops_its_assets_from_the_descriptor():
    base = {"algorithm": "declared-metrics-v3", "missingFont": "diagnose", "assets": []}
    kept = draft_font_metrics(("chrona.noto-sans+jp",), base, frozenset({"chrona-fonts-noto-cjk"}))
    families = {item["family"] for item in kept["assets"]}
    assert "Noto Sans JP" not in families and "Noto Sans" in families


@needs_cjk
def test_yuya_renders_the_halcyon_slip_suffix_without_an_installed_cjk_face():
    root = Path(__file__).resolve().parents[2] / "examples" / "halcyon-1"
    project_path = root / "project.yaml"
    project = yaml.safe_load(project_path.read_text(encoding="utf-8"))
    with use_installed_fonts(NO_FONTS):
        with TemporaryDirectory(prefix="chrona-fontset-package-store-") as directory:
            config = stage_project_package_store(Path(directory), project, root)
            reader = DraftExtensionPackageReader(lambda: load_store_config(str(config)))
            rendered = render_draft(DraftRenderRequest(project=project_path, actual=root / "actual.yaml",
                                                       target_kind="svg", preset="yuya", package_reader=reader))
    assert rendered.artifact.content


def _workspace_for(tmp_path: Path, preset: str) -> Path:
    from chrona.usecases.authoring_workspace import create_workspace

    def publish(directory: Path, files) -> None:
        directory.mkdir()
        for name, payload in files.items():
            (directory / name).parent.mkdir(parents=True, exist_ok=True)
            (directory / name).write_bytes(payload)

    return create_workspace(tmp_path / preset, {"id": "guided-fonts", "title": "Guided fonts", "tasks": [
        {"id": "task", "title": "Task", "planned": {"start": "2027-01-04", "finish": "2027-01-09"}}]},
        preset, publish=publish).workspace


@needs_cjk
@pytest.mark.parametrize("identifier", DECLARING)
def test_render_workspace_resolves_the_preset_font_sets_like_render_draft(starter, tmp_path, no_provider, hiragino, identifier):
    """Both routes read the preset's fontSets, so the same Project and preset give the same font warnings (#1891)."""
    from chrona.usecases.guided_render import WorkspaceRenderRequest, render_workspace

    workspace = _workspace_for(tmp_path, identifier)
    with use_installed_fonts(hiragino):
        guided = render_workspace(WorkspaceRenderRequest(workspace, "svg"))
        draft = render_draft(DraftRenderRequest(project=starter / "project.yaml", actual=starter / "actual.yaml",
                                                target_kind="svg", preset=str(workspace.parent / "preset" / "preset.yaml")))
    set_notes = [item for item in _skipped(guided) if "role=font-set" in item]
    assert set_notes and set_notes == [item for item in _skipped(draft) if "role=font-set" in item]
