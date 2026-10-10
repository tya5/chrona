"""Installed fonts as a normal source: discovery by scanning font directories, no fontconfig requirement (#1281).

An installed face is found by family name and CSS-style weight matching. macOS and Windows have no fontconfig, so the
standard font directories are scanned and each file's family and weight are read from its name and OS/2 tables
(TrueType collections included). On Linux fontconfig is used when its `fc-list` is present, else the XDG font
directories. The index is built once per process; tests inject their own directories and never read the host's.
Output that uses an installed face depends on the fonts installed where it is rendered, which is intended.
"""
from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
import logging
import os
from pathlib import Path
from struct import error as struct_error  # fontTools raises struct.error on truncated tables
import subprocess
import sys

from fontTools.ttLib import TTCollection, TTFont, TTLibError

FONT_SUFFIXES = frozenset({".ttf", ".otf", ".ttc", ".otc"})
PATH_VARIABLE = "CHRONA_FONT_PATH"  # extra directories, separated like PATH


@dataclass(frozen=True)
class InstalledFace:
    """One upright face of an installed font file (a collection file holds several)."""

    path: Path
    index: int
    family: str
    names: frozenset[str]  # case-folded family names this face answers to (typographic and legacy family)
    weight: int
    width: int = 5


def default_font_directories(*, platform: str | None = None, environ: Mapping[str, str] | None = None,
                             home: Path | None = None) -> tuple[Path, ...]:
    """The standard font directories of a platform, then any `CHRONA_FONT_PATH` additions."""
    env = os.environ if environ is None else environ
    user = Path.home() if home is None else home
    system = sys.platform if platform is None else platform
    if system == "darwin":
        directories = [Path("/System/Library/Fonts"), Path("/Library/Fonts"), user / "Library/Fonts"]
    elif system.startswith("win"):
        windir = Path(env.get("WINDIR", env.get("SystemRoot", r"C:\Windows")))
        local = env.get("LOCALAPPDATA")
        directories = [windir / "Fonts"] + ([Path(local) / "Microsoft" / "Windows" / "Fonts"] if local else [])
    else:
        data_home = Path(env["XDG_DATA_HOME"]) if env.get("XDG_DATA_HOME") else user / ".local/share"
        data_dirs = [Path(item) for item in env.get("XDG_DATA_DIRS", "/usr/local/share:/usr/share").split(":") if item]
        directories = [data_home / "fonts", user / ".fonts", *(item / "fonts" for item in data_dirs)]
    directories += [Path(item) for item in env.get(PATH_VARIABLE, "").split(os.pathsep) if item]
    return tuple(directories)


@contextmanager
def _quiet_fonttools() -> Iterator[None]:
    """Discovery reads every installed face; fontTools warns about each odd one (`'created' timestamp seems very low` on macOS).

    Those warnings are about a font file we only index, not about the render: silence them for the scan, and restore the level (#1369).
    """
    logger = logging.getLogger("fontTools")
    previous = logger.level
    logger.setLevel(logging.ERROR)
    try:
        yield
    finally:
        logger.setLevel(previous)


def _name_values(font: TTFont, name_ids: Iterable[int]) -> list[str]:
    values: list[str] = []
    for record in font["name"].names:
        if record.nameID in name_ids:
            try:
                text = record.toUnicode().strip()
            except (UnicodeDecodeError, ValueError):
                continue
            if text and text not in values:
                values.append(text)
    return values


def _face(path: Path, font: TTFont, index: int) -> InstalledFace | None:
    try:
        typographic = _name_values(font, (16,))
        legacy = _name_values(font, (1,))
        os2 = font["OS/2"] if "OS/2" in font else None
        weight = int(getattr(os2, "usWeightClass", 400)) if os2 is not None else 400
        italic = bool(os2 is not None and getattr(os2, "fsSelection", 0) & 1) or bool(
            "head" in font and font["head"].macStyle & 2)
        width = int(getattr(os2, "usWidthClass", 5)) if os2 is not None else 5
    except (KeyError, AttributeError, UnicodeDecodeError, ValueError):
        return None
    family = (typographic or legacy or [""])[0]
    if italic or not family:
        return None
    return InstalledFace(path, index, family, frozenset(name.casefold() for name in typographic + legacy),
                         weight if 1 <= weight <= 1000 else 400, width)


def _faces_in(path: Path) -> Iterator[InstalledFace]:
    try:
        if path.suffix.lower() in {".ttc", ".otc"}:
            collection = TTCollection(path, lazy=True)
            for index, font in enumerate(collection.fonts):
                face = _face(path, font, index)
                if face is not None:
                    yield face
        else:
            face = _face(path, TTFont(path, lazy=True, recalcTimestamp=False), 0)
            if face is not None:
                yield face
    except (OSError, TTLibError, KeyError, ValueError, AssertionError, struct_error):
        return


def _files_under(directory: Path) -> Iterator[Path]:
    try:
        entries = sorted(directory.rglob("*"))
    except OSError:
        return
    for entry in entries:
        if entry.suffix.lower() in FONT_SUFFIXES and entry.is_file():
            yield entry


def fontconfig_files(*, runner: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> tuple[Path, ...] | None:
    """The font files fontconfig lists, or None when `fc-list` is not installed or fails."""
    try:
        result = runner(["fc-list", "--format", "%{file}\\n"], check=True, capture_output=True, text=True)
    except (FileNotFoundError, subprocess.CalledProcessError, OSError):
        return None
    files = sorted({Path(line) for line in result.stdout.splitlines() if line.strip()})
    return tuple(files) or None


class InstalledFontIndex:
    """Faces found in a set of directories (and optionally explicit files), built once and cached."""

    def __init__(self, directories: Iterable[Path] | None = None, *, files: Iterable[Path] = ()) -> None:
        self._directories = tuple(Path(item) for item in (default_font_directories() if directories is None else directories))
        self._files = tuple(Path(item) for item in files)
        self._faces: tuple[InstalledFace, ...] | None = None

    @classmethod
    def from_host(cls, *, platform: str | None = None,
                  runner: Callable[..., subprocess.CompletedProcess] = subprocess.run) -> "InstalledFontIndex":
        """The host's fonts: fontconfig's list on Linux when present, otherwise the standard directories."""
        system = sys.platform if platform is None else platform
        if system.startswith("linux"):
            listed = fontconfig_files(runner=runner)
            if listed is not None:
                extra = tuple(Path(item) for item in os.environ.get(PATH_VARIABLE, "").split(os.pathsep) if item)
                return cls(extra, files=listed)
        return cls(default_font_directories(platform=system))

    def faces(self) -> tuple[InstalledFace, ...]:
        if self._faces is None:
            paths = list(self._files)
            for directory in self._directories:
                paths.extend(_files_under(directory))
            found: list[InstalledFace] = []
            with _quiet_fonttools():
                for path in dict.fromkeys(paths):
                    found.extend(_faces_in(path))
            self._faces = tuple(sorted(found, key=lambda face: (face.family.casefold(), face.weight, str(face.path), face.index)))
        return self._faces

    def find(self, family: str, weight: int) -> InstalledFace | None:
        """The upright face of `family` nearest `weight` by the CSS font-weight rule, or None when not installed."""
        wanted = family.strip().strip("'\"").casefold()
        candidates = [face for face in self.faces() if wanted in face.names]
        if not candidates:
            return None
        return min(candidates, key=lambda face: (_weight_rank(weight, face.weight), abs(face.width - 5), str(face.path), face.index))


def _weight_rank(wanted: int, actual: int) -> tuple[int, int]:
    """CSS font-matching order: how far down the list this weight is, and the distance within its step."""
    if actual == wanted:
        return (0, 0)
    if 400 <= wanted <= 500:
        if wanted < actual <= 500:
            return (1, actual - wanted)
        if actual < wanted:
            return (2, wanted - actual)
        return (3, actual - wanted)
    if wanted < 400:
        if actual < wanted:
            return (1, wanted - actual)
        return (2, actual - wanted)
    if actual > wanted:
        return (1, actual - wanted)
    return (2, wanted - actual)


_default_index: InstalledFontIndex | None = None
_override: InstalledFontIndex | None = None


def installed_fonts() -> InstalledFontIndex:
    """The index used to resolve installed faces: an injected one, else the host's (built once per process)."""
    global _default_index
    if _override is not None:
        return _override
    if _default_index is None:
        _default_index = InstalledFontIndex.from_host()
    return _default_index


@contextmanager
def use_installed_fonts(index: InstalledFontIndex) -> Iterator[InstalledFontIndex]:
    """Resolve installed faces from `index` for the duration (tests inject theirs; none reads the host's fonts)."""
    global _override
    previous, _override = _override, index
    try:
        yield index
    finally:
        _override = previous
