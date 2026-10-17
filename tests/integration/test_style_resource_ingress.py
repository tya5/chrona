"""Optional Style enters the real closure, not an injected normalizer seam."""
from collections.abc import Mapping
from datetime import date
from hashlib import sha256

import pytest
import yaml

from chrona.presentation.model.closure import ClosureError, resolve_draft_render, resolve_render_context
from chrona.presentation.scene.serialization import scene_document, validate_scene_document
from chrona.presentation.style import bind_style_rules, parse_style_rules
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.storage.snapshot_paths import snapshot_directory
from chrona.usecases.materialize import copy_context_closure
from chrona.usecases.failure_report import report_failure
from chrona.usecases.render_review import RenderFailed, RenderRequest, render_review
from tests.support import synthetic_review as sr


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _inputs(tmp_path, *, rules=None):
    parts = sr.bundle()
    body = parts["theme"]["body"]
    body["roles"]["authored-mark"] = dict(body["roles"]["planned"])
    for suffix in ("fill", "stroke"):
        body["colorBindings"]["authored-mark." + suffix] = body["colorBindings"]["planned." + suffix]
    source = sr.project({"one": sr.span("one", date(2026, 1, 5), 5)})
    values = {"project": source, **parts}
    if rules is not None:
        values["style"] = {"version": "chrona/style/v0.2", "kind": "style", "id": "authored-style",
                           "body": {"rules": rules}}
    paths = {name: sr._write(tmp_path / f"{name}.yaml", value) for name, value in values.items()}
    draft = resolve_draft_render(
        project_path=paths["project"], view_path=paths["view"], theme_path=paths["theme"],
        scheme_path=paths["scheme"], layout_path=paths["layout"], style_path=paths.get("style"))
    return draft, values


def _rules():
    return [{"id": "planned-treatment", "when": {"semantic": "planned"},
             "then": {"role": "authored-mark"}}]


def _render(draft, closure=None, snapshot_root=None):
    return render_review(RenderRequest(
        closure=closure or draft.closure, snapshot_root=snapshot_root or draft.asset_root,
        scheduler=ReferenceScheduler(), asset_root=draft.asset_root, require_all_inputs_read=True))


def _assert_style(rendered):
    assert "style" in rendered.read_inputs
    selected = [node for node in rendered.surface.primitives
                if node.source_ref == "one" and node.purpose == "planned"]
    assert selected
    assert all(node.theme_role == "authored-mark" for node in selected)
    assert all(node.style_match is not None and node.style_match.rule_ids == ("planned-treatment",)
               for node in selected)
    document = scene_document(rendered.scene)
    validate_scene_document(document)
    style, = [item for item in document["provenance"]["resources"] if item["kind"] == "style"]
    assert style["id"] == "authored-style"


def _snapshot(tmp_path, draft, values):
    root = tmp_path / "snapshot"
    directory = snapshot_directory(root, "style-test")
    directory.mkdir(parents=True)

    def store(name, value):
        kind = {"scheme": "color-scheme", "layout": "layout-profile"}.get(name, name)
        identifier = value["project"]["id"] if kind == "project" else value["id"]
        payload = yaml.safe_dump(value, sort_keys=True).encode()
        (directory / f"{name}.yaml").write_bytes(payload)
        return {"id": identifier, "kind": kind, "address": f"{name}.yaml",
                "store": {"provider": "local", "identity": "style-test"},
                "revision": {"token": "style-test"}, "contentIdentity": "sha256:" + sha256(payload).hexdigest()}

    refs = {name: store(name, value) for name, value in values.items()}
    environment = draft.closure.context.environment
    context = {"version": "chrona/render-context/v0.17", "kind": "render-context", "id": "saved",
               "body": {"project": refs["project"], "view": refs["view"], "theme": refs["theme"],
                        "colorScheme": refs["scheme"], "layout": refs["layout"], "inputs": {},
                        **({"style": refs["style"]} if "style" in refs else {}),
                        "environment": {"viewport": {"inlineSize": 1600, "blockSize": 900},
                                        "locale": environment.locale, "scenePrecision": environment.scene_precision,
                                        "fontMetrics": _plain(environment.font_metrics)},
                        "target": {"kind": "svg", "capabilities": [],
                                   "visualProfile": "chrona-output/visual/v0.5-baseline"}}}
    return root, directory, context, store("render-context", context)


def test_draft_style_changes_treatment_and_is_read_and_pinned(tmp_path):
    draft, _ = _inputs(tmp_path, rules=_rules())
    assert draft.closure.context.style.id == "authored-style"
    assert draft.closure.style.rules[0].rule_id == "planned-treatment"
    _assert_style(_render(draft))


def test_pinned_style_uses_verified_store_reader_and_reaches_render(tmp_path):
    draft, values = _inputs(tmp_path, rules=_rules())
    root, _, _, reference = _snapshot(tmp_path, draft, values)
    closed = resolve_render_context(reference, LocalSnapshotReader(root, "style-test"))
    assert closed.style.identity.revision == "style-test"
    assert [item.kind for item in closed.resources][:3] == ["project", "view", "style"]
    _assert_style(_render(draft, closed, root))


def test_store_style_bytes_cannot_change_behind_the_context_pin(tmp_path):
    draft, values = _inputs(tmp_path, rules=_rules())
    root, directory, _, reference = _snapshot(tmp_path, draft, values)
    (directory / "style.yaml").write_bytes(b"changed bytes\n")
    with pytest.raises(ClosureError) as caught:
        resolve_render_context(reference, LocalSnapshotReader(root, "style-test"))
    assert caught.value.diagnostic_id == "E_CONTENT_IDENTITY"


def test_materializer_copies_optional_style_and_its_pin(tmp_path):
    draft, values = _inputs(tmp_path, rules=_rules())
    _, directory, _, _ = _snapshot(tmp_path, draft, values)
    copied = tmp_path / "copied"
    reference, token = copy_context_closure(directory, directory / "render-context.yaml", copied)
    assert (snapshot_directory(copied, token) / "style.yaml").read_bytes() == (directory / "style.yaml").read_bytes()
    closed = resolve_render_context(reference, LocalSnapshotReader(copied, "style-test"))
    _assert_style(_render(draft, closed, copied))


def _preset(tmp_path, values):
    resources = {name: {"id": values[key]["id"],
                        "kind": {"scheme": "color-scheme", "layout": "layout-profile"}.get(key, key),
                        "path": f"{key}.yaml"}
                 for name, key in (("view", "view"), ("style", "style"), ("theme", "theme"),
                                   ("colorScheme", "scheme"), ("layout", "layout"))}
    return sr._write(tmp_path / "preset.yaml", {
        "version": "chrona/presentation-preset/v0.1", "kind": "presentation-preset", "id": "styled",
        "body": {"package": {"version": "1"}, "resources": resources,
                 "compatibleColorSchemes": [resources["colorScheme"]]}})


def test_explicit_style_overrides_preset_without_being_dropped_by_theme_override(tmp_path):
    draft, values = _inputs(tmp_path, rules=_rules())
    preset = _preset(tmp_path, values)
    inherited = resolve_draft_render(project_path=tmp_path / "project.yaml", preset_path=preset,
                                    theme_path=tmp_path / "theme.yaml")
    assert inherited.closure.style.identity.id == "authored-style"
    _assert_style(_render(inherited))
    explicit = sr._write(tmp_path / "override.yaml", {
        **values["style"], "id": "override", "body": {"rules": []}})
    overridden = resolve_draft_render(project_path=tmp_path / "project.yaml", preset_path=preset,
                                     style_path=explicit, theme_path=tmp_path / "theme.yaml")
    assert overridden.closure.context.style.id == "override"
    assert overridden.closure.style.rules == ()


def test_invalid_declared_preset_style_is_validated_even_when_overridden(tmp_path):
    _, values = _inputs(tmp_path, rules=_rules())
    preset = _preset(tmp_path, values)
    explicit = sr._write(tmp_path / "override.yaml", {**values["style"], "id": "override"})
    sr._write(tmp_path / "style.yaml", {**values["style"], "id": "wrong-id"})
    with pytest.raises(ClosureError) as caught:
        resolve_draft_render(project_path=tmp_path / "project.yaml", preset_path=preset, style_path=explicit)
    assert caught.value.diagnostic_id == "E_DRAFT_PRESET_RESOURCE"


def test_no_style_keeps_scene_and_artifact_equal_to_empty_style_except_provenance(tmp_path):
    absent = tmp_path / "absent"
    empty = tmp_path / "empty"
    absent.mkdir()
    empty.mkdir()
    draft_a, _ = _inputs(absent)
    draft_b, _ = _inputs(empty, rules=[])
    rendered_a, rendered_b = _render(draft_a), _render(draft_b)
    assert draft_a.closure.context.style is None
    assert "style" not in rendered_a.read_inputs
    assert rendered_a.surface == rendered_b.surface
    assert rendered_a.artifact == rendered_b.artifact


def test_style_rule_identity_is_resource_qualified_without_losing_authored_id():
    rules = parse_style_rules({"rules": _rules()})
    a, = bind_style_rules("one", rules)
    b, = bind_style_rules("two", rules)
    assert a.rule_id != b.rule_id
    assert a.authored_rule_id == b.authored_rule_id == "planned-treatment"
    assert a.source_ref == b.source_ref == "/body/rules/0"
    assert a.style_id == "one"
    assert rules[0].style_id is None


@pytest.mark.parametrize("change,code", [
    ({"id": "not-the-pinned-id"}, "E_CLOSURE_ID"),
    ({"version": "chrona/style/v999"}, "E_RESOURCE_VERSION_UNSUPPORTED"),
])
def test_style_identity_and_version_are_verified_by_normal_resource_ingress(tmp_path, change, code):
    draft, values = _inputs(tmp_path, rules=_rules())
    values["style"].update(change)
    # Preserve a distinct authored ID pin so an identity mismatch is not made
    # self-consistent by the fixture writer.
    root, directory, context, _ = _snapshot(tmp_path, draft, values)
    context["body"]["style"]["id"] = "authored-style"
    payload = yaml.safe_dump(context, sort_keys=True).encode()
    (directory / "render-context.yaml").write_bytes(payload)
    reference = {"id": "saved", "kind": "render-context", "address": "render-context.yaml",
                 "store": {"provider": "local", "identity": "style-test"},
                 "revision": {"token": "style-test"}, "contentIdentity": "sha256:" + sha256(payload).hexdigest()}
    with pytest.raises(ClosureError) as caught:
        resolve_render_context(reference, LocalSnapshotReader(root, "style-test"))
    assert caught.value.diagnostic_id == code


def test_real_style_conflict_retains_code_rule_pointer_and_occurrence_in_failure_report(tmp_path):
    rules = [*_rules(), {"id": "conflict", "when": {"semantic": "planned"},
                         "then": {"role": "planned"}}]
    draft, _ = _inputs(tmp_path, rules=rules)
    with pytest.raises(RenderFailed) as caught:
        _render(draft)
    record, = report_failure(caught.value).diagnostics
    assert record["code"] == "E_STYLE_RULE_CONFLICT"
    assert record["sourceRef"].startswith("/body/rules/")
    assert record["details"]["subject"]["subject_id"] == "one"
    assert set(record["details"]["ruleIds"]) == {
        'style:["authored-style","planned-treatment"]', 'style:["authored-style","conflict"]'}


def test_real_style_invalid_selector_retains_pointed_failure_before_placement(tmp_path):
    draft, _ = _inputs(tmp_path, rules=[{
        "id": "bad-selector", "when": {"semantic": "not-a-host-semantic"},
        "then": {"role": "planned"}}])
    with pytest.raises(RenderFailed) as caught:
        _render(draft)
    record, = report_failure(caught.value).diagnostics
    assert record["code"] == "E_STYLE_FACT_UNKNOWN"
    assert record["sourceRef"] == "/body/rules/0/when/semantic"
    assert record["details"]["ruleIds"] == ['style:["authored-style","bad-selector"]']


def test_style_named_role_is_a_declared_consumer_even_without_current_matches(tmp_path):
    draft, _ = _inputs(tmp_path, rules=[{
        "id": "no-current-actual", "when": {"semantic": "actual"},
        "then": {"role": "authored-mark"}}])
    rendered = _render(draft)
    assert "style" in rendered.read_inputs
    assert not any(item.startswith("W_THEME_ROLE_UNREAD:") and "authored-mark" in item
                   for item in rendered.surface.diagnostics)
    assert not any(item.style_match is not None for item in rendered.surface.primitives)
