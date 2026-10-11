"""The preset library names only gallery sets that exist (#1403)."""
from pathlib import Path

from chrona.resources import safe_load

from tools.check_preset_gallery_sets import LIBRARY, SETS, unknown_gallery_sets


def test_every_gallery_set_the_library_names_has_a_page():
    entries = safe_load(LIBRARY.read_bytes())["entries"]

    assert unknown_gallery_sets(entries) == []


def test_chrona_preset_list_names_only_existing_sets():
    from chrona.usecases.preset_library import list_builtin_presets

    named = {item["gallerySet"] for item in list_builtin_presets() if "gallerySet" in item}
    assert named <= {path.stem for path in SETS.glob("*.md")} and named  # at least one preset is shown by a set


def test_a_planted_unknown_set_name_fails_the_check(tmp_path: Path):
    (tmp_path / "real-set.md").write_text("# a set\n", encoding="utf-8")
    entries = [{"id": "a", "gallerySet": "real-set"}, {"id": "b", "gallerySet": "removed-set"}, {"id": "c"}]

    assert unknown_gallery_sets(entries, tmp_path) == ["b: removed-set"]
