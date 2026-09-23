import pytest

from chrona.presentation.icons import IconNormalizationError, normalize_icon


def test_normalizes_closed_svg_cubic_and_close():
    icon = normalize_icon("vector", b'<svg viewBox="0 0 24 24"><path d="M0 0 C 1 2 3 4 5 6 Z"/></svg>', (24, 24))
    assert [command.kind for command in icon.paths[0].commands] == ["move", "cubic", "close"]


@pytest.mark.parametrize("payload", (
    b'<svg viewBox="0 0 24 24"><script/></svg>',
    b'<svg viewBox="0 0 24 24"><path style="fill:red" d="M0 0"/></svg>',
    b'<svg viewBox="0 0 24 24"><path d="A 1 1 0 0 1 2 2"/></svg>',
))
def test_rejects_unsafe_svg(payload):
    with pytest.raises(IconNormalizationError):
        normalize_icon("vector", payload, (24, 24))


def test_rejects_png_with_wrong_intrinsic_dimensions():
    payload = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + (23).to_bytes(4, "big") + (24).to_bytes(4, "big")
    with pytest.raises(IconNormalizationError, match="E_ICON_PNG_INVALID"):
        normalize_icon("raster", payload, (24, 24))
