"""The system bridge is tested without assuming a CI host font."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from chrona.presentation.fonts.system import SystemFontError, resolve_draft_font, resolve_system_font


def _root() -> Path:
    return next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def _face() -> Path:
    return _root() / "src/chrona/resources/fonts/noto-sans-regular-v1.ttf"


def _runner(path: Path):
    def run(command, **_kwargs):
        assert command[:2] == ["fc-match", "--format=%{file}\\n%{family}\\n%{weight}\\n"]
        return SimpleNamespace(stdout=f"{path}\nNoto Sans\n80\n")
    return run


def test_system_font_resolution_verifies_the_actual_face_and_derives_exact_metrics():
    face = resolve_system_font("Noto Sans", 400, runner=_runner(_face()))
    resolved = resolve_draft_font(face)

    assert (face.family, face.weight) == ("Noto Sans", 400)
    assert resolved.metrics.content_identity == resolved.font_file.content_identity == face.content_identity
    assert resolved.metrics.width("111", 12, numeric_spacing="proportional") < resolved.metrics.width(
        "111", 12, numeric_spacing="tabular")


def test_system_font_rejects_a_substituted_family_before_metrics_are_created():
    with pytest.raises(SystemFontError, match="E_FONT_SYSTEM_MISMATCH") as error:
        resolve_system_font("Requested Sans", 400, runner=_runner(_face()))
    assert error.value.detail == "Requested Sans"


def test_system_font_reports_an_unavailable_bridge():
    def unavailable(*_args, **_kwargs):
        raise FileNotFoundError("fc-match")

    with pytest.raises(SystemFontError, match="E_FONT_SYSTEM_UNAVAILABLE"):
        resolve_system_font("Noto Sans", 400, runner=unavailable)


def test_system_font_reports_a_missing_face_and_malformed_resolved_file(tmp_path):
    missing = tmp_path / "missing.ttf"
    with pytest.raises(SystemFontError, match="E_FONT_SYSTEM_MISSING"):
        resolve_system_font("Noto Sans", 400, runner=_runner(missing))

    malformed = tmp_path / "malformed.ttf"
    malformed.write_bytes(b"not a font")
    with pytest.raises(SystemFontError, match="E_FONT_SYSTEM_MISMATCH"):
        resolve_system_font("Noto Sans", 400, runner=_runner(malformed))
