"""Validate documentary reusable-design gallery claims without rendering."""
from __future__ import annotations

from typing import Any, Callable, Mapping

from chrona.presentation.model.design_summary import PresentationDesignSummary


class DesignGalleryError(ValueError):
    """A gallery publication claim cannot be traced to its inspection evidence."""


def validate_catalog(
    value: Mapping[str, Any], *, corpus: Mapping[tuple[str, str], Mapping[str, Any]],
    summary_for: Callable[[str, str], PresentationDesignSummary],
    target_for: Callable[[str, str], Mapping[str, Any]],
) -> int:
    """Validate a design-gallery document as documentary data only.

    The callbacks are supplied by the publication boundary.  This module never
    loads a Context, locates package bytes, or invokes a materializer.
    """
    if value.get("version") != "chrona/design-gallery/v0.1" or not isinstance(value.get("entries"), list):
        raise DesignGalleryError("E_DESIGN_GALLERY_FORMAT")
    identities: set[str] = set()
    pairs: dict[str, list[tuple[str, str]]] = {}
    for entry in value["entries"]:
        if not isinstance(entry, Mapping):
            raise DesignGalleryError("E_DESIGN_GALLERY_ENTRY")
        identity, corpus_id, slide = entry.get("id"), entry.get("corpus"), entry.get("slide")
        if not all(isinstance(item, str) and item for item in (identity, corpus_id, slide)):
            raise DesignGalleryError("E_DESIGN_GALLERY_ENTRY")
        if identity in identities:
            raise DesignGalleryError("E_DESIGN_GALLERY_DUPLICATE")
        identities.add(identity)
        key = (corpus_id, slide)
        if key not in corpus:
            raise DesignGalleryError("E_DESIGN_GALLERY_REFERENCE")
        if not isinstance(entry.get("narrative"), Mapping) or not isinstance(entry["narrative"].get("title"), str):
            raise DesignGalleryError("E_DESIGN_GALLERY_NARRATIVE")
        summary = summary_for(*key)
        _assertions(entry.get("designAssertions", {}), summary)
        _target(entry.get("target", {}), target_for(*key))
        accessibility = entry.get("accessibility")
        if not isinstance(accessibility, Mapping) or not isinstance(accessibility.get("note"), str) or not accessibility["note"].strip():
            raise DesignGalleryError("E_DESIGN_GALLERY_ACCESSIBILITY")
        pair = entry.get("comparison")
        if not isinstance(pair, Mapping) or not isinstance(pair.get("set"), str) or not isinstance(pair.get("axis"), str):
            raise DesignGalleryError("E_DESIGN_GALLERY_PAIR")
        pairs.setdefault(pair["set"], []).append(key)
    if any(len(items) < 2 for items in pairs.values()):
        raise DesignGalleryError("E_DESIGN_GALLERY_UNPAIRED")
    return len(identities)


def _assertions(value: Any, summary: PresentationDesignSummary) -> None:
    if not isinstance(value, Mapping):
        raise DesignGalleryError("E_DESIGN_GALLERY_ASSERTION")
    for dimension, assertions in value.items():
        if not isinstance(dimension, str) or not isinstance(assertions, Mapping):
            raise DesignGalleryError("E_DESIGN_GALLERY_ASSERTION")
        available = summary.dimensions.get(dimension)
        if available is None:
            raise DesignGalleryError("E_DESIGN_GALLERY_ASSERTION")
        for name, expected in assertions.items():
            actual = available.get(str(name))
            if actual is None:
                raise DesignGalleryError("E_DESIGN_GALLERY_ASSERTION")
            if actual.value != expected:
                raise DesignGalleryError("E_DESIGN_GALLERY_ASSERTION_MISMATCH")


def _target(value: Any, actual: Mapping[str, Any]) -> None:
    if not isinstance(value, Mapping) or not isinstance(value.get("kind"), str):
        raise DesignGalleryError("E_DESIGN_GALLERY_TARGET")
    if value["kind"] != actual.get("kind"):
        raise DesignGalleryError("E_DESIGN_GALLERY_TARGET")
    capabilities = value.get("capabilities", [])
    if not isinstance(capabilities, list) or any(not isinstance(item, str) for item in capabilities):
        raise DesignGalleryError("E_DESIGN_GALLERY_TARGET")
    if not set(capabilities).issubset(set(actual.get("capabilities", ()) )):
        raise DesignGalleryError("E_DESIGN_GALLERY_TARGET")
