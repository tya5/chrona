from __future__ import annotations

import hashlib
import json
from pathlib import Path
import copy
import io

import pytest
import yaml

from chrona.resources import safe_load
from tools import check_design_purity as purity


def _project():
    return {
        "version": "timeline/v0.7",
        "project": {"id": "aster-work", "title": "ASTER Work"},
        "objects": {"launch-window": {"title": "Launch Window"}, "m0": {"title": "Platform"}},
        "entities": {"platform": {"title": "Platform Engineering"}},
        "calendars": {"engineering": {}},
        "periods": {"launch-window": {"title": "Launch Window"}},
        "scenarios": {"slip": {"title": "Launch Window slips"}},
        "relations": [{"id": "depends-on"}],
        "annotations": [{"id": "risk-note", "text": "Review the launch window"}],
    }


def _resource(value):
    return ({"version": "chrona/theme/v0.15", "kind": "theme", "id": "generic-design",
             "body": value})


def test_finds_complete_project_id_tokens_and_phrases_but_not_substrings():
    findings = purity.audit(_project(), [("theme.yaml", _resource({
        "values": {
            "launch-window": {"type": "text", "value": "Launch Window aster-work launch-window"},
            "unrelated": {"type": "text", "value": "launch-windows"},
            "longer": {"type": "text", "value": "aster-workflow"},
            "paint-candidate": {"type": "paint", "value": "group:launch-window.fill"},
            "user-text": {"type": "text", "value": "launch-window"},
            "risk-note": {"type": "text", "value": "0.35"},
            "token-only": {"type": "number", "value": "launch-window"},
        },
        "opaque-paint": {"opacity": 0.35, "strokeWidth": 2, "date": "2027-10-13",
                         "fill": "group:launch-window.fill"},
    }))])

    observed = {(item["pointer"], item["project_fact"], item["match_class"], item["location"])
                for item in findings}
    assert ("/body/values/launch-window/value", "wording:/objects/launch-window/title",
            "wording-candidate", "value") in observed
    assert ("/body/values/launch-window/value", "identifier:/project/id",
            "identifier-candidate", "value") in observed
    assert ("/body/values/launch-window/value", "identifier:/objects/launch-window",
            "identifier-candidate", "value") in observed
    assert ("/body/values/paint-candidate/value", "identifier:/objects/launch-window",
            "identifier-candidate", "value") not in observed
    assert ("/body/values/user-text/value", "identifier:/objects/launch-window",
            "identifier-candidate", "value") in observed
    assert not any(item["pointer"].endswith("/token-only/value") for item in findings)
    assert not any(item["pointer"].endswith("/risk-note") for item in findings)
    assert not any(item["pointer"].startswith("/body/opaque-paint") for item in findings)
    assert not any(item["pointer"].endswith("/unrelated/value") for item in findings)
    assert not any(item["pointer"].endswith("/longer/value") for item in findings)
    assert findings == purity._sort_findings(list(reversed(findings)))


def test_generic_slots_are_masked_but_escaped_braces_are_not():
    resource = _resource({
        "heading": "Meanwhile, in the {title}: {project} — {ordinal}",
        "marked": {"text": "ACT {ordinal|group-ordinal} · {title}"},
        "named-figure": {"text": "ACT {figure:launch-window}"},
        "escaped": {"text": "{{launch-window}}"},
        "embedded": {"text": "Launch Window — {title}"},
        "unknown": {"text": "{launch-window}"},
    })
    findings = purity.audit(_project(), [("theme.yaml", resource)])
    pointers = {item["pointer"] for item in findings}
    assert "/body/heading" not in pointers
    assert "/body/marked/text" not in pointers
    assert "/body/named-figure/text" in pointers
    assert "/body/embedded/text" in pointers
    assert "/body/escaped/text" in pointers
    assert "/body/unknown/text" in pointers


def test_unicode_casefold_and_whitespace_normalization_finds_cjk_phrase():
    project = {"version": "timeline/v0.7",
               "project": {"id": "プロジェクト", "title": "コントローラ Z"},
               "objects": {"設計": {"title": "仕様 凍結"}}}
    design = _resource({"copy": "コントローラ　Ｚ — 仕様   凍結"})
    findings = purity.audit(project, [("theme.yaml", design)])
    assert {item["project_fact"] for item in findings} == {
        "wording:/project/title", "wording:/objects/設計/title"
    }


def test_typed_object_source_is_distinguished_from_collision_candidate():
    design = {
        "version": "chrona/summary-profile/v0.1", "kind": "summary-profile",
        "body": {"panels": [{"metrics": [
            {"source": {"object": "launch-window"}},
            {"label": "Launch Window"},
        ]}]},
    }
    findings = purity.audit(_project(), [("summary.yaml", design)])
    typed = [item for item in findings if item["match_class"] == "typed-connection-identifier"]
    assert [(item["pointer"], item["project_fact"]) for item in typed] == [
        ("/body/panels/0/metrics/0/source/object", "identifier:/objects/launch-window"),
    ]
    assert any(item["pointer"].endswith("/source/object")
               and item["project_fact"] == "identifier:/periods/launch-window"
               and item["match_class"] == "identifier-candidate" for item in findings)
    assert any(item["pointer"].endswith("/label") and item["match_class"] == "wording-candidate"
               for item in findings)


def test_project_id_in_summary_object_reference_remains_an_identifier_candidate():
    project = {**_project(), "project": {"id": "project-key", "title": "ASTER Work"}}
    design = {
        "version": "chrona/summary-profile/v0.1", "kind": "summary-profile",
        "body": {"panels": [{"metrics": [{"source": {"object": "project-key"}}]}]},
    }

    findings = purity.audit(project, [("summary.yaml", design)])

    assert any(item["pointer"] == "/body/panels/0/metrics/0/source/object"
               and item["project_fact"] == "identifier:/project/id"
               and item["match_class"] == "identifier-candidate" for item in findings)


def test_lookalike_theme_source_is_not_a_typed_project_connection():
    findings = purity.audit(_project(), [("theme.yaml", _resource({"source": {"object": "launch-window"}}))])
    assert not findings


def test_resource_envelope_metadata_is_not_design_content():
    project = {**_project(), "project": {"id": "chrona", "title": "Chrona"}}
    findings = purity.audit(project, [("theme.yaml", {
        "version": "chrona/theme/v0.15", "kind": "theme", "id": "launch-window",
        "body": {"title": "Generic theme"},
    })])
    assert findings == []


def test_empty_or_unsupported_explicit_inputs_fail_closed(tmp_path, capsys):
    with pytest.raises(purity.DesignPurityError, match="EMPTY"):
        purity.audit(_project(), [])
    project = _write(tmp_path / "project.yaml", "version: timeline/v0.7\nproject: {id: sample}\n")
    resource = _write(tmp_path / "unknown.yaml", "version: chrona/theme/v99.0\nkind: theme\nbody: {}\n")
    assert purity.main(["--project", str(project), "--resource", str(resource), "--report-only"]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["findings"] == [] and report["errors"]


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _reference(kind: str, identity: str, address: str, payload: bytes,
               *, store_identity: str = "example"):
    return {"id": identity, "kind": kind,
            "store": {"provider": "local", "identity": store_identity},
            "address": address, "revision": {"token": "v1"},
            "contentIdentity": "sha256:" + hashlib.sha256(payload).hexdigest()}


def test_manifest_uses_slide_context_override_shared_store_and_theme_base(tmp_path, monkeypatch):
    examples = tmp_path / "examples"
    example = examples / "sample"
    shared = example / "shared"
    project_bytes = b"version: timeline/v0.7\nproject: {id: sample, title: Sample Project}\nobjects: {special: {title: Special Milestone}}\n"
    layout_bytes = b"version: chrona/layout-profile/v0.10\nid: layout\nbody: {rows: {mode: compact}}\n"
    summary_bytes = b"version: chrona/summary-profile/v0.1\nkind: summary-profile\nid: summary\nbody:\n  panels: [{metrics: [{source: {object: special}}]}]\n"
    detail_bytes = b"version: chrona/review-detail-profile/v0.1\nid: detail\nbody: {legend: [{label: Special Milestone}]}\n"
    neutral_summary_bytes = b"version: chrona/summary-profile/v0.1\nkind: summary-profile\nid: neutral\nbody:\n  panels: [{id: neutral, metrics: [{id: as-of, source: actual.asOf, format: date}]}]\n"
    base_bytes = b"version: chrona/theme/v0.15\nkind: theme\nid: shared\nbody: {values: {special: {type: number, value: 1}}}\n"
    base_identity = "sha256:" + hashlib.sha256(base_bytes).hexdigest()
    derived = ("version: chrona/theme/v0.16\nkind: theme\nid: derived\nbody:\n  extends:\n    id: shared\n    path: base.yaml\n    sourceContentIdentity: " + base_identity + "\n    contentIdentity: " + base_identity + "\n").encode()
    (shared / "themes").mkdir(parents=True, exist_ok=True)
    (shared / "themes" / "base.yaml").write_bytes(base_bytes)
    (example / "project.yaml").write_bytes(project_bytes)
    (example / "layout.yaml").write_bytes(layout_bytes)
    (example / "summary.yaml").write_bytes(summary_bytes)
    (example / "summary-neutral.yaml").write_bytes(neutral_summary_bytes)
    (example / "detail.yaml").write_bytes(detail_bytes)
    (shared / "themes" / "derived.yaml").write_bytes(derived)
    references = {
        "project": _reference("project", "sample", "project.yaml", project_bytes),
        "layout": _reference("layout-profile", "layout", "layout.yaml", layout_bytes),
        "theme": _reference("theme", "derived", "themes/derived.yaml", derived,
                            store_identity="shared-design"),
        "summaryProfile": _reference("summary-profile", "summary", "summary.yaml", summary_bytes),
        "detailProfile": _reference("review-detail-profile", "detail", "detail.yaml", detail_bytes),
    }
    references["theme"]["contentIdentity"] = "sha256:" + hashlib.sha256(derived).hexdigest()
    context_body = {key: references[key] for key in ("project", "layout", "theme")}
    context_body["inputs"] = {key: references[key] for key in ("summaryProfile", "detailProfile")}
    context = {"version": "chrona/render-context/v0.17", "kind": "render-context", "body": context_body}
    default_context = copy.deepcopy(context)
    default_context["body"]["inputs"]["summaryProfile"] = _reference(
        "summary-profile", "neutral", "summary-neutral.yaml", neutral_summary_bytes)
    _write(example / "default.yaml", yaml.safe_dump(default_context, sort_keys=False))
    _write(example / "custom.yaml", yaml.safe_dump(context, sort_keys=False))
    (example / "manifest.yaml").write_text(
        "version: chrona/example-materializer/v0.1\nid: sample\nrole: regression-corpus\n"
        "context: default.yaml\nstores: [{identity: shared-design, root: shared}]\n"
        "slides: [{id: no-override, evidence: default, expectedSvg: generated/default.svg}, "
        "{id: override, evidence: override, expectedSvg: generated/override.svg, context: custom.yaml}]\n",
        encoding="utf-8",
    )

    from chrona.usecases import materialize
    original_roots = materialize.materializer_store_roots
    original_reader = materialize.read_materializer_reference

    def roots(root, declared):
        return original_roots(root, declared)

    def reader(root, reference, stores=None):
        return original_reader(root, reference, stores)

    monkeypatch.setattr(materialize, "materializer_store_roots", roots)
    monkeypatch.setattr(materialize, "read_materializer_reference", reader)
    findings = purity._batch(examples)

    assert any(item["resource"] == "local:example/summary.yaml"
               and item["match_class"] == "typed-connection-identifier" for item in findings)
    assert not any(item["resource"] == "local:shared-design/themes/base.yaml"
                   and item["pointer"] == "/body/values/special" for item in findings)
    assert any(item["resource"] == "local:example/detail.yaml"
               and item["match_class"] == "wording-candidate" for item in findings)
    assert not any(item["resource"] == "local:example/default.yaml" for item in findings)
    assert {item["project"] for item in findings} == {"local:example/project.yaml"}
    assert {item["context"] for item in findings} == {
        "sample/default.yaml", "sample/custom.yaml"}


def test_empty_batch_is_an_error_not_a_clean_result(tmp_path):
    empty = tmp_path / "no-examples"
    empty.mkdir()
    with pytest.raises(purity.DesignPurityError, match="EMPTY"):
        purity._batch(empty)


def test_cli_report_only_preserves_findings_and_strict_mode_fails(tmp_path, capsys):
    project = _write(tmp_path / "project.yaml", "version: timeline/v0.7\nproject: {id: acme, title: Acme Plan}\n")
    design = _write(tmp_path / "theme.yaml", "version: chrona/theme/v0.15\nkind: theme\nid: design\nbody: {label: Acme Plan}\n")
    assert purity.main(["--project", str(project), "--resource", str(design), "--report-only"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["errors"] == [] and len(report["findings"]) == 2
    assert report["counts"] == {"findings": 2, "resourcesWithFindings": 1, "contextsWithFindings": 0}
    assert purity.main(["--project", str(project), "--resource", str(design)]) == 1
    strict = json.loads(capsys.readouterr().out)
    assert strict["findings"] == report["findings"]


def test_cli_invalid_yaml_and_no_inputs_fail_closed(tmp_path, capsys):
    bad = _write(tmp_path / "bad.yaml", "project: [unterminated\n")
    design = _write(tmp_path / "theme.yaml", "body: {}\n")
    assert purity.main(["--project", str(bad), "--resource", str(design), "--report-only"]) == 2
    assert json.loads(capsys.readouterr().out)["errors"]
    assert purity.main(["--examples-root", str(tmp_path / "empty"), "--report-only"]) == 2
    assert json.loads(capsys.readouterr().out)["errors"]


@pytest.mark.parametrize(("project_version", "design_version"), [
    ({"bad": "shape"}, "chrona/theme/v0.15"),
    ("timeline/v0.7", ["bad-shape"]),
])
def test_non_string_versions_are_structured_errors_in_report_mode(tmp_path, capsys,
                                                                project_version, design_version):
    project = _write(tmp_path / "project.yaml", yaml.safe_dump({
        "version": project_version, "project": {"id": "sample"}}))
    design = _write(tmp_path / "theme.yaml", yaml.safe_dump({
        "version": design_version, "kind": "theme", "body": {}}))
    assert purity.main(["--project", str(project), "--resource", str(design), "--report-only"]) == 2
    assert json.loads(capsys.readouterr().out)["errors"]


def _batch_fixture(tmp_path):
    example = tmp_path / "examples" / "sample"
    values = {
        "project": _project(),
        "theme": _resource({"caption": "Launch Window"}),
        "layout": {"version": "chrona/layout-profile/v0.10", "id": "layout", "root": {}},
    }
    refs = {}
    for key, value in values.items():
        path = _write(example / f"{key}.yaml", yaml.safe_dump(value))
        kind = {"project": "project", "theme": "theme", "layout": "layout-profile"}[key]
        identifier = value["project"]["id"] if key == "project" else value["id"]
        refs[key] = _reference(kind, identifier, path.name, path.read_bytes())
    context = {"version": "chrona/render-context/v0.17", "kind": "render-context", "body": refs}
    _write(example / "context.yaml", yaml.safe_dump(context))
    _write(example / "manifest.yaml", yaml.safe_dump({
        "version": "chrona/example-materializer/v0.1", "id": "sample", "role": "regression-corpus",
        "context": "context.yaml", "slides": [{"id": "first", "evidence": "first", "expectedSvg": "generated/first.svg"}]}))
    return example, context


@pytest.mark.parametrize(("defect", "code"), [
    ("pin", "E_DESIGN_PURITY_REFERENCE"),
    ("id", "E_DESIGN_PURITY_IDENTITY"),
    ("kind", "E_DESIGN_PURITY_RESOURCE"),
    ("missing-theme-kind", "E_DESIGN_PURITY_RESOURCE"),
    ("project-id", "E_DESIGN_PURITY_IDENTITY"),
])
def test_batch_reference_errors_are_fatal_even_in_report_mode(tmp_path, capsys, defect, code):
    example, context = _batch_fixture(tmp_path)
    if defect == "pin":
        context["body"]["layout"]["contentIdentity"] = "sha256:" + "f" * 64
    elif defect == "id":
        context["body"]["layout"]["id"] = "wrong-layout"
    elif defect == "project-id":
        context["body"]["project"]["id"] = "wrong-project"
    else:
        key = "theme" if defect == "missing-theme-kind" else "layout"
        path = example / f"{key}.yaml"
        value = safe_load(path.read_bytes())
        if defect == "missing-theme-kind":
            value.pop("kind")
        else:
            value["kind"] = "theme"
        _write(path, yaml.safe_dump(value))
        context["body"][key]["contentIdentity"] = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    _write(example / "context.yaml", yaml.safe_dump(context))
    assert purity.main(["--examples-root", str(tmp_path / "examples"), "--report-only"]) == 2
    report = json.loads(capsys.readouterr().out)
    assert any(code in error for error in report["errors"])
    if defect in {"pin", "id", "kind"}:
        assert any(item["resource"] == "local:example/theme.yaml" for item in report["findings"])


def test_later_context_error_does_not_discard_earlier_findings(tmp_path, capsys):
    example, _ = _batch_fixture(tmp_path)
    manifest = safe_load((example / "manifest.yaml").read_bytes())
    manifest["slides"].append({"id": "missing", "evidence": "missing", "expectedSvg": "generated/missing.svg", "context": "missing.yaml"})
    _write(example / "manifest.yaml", yaml.safe_dump(manifest))
    assert purity.main(["--examples-root", str(tmp_path / "examples"), "--report-only"]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["findings"] and report["errors"]
    assert report["counts"]["findings"] == len(report["findings"])


def test_cli_emits_utf8_even_with_a_non_utf8_redirected_stdout(tmp_path, monkeypatch):
    project = _write(tmp_path / "project.yaml", "version: timeline/v0.7\nproject: {id: sample, title: 設計}\n")
    design = _write(tmp_path / "theme.yaml", "version: chrona/theme/v0.15\nkind: theme\nid: generic\nbody: {caption: 設計}\n")
    buffer = io.BytesIO()
    stream = io.TextIOWrapper(buffer, encoding="ascii")
    monkeypatch.setattr(purity.sys, "stdout", stream)
    assert purity.main(["--project", str(project), "--resource", str(design), "--report-only"]) == 0
    stream.flush()
    report = json.loads(buffer.getvalue().decode("utf-8"))
    assert any(item["match"] == "設計" for item in report["findings"])


def test_batch_audit_covers_every_packaged_shared_design_and_finds_nothing_in_them(monkeypatch):
    """The packaged shared designs (#1342) are audited through the Contexts that reference them, and stay Project-free."""
    root = Path(__file__).resolve().parents[3]
    scanned: set[str] = set()
    scan = purity._scan_design

    def recording(name, value, facts):
        scanned.add(name)
        return scan(name, value, facts)

    monkeypatch.setattr(purity, "_scan_design", recording)
    errors: list[str] = []
    findings = purity._batch(root / "examples", errors=errors)
    packaged = {f"package:chrona.resources/{path.relative_to(root / 'src/chrona/resources').as_posix()}"
                for path in (root / "src/chrona/resources/designs").glob("*/*.yaml")
                if safe_load(path.read_bytes()).get("kind") != "color-scheme"}
    assert packaged and not errors
    assert packaged <= scanned
    assert not [item for item in findings if item["resource"] in packaged]
