"""Compile adapter source with the pinned native engines and rasterise it (opt-in, #1532).

`CHRONA_TYPST` and `CHRONA_TECTONIC` name the executables; the typesetter-compile workflow supplies the pinned versions.
Tectonic finds only the bundled Chrona fonts, through a fontconfig file local to the run.
"""
from __future__ import annotations

import html
import os
from io import BytesIO
from pathlib import Path
import subprocess

import pypdfium2 as pdfium
import pytest
import resvg_py
from PIL import Image

FONTS = Path(__file__).resolve().parents[2] / "src/chrona/resources/fonts"


def engine(target: str) -> str:
    executable = os.environ.get("CHRONA_TYPST" if target == "typst" else "CHRONA_TECTONIC")
    if not executable:
        pytest.skip(f"native {target} path absent; the typesetter-compile workflow supplies the pinned engine")
    return executable


def tectonic_source(text: str) -> str:
    """The TikZ source as compiled; the identity, so the engine sees exactly what the adapter wrote."""
    return text


def _pdf_image(path: Path, scale: float = 4) -> Image.Image:
    document = pdfium.PdfDocument(str(path))
    page = document[0]
    bitmap = page.render(scale=scale)
    image = bitmap.to_pil().convert("RGB").copy()
    bitmap.close(), page.close(), document.close()
    return image


def compile_to_image(target: str, source: str, directory: Path, name: str, canvas: tuple[float, float]) -> tuple[Image.Image, Path]:
    """Compile adapter `source` and return the raster (4 px per point) and the compiled source path."""
    executable = engine(target)
    directory.mkdir(parents=True, exist_ok=True)
    if target == "typst":
        path, svg = directory / f"{name}.typ", directory / f"{name}.svg"
        path.write_text(source, encoding="utf-8")
        result = subprocess.run([executable, "compile", "--format", "svg", "--ignore-system-fonts", "--ignore-embedded-fonts",
                                 "--font-path", str(FONTS), str(path), str(svg)], capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stdout + result.stderr
        raster = resvg_py.svg_to_bytes(svg_path=str(svg), font_files=[str(item) for item in FONTS.glob("*.ttf")],
                                       skip_system_fonts=True, width=round(canvas[0] * 4), height=round(canvas[1] * 4), dpi=96)
        return Image.open(BytesIO(raster)).convert("RGB"), path
    path = directory / f"{name}.tex"
    path.write_text(tectonic_source(source), encoding="utf-8")
    config = directory / "fonts.conf"
    (directory / "cache").mkdir(exist_ok=True)
    config.write_text('<?xml version="1.0"?>\n<!DOCTYPE fontconfig SYSTEM "fonts.dtd">\n<fontconfig>\n'
                      f'  <dir>{html.escape(str(FONTS))}</dir>\n  <cachedir>{html.escape(str(directory / "cache"))}</cachedir>\n'
                      "</fontconfig>\n", encoding="utf-8")
    env = {**os.environ, "FONTCONFIG_FILE": str(config)}
    result = subprocess.run([executable, "--outdir", str(directory), "--keep-logs", str(path)],
                            capture_output=True, text=True, timeout=300, env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    pdf = path.with_suffix(".pdf")
    assert pdf.is_file() and pdf.stat().st_size > 0
    return _pdf_image(pdf), path
