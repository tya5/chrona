"""The baseline `new` and `removed` markers are wording keys, not English literals (#1781, follow-up of #1755)."""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import re

import yaml

from chrona.presentation.contracts.resources import ViewComparison, ViewInput, ViewRows, ViewVisibility, ViewWindow
from chrona.presentation.model.projection import build_review_projection, finish_delta_text
from chrona.presentation.model.wording_tables import wording_resolver
from chrona.resources import safe_load
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from tests.support.text_treatments import CJK_DESCRIPTOR

ROOT = Path(__file__).resolve().parents[2]
KEPT = {"type": "task", "title": "Kept task", "schedule": {"mode": "fixed-span", "start": "2026-01-01", "end": "2026-01-03"}}
ADDED = {"type": "task", "title": "Added task", "schedule": {"mode": "fixed-span", "start": "2026-01-03", "end": "2026-01-05"}}
DROPPED = {"type": "task", "title": "Dropped task", "schedule": {"mode": "fixed-span", "start": "2026-01-05", "end": "2026-01-06"}}


ACTUAL = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed", "body": {
    "asOf": "2026-01-10", "observations": [
        {"id": "kept-1", "sequence": 1, "projectObjectId": "kept", "actual": {"start": "2026-01-01", "finish": "2026-01-04"}},
        {"id": "added-1", "sequence": 1, "projectObjectId": "added", "actual": {"start": "2026-01-03", "finish": "2026-01-06"}}]}}


def _plans():
    head = {"version": "timeline/v0.7", "project": {"id": "markers"}}
    return {**head, "objects": {"kept": KEPT, "added": ADDED}}, {**head, "objects": {"kept": KEPT, "dropped": DROPPED}}


def _write(path, document):
    path.write_text(yaml.safe_dump(document, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def _font_descriptor(directory):
    descriptor = safe_load((ROOT / "src/chrona/resources/fonts/default-font-metrics.yaml").read_bytes())
    descriptor["assets"] = [*descriptor["assets"], *safe_load(CJK_DESCRIPTOR.read_bytes())["assets"]]
    return _write(directory / "font-metrics.yaml", descriptor)


def _texts(tmp_path, locale):
    tmp_path.mkdir()
    project, snapshot = _plans()
    review = render_draft(DraftRenderRequest(
        _write(tmp_path / "project.yaml", project), "svg", preset="target-b",
        actual=_write(tmp_path / "actual.yaml", ACTUAL),
        snapshot=_write(tmp_path / "snapshot.yaml", snapshot), viewport="1600xauto", locale=locale, forecast=True,
        font_metrics=_font_descriptor(tmp_path))).rendered
    content = review.artifact.content
    svg = content.decode("utf-8") if isinstance(content, bytes) else content
    return [re.sub(r"<[^>]+>", "", body).strip() for body in re.findall(r"<text\b[^>]*>(.*?)</text>", svg, flags=re.S)]


def test_ja_jp_render_shows_both_japanese_markers_and_en_us_is_unchanged(tmp_path):
    ja = _texts(tmp_path / "ja", "ja-JP")
    assert "新規" in ja and any(text.endswith("(削除)") for text in ja), ja
    assert "new" not in ja and not any("(removed)" in text for text in ja), ja
    en = _texts(tmp_path / "en", "en-US")
    assert "new" in en and any(text.endswith("(removed)") for text in en), en


def _item(projection, object_id):
    return next(item for item in projection.items if item.object_id == object_id)


def _projection(wording):
    project, snapshot = _plans()
    scheduler = ReferenceScheduler()
    view = ViewInput(None, None, None, ViewWindow("selected-planned", None, None, 0),
                     ViewComparison("snapshot", "optional", None, None, (), baseline_marks="ghost"),
                     ViewVisibility(False, "none", "none"), (), (), ViewRows("automatic", ()), None, (), None, None, None)
    return build_review_projection(project, scheduler.schedule(project).placements, view, None, snapshot_project=snapshot,
                                   snapshot_placements=scheduler.schedule(snapshot).placements, wording=wording)


def test_markers_follow_the_locale_and_view_wording_keys_override():
    default = _projection(None)
    assert finish_delta_text(_item(default, 'added')) == "new" and default.rows[-1].items[0].title == "Dropped task (removed)"
    ja = _projection(wording_resolver("ja-JP", None))
    assert finish_delta_text(_item(ja, 'added')) == "新規" and ja.rows[-1].items[0].title == "Dropped task (削除)"
    custom = _projection(wording_resolver("en-US", {"keys": {"marker.baselineNew": "NEW!", "marker.baselineRemoved": "gone"}}))
    assert finish_delta_text(_item(custom, 'added')) == "NEW!" and custom.rows[-1].items[0].title == "Dropped task (gone)"
