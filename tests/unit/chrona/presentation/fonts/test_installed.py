"""Installed fonts as a normal source (#1281): discovery by scanning directories, CSS weight matching, no fontconfig.

Every test builds its own font directory from the packaged faces (renamed copies); none reads the host's fonts.
"""
from __future__ import annotations

import logging
from pathlib import Path
import subprocess

from fontTools.ttLib import TTCollection, TTFont
import pytest

from chrona.presentation.fonts.installed import (
    InstalledFontIndex, default_font_directories, fontconfig_files, installed_fonts, use_installed_fonts)

PACKAGED = Path(__file__).resolve().parents[5] / "src/chrona/resources/fonts"
REGULAR = PACKAGED / "noto-sans-regular-v1.ttf"


def renamed(target: Path, family: str, weight: int, *, legacy_suffix: str = "", italic: bool = False) -> Path:
    """A copy of the packaged regular face under another family name and weight."""
    logging.getLogger("fontTools").setLevel(logging.ERROR)
    font = TTFont(REGULAR)
    names = font["name"]
    for item in (1, 2, 4, 6, 16, 17):
        names.removeNames(nameID=item)
    names.setName(family + legacy_suffix, 1, 3, 1, 0x409)
    names.setName("Regular", 2, 3, 1, 0x409)
    names.setName(family, 16, 3, 1, 0x409)
    font["OS/2"].usWeightClass = weight
    if italic:
        font["OS/2"].fsSelection |= 1
    font.save(target)
    return target


def test_a_face_is_found_by_family_name_and_ignores_italic_and_unreadable_files(tmp_path):
    renamed(tmp_path / "a.ttf", "Acme Sans", 400)
    renamed(tmp_path / "b-italic.ttf", "Acme Sans", 400, italic=True)
    (tmp_path / "broken.ttf").write_bytes(b"not a font")
    (tmp_path / "notes.txt").write_text("not a font file")
    index = InstalledFontIndex([tmp_path])

    assert [(face.family, face.weight) for face in index.faces()] == [("Acme Sans", 400)]
    assert index.find("acme sans", 400).path == tmp_path / "a.ttf"
    assert index.find("Missing Sans", 400) is None


def test_the_legacy_family_name_with_a_style_word_is_also_answered(tmp_path):
    renamed(tmp_path / "w.ttf", "Acme Sans", 300, legacy_suffix=" W3")
    index = InstalledFontIndex([tmp_path])

    assert index.find("Acme Sans", 300) is not None and index.find("Acme Sans W3", 300) is not None


@pytest.mark.parametrize("wanted,expected", [(400, 300), (300, 300), (200, 300), (700, 600), (600, 600), (900, 600),
                                             (500, 300)])
def test_the_weight_nearest_by_the_css_rule_is_chosen(tmp_path, wanted, expected):
    renamed(tmp_path / "light.ttf", "Acme Sans", 300)
    renamed(tmp_path / "semi.ttf", "Acme Sans", 600)

    assert InstalledFontIndex([tmp_path]).find("Acme Sans", wanted).weight == expected


def test_the_regular_range_prefers_the_next_heavier_face_up_to_500(tmp_path):
    renamed(tmp_path / "medium.ttf", "Acme Sans", 500)
    renamed(tmp_path / "bold.ttf", "Acme Sans", 700)

    assert InstalledFontIndex([tmp_path]).find("Acme Sans", 400).weight == 500


def test_a_collection_file_yields_each_of_its_faces(tmp_path):
    first = renamed(tmp_path / "one.ttf", "Acme Sans", 300)
    second = renamed(tmp_path / "two.ttf", "Acme Sans", 600)
    collection = TTCollection()
    collection.fonts = [TTFont(first), TTFont(second)]
    collection.save(tmp_path / "pair.ttc")
    first.unlink()
    second.unlink()
    index = InstalledFontIndex([tmp_path])
    found = index.find("Acme Sans", 600)

    assert [(face.weight, face.index) for face in index.faces()] == [(300, 0), (600, 1)]
    assert found.path == tmp_path / "pair.ttc" and found.index == 1


def test_the_index_is_built_once(tmp_path):
    renamed(tmp_path / "a.ttf", "Acme Sans", 400)
    index = InstalledFontIndex([tmp_path])
    first = index.faces()
    (tmp_path / "a.ttf").unlink()

    assert index.faces() is first


def test_the_standard_directories_of_each_platform(tmp_path):
    home = tmp_path / "home"
    mac = default_font_directories(platform="darwin", environ={}, home=home)
    windows = default_font_directories(platform="win32", environ={"WINDIR": r"C:\Windows", "LOCALAPPDATA": r"C:\Users\x\AppData\Local"},
                                       home=home)
    linux = default_font_directories(platform="linux", environ={"XDG_DATA_DIRS": "/opt/share"}, home=home)

    assert Path("/System/Library/Fonts") in mac and Path("/Library/Fonts") in mac and home / "Library/Fonts" in mac
    assert any(item.name == "Fonts" and "Windows" in str(item) for item in windows)
    assert any("Microsoft" in str(item) for item in windows)
    assert home / ".local/share/fonts" in linux and Path("/opt/share/fonts") in linux and home / ".fonts" in linux


def test_the_extra_directory_variable_adds_to_the_standard_ones(tmp_path):
    extra = default_font_directories(platform="linux", environ={"CHRONA_FONT_PATH": f"{tmp_path}"}, home=tmp_path)

    assert extra[-1] == tmp_path


def test_fontconfig_is_used_when_present_and_absent_means_the_directory_scan():
    def listed(*_args, **_kwargs):
        return subprocess.CompletedProcess([], 0, stdout="/fonts/a.ttf\n/fonts/b.otf\n", stderr="")

    def absent(*_args, **_kwargs):
        raise FileNotFoundError("fc-list")

    assert fontconfig_files(runner=listed) == (Path("/fonts/a.ttf"), Path("/fonts/b.otf"))
    assert fontconfig_files(runner=absent) is None


def test_an_injected_index_replaces_the_hosts_for_its_scope(tmp_path):
    renamed(tmp_path / "a.ttf", "Acme Sans", 400)
    with use_installed_fonts(InstalledFontIndex([tmp_path])) as injected:
        assert installed_fonts() is injected
        assert installed_fonts().find("Acme Sans", 400) is not None
    assert installed_fonts() is not injected


def test_discovery_over_a_face_with_an_old_created_timestamp_writes_nothing_to_stderr(tmp_path, capfd):
    """#1369: fontTools warns `'created' timestamp seems very low` per face; the scan must stay silent and leave logging as it found it."""
    font = TTFont(REGULAR)
    font["head"].created = 0  # 1904-01-01, what some system faces carry
    font.save(tmp_path / "old.ttf")
    logger = logging.getLogger("fontTools")
    handler = logging.StreamHandler()  # the stderr handler the CLI's unconfigured logging ends up with
    previous_level, previous_handlers = logger.level, list(logger.handlers)
    logger.setLevel(logging.NOTSET)
    logger.addHandler(handler)
    try:
        faces = InstalledFontIndex([tmp_path]).faces()
        assert [face.path.name for face in faces] == ["old.ttf"]
        assert logger.level == logging.NOTSET  # restored
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
        logger.handlers[:] = previous_handlers
    captured = capfd.readouterr()
    assert captured.err == "" and captured.out == ""
