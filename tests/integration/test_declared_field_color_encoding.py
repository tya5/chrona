"""#344 Level 1: a profile-declared typed field colours planned marks through ``colorEncoding``.

A synthetic Project declares ``acme.risk`` (enum) and ``acme.reviewed`` (boolean) in a pinned profile package,
values on its objects, and the packaged default View gains only a ``colorEncoding`` declaration. No code change,
no ``examples/`` input; the Context closure is built in a temporary Store.
"""
from __future__ import annotations

import os
from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from chrona.presentation.contracts.resources import RENDER_CONTEXT_VERSION
from chrona.presentation.model.closure import resolve_render_context
from chrona.presentation.scene.visual_capabilities import BASELINE_PROFILE
from chrona.resources import default_preset_resource, default_preset_root
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.storage.snapshot_paths import snapshot_directory
from chrona.usecases.render_review import RenderFailed, RenderRejected, RenderRequest, render_review

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = {
    "version": "chrona/profile/v0.3", "packageId": "acme-risk", "contentIdentity": "sha256:" + "1" * 64,
    "requires": {"projectFormat": "timeline/v0.7"},
    "profiles": {"acme.item": {"extends": "task", "fields": {
        "acme.risk": {"type": "enum", "enumValues": ["low", "medium", "high"]},
        "acme.reviewed": {"type": "boolean"},
    }}},
}
RISK_COLOURS = {"low": "#2e7d32", "medium": "#f9a825", "high": "#c62828"}


def _project(values: dict[str, dict]) -> dict:
    objects = {}
    for index, (key, fields) in enumerate(values.items()):
        objects[key] = {"type": "acme.item", "title": key.title(), "fields": fields,
                        "schedule": {"mode": "fixed-span", "start": f"2026-03-{2 + index * 7:02d}", "end": f"2026-03-{8 + index * 7:02d}"}}
    return {"version": "timeline/v0.7", "project": {"id": "acme"}, "extensions": [{"packageId": "acme-risk"}], "objects": objects}


def _render(tmp_path: Path, project: dict, *, field: str, domain: list[str], slots: dict[str, str]):
    revision = "decl"
    snapshot = snapshot_directory(tmp_path, revision)
    snapshot.mkdir(parents=True)

    def pin(value, kind, address, identifier=None):
        content = yaml.safe_dump(value, sort_keys=False).encode()
        (snapshot / address).write_bytes(content)
        return {"id": identifier or value["id"], "kind": kind, "store": {"provider": "local", "identity": "decl"},
                "address": address, "revision": {"token": revision}, "contentIdentity": "sha256:" + sha256(content).hexdigest()}

    project = {**project, "extensions": [{"packageId": "acme-risk", "resource": pin(PACKAGE, "profile-package", "acme-risk.yaml", "acme-risk")}]}
    preset = yaml.safe_load(default_preset_resource().read_bytes())
    parts = {key: yaml.safe_load(default_preset_root().joinpath(d["path"]).read_bytes()) for key, d in preset["body"]["resources"].items()}
    parts["view"]["body"]["colorEncoding"] = {"scale": "risk", "target": "planned", "source": {"field": field}, "domain": domain}
    parts["theme"]["body"]["colorScales"] = {"risk": {"slots": {value: f"risk-{value}" for value in domain}}}
    parts["colorScheme"]["body"]["categories"].update({f"risk-{value}": slots[value] for value in domain})
    references = {key: pin(value, preset["body"]["resources"][key]["kind"], key + ".yaml") for key, value in parts.items()}
    context = {"version": RENDER_CONTEXT_VERSION, "kind": "render-context", "id": "decl", "body": {
        "project": pin(project, "project", "project.yaml", "acme"),
        **{key: references[key] for key in ("view", "theme", "colorScheme", "layout")},
        "inputs": {"detailProfile": references["detailProfile"]},
        "environment": {"viewport": {"inlineSize": 1600, "blockSize": 900}, "locale": "en-US",
                        "fontMetrics": yaml.safe_load((ROOT / "src/chrona/resources/fonts/default-font-metrics.yaml").read_bytes()),
                        "scenePrecision": 3},
        "target": {"kind": "svg", "capabilities": [], "visualProfile": BASELINE_PROFILE}}}
    closure = resolve_render_context(pin(context, "render-context", "context.yaml"), LocalSnapshotReader(tmp_path, "decl"))
    return render_review(RenderRequest(closure=closure, snapshot_root=snapshot, scheduler=ReferenceScheduler()))


def _fills(rendered) -> dict[str, str]:
    return {p.scene_id.split(":")[1]: p.paint.fill for p in rendered.surface.primitives
            if p.scene_id.startswith("planned:") and getattr(p.paint, "fill", None)}


def test_enum_field_colours_planned_marks_and_exports_a_picture(tmp_path):
    project = _project({"alpha": {"acme.risk": "low"}, "beta": {"acme.risk": "high"}, "gamma": {"acme.risk": "medium"}})
    rendered = _render(tmp_path, project, field="acme.risk", domain=["low", "medium", "high"], slots=RISK_COLOURS)
    fills = _fills(rendered)
    assert fills == {"alpha": RISK_COLOURS["low"], "beta": RISK_COLOURS["high"], "gamma": RISK_COLOURS["medium"]}
    witnesses = {p.source_ref: p.encoding for p in rendered.surface.primitives
                 if p.scene_id.startswith("planned:")}
    assert {key: value.value for key, value in witnesses.items()} == {
        "alpha": "low", "beta": "high", "gamma": "medium"}
    assert all(value.field == "acme.risk" and value.sources[0].kind == "view"
               and value.sources[0].source_ref == "/body/colorEncoding"
               for value in witnesses.values())
    out = os.environ.get("CHRONA_344_SVG")
    if out:
        Path(out).write_bytes(rendered.artifact.content if isinstance(rendered.artifact.content, bytes) else rendered.artifact.content.encode())


def test_boolean_field_colours_planned_marks(tmp_path):
    project = _project({"alpha": {"acme.reviewed": True}, "beta": {"acme.reviewed": False}})
    rendered = _render(tmp_path, project, field="acme.reviewed", domain=["true", "false"],
                       slots={"true": "#2e7d32", "false": "#c62828"})
    assert _fills(rendered) == {"alpha": "#2e7d32", "beta": "#c62828"}
    assert {p.source_ref: p.encoding.value for p in rendered.surface.primitives
            if p.scene_id.startswith("planned:")} == {"alpha": "true", "beta": "false"}


def test_number_source_is_not_admitted_yet(tmp_path):
    package = PACKAGE["profiles"]["acme.item"]["fields"]
    package["acme.cost"] = {"type": "number"}
    try:
        project = _project({"alpha": {"acme.cost": 3}})
        with pytest.raises(RenderFailed) as caught:
            _render(tmp_path, project, field="acme.cost", domain=["3"], slots={"3": "#2e7d32"})
    finally:
        del package["acme.cost"]
    assert caught.value.args[0] == "E_PRESENTATION_SCALE_VALUE"


def test_an_undeclared_value_fails_with_a_pointer_before_colouring(tmp_path):
    project = _project({"alpha": {"acme.risk": "severe"}})
    with pytest.raises((RenderRejected, RenderFailed)) as caught:
        _render(tmp_path, project, field="acme.risk", domain=["low", "medium", "high"], slots=RISK_COLOURS)
    assert "E_PROFILE_FIELD_ENUM" in str(caught.value) or "E_PROFILE_FIELD_ENUM" in repr(getattr(caught.value, "diagnostics", ""))
