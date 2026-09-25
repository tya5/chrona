from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import pytest
import yaml
from fontTools.ttLib import TTCollection, TTFont

from chrona.presentation.fonts import importer
from chrona.presentation.fonts.importer import FontImportError, import_font
from chrona.presentation.model.font_metrics import resolve_font_metrics


def _source() -> Path:
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    return root / "src/chrona/resources/fonts/noto-sans-regular-v1.ttf"


def test_import_static_face_creates_resolvable_declared_pair(tmp_path):
    result = import_font(_source(), tmp_path, family="Private Sans", weight=400)

    assert (tmp_path / result["font"]).read_bytes() == _source().read_bytes()
    descriptor = yaml.safe_load((tmp_path / "font-metrics.yaml").read_text(encoding="utf-8"))
    metric = resolve_font_metrics("Private Sans", descriptor, asset_root=tmp_path)
    assert metric.content_identity == "sha256:" + sha256(_source().read_bytes()).hexdigest()
    assert metric.width("Private", 12) > 0
    assert metric.width("111", 12, numeric_spacing="proportional") < metric.width("111", 12, numeric_spacing="tabular")


def test_import_ttc_extracts_selected_face_as_static_ttf(tmp_path):
    collection = TTCollection()
    collection.fonts = [TTFont(_source()), TTFont(_source())]
    source = tmp_path / "source.ttc"
    collection.save(source)

    result = import_font(source, tmp_path / "output", family="Collection Sans", weight=400, index=1)

    assert result["font"].endswith(".ttf")
    assert TTFont(tmp_path / "output" / result["font"])["head"].unitsPerEm > 0


def test_import_axis_serializes_selected_static_instance(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(importer, "instantiateVariableFont", lambda font, axes, inplace: calls.append(axes) or font)

    result = import_font(_source(), tmp_path, family="Axis Sans", weight=400, axis=("wght=400",))

    assert calls == [{"wght": 400.0}]
    assert TTFont(tmp_path / result["font"])["head"].unitsPerEm > 0


def test_import_rejects_duplicate_without_mutating_existing_descriptor_or_assets(tmp_path):
    import_font(_source(), tmp_path, family="Private Sans", weight=400)
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}

    with pytest.raises(FontImportError, match="E_FONT_IMPORT_DUPLICATE"):
        import_font(_source(), tmp_path, family="Private Sans", weight=400)

    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == before


@pytest.mark.parametrize("axis", [("weight=400",), ("wght=bad",), ("wght=400", "wght=500")])
def test_import_rejects_invalid_axis_before_creating_output(tmp_path, axis):
    with pytest.raises(FontImportError, match="E_FONT_IMPORT_AXIS"):
        import_font(_source(), tmp_path / "output", family="Private Sans", weight=400, axis=axis)
    assert not (tmp_path / "output").exists()
