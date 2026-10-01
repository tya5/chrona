"""The kinds that adopt the strict `storeAddress` through a version bump (#710, row 1, slice S-B).

layout-profile v0.9 -> v0.10 and render-context v0.16 -> v0.17 (both predecessors were retired in #731, C1 and C2).
Every verdict is decided from data, the validators and the production readers; none consults the host path flavour.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from chrona.presentation.contracts import ClosureIdentity, ContractError, parse_contract
from chrona.presentation.contracts.resources import UnsupportedResourceVersionError
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.profile import LAYOUT_SCHEMAS, LAYOUT_VERSION, _validate_schema
from chrona.presentation.contracts.resources import RENDER_CONTEXT_VERSION, RENDER_CONTEXT_VERSIONS
from tools.schema_equivalence import (
    BASELINE, EXPECTED_DELTAS, PROBE_SITES, PROBE_STRINGS, SchemaValidators, _MISSING, _difference, _load_corpus,
    _same, fingerprint_schemas, load_baseline, load_deltas, load_schema_dir, run_probes, tracked_documents,
)
from tools.schema_inventory import load_inventory


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
SCHEMAS = load_schema_dir(ROOT / "schemas")
VALIDATORS = SchemaValidators(SCHEMAS)
PAIRS = {  # predecessor document version -> (successor document version, predecessor schema, successor schema)
    "chrona/automation-result/v0.1": ("chrona/automation-result/v0.2", "automation-result-v0.1.schema.yaml", "automation-result-v0.2.schema.yaml"),
    "chrona/snapshot-ref/v0.2": ("chrona/snapshot-ref/v0.3", "snapshot-ref-v0.2.schema.yaml", "snapshot-ref-v0.3.schema.yaml"),
}
# Committed documents that stay on a predecessor on purpose, each with its reason.
PINNED = {
    "examples/halcyon-1/snapshots/baseline-2027-06.yaml":
        "an immutable, content-pinned baseline: the Halcyon replan Context pins its sha256, so its bytes (and version) cannot change; "
        "it is the committed stand-in for the v0.2 baselines already in operators' Stores",
}
# Predecessors already retired (#731): the document version string must appear in no committed or packaged document.
RETIRED = ("chrona/layout-profile/v0.9", "chrona/render-context/v0.16", "chrona/command/v0.2")
SUCCESSOR_OF = {old: new for old, (new, _, _) in PAIRS.items()}
PREDECESSOR_OF = {new: old for old, new in SUCCESSOR_OF.items()}
ADDRESS_SITES = tuple(site for site in PROBE_SITES if site.family in ("address", "segment"))
THIS_TEST = "tests/unit/tools/test_store_address_kinds.py::test_each_address_site_refuses_every_listed_input"


def _documents() -> dict[str, bytes]:
    return tracked_documents(ROOT)


def _run_sites() -> dict[str, Any]:
    corpus = _load_corpus(_documents(), sorted({site.source for site in ADDRESS_SITES if not site.source.startswith("inline:")}))
    return run_probes(corpus, VALIDATORS, ADDRESS_SITES)


def test_the_inventory_marks_the_predecessors_transitioning_with_their_successors():
    entries = {entry["file"]: entry for entry in load_inventory(ROOT / "schemas/schema-inventory-v0.1.yaml")}
    for _, (_, old, new) in PAIRS.items():
        assert entries[old]["state"] == "transitioning" and entries[old]["successor"] == new
        assert entries[old]["removalSlice"].startswith("issue-710-")
        assert entries[new]["state"] == "live" and "successor" not in entries[new]


def test_the_readers_accept_both_versions_and_emit_the_successor():
    assert set(LAYOUT_SCHEMAS) == {"chrona/layout-profile/v0.10"} and LAYOUT_VERSION == "chrona/layout-profile/v0.10"
    assert RENDER_CONTEXT_VERSIONS == ("chrona/render-context/v0.17",) and RENDER_CONTEXT_VERSION == RENDER_CONTEXT_VERSIONS[-1]


def _document(path: str, version: str) -> dict[str, Any]:
    document = yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))
    document["version"] = version
    return document


def test_the_retired_layout_version_is_unsupported_and_the_current_one_refuses_a_loose_address():
    layout = _document("conformance/layout-profile-override-v0.2.yaml", "chrona/layout-profile/v0.9")
    with pytest.raises(LayoutError) as unsupported:
        _validate_schema(layout)
    assert (unsupported.value.diagnostic_id, unsupported.value.path) == ("E_LAYOUT_SCHEMA", "/version")
    layout["version"] = LAYOUT_VERSION
    _validate_schema(layout)
    layout["extends"]["address"] = "my layouts/briefing.yaml"
    with pytest.raises(LayoutError):
        _validate_schema(layout)


def test_the_retired_context_version_is_unsupported_and_the_current_one_refuses_a_loose_address():
    context = _document("examples/aster-ssd/contexts/01-overview.yaml", "chrona/render-context/v0.16")
    identity = ClosureIdentity("render-context", context["id"], "draft", "sha256:" + "0" * 64)
    with pytest.raises(UnsupportedResourceVersionError) as unsupported:
        parse_contract(identity, deepcopy(context))
    assert unsupported.value.found_version == "chrona/render-context/v0.16"
    assert unsupported.value.supported_versions == (RENDER_CONTEXT_VERSION,)
    context["version"] = RENDER_CONTEXT_VERSION
    assert parse_contract(identity, deepcopy(context)).version == RENDER_CONTEXT_VERSION
    context["body"]["project"]["address"] = "my projects/main.yaml"
    with pytest.raises(ContractError):
        parse_contract(identity, context)


def test_successors_differ_from_their_predecessors_only_at_the_address_sites():
    prints = fingerprint_schemas(SCHEMAS)
    for _, (_, old, new) in PAIRS.items():
        changed = [pointer for pointer, _before, _after in _difference(prints.trees[old], prints.trees[new], prints.hasher, limit=500)
                   if "$recursive" not in pointer]  # a recursive reference names its own file; that is the identity change
        assert changed, old
        assert all(pointer.endswith(("/address/pattern", "/address/minLength", "/snapshotId/allOf", "/snapshotId/minLength", "/snapshotId/type"))
                   or pointer == "/properties/version/const" for pointer in changed), changed  # `minLength: 1` is implied by the pattern
        assert "/properties/version/const" in changed


def test_each_address_site_refuses_every_listed_input():
    """Owner row 1 and design D5: the successor refuses each listed input; each change is a listed L3 delta citing this test."""
    baseline = load_baseline(ROOT / BASELINE)["diagnostics"]["probes"]
    deltas = {item.subject: item for item in load_deltas(ROOT / EXPECTED_DELTAS) if item.layer == "L3" and item.test == THIS_TEST}
    current = _run_sites()
    assert len(current) == sum(len(PROBE_STRINGS[site.family]) for site in ADDRESS_SITES)
    changed: set[str] = set()
    for key, after in current.items():
        label = key.rsplit(":", 1)[1]
        before = baseline.get(key, _MISSING)
        assert before is not _MISSING, f"{key} has no predecessor record in the baseline"
        assert (after is None) is (label == "valid"), f"{key}: the successor must accept only the valid address"
        if label == "valid":
            assert before is None and after is None, key
        if not _same(before, after):
            changed.add(key)
            assert key in deltas, f"{key} changed without an expected delta"
            assert _same(deltas[key].before, before) and _same(deltas[key].after, after), key
    # Every path-family probe at the render-context project address that moved is listed too, and no listed delta is stale.
    assert changed <= set(deltas)
    for key, item in deltas.items():
        if key not in current:
            assert "|path:" in key, f"{key} is neither an address-family probe nor a path-family probe"
    assert {"nul", "backslash", "drive-absolute", "drive-relative", "unc", "all-dot-segment", "empty-segment", "trailing-slash",
            "trailing-newline", "embedded-newline", "colon", "space", "non-ascii", "tab"} <= {key.rsplit(":", 1)[1] for key in changed}, \
        "the narrowed inputs are listed"


def test_the_path_family_probe_at_the_render_context_reference_moves_only_in_the_listed_way():
    """`reference.address` had no guard at all: every unsafe path probe was accepted by the schema before, refused now."""
    baseline = load_baseline(ROOT / BASELINE)["diagnostics"]["probes"]
    site = next(item for item in PROBE_SITES if item.family == "path" and item.pointer == "/body/project/address" and item.kind == "render-context")
    corpus = _load_corpus(_documents(), [site.source])
    current = run_probes(corpus, VALIDATORS, (site,))
    refused = {key.rsplit(":", 1)[1] for key, value in current.items() if value is not None}
    accepted_before = {key.rsplit(":", 1)[1] for key in current if baseline[key] is None}
    assert {"traversal", "absolute", "backslash", "nul", "dot", "dot-dot", "double-slash", "space", "non-ascii",
            "embedded-newline", "trailing-newline"} <= refused
    assert {"valid", "nested"}.isdisjoint(refused)
    assert {"traversal", "absolute", "backslash", "nul"} <= accepted_before


def test_every_migrated_document_keeps_its_verdict_under_the_successor():
    """Re-pointing a committed document is a version-string edit: it validates (or fails) exactly as under the predecessor."""
    checked = 0
    for path, content in _documents().items():
        try:
            document = yaml.safe_load(content) if not path.endswith(".json") else json.loads(content)
        except Exception:  # noqa: BLE001 - not a document
            continue
        version = document.get("version") if isinstance(document, dict) else None
        if version not in PREDECESSOR_OF:
            continue
        old_version = PREDECESSOR_OF[version]
        _, old_schema, new_schema = PAIRS[old_version]
        successor = VALIDATORS.first_error(new_schema, document)
        predecessor = VALIDATORS.first_error(old_schema, {**document, "version": old_version})
        assert successor == predecessor, path
        checked += 1
    assert checked >= 1, "the migration still covers the committed documents of the remaining successor kinds"


def test_no_committed_or_packaged_document_is_left_on_a_predecessor_version():
    """Anything pinned on purpose must be named here with its reason; the migration leaves none."""
    pinned = PINNED
    left = [path for path, content in _documents().items() if any(old.encode() in content for old in (*PAIRS, *RETIRED))
            and not path.startswith(("schemas/", "docs/", "conformance/schema-equivalence/"))]
    assert sorted(left) == sorted(pinned), left


def test_the_font_locator_of_a_context_keeps_a_package_address():
    context = _document("examples/aster-ssd/contexts/01-overview.yaml", RENDER_CONTEXT_VERSION)
    identity = ClosureIdentity("render-context", context["id"], "draft", "sha256:" + "0" * 64)
    assert parse_contract(identity, context).version == RENDER_CONTEXT_VERSION
    context["body"]["environment"]["fontMetrics"]["assets"][0]["font"]["locator"]["address"] = "fonts/./noto.ttf"
    with pytest.raises(ContractError):
        parse_contract(identity, context)


def test_the_baseline_records_of_the_address_probes_are_what_the_predecessors_say():
    """The baseline gained these probes in S-B; each record is the predecessor reader's answer, so it can be re-derived."""
    from tools.schema_equivalence import _set_at, probe_documents, probe_id, run_ingress

    baseline = load_baseline(ROOT / BASELINE)["diagnostics"]["probes"]
    corpus = _load_corpus(_documents(), sorted({site.source for site in ADDRESS_SITES if not site.source.startswith("inline:")}))
    for site in ADDRESS_SITES:
        for label, value in PROBE_STRINGS[site.family]:
            document = probe_documents(site, corpus)
            if document["version"] not in PREDECESSOR_OF:
                continue  # a retired predecessor can no longer be run; its record stays in the baseline as history
            document["version"] = PREDECESSOR_OF[document["version"]]
            _set_at(document, site.pointer, value)
            assert _same(run_ingress(document, VALIDATORS), baseline[probe_id(site, label)]), (site.pointer, label)
