"""Canonical semantic identities from a complete normalized relation list."""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import quote


def relation_identities(relations: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    """Close identity before filtering; only exact fallback duplicates need order.

    Dates, lag and paint are not identity. Uniqueness is Project-wide, not
    visibility-local. Components cannot introduce delimiters or suffixes.
    """
    declared_counts = Counter(relation.get("id") for relation in relations
                              if isinstance(relation.get("id"), str) and relation["id"])
    bases = []
    for relation in relations:
        declared = relation.get("id")
        if isinstance(declared, str) and declared and declared_counts[declared] == 1:
            bases.append("relation:id:" + quote(declared, safe=""))
        else:
            source, target = relation["from"], relation["to"]
            components = (relation["type"], source["object"], source["endpoint"],
                          target["object"], target["endpoint"])
            bases.append("relation:edge:" + ":".join(quote(value, safe="") for value in components))
    counts = Counter(bases)
    occurrences: Counter[str] = Counter()
    identities = []
    for base in bases:
        occurrences[base] += 1
        identities.append(base if counts[base] == 1 else f"{base}:occurrence:{occurrences[base]}")
    return tuple(identities)
