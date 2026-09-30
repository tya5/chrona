"""#662 S5: archived historical schema files stay archived and unread."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
ARCHIVE = ROOT / "docs" / "archive" / "schemas"
ARCHIVED = sorted(path.name for path in ARCHIVE.glob("*.schema.yaml"))
# Executable surface: a file here that names an archived schema is a reader of it.
SCANNED_DIRECTORIES = ("src", "tools", "tests", "conformance", ".github")
SCANNED_FILES = ("pyproject.toml",)
# The S0 baseline records historical verdicts by schema name and is regenerated, not read as a schema.
SKIPPED_PARTS = {"schema-equivalence", "__pycache__"}
TEXT_SUFFIXES = {".py", ".yaml", ".yml", ".json", ".toml", ".md", ".txt", ".cfg", ".sh"}


def _scanned_files() -> list[Path]:
    files = [ROOT / name for name in SCANNED_FILES]
    for directory in SCANNED_DIRECTORIES:
        for path in (ROOT / directory).rglob("*"):
            if not path.is_file() or path.suffix not in TEXT_SUFFIXES or path == Path(__file__).resolve():
                continue
            relative = path.relative_to(ROOT).parts
            if SKIPPED_PARTS & set(relative):
                continue
            files.append(path)
    return files


def _identifiers(name: str) -> list[str]:
    declared = re.search(r"^\$id:\s*[\"']?([^\"'\s]+)", (ARCHIVE / name).read_text(encoding="utf-8"), re.MULTILINE)
    assert declared, name
    return [name, name.removesuffix(".schema.yaml"), declared[1]]


def test_archive_holds_schema_files_and_a_readme():
    assert (ARCHIVE / "README.md").is_file()
    assert ARCHIVED, "the archive folder has no schema files"


def test_archived_schema_is_not_in_schemas_directory_or_inventory():
    inventory = yaml.safe_load((ROOT / "schemas" / "schema-inventory-v0.1.yaml").read_text(encoding="utf-8"))
    listed = {entry["file"] for entry in inventory["schemas"]}
    for name in ARCHIVED:
        assert not (ROOT / "schemas" / name).exists(), name
        assert name not in listed, name


def test_no_executable_file_names_an_archived_schema():
    owner = {text: name for name in ARCHIVED for text in _identifiers(name)}
    pattern = re.compile(r"(?<![A-Za-z0-9-])(" + "|".join(re.escape(text) for text in sorted(owner, key=len, reverse=True)) + r")(?![0-9])")
    offenders: list[str] = []
    for path in _scanned_files():
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for match in pattern.finditer(text):
            offenders.append(f"{path.relative_to(ROOT)} names {owner[match[1]]}")
    assert not offenders, sorted(set(offenders))
