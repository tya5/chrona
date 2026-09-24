from __future__ import annotations

import yaml

from chrona.resources import safe_load, schema_document
from chrona.presentation.contracts.resources import _registry


def test_safe_load_preserves_safe_loader_values() -> None:
    payload = "date: 2026-09-24\nitems: [one, two]\n"

    assert safe_load(payload) == yaml.safe_load(payload)


def test_safe_load_falls_back_for_a_yaml_flow_mapping() -> None:
    payload = "{version: timeline/v0.6, kind: project}"

    assert safe_load(payload) == {"version": "timeline/v0.6", "kind": "project"}


def test_packaged_schema_document_is_decoded_once_per_name() -> None:
    schema_document.cache_clear()

    first = schema_document("project-v0.6.schema.yaml")
    second = schema_document("project-v0.6.schema.yaml")

    assert first is second
    assert schema_document.cache_info().misses == 1
    assert schema_document.cache_info().hits == 1

    schema_document.cache_clear()


def test_contract_registry_is_constructed_once_per_process() -> None:
    _registry.cache_clear()

    first = _registry()
    second = _registry()

    assert first is second
    assert _registry.cache_info().misses == 1
    assert _registry.cache_info().hits == 1

    _registry.cache_clear()
