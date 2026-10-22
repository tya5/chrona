"""Snapshot table sources widen live View/Style without changing frozen sources."""
from copy import deepcopy

import pytest

from chrona.resources import schema_document, schema_validator, validator_for_schema
from tests.support import synthetic_review as sr


def _source_validator(version):
    return validator_for_schema({"$ref": f"urn:chrona:common-v{version}#/$defs/tableColumnSource"})


@pytest.mark.parametrize("source", ["title", {"field": "owner"}, {"facet": "finishDelta"},
                                    {"comparisonFacet": "finishDelta"}, {"scenario": "title"}])
def test_original_table_sources_keep_their_verdict(source):
    assert _source_validator("0.1").is_valid(source)
    assert _source_validator("0.2").is_valid(source)


def test_snapshot_source_is_additive_and_old_part_stays_frozen():
    source = {"comparisonFacet": "snapshotFinishDelta"}
    assert not _source_validator("0.1").is_valid(source)
    assert _source_validator("0.2").is_valid(source)
    assert schema_document("vocabulary-v0.2.schema.yaml")["$defs"]["snapshotComparisonFacet"]["const"] == "snapshotFinishDelta"
    for invalid in ({"facet": "snapshotFinishDelta"}, {**source, "extra": True},
                    {"comparisonFacet": "unrecognised"}):
        assert not _source_validator("0.2").is_valid(invalid)


def test_live_view_and_style_share_snapshot_source_grammar():
    view = deepcopy(sr.bundle("executive-light")["view"])
    view["body"]["rows"] = {"mode": "automatic"}
    view["body"]["comparison"]["facets"].append("snapshotFinishDelta")
    view["body"]["tableColumns"] = [{"id": "Baseline", "source": {"comparisonFacet": "snapshotFinishDelta"},
        "format": "signedDays", "missing": "blank", "align": "end", "width": "content",
        "headerOrientation": "horizontal"}]
    assert list(schema_validator("view-v0.28.schema.yaml").iter_errors(view)) == []
    style = {"version": "chrona/style/v0.2", "kind": "style", "id": "baseline-delta", "body": {
        "rules": [{"id": "baseline-column", "when": {"columnSource": {"comparisonFacet": "snapshotFinishDelta"}},
                   "then": {"role": "text"}}]}}
    assert list(schema_validator("style-v0.2.schema.yaml").iter_errors(style)) == []
