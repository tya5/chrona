from pathlib import Path

import pytest
import yaml

from chrona.usecases.deck_context import load_deck_manifest, select_deck_context
from chrona.usecases.failure_report import StableFailure


ROOT = Path(__file__).resolve().parents[4]


def _manifest(tmp_path: Path, *, extra: str = "") -> Path:
    source = ROOT / "tests/fixtures/aster-ssd/contexts/01-overview.yaml"
    context = yaml.safe_load(source.read_bytes())
    document = {
        "version": "chrona/example-materializer/v0.1",
        "id": "sample-deck",
        "role": "regression-corpus",
        "contextDefaults": context["body"],
        "slides": [{"id": "overview", "contextOverrides": {"id": context["id"]},
                    "evidence": "test", "expectedSvg": "generated/overview.svg"}],
    }
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return path


def test_manifest_schema_errors_keep_selected_slide_and_exact_unknown_pointer(tmp_path):
    path = _manifest(tmp_path)
    raw = yaml.safe_load(path.read_bytes())
    raw["slides"][0]["unexpected/key"] = True
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(StableFailure) as caught:
        select_deck_context(path, load_deck_manifest(path), "overview")

    assert caught.value.code == "E_MATERIALIZER_MANIFEST_SCHEMA"
    assert caught.value.source_ref == "/slides/0/unexpected~1key"
    assert "overview" in caught.value.message


def test_manifest_root_schema_errors_still_name_selected_slide(tmp_path):
    path = _manifest(tmp_path)
    raw = yaml.safe_load(path.read_bytes())
    raw["unexpected"] = True
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(StableFailure) as caught:
        select_deck_context(path, load_deck_manifest(path), "overview")

    assert caught.value.source_ref == "/unexpected"
    assert "slide overview" in caught.value.message


def test_explicit_context_uses_store_address_grammar_and_preserves_exact_bytes(tmp_path):
    path = _manifest(tmp_path)
    raw = yaml.safe_load(path.read_bytes())
    raw.pop("contextDefaults")
    address = "_deck-contexts/sample-deck/overview.yaml"
    raw["slides"][0].pop("contextOverrides")
    raw["slides"][0]["context"] = address
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    source = ROOT / "tests/fixtures/aster-ssd/contexts/01-overview.yaml"
    exact = source.read_bytes()
    target = tmp_path / address
    target.parent.mkdir(parents=True)
    target.write_bytes(exact)

    selected = select_deck_context(path, load_deck_manifest(path), "overview")

    assert selected.address == address
    assert selected.source_path == target.resolve()
    assert selected.payload == exact


def test_explicit_context_keeps_existing_yaml_merge_syntax_and_raw_payload(tmp_path):
    path = _manifest(tmp_path)
    raw = yaml.safe_load(path.read_bytes())
    raw.pop("contextDefaults")
    raw["slides"][0].pop("contextOverrides")
    raw["slides"][0]["context"] = "contexts/merged.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    target = tmp_path / "contexts/merged.yaml"
    target.parent.mkdir()
    exact = (b"version: chrona/render-context/v0.17\nkind: render-context\nid: explicit\n"
             b"body:\n  <<: &defaults {forecast: false}\n  forecast: true\n")
    target.write_bytes(exact)

    selected = select_deck_context(path, load_deck_manifest(path), "overview")

    assert selected.payload == exact
    assert selected.body["forecast"] is True


def test_shared_store_root_may_be_a_sibling_relative_path(tmp_path):
    path = _manifest(tmp_path)
    raw = yaml.safe_load(path.read_bytes())
    raw["stores"] = [{"identity": "shared", "root": "../shared"}]
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    selected = select_deck_context(path, load_deck_manifest(path), "overview")

    assert selected.source_mode == "composed"


def test_merge_keys_are_rejected_at_their_source_pointer(tmp_path):
    path = tmp_path / "manifest.yaml"
    path.write_text(
        "version: chrona/example-materializer/v0.1\n"
        "id: sample-deck\nrole: regression-corpus\nslides: []\n"
        "contextDefaults: &defaults {project: {id: p}}\n"
        "other: {<<: *defaults}\n", encoding="utf-8")

    with pytest.raises(StableFailure) as caught:
        load_deck_manifest(path)

    assert caught.value.code == "E_MATERIALIZER_YAML_MERGE"
    assert caught.value.source_ref == "/other"


def test_null_defaults_are_omitted_from_the_completed_context(tmp_path):
    path = _manifest(tmp_path)
    raw = yaml.safe_load(path.read_bytes())
    raw["contextDefaults"]["forecast"] = None
    raw["contextDefaults"].setdefault("inputs", {})["snapshot"] = None
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    selected = select_deck_context(path, load_deck_manifest(path), "overview")

    assert "forecast" not in selected.body
    assert selected.body.get("inputs", {}).get("snapshot") is None
    assert "/body/forecast" in selected.origins


def test_atomic_reference_override_replaces_defaults_and_owns_nested_origin(tmp_path):
    path = _manifest(tmp_path)
    raw = yaml.safe_load(path.read_bytes())
    replacement = dict(raw["contextDefaults"]["project"])
    replacement["id"] = "replacement-project"
    raw["slides"][0]["contextOverrides"]["body"] = {"project": replacement}
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    selected = select_deck_context(path, load_deck_manifest(path), "overview")

    assert selected.body["project"] == replacement
    assert selected.origins["/body/project"].source_ref == "/slides/0/contextOverrides/body/project"
    from chrona.usecases.deck_context import _origin_for
    origin = _origin_for(selected.origins, "/body/project/revision/token")
    assert origin is not None
    assert origin.source_ref == "/slides/0/contextOverrides/body/project/revision/token"


def test_overrides_are_per_slide_and_do_not_mutate_shared_defaults(tmp_path):
    path = _manifest(tmp_path)
    raw = yaml.safe_load(path.read_bytes())
    second = dict(raw["slides"][0])
    second["id"] = "delivery"
    second["contextOverrides"] = {"id": "delivery-context", "body": {"forecast": True}}
    raw["slides"].append(second)
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    manifest = load_deck_manifest(path)

    first_context = select_deck_context(path, manifest, "overview")
    second_context = select_deck_context(path, manifest, "delivery")

    assert "forecast" not in first_context.body
    assert second_context.body["forecast"] is True
    assert raw["contextDefaults"].get("forecast") is None


def test_unselected_slide_schema_errors_are_not_hidden_by_selection(tmp_path):
    path = _manifest(tmp_path)
    raw = yaml.safe_load(path.read_bytes())
    second = dict(raw["slides"][0])
    second["id"] = "delivery"
    second["notDeclared"] = True
    raw["slides"].append(second)
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(StableFailure) as caught:
        select_deck_context(path, load_deck_manifest(path), "overview")

    assert caught.value.source_ref == "/slides/1/notDeclared"
    assert "overview" in caught.value.message


def test_duplicate_slide_ids_are_rejected_at_the_second_declaration(tmp_path):
    path = _manifest(tmp_path)
    raw = yaml.safe_load(path.read_bytes())
    raw["slides"].append(dict(raw["slides"][0]))
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(StableFailure) as caught:
        select_deck_context(path, load_deck_manifest(path), "overview")

    assert caught.value.code == "E_MATERIALIZER_SLIDE_ID_DUPLICATE"
    assert caught.value.source_ref == "/slides/1/id"


def test_context_defaults_alone_do_not_implicitly_select_a_slide_source(tmp_path):
    path = _manifest(tmp_path)
    raw = yaml.safe_load(path.read_bytes())
    raw["slides"][0].pop("contextOverrides")
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(StableFailure) as caught:
        select_deck_context(path, load_deck_manifest(path), "overview")

    assert caught.value.code == "E_MATERIALIZER_CONTEXT_SOURCE"
    assert caught.value.source_ref == "/slides/0"


@pytest.mark.parametrize("override", [False, True])
def test_nested_invalid_reference_reports_the_authored_address_pointer(tmp_path, override):
    path = _manifest(tmp_path)
    raw = yaml.safe_load(path.read_bytes())
    if override:
        project = dict(raw["contextDefaults"]["project"])
        project["address"] = "../outside.yaml"
        raw["slides"][0]["contextOverrides"]["body"] = {"project": project}
        pointer = "/slides/0/contextOverrides/body/project/address"
    else:
        raw["contextDefaults"]["project"]["address"] = "../outside.yaml"
        pointer = "/contextDefaults/project/address"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")

    with pytest.raises(StableFailure) as caught:
        select_deck_context(path, load_deck_manifest(path), "overview")

    assert caught.value.source_ref == pointer


def test_composition_condition_does_not_treat_scalar_slide_as_override(tmp_path):
    path = tmp_path / "manifest.yaml"
    path.write_text(
        "version: chrona/example-materializer/v0.1\nid: sample\nrole: regression-corpus\n"
        "slides:\n  - 42\n  - id: overview\n    evidence: test\n"
        "    expectedSvg: generated/overview.svg\n    context: contexts/overview.yaml\n",
        encoding="utf-8")

    with pytest.raises(StableFailure) as caught:
        select_deck_context(path, load_deck_manifest(path), "overview")

    assert caught.value.source_ref == "/slides/0"
