"""#1567: an absent contentIdentity is accepted by the example materializer and renderer; a wrong supplied pin is rejected."""
from pathlib import Path
import re
import shutil

import pytest
import yaml

from chrona.usecases.materialize import materialize

ROOT = Path(__file__).resolve().parents[2]
PIN_LINE = re.compile(r"^[ \t]*(?:source)?[cC]ontentIdentity: ?'?sha256:[0-9a-f]{64}'?[ \t]*\n", re.MULTILINE)


def _copy_example(tmp_path: Path) -> Path:
    target = tmp_path / "halcyon-1"
    shutil.copytree(ROOT / "examples" / "halcyon-1", target)
    return target


def _strip_pins(example: Path) -> int:
    removed = 0
    for path in sorted(example.rglob("*.yaml")):
        if "extensions" in path.relative_to(example).parts:
            continue  # a profile package frames its own identity (Spec 62); it is not an authored pin
        text = path.read_text(encoding="utf-8")
        stripped, count = PIN_LINE.subn("", text)
        document = yaml.safe_load(stripped)
        extends = document.get("body", {}).get("extends") if isinstance(document, dict) and isinstance(document.get("body"), dict) else None
        if isinstance(extends, dict) and ("contentIdentity" in extends or "sourceContentIdentity" in extends):
            extends.pop("contentIdentity", None)
            extends.pop("sourceContentIdentity", None)
            stripped, count = yaml.safe_dump(document, sort_keys=False), count + 1
        if count:
            path.write_text(stripped, encoding="utf-8")
            removed += count
    return removed


def test_example_without_any_pin_renders_the_same_picture(tmp_path):
    original = (ROOT / "examples" / "halcyon-1" / "generated").glob("*.svg")
    expected = {path.name: path.read_bytes() for path in original}
    example = _copy_example(tmp_path)
    assert _strip_pins(example) > 0
    # profile package self-identity (Spec 62) and Actual intake source identities are data, not authored pins
    assert not any("ontentIdentity" in path.read_text(encoding="utf-8")
                   for folder in ("contexts", "themes") for path in (example / folder).rglob("*.yaml"))
    assert "ontentIdentity" not in (example / "project.yaml").read_text(encoding="utf-8")
    manifest = yaml.safe_load((example / "manifest.yaml").read_text(encoding="utf-8"))
    slide = manifest["slides"][0]
    # Generated evidence may differ only in identity fields, so refresh it in the copy and compare the picture.
    materialize(example / "manifest.yaml", slide["id"], tmp_path / "out", write=True)
    produced = (example / slide["expectedSvg"]).read_bytes()
    assert produced == expected[Path(slide["expectedSvg"]).name]


def test_a_wrong_supplied_pin_is_still_rejected(tmp_path):
    example = _copy_example(tmp_path)
    _strip_pins(example)
    context = example / "contexts" / "01-mission-brief.yaml"
    document = yaml.safe_load(context.read_text(encoding="utf-8"))
    document["body"]["environment"]["fontMetrics"]["assets"][0]["metrics"]["contentIdentity"] = "sha256:" + "0" * 64
    context.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    manifest = yaml.safe_load((example / "manifest.yaml").read_text(encoding="utf-8"))
    with pytest.raises(Exception, match="IDENTITY"):
        materialize(example / "manifest.yaml", manifest["slides"][0]["id"], tmp_path / "out", write=False)


def test_replace_reruns_into_a_filled_directory_and_refuses_foreign_files(tmp_path):
    example = _copy_example(tmp_path)
    manifest = example / "manifest.yaml"
    slide = yaml.safe_load(manifest.read_text(encoding="utf-8"))["slides"][0]["id"]
    out = tmp_path / "out"
    materialize(manifest, slide, out, write=False)
    with pytest.raises(ValueError, match="E_MATERIALIZER_OUTPUT"):
        materialize(manifest, slide, out, write=False)
    (out / "review.svg").write_bytes(b"stale")
    materialize(manifest, slide, out, write=False, replace=True)
    assert (out / "review.svg").read_bytes() != b"stale"
    (out / "notes.txt").write_text("mine", encoding="utf-8")
    with pytest.raises(ValueError, match="E_MATERIALIZER_OUTPUT"):
        materialize(manifest, slide, out, write=False, replace=True)
    assert (out / "notes.txt").read_text(encoding="utf-8") == "mine"


def _project_with_extension(extension):
    return {"version": "timeline/v0.7", "project": {"id": "p", "title": "P", "calendar": "c"},
            "calendars": {"c": {"working_days": ["mon", "tue", "wed", "thu", "fri"]}},
            "extensions": [extension], "objects": {}, "relations": []}


def test_extension_package_reference_without_a_pin_passes_the_project_schema():
    from chrona.core.validation import validate_project
    pinned = {"packageId": "pkg", "path": "extensions/example.yaml", "revision": "git:" + "0" * 40}
    codes = [item.code for item in validate_project(_project_with_extension(pinned))]
    assert "E_SCHEMA" not in codes and not any("contentIdentity" in str(item) for item in validate_project(_project_with_extension(pinned)))
    wrong_shape = pinned | {"contentIdentity": "not-a-digest"}
    assert validate_project(_project_with_extension(wrong_shape))
