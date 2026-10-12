"""Default-owned paint is safe across every semantically valid conformance Project.

The delivery fixture needs its real extension package: test it through a
verified immutable Context, not a fake native-object conversion.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from xml.etree import ElementTree

import yaml

from chrona.core.validation import validate_project
from chrona.presentation.contracts.resources import RENDER_CONTEXT_VERSION
from chrona.presentation.model.closure import resolve_render_context
from chrona.presentation.scene.visual_capabilities import BASELINE_PROFILE
from chrona.resources import default_preset_resource, default_preset_root
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.storage.snapshot_paths import snapshot_directory
from chrona.usecases.draft_render import DraftRenderRequest, render_draft, warning_payloads
from chrona.usecases.render_review import RenderRequest, render_review


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_FIXTURES = {
    "implementation-delivery": "implementation-delivery-profile-v0.2.yaml",
}


def _projects():
    # Called during execution, not collection. expectedPlacements belongs to the
    # conformance oracle, not the Project schema; preserve every Project field.
    for path in sorted((ROOT / "conformance").rglob("*.yaml")):
        source = yaml.safe_load(path.read_bytes())
        if not isinstance(source, dict) or not str(source.get("version", "")).startswith("timeline/"):
            continue
        source.pop("expectedPlacements", None)
        if not validate_project(source):
            yield path, source


def _pinned_default_render(tmp_path, source):
    source = deepcopy(source)
    revision = "conformance-default"
    snapshot = snapshot_directory(tmp_path, revision)
    snapshot.mkdir(parents=True)

    def pin(value, kind, address, identifier=None):
        content = yaml.safe_dump(value, sort_keys=False).encode()
        (snapshot / address).write_bytes(content)
        return {"id": identifier or value["id"], "kind": kind,
                "store": {"provider": "local", "identity": "conformance-default"},
                "address": address, "revision": {"token": revision},
                "contentIdentity": "sha256:" + sha256(content).hexdigest()}

    # Replace the fixture's placeholder locator/pin with an actually stored,
    # hash-verified package. Its package, objects, fields and relations stay real.
    package_ids = []
    for extension in source.get("extensions", []):
        package_id = extension["packageId"]
        if package_id == "semiconductor-example":
            # This legacy extension declaration is metadata on native tasks and
            # gates, not a current profile-package resource. Preserve it exactly;
            # semiconductor-profile-v0.2.yaml declares a DIFFERENT package.
            assert "resource" not in extension
        else:
            manifest = yaml.safe_load((ROOT / "conformance" / PACKAGE_FIXTURES[package_id]).read_bytes())
            extension.clear()
            extension.update({"packageId": package_id, "resource":
                              pin(manifest, "profile-package", package_id + ".yaml", package_id)})
            package_ids.append(package_id)

    preset = yaml.safe_load(default_preset_resource().read_bytes())
    references = {}
    for key, declaration in preset["body"]["resources"].items():
        value = yaml.safe_load(default_preset_root().joinpath(declaration["path"]).read_bytes())
        references[key] = pin(value, declaration["kind"], key + ".yaml")
    context = {
        "version": RENDER_CONTEXT_VERSION, "kind": "render-context", "id": "conformance-default",
        "body": {
            "project": pin(source, "project", "project.yaml", source["project"]["id"]),
            **{key: references[key] for key in ("view", "theme", "colorScheme", "layout")},
            "inputs": {"detailProfile": references["detailProfile"]},
            "environment": {"viewport": {"inlineSize": 1600, "blockSize": 900}, "locale": "en-US",
                            "fontMetrics": yaml.safe_load((ROOT / "src/chrona/resources/fonts/default-font-metrics.yaml").read_bytes()),
                            "scenePrecision": 3},
            "target": {"kind": "svg", "capabilities": [], "visualProfile": BASELINE_PROFILE},
        },
    }
    reader = LocalSnapshotReader(tmp_path, "conformance-default")
    closure = resolve_render_context(pin(context, "render-context", "context.yaml"), reader)
    assert [package.package_id for package in closure.profile_packages] == package_ids
    return render_review(RenderRequest(closure=closure, snapshot_root=snapshot,
                                       scheduler=ReferenceScheduler()))


def _assert_default_theme_safe(rendered, name):
    # Inspect the actual validated SVG, not only a Scene-only paint report.
    assert ElementTree.fromstring(rendered.artifact.content).tag.endswith("svg"), name
    assert rendered.surface.primitives, name
    findings = [warning for warning in warning_payloads(rendered)
                if warning["code"].startswith(("W_THEME_", "E_THEME_")) or
                any(word in warning["code"] for word in ("CONTRAST", "DECORATION", "PERCEPTIBILITY"))]
    assert findings == [], (name, findings)


def test_every_valid_conformance_project_has_safe_default_theme(tmp_path):
    projects = list(_projects())
    assert len(projects) == 6
    assert {path.name for path, _ in projects} == {
        "calendar.yaml", "controller-x.yaml", "dependencies.yaml",
        "implementation-delivery-roadmap-v0.1.yaml", "minimal.yaml", "semiconductor.yaml",
    }
    for index, (path, source) in enumerate(projects):
        directory = tmp_path / str(index)
        directory.mkdir()
        # Every valid Project, including the extension-bearing delivery fixture,
        # gets the same packaged default resources on the immutable path.
        _assert_default_theme_safe(_pinned_default_render(directory, source), path.name)
        if not any(extension["packageId"] == "implementation-delivery"
                   for extension in source.get("extensions", [])):
            project_path = directory / "draft.yaml"
            project_path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")
            _assert_default_theme_safe(render_draft(DraftRenderRequest(
                project=project_path, target_kind="svg")).rendered, path.name)
