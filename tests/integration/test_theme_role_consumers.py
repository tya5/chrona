"""A Theme role or binding no document of the render reads is reported, never silently accepted (#1117).

Synthetic Project through the packaged `executive-light` bundle; no test reads `examples/`.
"""
from __future__ import annotations

from datetime import date

from chrona.presentation.model.theme_role_consumers import unread_role_pointers
from tests.support import synthetic_review as sr

UNREAD = "W_THEME_ROLE_UNREAD"


def _render(directory, *, bindings=None, roles=None, mutate=None):
    directory.mkdir(parents=True, exist_ok=True)
    source = sr.project({"a": sr.span("a", date(2026, 2, 2), 30, title="Alpha")})
    parts = sr.bundle("executive-light")
    body = parts["theme"]["body"]
    for role in ("table-header", "annotation-text", "range"):  # the three dead names of the bundled Theme (#1117)
        body["colorBindings"].pop(f"{role}.fill", None)
    body["colorBindings"].update(bindings or {})
    body["roles"].update(roles or {})
    if mutate:
        mutate(parts)
    return sr.render(directory, source, presentation=parts)


def _unread(rendered):
    return [item for item in rendered.surface.diagnostics if item.startswith(UNREAD)]


def test_a_binding_on_a_role_nothing_reads_is_reported_at_its_pointer(tmp_path):
    rendered = _render(tmp_path, bindings={"no-such-role.fill": "accent"})
    assert _unread(rendered) == [f"{UNREAD}:/body/roles/no-such-role"]
    assert any(item.identity.startswith(UNREAD) for item in rendered.warning_records)  # surfaced as a render warning


def test_a_misspelt_registered_role_is_reported(tmp_path):
    rendered = _render(tmp_path, bindings={"as-of-lable.fill": "accent"})
    assert _unread(rendered) == [f"{UNREAD}:/body/roles/as-of-lable"]


def test_a_registered_role_a_group_name_and_clean_themes_are_not_reported(tmp_path):
    clean = _render(tmp_path / "clean")
    assert _unread(clean) == []
    registered = _render(tmp_path / "registered", bindings={"planned.fill": "accent", "group:team-a.fill": "accent"})
    assert _unread(registered) == []


def _column_role(parts):
    roles = parts["theme"]["body"]["roles"]
    roles["column-ink"] = {key: value for key, value in roles["text"].items() if key not in {"iconScale", "iconGap"}}


def test_a_role_a_column_text_role_names_is_read_and_one_nothing_names_is_not(tmp_path):
    def name_it(parts):
        _column_role(parts)
        view = parts["view"]["body"]
        view["rows"] = {"mode": "automatic"}
        view["tableColumns"] = [
            {"id": "Work package", "source": "title", "missing": "em-dash", "align": "start", "width": "content",
             "headerOrientation": "horizontal", "textRole": "column-ink"}]
    named = _render(tmp_path / "named", bindings={"column-ink.fill": "accent"}, mutate=name_it)
    assert _unread(named) == []
    unnamed = _render(tmp_path / "unnamed", bindings={"column-ink.fill": "accent"}, mutate=_column_role)
    assert _unread(unnamed) == [f"{UNREAD}:/body/roles/column-ink"]


def test_every_declaration_of_an_unread_role_is_reported_once_per_pointer(tmp_path):
    rendered = _render(tmp_path, bindings={"ghost.fill": "accent", "ghost.stroke": "text"}, roles={"ghost": {"strokeWidth": "stroke-width"}})
    assert _unread(rendered) == [f"{UNREAD}:/body/roles/ghost"]  # the resolved Theme holds one role entry


def test_the_function_reports_declarations_across_roles_and_bindings():
    body = {"roles": {"ghost": {}, "text": {}}, "colorBindings": {"phantom.fill": "accent", "text.fill": "text"}}
    assert unread_role_pointers(body, ({"x": "y"},)) == ("/body/colorBindings/phantom.fill", "/body/roles/ghost")
    assert unread_role_pointers(body, ({"x": ["ghost", {"y": "phantom"}]},)) == ()
