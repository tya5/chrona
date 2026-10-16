"""Exact packaged-policy migrations; unrelated reference declarations stay guarded."""
from pathlib import Path

import yaml


def assert_view_copy_except_axis(packaged: Path, corpus: Path, *, first_run: bool = False) -> None:
    package_document = yaml.safe_load(packaged.read_bytes())
    corpus_document = yaml.safe_load(corpus.read_bytes())
    if first_run:
        # Specs32/38 change the first-run default, not independently authored examples.
        body = corpus_document["body"]
        body["selection"].pop("exclude")
        body["grouping"] = {"by": "hierarchy", "depth": "all", "rollup": "header"}
        body["hierarchyColumn"] = "Task"
        body["backgroundDecoration"]["rows"] = "rules"
        # #1583 switches only the bundled default; the authored reference keeps
        # its explicit calendar-day policy. Guard both sides before normalizing.
        assert body["comparison"]["deltaUnit"] == "calendar-days"
        assert package_document["body"]["comparison"]["deltaUnit"] == "working-days"
        body["comparison"]["deltaUnit"] = "working-days"
    lane_table = package_document["body"].get("rows", {}).get("laneTable", {})
    if lane_table.get("count") == "auto":
        reference_table = corpus_document["body"]["rows"]["laneTable"]
        assert reference_table["count"] is True
        reference_table["count"] = "auto"
    for document in (package_document, corpus_document):
        document.pop("version")
        document["body"].pop("axis")
        heading = document["body"].get("heading", {})
        heading.pop("text", None)
        if not heading:
            document["body"].pop("heading", None)
        for column in document["body"].get("tableColumns", ()):
            column.pop("endDisplay", None)
            column.pop("text", None)
        document["body"].get("rows", {}).get("laneTable", {}).pop("text", None)
    assert package_document == corpus_document
