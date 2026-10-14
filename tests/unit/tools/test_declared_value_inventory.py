import pytest
from pathlib import Path

from tools.declared_value_inventory import ComparisonSite, DeclaredValueInventoryError, discover, load_policy, render, validate


def _site(field: str = "contentIdentity") -> ComparisonSite:
    return ComparisonSite("src/chrona/usecases/sample.py", "check", field, 10, "reference.get('contentIdentity')", "identity")


def test_every_discovered_site_requires_one_classification(monkeypatch):
    monkeypatch.setattr("tools.declared_value_inventory.command_paths", lambda: {"chrona identity bytes"})
    site = _site()

    with pytest.raises(DeclaredValueInventoryError, match="missing=src/chrona/usecases/sample.py\\|check\\|contentIdentity"):
        validate((site,), ())

    validate((site,), ({"path": site.path, "function": site.function, "field": site.field,
                        "classification": "pinned-deliberately", "producer": "chrona identity bytes"},))


def test_nonexistent_identity_producer_fails(monkeypatch):
    monkeypatch.setattr("tools.declared_value_inventory.command_paths", lambda: {"chrona identity bytes"})
    site = _site()

    with pytest.raises(DeclaredValueInventoryError, match="E_DECLARED_VALUE_PRODUCER:chrona identity document"):
        validate((site,), ({"path": site.path, "function": site.function, "field": site.field,
                            "classification": "pinned-deliberately", "producer": "chrona identity document"},))


def test_report_exposes_resolution_route():
    site = _site("baseRevision")
    report = render((site,), ({"path": site.path, "function": site.function, "field": site.field,
                               "classification": "product-bookkeeping", "resolver": "chrona workspace revision"},))

    assert "chrona workspace revision" in report


def test_materializer_font_copy_plan_keeps_deliberate_identity_pinning():
    root = Path(__file__).resolve().parents[3]
    sites = discover(root)
    policy = load_policy(root / "conformance/resolvability-quality-policy-v0.1.yaml")
    validate(sites, policy)
    entry = next(item for item in policy if item["path"] == "src/chrona/usecases/materialize.py"
                 and item["function"] == "_font_copy_plan" and item["field"] == "contentIdentity")
    assert entry["classification"] == "pinned-deliberately"
    assert entry["producer"] == "chrona identity bytes"
