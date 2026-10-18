"""The `initials` column cell transform (#1373 row 2).

Every literal below is ASCII: non-ASCII text is written as \\u escapes so the file and its console output
are encoding-safe on Windows. Synthetic Project through the packaged `executive-light` bundle; no test reads `examples/`.
"""
from __future__ import annotations

from datetime import date

import pytest

from chrona.presentation.model.surface_content import display_value, initials
from tests.support import synthetic_review as sr


@pytest.mark.parametrize(("text", "expected"), [
    ("Ana Maria Lopez", "AML"),                    # one letter per whitespace-separated word
    ("fw-team", "FT"),                             # hyphen is a word break
    ("Jean\u2010Luc\u2011Picard", "JLP"),          # U+2010 and U+2011 hyphens are word breaks
    ("alice", "alice"),                            # a single word is shown whole, as written (#1629)
    ("Raj", "Raj"), ("pm", "pm"), ("QT", "QT"),
    ("Priya Raman", "PR"),                         # two words: initials
    ("\u4f50\u85e4", "\u4f50\u85e4"),                # one unspaced CJK word is whole (#1629)
    ("\u4f50\u85e4\u5065\u592a\u90ce", "\u4f50\u85e4\u5065\u592a\u90ce"),
    (" Raj ", "Raj"),                              # edge whitespace is not part of the word
    ("e\u0301mile", "\u00e9mile"),                 # one word: whole, NFC
    ("  Ana \t\n Lopez  ", "AL"),                  # runs and edges of whitespace add no word
    ("\u00e9mile zola", "\u00c9Z"),                # non-ASCII letters upper-case by the Unicode default mapping
    ("e\u0301mile zola", "\u00c9Z"),               # a combining mark stays with its letter (NFC result)
    ("(Ken) \"Ito\"", "KI"),                       # leading punctuation is skipped
    ("3rd floor", "3F"),                           # a digit is an initial
    ("\u5c71\u7530 \u592a\u90ce", "\u5c71\u592a"), # CJK with a separator: first character of each word
    ("\u5c71\u7530\u592a\u90ce", "\u5c71\u7530\u592a\u90ce"),  # unspaced CJK is one word: shown whole
    ("\u5c71\u7530\u3000\u592a\u90ce", "\u5c71\u592a"),  # U+3000 ideographic space is whitespace
    ("istanbul izmir", "II"),                      # no locale tailoring: i is always I
    ("", ""), ("   ", ""), ("- -", ""), ("(!)", ""),  # no letter or digit: empty
])
def test_the_initials_rule(text, expected):
    assert initials(text) == expected


def test_initials_is_the_same_whatever_the_process_locale(monkeypatch):
    import locale
    before = initials("istanbul izmir")
    for name in ("tr_TR.UTF-8", "C"):
        try:
            locale.setlocale(locale.LC_ALL, name)
        except locale.Error:
            continue
        try:
            assert initials("istanbul izmir") == before == "II"
        finally:
            locale.setlocale(locale.LC_ALL, "")


def test_an_empty_result_reads_as_the_missing_text_and_a_non_text_value_is_a_diagnostic():
    assert display_value("", "em-dash", "text", transform="initials") == "\u2014"
    assert display_value("(!)", {"text": "?"}, "text", transform="initials") == "?"
    assert display_value(None, "blank", "text", transform="initials") == ""
    with pytest.raises(Exception) as caught:
        display_value(7, "blank", "text", transform="initials")
    assert "E_VIEW_COLUMN_TRANSFORM" in str(getattr(caught.value, "code", "")) + str(caught.value)


def test_no_transform_is_the_unchanged_text():
    assert display_value("Ana Maria", "blank", "text") == "Ana Maria"
    assert display_value("Ana Maria", "blank", "text", transform=None) == "Ana Maria"


OWNERS = {"a": "Ana Maria Lopez", "b": "fw-team", "c": "", "d": "zoe-ann ito"}


def _owner_cells(tmp_path, *, transform=None, source=None, fmt="text", affixes=None):
    objects = {key: sr.span(key, date(2026, 2, 2), 5, owner=owner or "-", title=key.upper()) for key, owner in OWNERS.items()}
    objects["c"]["fields"]["owner"] = ""
    source_doc = sr.project(objects)
    source_doc["entities"] = {}  # owner values are person names here, not entity ids (#1683)
    parts = sr.bundle("executive-light")
    column = {"id": "Owner", "source": source or {"field": "owner"}, "format": fmt, "missing": "em-dash", "align": "start",
              "width": "content", "headerOrientation": "horizontal"}
    if transform is not None:
        column["transform"] = transform
    if affixes is not None:
        column["affixes"] = affixes
    title = {"id": "Task", "source": "title", "missing": "em-dash", "align": "start", "width": "content",
             "headerOrientation": "horizontal"}
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    parts["view"]["body"]["tableColumns"] = [title, column]
    review = sr.render(tmp_path, source_doc, presentation=parts)
    return {item.source_ref: item.text for item in review.surface.primitives
            if item.purpose == "table-cell" and item.table_column_id == "Owner"}


def test_an_initials_column_puts_completed_initials_text_in_the_scene(tmp_path):
    cells = _owner_cells(tmp_path, transform="initials")

    assert cells == {"a": "AML", "b": "FT", "c": "\u2014", "d": "ZAI"}


def test_an_absent_transform_is_byte_identical_to_the_untransformed_column(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()

    assert _owner_cells(tmp_path / "a") == _owner_cells(tmp_path / "b") and _owner_cells(tmp_path / "a")["a"] == "Ana Maria Lopez"


def test_the_missing_affix_wraps_an_initials_cell_with_no_letter(tmp_path):
    cells = _owner_cells(tmp_path, transform="initials", affixes={"missing": {"suffix": "?"}})

    assert cells["c"] == "\u2014?" and cells["a"] == "AML"


@pytest.mark.parametrize(("kwargs", "code"), [
    ({"transform": "uppercase"}, "E_VIEW_SCHEMA"),                                 # outside the closed set
    ({"transform": "initials", "source": "id"}, "E_VIEW_COLUMN_TRANSFORM"),        # not a field or title source
    ({"transform": "initials", "source": {"facet": "planned"}}, "E_VIEW_COLUMN_TRANSFORM"),
    ({"transform": "initials", "fmt": "date"}, "E_VIEW_COLUMN_TRANSFORM"),          # not the text format
])
def test_an_unusable_transform_is_a_diagnostic(tmp_path, kwargs, code):
    with pytest.raises(Exception) as caught:
        _owner_cells(tmp_path, **kwargs)

    assert code in str(getattr(caught.value, "code", "")) + str(caught.value)
