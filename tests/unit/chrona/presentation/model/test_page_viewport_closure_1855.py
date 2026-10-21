"""Draft viewport closure follows effective Layout page defaults (#1855)."""
from copy import deepcopy
from datetime import date
from hashlib import sha256
from pathlib import Path

import yaml
import pytest

from chrona.presentation.model.closure import resolve_draft_render
from chrona.resources import builtin_preset_source_root, safe_load
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.storage.snapshot_paths import snapshot_directory
from tests.support.synthetic_review import project, span


def _bundle():
    root = builtin_preset_source_root("presets/bundles/executive-light")
    return {name: safe_load(root.joinpath(f"{name}.yaml").read_bytes())
            for name in ("view", "theme", "scheme", "layout")}


def _write(path: Path, value):
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")
    return path


def _resolve(tmp_path, *, layout=None, viewport=None, package_reader=None, omit_argument=False):
    tmp_path.mkdir(parents=True, exist_ok=True)
    parts = _bundle()
    if layout is not None:
        parts["layout"] = layout
    paths = {name: _write(tmp_path / f"{name}.yaml", value)
             for name, value in parts.items()}
    return resolve_draft_render(
        project_path=_write(tmp_path / "project.yaml", project({"task": span("task", date(2026, 1, 1), 10)})),
        view_path=paths["view"], theme_path=paths["theme"], scheme_path=paths["scheme"],
        layout_path=paths["layout"], target_kind="svg",
        package_reader=package_reader,
        **({} if omit_argument else {"viewport": viewport}),
    )


def _viewport(draft):
    environment = draft.closure.context.environment
    return environment.viewport_inline, environment.viewport_block


@pytest.mark.parametrize("omit_argument", (True, False))
def test_omitted_viewport_without_page_size_keeps_1600_by_auto_default(tmp_path, omit_argument):
    draft = _resolve(tmp_path, omit_argument=omit_argument)

    assert _viewport(draft) == (1600, 900)
    assert draft.auto_block is True


@pytest.mark.parametrize("omit_argument", (True, False))
def test_omitted_viewport_uses_a4_landscape_page_size(tmp_path, omit_argument):
    layout = _bundle()["layout"]
    layout["pageSize"] = "a4-landscape"
    draft = _resolve(tmp_path, layout=layout, omit_argument=omit_argument)

    assert _viewport(draft) == (1123, 794)
    assert draft.auto_block is False
    assert "extends" not in draft.closure.layout_profile.layout_input
    assert draft.closure.layout_profile.layout_input["pageSize"] == "a4-landscape"


def test_explicit_fixed_viewport_overrides_page_size_as_a_whole(tmp_path):
    layout = _bundle()["layout"]
    layout["pageSize"] = "a4-landscape"
    draft = _resolve(tmp_path, layout=layout, viewport=(900, 600))

    assert _viewport(draft) == (900, 600)
    assert draft.auto_block is False


def test_explicit_auto_height_overrides_page_size_as_a_whole(tmp_path):
    layout = _bundle()["layout"]
    layout["pageSize"] = "a4-landscape"
    draft = _resolve(tmp_path, layout=layout, viewport=(1200, None))

    assert _viewport(draft) == (1200, 900)
    assert draft.auto_block is True


def test_omitted_viewport_uses_inherited_page_size_from_pinned_layout_base(tmp_path):
    base = _bundle()["layout"]
    base["pageSize"] = "a4-landscape"
    token, address = "base-r1", "layouts/base.yaml"
    payload = yaml.safe_dump(base, sort_keys=False).encode("utf-8")
    base_path = snapshot_directory(tmp_path / "store", token) / address
    base_path.parent.mkdir(parents=True)
    base_path.write_bytes(payload)
    reference = {
        "id": base["id"], "kind": "layout-profile",
        "store": {"provider": "local", "identity": "print-design"},
        "address": address, "revision": {"token": token},
        "contentIdentity": "sha256:" + sha256(payload).hexdigest(),
    }
    derived = {key: deepcopy(base[key]) for key in (
        "version", "id", "flowDirection", "dependencyNetworkFlowDirection",
        "requiredThemeTokens", "reviewSurface",
    )}
    derived.update(
        extends=reference,
        overrides={"page": {"padding": deepcopy(base["root"]["padding"])}},
    )

    draft = _resolve(
        tmp_path / "draft", layout=derived,
        package_reader=LocalSnapshotReader(tmp_path / "store", "print-design"),
    )

    assert _viewport(draft) == (1123, 794)
    assert draft.auto_block is False
    assert "extends" not in draft.closure.layout_profile.layout_input
    assert draft.closure.layout_profile.layout_input["pageSize"] == "a4-landscape"
