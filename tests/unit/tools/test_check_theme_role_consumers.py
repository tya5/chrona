"""The corpus tool that fails on Theme roles no closure reads (#1117): synthetic trees, no `examples/` input."""
from __future__ import annotations

from pathlib import Path

import yaml

from tools.check_theme_role_consumers import dead_declarations, main


def _write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _example(root: Path, *, theme_roles, bindings, views, name="demo", version="chrona/theme/v0.15"):
    """One example with a shared Theme and one Render Context per View in `views` (name -> View body)."""
    base = root / "examples" / name
    _write(base / "themes/t.yaml", {"version": version, "kind": "theme", "id": "t",
                                    "body": {"roles": theme_roles, "colorBindings": bindings}})
    _write(base / "layouts/l.yaml", {"version": "chrona/layout-profile/v0.10", "id": "l", "root": {}})
    for view_name, body in views.items():
        _write(base / f"views/{view_name}.yaml", {"version": "chrona/view/v0.28", "kind": "view", "id": view_name, "body": body})
        _write(base / f"contexts/{view_name}.yaml", {"body": {
            "theme": {"address": "themes/t.yaml"}, "view": {"address": f"views/{view_name}.yaml"},
            "layout": {"address": "layouts/l.yaml"}, "inputs": {}}})


def test_a_role_no_closure_names_is_dead(tmp_path):
    _example(tmp_path, theme_roles={"ghost": {}}, bindings={"ghost.fill": "accent", "text.fill": "text"},
             views={"a": {"surface": "table-timeline"}})
    assert dead_declarations(tmp_path) == ("E_THEME_ROLE_UNREAD:examples/demo/themes/t.yaml:ghost",)


def test_a_role_one_of_several_closures_names_is_not_dead(tmp_path):
    _example(tmp_path, theme_roles={"column-ink": {}}, bindings={"column-ink.fill": "accent"},
             views={"names-it": {"tableColumns": [{"id": "x", "textRole": "column-ink"}]}, "silent": {"surface": "table-timeline"}})
    assert dead_declarations(tmp_path) == ()


def test_registered_roles_group_names_and_derived_themes_are_not_reported(tmp_path):
    _example(tmp_path, theme_roles={"planned": {}}, bindings={"planned.fill": "accent", "group:team-a.fill": "accent"},
             views={"a": {"surface": "table-timeline"}})
    _example(tmp_path, theme_roles={"ghost": {}}, bindings={}, views={"a": {"surface": "table-timeline"}},
             name="derived", version="chrona/theme/v0.16")
    assert dead_declarations(tmp_path) == ()


def test_the_cli_exits_one_on_a_dead_role_and_zero_on_a_clean_tree(tmp_path, monkeypatch, capsys):
    _example(tmp_path / "dirty", theme_roles={"ghost": {}}, bindings={}, views={"a": {"surface": "table-timeline"}})
    _example(tmp_path / "clean", theme_roles={"planned": {}}, bindings={}, views={"a": {"surface": "table-timeline"}})
    import sys
    for tree, code in (("dirty", 1), ("clean", 0)):
        monkeypatch.setattr(sys, "argv", ["check_theme_role_consumers", "--root", str(tmp_path / tree)])
        assert main() == code
    assert "E_THEME_ROLE_UNREAD" in capsys.readouterr().out
