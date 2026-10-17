"""The host vocabulary is a verified input on both render entry paths (#419 V1)."""
from collections.abc import Mapping
from dataclasses import replace
from datetime import date
from hashlib import sha256

import pytest
import yaml

from chrona.presentation.contracts import SemanticVocabularyContract
from chrona.presentation.model.closure import resolve_draft_render, resolve_render_context
from chrona.presentation.scene.serialization import scene_document, validate_scene_document
from chrona.resources.semantic_vocabulary import builtin_semantic_vocabulary
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.storage.snapshot_paths import snapshot_directory
from chrona.usecases.render_review import RenderFailed, RenderRequest, render_review
from tests.support import synthetic_review as sr


def _inputs(tmp_path):
    parts = sr.bundle()
    values = {"project": sr.project({"one": sr.span("one", date(2026, 1, 5), 5)}), **parts}
    paths = {name: sr._write(tmp_path / f"{name}.yaml", value) for name, value in values.items()}
    draft = resolve_draft_render(project_path=paths["project"], view_path=paths["view"],
                                 theme_path=paths["theme"], scheme_path=paths["scheme"], layout_path=paths["layout"])
    return draft, values


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _assert_input(closure):
    vocabulary, = [item for item in closure.resources if item.kind == "semantic-vocabulary"]
    expected = builtin_semantic_vocabulary()
    assert isinstance(vocabulary.contract, SemanticVocabularyContract)
    assert (vocabulary.id, vocabulary.revision, vocabulary.content_identity) == (
        expected.id, "v0.1", expected.content_identity)
    assert vocabulary.contract.bindings == expected.bindings
    closure.require_semantic_vocabulary()


def _assert_render(closure, asset_root, snapshot_root):
    rendered = render_review(RenderRequest(closure, snapshot_root, ReferenceScheduler(),
                                          asset_root=asset_root, require_all_inputs_read=True))
    assert "semantic-vocabulary" in rendered.read_inputs
    document = scene_document(rendered.scene)
    validate_scene_document(document)
    resource, = [item for item in document["provenance"]["resources"] if item["kind"] == "semantic-vocabulary"]
    assert resource["contentIdentity"] == builtin_semantic_vocabulary().content_identity


def test_draft_closes_and_reads_the_same_vocabulary_that_owns_runtime_bindings(tmp_path):
    draft, _ = _inputs(tmp_path)
    _assert_input(draft.closure)
    _assert_render(draft.closure, draft.asset_root, tmp_path)


def test_immutable_context_closes_the_host_vocabulary_without_new_authored_input(tmp_path):
    draft, values = _inputs(tmp_path)
    snapshot = tmp_path / "snapshot"
    token = "vocabulary-test"
    directory = snapshot_directory(snapshot, token)
    directory.mkdir(parents=True)

    def store(kind, identifier, address, value):
        payload = yaml.safe_dump(value, sort_keys=True).encode()
        (directory / address).write_bytes(payload)
        return {"id": identifier, "kind": kind, "address": address,
                "store": {"provider": "local", "identity": "vocabulary-test"},
                "revision": {"token": token}, "contentIdentity": "sha256:" + sha256(payload).hexdigest()}

    refs = {}
    for key, value in values.items():
        kind = {"scheme": "color-scheme", "layout": "layout-profile"}.get(key, key)
        identifier = value["project"]["id"] if key == "project" else value["id"]
        refs[key] = store(kind, identifier, f"{key}.yaml", value)
    environment = draft.closure.context.environment
    context = {"version": "chrona/render-context/v0.17", "kind": "render-context", "id": "saved",
               "body": {"project": refs["project"], "view": refs["view"], "theme": refs["theme"],
                        "colorScheme": refs["scheme"], "layout": refs["layout"], "inputs": {},
                        "environment": {"viewport": {"inlineSize": 1600, "blockSize": 900},
                                        "locale": environment.locale, "scenePrecision": environment.scene_precision,
                                        "fontMetrics": _plain(environment.font_metrics)},
                        "target": {"kind": "svg", "capabilities": [],
                                   "visualProfile": "chrona-output/visual/v0.5-baseline"}}}
    reference = store("render-context", "saved", "context.yaml", context)
    closure = resolve_render_context(reference, LocalSnapshotReader(snapshot, "vocabulary-test"))
    _assert_input(closure)
    _assert_render(closure, draft.asset_root, snapshot)


@pytest.mark.parametrize("missing", [False, True])
def test_render_rejects_a_missing_or_forged_vocabulary_before_scene_output(tmp_path, missing):
    draft, _ = _inputs(tmp_path)
    resources = tuple(item for item in draft.closure.resources if item.kind != "semantic-vocabulary")
    if not missing:
        vocabulary = next(item for item in draft.closure.resources if item.kind == "semantic-vocabulary")
        resources += (replace(vocabulary, content_identity="sha256:" + "0" * 64),)
    invalid = replace(draft.closure, resources=resources)
    with pytest.raises(RenderFailed) as error:
        render_review(RenderRequest(invalid, tmp_path, ReferenceScheduler(), asset_root=draft.asset_root))
    assert error.value.code == ("E_CLOSURE_REQUIRED" if missing else "E_RESOURCE_IDENTITY_MISMATCH")
