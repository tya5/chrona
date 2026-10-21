"""`grouping.missing` accepts `{wording: key}` and follows the Render Context locale (#1865)."""
from __future__ import annotations

from copy import deepcopy
from datetime import date
import re

import pytest

from chrona.presentation.model.closure import ClosureError
from chrona.resources import schema_validator
from tests.integration.test_ja_jp_builtin_wording import _font_descriptor
from tests.support import synthetic_review as sr

UNASSIGNED = {"wording": "grouping.unassigned"}


def _source():
    objects = {"design": sr.span("design", date(2026, 3, 2), 14, owner="a"),
               "build": sr.span("build", date(2026, 3, 9), 14, owner="b"),
               "loose": sr.span("loose", date(2026, 3, 16), 14)}
    objects["loose"]["fields"] = {}
    return sr.project(objects)


def _texts(review):
    content = review.artifact.content
    svg = content.decode("utf-8") if isinstance(content, bytes) else content
    return [re.sub(r"<[^>]+>", "", body).strip() for body in re.findall(r"<text\b[^>]*>(.*?)</text>", svg, flags=re.S)]


def _render(tmp_path, missing, locale, *, by_field):
    parts = sr.bundle()
    grouping = parts["view"]["body"]["grouping"]
    grouping["missing"] = deepcopy(missing)
    if by_field:
        grouping.pop("fallback")
        grouping["by"] = "field"
        grouping["field"] = "owner"
    directory = tmp_path / f"{locale}-{by_field}"
    directory.mkdir()
    return _texts(sr.render(directory, _source(), presentation=parts, locale=locale,
                            font_metrics_path=_font_descriptor(directory)))


@pytest.mark.parametrize("by_field", [True, False], ids=["field", "field-role"])
def test_a_wording_reference_reads_the_table_entry_for_each_locale(tmp_path, by_field):
    japanese = _render(tmp_path, UNASSIGNED, "ja-JP", by_field=by_field)
    english = _render(tmp_path, UNASSIGNED, "en-US", by_field=by_field)
    assert any("未割り当て" in text for text in japanese), japanese
    assert not any("nassigned" in text for text in japanese), japanese
    assert any("Unassigned" in text for text in english), english
    assert not any("未割り当て" in text for text in english), english


def test_a_plain_string_is_unchanged_under_every_locale(tmp_path):
    for locale in ("en-US", "ja-JP"):
        texts = _render(tmp_path, "Unset", locale, by_field=True)
        assert any("Unset" in text for text in texts), texts


def test_the_schema_accepts_a_known_key_and_rejects_an_unknown_one():
    validator = schema_validator("view-v0.28.schema.yaml")
    view = sr.bundle()["view"]
    view["body"]["grouping"]["missing"] = UNASSIGNED
    assert not list(validator.iter_errors(view))
    view["body"]["grouping"]["missing"] = {"wording": "grouping.nope"}
    assert list(validator.iter_errors(view))


def test_an_unknown_key_is_refused_at_the_missing_pointer_like_a_column_header(tmp_path):
    with pytest.raises(ClosureError) as raised:
        _render(tmp_path, {"wording": "grouping.nope"}, "en-US", by_field=True)
    assert (raised.value.diagnostic_id, raised.value.source_ref) == ("E_VIEW_SCHEMA", "/body/grouping/missing")
