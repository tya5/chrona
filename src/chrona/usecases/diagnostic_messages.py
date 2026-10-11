"""What a diagnostic row says: the message every row an agent can see must carry (#782).

A producer that knows the offending value says so in its own message. A producer that
raises a bare code (a ``ValueError("E_X")``, an importer that reports ``E_X source=/``)
leaves a message that is only the code, which tells a reader nothing. ``error_message``
is the one guarantee placed on the single record builder: an informative message passes
through unchanged; a bare one is replaced by a curated sentence for the code, or else by
a derived one that says plainly that no further detail is recorded for it.

Nothing here prints, reads arguments or imports a presentation, core or adapter module:
it reads strings.
"""
from __future__ import annotations

import re
from typing import Iterable, Mapping

# Codes whose producers cannot know the value, so the sentence names the cause and the
# next action instead. Add one entry per code an agent reaches by an ordinary mistake;
# a code with no entry is still safe (the derived sentence), only less helpful.
CURATED_MESSAGES: Mapping[str, str] = {
    "E_LAYOUT_VIEWER_FIT_STATIC_CHROME": (
        "an annotation with a kind frame or a label visual sits in a box role whose viewerFit is box-follows-text, "
        "but that chrome stands at fixed offsets the box cannot follow; use text-follows-box or remove the chrome"
    ),
    "E_PRESENTATION_VIEWER_FIT_PAINT": (
        "a box role whose viewerFit is box-follows-text has an outline, gradient, shadow, glow, pattern, image or "
        "wobble; give it a solid fill only, or use text-follows-box"
    ),
    "E_SCHEME_INTENT_UNKNOWN": (
        "a Color Scheme colorBindings entry is not ROLE.PROPERTY bound to a known intent or a declared color; "
        "check every target name and value in colorBindings"
    ),
    "E_SCHEME_THEME_BINDING": (
        "a Color Scheme colorBindings target names an unsupported property; "
        "use fill, stroke, gradientStart, gradientEnd, shadowColor or glowColor"
    ),
    "E_THEME_ROLE_PROPERTY_UNSUPPORTED": (
        "a Theme role binds a property that no drawing rule reads; remove it or bind a supported property"
    ),
    "E_LAYOUT_TOKEN_REQUIREMENT_UNAVAILABLE": (
        "a Layout profile refers to a Theme token that the Theme does not declare; "
        "add the token to the Theme or use a Theme that declares it"
    ),
    "E_LAYOUT_TOKEN_REQUIREMENT_TYPE": (
        "a Layout profile uses a Theme token whose type does not fit that place; "
        "the token must be a number here"
    ),
}

_SOURCE_SUFFIX = re.compile(r"\bsource=\S*")
_PUNCTUATION = " \t\r\n:;,.-"


def is_bare(code: str, message: str | None) -> bool:
    """Whether ``message`` says nothing beyond ``code``: empty, the code itself, or the code and ``source=<ref>``."""
    text = (message or "").strip()
    if not text:
        return True
    remainder = _SOURCE_SUFFIX.sub("", text.replace(code, ""))
    return not remainder.strip(_PUNCTUATION)


def derived_message(code: str) -> str:
    """A sentence built from the code alone; honest that it is only the code's name."""
    words = code.split("_", 1)[-1].replace("_", " ").lower() or code
    return f"{words}: no further detail is recorded for this code ({code})"


def error_message(code: str, message: str | None) -> str:
    """The message a row carries: the producer's if informative, else the curated or derived sentence."""
    if not is_bare(code, message):
        return str(message)
    return CURATED_MESSAGES.get(code) or derived_message(code)


# --- render warnings -----------------------------------------------------------------------------------------
#
# A warning's *cause* is the sentence for its code (and, for a fit warning, its failure kind): what happened and
# why. Its *subject* is the per-instance part: which label, placement, object. Two warnings with the same code,
# severity and cause are one finding that happened more than once, and collapse into one row (design D1).

_SURFACE_CAUSES: Mapping[str, str] = {
    "W_LAYOUT_OUTSIDE_WINDOW": "objects outside the explicit window were clipped or left out of the plot; their source data is unchanged",
    "W_LAYOUT_MARK_STACK_OVERFLOW": "a comparison stack exceeds its nominal track; row space was expanded",
    "W_LAYOUT_LABEL_SUPPRESSED": "a label was left out of the picture because it does not fit",
    "W_THEME_ROLE_UNREAD": "a Theme role or colour binding is declared but no registered role, group colour or document of the render reads it",
    "W_LAYOUT_ASOF_BELOW_PLOT_FALLBACK": (
        "the as-of chip could not be placed below the plot, so it sits inside the plot foot instead"),
    "W_LAYOUT_RELATION_SUPPRESSED": "a relation line was left out of the picture because no route fits",
    "I_LAYOUT_RELATION_MARK_BLOCKED": "a relation was left out because its fallback would cross a primary mark",
    "I_LAYOUT_RELATION_SEGMENT_TOO_SHORT": "a relation was left out because its fallback would have a segment shorter than its stroke width",
    "E_LAYOUT_ROUTE_THROUGH_MARK": "a relation route crosses a primary mark interior",
    "W_SCENE_RELATION_THROUGH_MARK": "a dependency line runs through a primary mark",
    "W_LAYOUT_RELATION_LABEL_SUPPRESSED": "a relation label was left out of the picture because it does not fit",
    "W_LAYOUT_ACTUAL_INCOMPLETE": "an actual observation is incomplete, so its actual bar is not drawn",
    "W_LAYOUT_OPEN_ACTUAL_INVALID": "an open actual does not start before the as-of date, so its bar is not drawn",
    "W_LAYOUT_OPEN_ACTUAL_AS_OF_REQUIRED": (
        "an actual is open until the as-of date but no as-of date is given, so its bar is not drawn"),
    "W_LAYOUT_AXIS_LABEL_THINNED": "an axis label was dropped because the labels of its tier do not all fit",
    "W_LAYOUT_AXIS_DENSITY": "an axis tier was thinned because its labels do not all fit",
    "W_LAYOUT_AXIS_FORM_EQUIVALENT": "an axis label form coincides with another canonical form of the same month",
    "W_LAYOUT_AXIS_SECONDARY_OMITTED": "the secondary label of an axis cell was omitted because it does not fit beside or below the main label",
    "W_LAYOUT_AXIS_CELL_CORNER_REDUCED": "the corner of an axis band cell was reduced to half the cell width because the cell is narrower than twice the declared corner",
    "W_LAYOUT_REGION_FRAME_CORNER_REDUCED": "the corner radius of a region frame was reduced to half its shorter side because the frame is smaller than twice the declared radius",
    "W_LAYOUT_ANNOTATION_ROUTE_SEARCH_EXHAUSTED": "the search for a route for an annotation tail ran out of candidates",
    "W_LAYOUT_ANNOTATION_CANDIDATE_FALLBACK": "an annotation was placed at a later candidate than the first one declared",
    "W_LAYOUT_ANNOTATION_FILL_NOT_SLOT": "a note box declared inlineSize fill but was not placed in an annotations slot, so it keeps the size of its text",
    "W_LAYOUT_ANNOTATION_SUPPRESSED": "an annotation was left out because it does not fit",
    "W_LAYOUT_NOTE_INDEX_SUPPRESSED": "a note index mark was left out because it does not fit",
    "W_VIEWER_FIT_NOT_HONOURED": "a box role declared a viewer-fit mode that the output target cannot honour, so it is drawn as raw",
}
_FIT_CAUSES: Mapping[str, str] = {
    "W_LAYOUT_VISIBLE_OVERFLOW": "text or content is drawn past its box",
    "W_LAYOUT_TEXT_ELLIPSIZED": "text was shortened with an ellipsis to fit its box",
    "W_LAYOUT_DETAIL_PANEL_CLIPPED": "detail panel content was cut off at the panel edge",
    "W_LAYOUT_NETWORK_OVERFLOW": "the dependency network is larger than its area",
    "W_LAYOUT_ROUTE_FALLBACK": "a relation route fell back to a simpler path",
    "W_LAYOUT_ROW_DENSITY": "a row is too dense for its height",
    "W_LAYOUT_MARK_OVERFLOW": "a mark does not fit its space",
    "W_LAYOUT_LABEL_OVERFLOW": "a label does not fit its space",
    "W_LAYOUT_GROUP_HEADER_OVERFLOW": "a group header does not fit its space",
    "W_LAYOUT_CANVAS_EXCEEDS_VIEWPORT": "the completed canvas exceeds the declared viewport",
}
_SCENE_CAUSES: Mapping[str, str] = {
    "W_SCENE_SUPPRESSED_PRIMITIVE_EMITTED": "a drawing element that layout left out was emitted anyway",
    "W_SCENE_TEXT_SLOT_ESCAPE": "text is drawn outside the slot it belongs to",
    "W_SCENE_TEXT_OCCLUDED": "text is covered by another shape",
    "W_SCENE_TEXT_INTERSECTION": "two pieces of text overlap",
    "W_SCENE_RELATION_PATH_DUPLICATE": "one dependency is drawn more than once",
    "W_SCENE_RELATION_PATH_REVERSES": "a dependency line doubles back over itself",
    "W_SCENE_RELATION_SEGMENT_TOO_SHORT": "a dependency line has a segment shorter than its stroke width",
    "W_SCENE_RELATION_NODE_APPROACH_SHARED": "two dependency lines share a positive-length approach segment at the same node",
    "W_SCENE_RELATION_FAN_IN_INVALID": "shared dependency arrivals do not agree on their target port, terminal owner, paint, or approach direction",
    "W_SCENE_DECORATION_CONTRAST": "a background decoration is fainter than its visibility floor against the ground it lies on",
    "W_SCENE_MARK_CONTRAST": "a mark is fainter than its 3:1 visibility floor against the ground it lies on",
    "W_SCENE_STATE_TEXT_CONTRAST": "text is fainter than its contrast floor against the ground it lies on",
    "W_SCENE_CONTRAST_GROUND_UNSUPPORTED": "a mark or text lies on a ground whose colour cannot be computed, so its contrast cannot be judged",
    "W_SCENE_DECORATION_GROUND_UNSUPPORTED": "a background decoration lies on a translucent ground, so its contrast cannot be judged",
}
MAX_OCCURRENCES = 20


class WarningText:
    """The cause and the per-instance subject of one render warning."""

    __slots__ = ("cause", "subject")

    def __init__(self, cause: str, subject: str = "") -> None:
        self.cause, self.subject = cause, subject


def _items(value: object) -> list[object]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _number(value: object) -> str:
    return f"{value:g}" if isinstance(value, (int, float)) else str(value)


def _describe_warning(payload: Mapping[str, object]) -> WarningText:
    """Name the cause and the subject of one warning record of ``usecases.warning_ledger``."""
    code = str(payload.get("code", ""))
    identity = str(payload.get("diagnostic", ""))
    if code in _SURFACE_CAUSES:
        return WarningText(_SURFACE_CAUSES[code], identity.removeprefix(code).removeprefix(":"))
    if code in _FIT_CAUSES:
        if code == "W_LAYOUT_CANVAS_EXCEEDS_VIEWPORT":
            declared = payload.get("declared")
            actual = payload.get("actual")
            if isinstance(declared, Mapping) and isinstance(actual, Mapping):
                block = "auto" if declared.get("blockSize") is None else _number(declared.get("blockSize"))
                declared_size = f"{_number(declared.get('inlineSize'))}x{block}"
                actual_extent = (f"origin {_number(actual.get('inlineStart'))},{_number(actual.get('blockStart'))} "
                                 f"size {_number(actual.get('inlineSize'))}x{_number(actual.get('blockSize'))}")
            else:
                declared_size, actual_extent = "unknown", "unknown"
            subjects = []
            for item in _items(payload.get("contributors")):
                if not isinstance(item, Mapping):
                    continue
                overrun = item.get("overrun")
                if not isinstance(overrun, Mapping):
                    continue
                edges = [f"{edge} {_number(overrun.get(key))}" for edge, key in (
                    ("inline-start", "inlineStart"), ("inline-end", "inlineEnd"),
                    ("block-start", "blockStart"), ("block-end", "blockEnd"))
                    if isinstance(overrun.get(key), (int, float)) and overrun.get(key) > 0]
                if edges:
                    subjects.append(f"{item.get('slotId')} ({', '.join(edges)})")
            contributor_count = payload.get("contributorCount", len(subjects))
            contributor_text = ", ".join(subjects) if subjects else "no slot detail"
            if isinstance(contributor_count, int) and contributor_count > len(subjects):
                contributor_text += f", and {contributor_count - len(subjects)} more"
            subject = (f"surface {payload.get('surfaceId')} at {payload.get('sourceRef')}: "
                       f"declared {declared_size}, actual {actual_extent}; contributors: {contributor_text}")
            return WarningText(_FIT_CAUSES[code], subject)
        cause = f"{_FIT_CAUSES[code]} ({payload.get('failureKind')}, {payload.get('behaviour')})"
        needs = f"needs {_number(payload.get('requiredInline'))}x{_number(payload.get('requiredBlock'))}"
        has = f"has {_number(payload.get('availableInline'))}x{_number(payload.get('availableBlock'))}"
        return WarningText(cause, f"{payload.get('placementId')} ({needs}, {has})")
    if code in _SCENE_CAUSES:
        return WarningText(_SCENE_CAUSES[code], ", ".join(str(item) for item in _items(payload.get("primitiveIds"))))
    if code == "W_FONT_TABULAR_UNAVAILABLE":
        return WarningText(f"font {payload.get('family')} {payload.get('weight')} has no tabular digits, "
                           "so numbers use proportional spacing", str(payload.get("role")))
    if code == "W_FONT_GLYPH_SUBSTITUTED":
        return WarningText(f"a glyph missing from {payload.get('requestedFamily')} is drawn with "
                           f"{payload.get('fallbackFamily')}", f"{payload.get('codepoint')} in {payload.get('text')!r}")
    if code == "W_FONT_FALLBACK_PACKAGED":
        fields = dict(part.split("=", 1) for part in identity.removeprefix(code).removeprefix(":").split(";") if "=" in part)
        return WarningText(f"no installed face matches {fields.get('requested', '?')}, so the packaged "
                           f"{fields.get('face', 'Noto Sans')} is used", fields.get("role", ""))
    if code == "W_PRESENTATION_SCALE_NOT_SEPARABLE":
        first, second = (_items(payload.get("values")) + ["?", "?"])[:2]
        return WarningText(f"two colors of scale {payload.get('scaleId')} are not separable under "
                           f"{payload.get('vision')} vision", f"{first} and {second}")
    if code == "W_PROJECT_ATTACHED_OUTSIDE_HOST":
        return WarningText(f"an attached object is dated outside the planned span of its host {payload.get('host')}",
                           str(payload.get("sourceRef")))
    own = payload.get("message")
    if isinstance(own, str) and own != derived_message(code) and not is_bare(code, own):
        return WarningText(own)  # a family that says what is wrong keeps its sentence; only equal sentences merge
    tail = identity.removeprefix(code).removeprefix(":") if identity.startswith(code) else ""
    return WarningText(derived_message(code), tail)


def describe_warning(payload: Mapping[str, object]) -> WarningText:
    """Keep the cause stable while naming explicitly supplied Project subjects."""
    text = _describe_warning(payload)
    supplied = payload.get("sourceSubjects")
    if isinstance(supplied, (list, tuple)):
        subjects = [item for item in supplied if isinstance(item, Mapping)]
    elif "sourceTitle" in payload:
        subjects = [{"sourceRef": payload.get("sourceRef", "/"), "title": payload["sourceTitle"]}]
    else:
        return text
    names = [f"{item['title']!r} ({item.get('sourceRef', '/')})" if item.get("title") is not None
             else str(item.get("sourceRef", "/")) for item in subjects]
    if not names:
        return text
    owner = ", ".join(names)
    return WarningText(text.cause, f"{owner}; {text.subject}" if text.subject else owner)


def warning_message(text: WarningText, count: int = 1) -> str:
    """``cause: subject``; for several, ``cause: first subject and N more``."""
    if not text.subject:
        return text.cause if count == 1 else f"{text.cause} ({count} times)"
    return f"{text.cause}: {text.subject}" + ("" if count == 1 else f" and {count - 1} more")


def collapse_warnings(payloads: Iterable[Mapping[str, object]]) -> list[dict[str, object]]:
    """Merge warnings with the same code, severity and cause into the first, in order of first occurrence.

    A single warning is returned with its ``message``. A merged row keeps every key of the first occurrence,
    gains ``count`` (2 or more) and ``occurrences`` (the distinct identities in order, at most 20), and its
    message names the first subject and how many more there were.
    """
    groups: dict[tuple[str, str, str], list[Mapping[str, object]]] = {}
    for payload in payloads:
        key = (str(payload.get("code")), str(payload.get("severity")), describe_warning(payload).cause)
        groups.setdefault(key, []).append(payload)
    rows: list[dict[str, object]] = []
    for members in groups.values():
        row = dict(members[0])
        if len(members) > 1:
            identities = list(dict.fromkeys(str(item["diagnostic"]) for item in members if "diagnostic" in item))
            row["count"] = len(members)
            row["occurrences"] = identities[:MAX_OCCURRENCES]
        row["message"] = warning_message(describe_warning(members[0]), len(members))
        rows.append(row)
    return rows
