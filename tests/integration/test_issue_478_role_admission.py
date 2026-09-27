"""Role admission keeps exact Theme pointers across both closure paths."""
from hashlib import sha256
from pathlib import Path
import shutil

import pytest
import yaml

from chrona.core.identity import content_identity
from chrona.presentation.model.closure import ClosureError, resolve_draft_render, resolve_render_context
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.usecases.materialize import copy_context_closure


ROOT = Path(__file__).resolve().parents[2]


def _paths(root: Path) -> dict[str, Path]:
    example = root / "examples/controller-z"
    return {
        "project_path": example / "project.yaml",
        "view_path": example / "views/executive.yaml",
        "theme_path": example / "themes/executive-light.yaml",
        "scheme_path": example / "schemes/executive-light.yaml",
        "layout_path": example / "layouts/executive-review.yaml",
    }


def _write_yaml(path: Path, value: dict) -> bytes:
    payload = yaml.safe_dump(value, sort_keys=False).encode("utf-8")
    path.write_bytes(payload)
    return payload


def _add_invalid_property(theme: dict) -> None:
    # Text-only state role: Theme roles cannot carry strokeWidth here.
    theme["body"]["roles"].setdefault("variance-behind", {})["strokeWidth"] = "stroke-width"


def test_draft_closure_reports_invalid_role_property_at_direct_pointer(tmp_path: Path):
    paths = _paths(ROOT)
    theme = yaml.safe_load(paths["theme_path"].read_bytes())
    _add_invalid_property(theme)
    invalid_path = tmp_path / "invalid-theme.yaml"
    _write_yaml(invalid_path, theme)

    with pytest.raises(ClosureError) as error:
        resolve_draft_render(**(paths | {"theme_path": invalid_path}))

    assert error.value.diagnostic_id == "E_THEME_ROLE_PROPERTY_UNSUPPORTED"
    assert error.value.source_ref == "/body/roles/variance-behind/strokeWidth"


def test_immutable_closure_reports_invalid_scheme_target_at_exact_pointer(tmp_path: Path):
    example = tmp_path / "controller-z"
    shutil.copytree(ROOT / "examples/controller-z", example)
    theme_path = example / "themes/executive-light.yaml"
    theme = yaml.safe_load(theme_path.read_bytes())
    theme["body"]["colorBindings"]["variance-behind.stroke"] = "negative"
    theme_bytes = _write_yaml(theme_path, theme)

    context_path = example / "contexts/executive.yaml"
    context = yaml.safe_load(context_path.read_bytes())
    context["body"]["theme"]["contentIdentity"] = "sha256:" + sha256(theme_bytes).hexdigest()
    _write_yaml(context_path, context)

    snapshot = tmp_path / "snapshot"
    reference, _ = copy_context_closure(example, context_path, snapshot)
    with pytest.raises(ClosureError) as error:
        resolve_render_context(reference, LocalSnapshotReader(snapshot, "controller-z-example"))

    assert error.value.diagnostic_id == "E_THEME_ROLE_PROPERTY_UNSUPPORTED"
    assert error.value.source_ref == "/body/colorBindings/variance-behind.stroke"


def test_draft_closure_checks_inherited_effective_theme_role(tmp_path: Path):
    paths = _paths(ROOT)
    base = yaml.safe_load(paths["theme_path"].read_bytes())
    _add_invalid_property(base)
    base_path = tmp_path / "base-theme.yaml"
    base_bytes = _write_yaml(base_path, base)
    derived = {
        "version": "chrona/theme/v0.12",
        "kind": "theme",
        "id": base["id"],
        "body": {
            "extends": {
                "id": base["id"],
                "path": base_path.name,
                "sourceContentIdentity": "sha256:" + sha256(base_bytes).hexdigest(),
                "contentIdentity": content_identity(base),
            },
        },
    }
    derived_path = tmp_path / "derived-theme.yaml"
    _write_yaml(derived_path, derived)

    with pytest.raises(ClosureError) as error:
        resolve_draft_render(**(paths | {"theme_path": derived_path}))

    assert error.value.diagnostic_id == "E_THEME_ROLE_PROPERTY_UNSUPPORTED"
    assert error.value.source_ref == "/body/roles/variance-behind/strokeWidth"
