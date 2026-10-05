"""Which declared Theme roles and colour bindings has no consumer in a render closure (#1117).

A Theme names roles in `roles` and `colorBindings`. A registered role has a Scene or Layout consumer; a `group:<id>`
colour name is read by group colour encoding. Any other name is read only if a View or Detail Profile names it (an
axis tier or secondary `typographyRole`, a table column `textRole`, a legend entry `role`, a colour-encoding target).
A name no document of the closure carries is dead: nothing can read what it declares.

The test is structural and deliberately generous: a name counts as consumed when any string of the View, Detail
Profile, Layout Profile or Summary Profile equals it, so a role is never called dead while some document names it.
"""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any, Iterable, Mapping

from chrona.presentation.scene.capabilities import theme_role_contract

UNREAD_DIAGNOSTIC = "W_THEME_ROLE_UNREAD"


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        frame = value.get("frame")
        if isinstance(frame, Mapping) and isinstance(frame.get("paint"), str):
            yield f"region-frame-{frame['paint']}"
        for key, item in value.items():
            yield from _strings(key)
            yield from _strings(item)
    elif is_dataclass(value) and not isinstance(value, type):
        for item in fields(value):
            yield from _strings(getattr(value, item.name))
    elif isinstance(value, (list, tuple, set, frozenset)):
        for item in value:
            yield from _strings(item)


def declared_role_pointers(theme_body: Mapping[str, Any]) -> dict[str, tuple[str, ...]]:
    """Every role name the Theme declares, with the pointers that declare it."""
    found: dict[str, list[str]] = {}
    for role in (theme_body.get("roles") or {}):
        found.setdefault(str(role), []).append(f"/body/roles/{role}")
    for target in (theme_body.get("colorBindings") or {}):
        text = str(target)
        if "." in text:
            found.setdefault(text.rsplit(".", 1)[0], []).append(f"/body/colorBindings/{text}")
    return {role: tuple(pointers) for role, pointers in found.items()}


def unread_roles(theme_body: Mapping[str, Any], documents: Iterable[Any]) -> frozenset[str]:
    """The role names the Theme declares that no registered contract, group name or document reads."""
    named = frozenset(string for document in documents for string in _strings(document))
    return frozenset(role for role in declared_role_pointers(theme_body)
                     if (theme_role_contract(role) is None or role.startswith("region-frame-"))
                     and not role.startswith("group:") and role not in named)


def unread_role_pointers(theme_body: Mapping[str, Any], documents: Iterable[Any]) -> tuple[str, ...]:
    """The pointers of every declaration of an unread role."""
    declared = declared_role_pointers(theme_body)
    return tuple(sorted(pointer for role in unread_roles(theme_body, documents) for pointer in declared[role]))


def unread_diagnostics(theme_body: Mapping[str, Any], documents: Iterable[Any]) -> tuple[str, ...]:
    """Typed warnings, one per unread declaration, in pointer order."""
    return tuple(f"{UNREAD_DIAGNOSTIC}:{pointer}" for pointer in unread_role_pointers(theme_body, documents))
