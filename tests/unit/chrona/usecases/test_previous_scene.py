import json
from hashlib import sha256
from pathlib import Path

import pytest

from chrona.presentation.scene.serialization import SceneSerializationError, serialize_scene
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from chrona.usecases.previous_scene import decode_previous_scene
from chrona.core.ports import SnapshotReadError
from chrona.presentation.contracts import ArtifactPin, freeze
from chrona.presentation.model.closure import ClosureError, _read_previous_scene
from chrona.storage.revision_store import LocalSnapshotReader, snapshot_directory
from chrona.usecases.materialize import _OverlayBuilder
from chrona.usecases.failure_report import report_failure


@pytest.fixture(scope="module")
def previous_bytes():
    project = Path(__file__).resolve().parents[3] / "fixtures/routing_revision/project-v1.yaml"
    return serialize_scene(render_draft(DraftRenderRequest(project, "svg")).rendered.scene)


def test_neutral_pin_capture_checks_exact_bytes_even_with_injected_reader(previous_bytes):
    pin = ArtifactPin(freeze({"provider": "local", "identity": "prior"}),
                      "prior.scene.json", "revision-1", f"sha256:{sha256(previous_bytes).hexdigest()}")
    class Reader:
        def read(self, reference):
            assert "id" not in reference and "kind" not in reference
            assert reference == pin.as_reader_reference()
            return previous_bytes
    assert _read_previous_scene(pin, Reader()) == previous_bytes
    class CorruptReader:
        def read(self, reference):
            return previous_bytes + b" "
    with pytest.raises(ClosureError) as error:
        _read_previous_scene(pin, CorruptReader())
    assert error.value.diagnostic_id == "E_CONTENT_IDENTITY"
    assert error.value.source_ref == "/body/inputs/previousScene"


def test_neutral_pin_reader_failure_keeps_store_code():
    pin = ArtifactPin(freeze({"provider": "local", "identity": "prior"}),
                      "prior.scene.json", "revision-1", "sha256:" + "0" * 64)
    class MissingReader:
        def read(self, reference):
            raise SnapshotReadError("E_STORE_REFERENCE", "missing immutable bytes")
    with pytest.raises(ClosureError) as error:
        _read_previous_scene(pin, MissingReader())
    assert error.value.diagnostic_id == "E_STORE_REFERENCE"


def test_real_store_and_execution_overlay_read_identity_neutral_pin(tmp_path, previous_bytes):
    pin = ArtifactPin(freeze({"provider": "local", "identity": "prior"}),
                      "prior.scene.json", "revision-1", f"sha256:{sha256(previous_bytes).hexdigest()}")
    root = tmp_path / "store"
    revision = snapshot_directory(root, pin.revision_token)
    revision.mkdir(parents=True)
    (revision / pin.address).write_bytes(previous_bytes)
    assert _read_previous_scene(pin, LocalSnapshotReader(root, "prior")) == previous_bytes
    staging = tmp_path / "overlay"
    staging.mkdir()
    builder = _OverlayBuilder(staging)
    builder.add_reference(pin.as_reader_reference(), previous_bytes)
    overlay = builder.finish()
    assert _read_previous_scene(pin, overlay) == previous_bytes
    altered = dict(pin.as_reader_reference())
    altered["revision"] = {"token": "different-revision"}
    with pytest.raises(SnapshotReadError, match="E_STORE_REFERENCE"):
        overlay.read(altered)


def test_same_project_accepts_prior_revision_and_freezes_input(previous_bytes):
    result = decode_previous_scene(previous_bytes, "nimbus-launch")
    assert result.value["kind"] == "scene"
    with pytest.raises(TypeError):
        result.value["kind"] = "changed"


@pytest.mark.parametrize("payload", [b"not-json", b"[]", b"\xff", b'{"version":"chrona/scene/v999"}'])
def test_malformed_or_unsupported_previous_scene_fails_ingress(payload):
    with pytest.raises(SceneSerializationError, match="E_SCENE_SERIALIZATION"):
        decode_previous_scene(payload, "nimbus-launch")


def test_wrong_project_fails_before_hint_matching(previous_bytes):
    with pytest.raises(SceneSerializationError, match="current primary Project"):
        decode_previous_scene(previous_bytes, "different-project")


def test_wrong_project_maps_to_stable_transport_failure(previous_bytes):
    try:
        decode_previous_scene(previous_bytes, "different-project")
    except SceneSerializationError as error:
        failure = report_failure(error)
    assert failure.diagnostics[0]["code"] == "E_SCENE_SERIALIZATION"


def test_draft_captures_prior_bytes_without_modifying_file(tmp_path, previous_bytes):
    project = Path(__file__).resolve().parents[3] / "fixtures/routing_revision/project-v1.yaml"
    previous = tmp_path / "prior.scene.json"
    previous.write_bytes(previous_bytes)
    result = render_draft(DraftRenderRequest(project, "svg", previous_scene=previous)).rendered
    assert result.scene.provenance.mode == "draft"
    assert previous.read_bytes() == previous_bytes


def test_draft_refuses_wrong_project_input(tmp_path, previous_bytes):
    project = Path(__file__).resolve().parents[3] / "fixtures/routing_revision/project-v1.yaml"
    previous = tmp_path / "prior.scene.json"
    value = json.loads(previous_bytes)
    next(item for item in value["provenance"]["resources"]
         if item["kind"] == "project")["id"] = "other-project"
    previous.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(SceneSerializationError, match="current primary Project"):
        render_draft(DraftRenderRequest(project, "svg", previous_scene=previous))


@pytest.mark.parametrize("duplicate", [False, True])
def test_missing_or_duplicate_primary_project_is_not_a_hint_miss(previous_bytes, duplicate):
    value = json.loads(previous_bytes)
    resources = value["provenance"]["resources"]
    project = next(item for item in resources if item["kind"] == "project")
    value["provenance"]["resources"] = (resources + [project] if duplicate else
                                          [item for item in resources if item["kind"] != "project"])
    with pytest.raises(SceneSerializationError, match="current primary Project"):
        decode_previous_scene(json.dumps(value).encode(), "nimbus-launch")
