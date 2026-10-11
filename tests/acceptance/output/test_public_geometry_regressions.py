"""Corpus-wide literal acceptance guards for #439, #443, #435 and #455.

No test here states how many slides, scenes or labels the corpus has (#977): the slides are the ones the manifests
declare and the per-slide counts are the reviewed rows of `public-slide-ledger.yaml`.
"""
from pathlib import Path
from xml.etree import ElementTree
import json
import pytest

from tests.support.public_evidence import declared_slides


ROOT = Path(__file__).resolve().parents[3]
MICRO_POINT = 0.000001


@pytest.fixture(scope="module")
def declared():
    """Load public manifest declarations once, on first test execution."""
    return declared_slides()


def _overlap(left: dict, right: dict) -> bool:
    return (min(left["inline"] + left["inlineSize"], right["inline"] + right["inlineSize"])
            - max(left["inline"], right["inline"]) > MICRO_POINT
            and min(left["block"] + left["blockSize"], right["block"] + right["blockSize"])
            - max(left["block"], right["block"]) > MICRO_POINT)


def test_all_public_axis_labels_and_independent_notes_have_no_positive_area_intersection(declared):
    scenes = tuple(sorted(slide.scene.resolve() for slide in declared if slide.scene))
    assert scenes == tuple(sorted((ROOT / "examples").glob("*/generated/*.scene.json")))
    axis_count = 0
    for path in scenes:
        for surface in json.loads(path.read_bytes())["surfaces"]:
            primitives = surface["primitives"]
            axis = [item for item in primitives if item.get("purpose") == "axis-label"]
            axis_count += len(axis)
            for index, left in enumerate(axis):
                assert all(not _overlap(left["bounds"], right["bounds"]) for right in axis[index + 1:]), path
            notes = [item for item in primitives if item.get("purpose") == "project-note"]
            for index, left in enumerate(notes):
                assert all(left["slotId"] != right["slotId"] or not _overlap(left["bounds"], right["bounds"])
                           for right in notes[index + 1:]), path
    assert axis_count > 0


def test_all_public_ellipsized_legends_stay_in_slot_and_boolean_cells_are_readable(declared):
    scenes = tuple(sorted(slide.scene.resolve() for slide in declared if slide.scene))
    assert scenes == tuple(sorted((ROOT / "examples").glob("*/generated/*.scene.json")))
    for path in scenes:
        for surface in json.loads(path.read_bytes())["surfaces"]:
            slots = {item["id"]: item for item in surface["slots"]}
            for item in surface["primitives"]:
                if item.get("purpose") == "table-cell":
                    assert item.get("text") not in {"True", "False"}, (path, item["id"])
                if item.get("purpose") != "legend-label":
                    continue
                slot = slots[item["slotId"]]
                if slot["overflow"] != "ellipsize-with-source":
                    continue
                bounds, limit = item["bounds"], slot["bounds"]
                assert bounds["inline"] >= limit["inline"] - MICRO_POINT, (path, item["id"])
                assert bounds["inline"] + bounds["inlineSize"] <= (
                    limit["inline"] + limit["inlineSize"] + MICRO_POINT), (path, item["id"])


def test_every_public_svg_axis_label_is_after_its_band_and_hosted_dvt_label_is_after_its_bar(declared):
    svgs = tuple(sorted(slide.svg.resolve() for slide in declared))
    assert svgs == tuple(sorted((ROOT / "examples").glob("*/generated/*.svg")))
    axis_count = 0
    hosted = 0
    for path in svgs:
        elements = list(ElementTree.parse(path).getroot())
        bands = [index for index, item in enumerate(elements) if item.get("data-purpose") == "axis-band"]
        labels = [index for index, item in enumerate(elements) if item.get("data-purpose") == "axis-label"]
        axis_count += len(labels)
        if bands and labels:
            assert min(labels) > max(bands), path
        if path.parent.parent.name != "controller-z":
            continue
        host = next((index for index, item in enumerate(elements)
                     if item.get("data-purpose") == "planned" and item.get("data-source-ref") == "dvt"), None)
        label = next((index for index, item in enumerate(elements)
                      if item.get("data-purpose") == "member-label" and item.get("data-source-ref") == "dvt"), None)
        if host is not None and label is not None:
            hosted += 1
            assert label > host, path
    assert axis_count > 0 and hosted > 0
