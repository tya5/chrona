import pytest

from tools.declared_value_inventory import ComparisonSite, DeclaredValueInventoryError, render, validate


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
