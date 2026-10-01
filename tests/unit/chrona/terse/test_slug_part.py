"""The compiler's name pattern is the shared `slug` of common-v0.1; a changed schema part fails here instead of drifting."""
from __future__ import annotations

from chrona.resources import schema_document
from chrona.terse.parser import KINDS, RESERVED, SLUG


def test_name_pattern_equals_the_common_schema_slug():
    schema = schema_document("common-v0.1.schema.yaml")
    assert "^" + SLUG.pattern + "$" == schema["$defs"]["slug"]["pattern"]


def test_reserved_words_and_kinds_are_the_specified_sets():
    assert RESERVED == frozenset("terse project calendar task gate group after from until in except work start end at".split())
    assert KINDS == ("task", "gate", "group") and set(KINDS) <= RESERVED
