"""A Render Context references a shared design Store on every render path, without copying it (#1342).

The fixtures rewrite one HALCYON Context so its Theme, Color Scheme and Layout live in a second, read-only Store, then check
that `materialize` (manifest `stores`) and `render-review` (Store config) draw the same slide as the single-Store original,
that editing the shared design changes the slide with no Context edit, and that a derived Layout resolves its base from
another Store or from the packaged store.
"""
from __future__ import annotations

import shutil
from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from chrona.core.ports import SnapshotReadError
from chrona.operational.store_config import load_store_config
from chrona.operational.store_reads import load_reference, snapshot_reader_for
from chrona.presentation.model.closure import ClosureError
from chrona.resources import safe_load
from chrona.storage.snapshot_paths import snapshot_directory
from chrona.usecases.context_review import render_context_closure, resolve_context_closure
from chrona.usecases.local_authoring import initialize_project
from chrona.usecases.materialize import materialize

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "examples" / "halcyon-1"
CONTEXT = "contexts/01-mission-brief.yaml"
DESIGN = "shared-design"
SHARED = ("theme", "colorScheme", "layout")


def _dump(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.fixture()
def example(tmp_path: Path) -> Path:
    """One HALCYON slide: its Context, Project, View, resources and expected evidence, with a one-slide manifest."""
    target = tmp_path / "halcyon-1"
    shutil.copytree(SOURCE, target, ignore=shutil.ignore_patterns("generated", "contexts", "snapshots"))
    (target / "contexts").mkdir()
    (target / "generated").mkdir()
    shutil.copy2(SOURCE / CONTEXT, target / CONTEXT)
    for name in ("01-mission-brief.svg", "01-mission-brief.scene.json"):
        shutil.copy2(SOURCE / "generated" / name, target / "generated" / name)
    manifest = _load(SOURCE / "manifest.yaml")
    manifest["slides"] = [item for item in manifest["slides"] if item["id"] == "mission-brief"]
    _dump(target / "manifest.yaml", manifest)
    return target


def _tint(scheme: Path) -> None:
    """Edit the shared Color Scheme's surface colour."""
    value = safe_load(scheme.read_bytes())
    value["body"]["colors"]["surface"] = "#F6F3EA"
    _dump(scheme, value)


def _share(example: Path, designs: Path) -> dict:
    """Copy the Context's Theme, Scheme and Layout into ``designs`` and point the Context at that Store."""
    context = _load(example / CONTEXT)
    for name in SHARED:
        reference = context["body"][name]
        target = designs / reference["address"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(example / reference["address"], target)
        reference["store"] = {"provider": "local", "identity": DESIGN}
    _dump(example / CONTEXT, context)
    manifest = _load(example / "manifest.yaml")
    manifest["stores"] = [{"identity": DESIGN, "root": "../designs"}]
    _dump(example / "manifest.yaml", manifest)
    return context


def test_materialize_draws_the_same_slide_from_a_shared_design_store(example: Path, tmp_path: Path) -> None:
    own = materialize(example / "manifest.yaml", "mission-brief", tmp_path / "own", write=False)

    _share(example, tmp_path / "designs")
    # the Scene's provenance names each resource's Store, so only the Scene evidence is re-recorded (write=True); the SVG,
    # compared with the declared evidence first, is the same bytes
    shared = materialize(example / "manifest.yaml", "mission-brief", tmp_path / "shared", write=True)

    assert shared.rendered.artifact.content == own.rendered.artifact.content == (example / "generated/01-mission-brief.svg").read_bytes()


def test_editing_the_shared_scheme_changes_the_slide_and_no_context(example: Path, tmp_path: Path) -> None:
    designs = tmp_path / "designs"
    context = _share(example, designs)
    before = (example / CONTEXT).read_bytes()
    first = materialize(example / "manifest.yaml", "mission-brief", tmp_path / "first", write=True)

    _tint(designs / context["body"]["colorScheme"]["address"])

    with pytest.raises(Exception, match="E_MATERIALIZER_MISMATCH"):  # the declared evidence is now stale: the design edit reached it
        materialize(example / "manifest.yaml", "mission-brief", tmp_path / "second", write=False)
    second = materialize(example / "manifest.yaml", "mission-brief", tmp_path / "third", write=True)
    assert (example / CONTEXT).read_bytes() == before  # no Context edit and no re-pin
    assert second.rendered.artifact.content != first.rendered.artifact.content


def test_a_shared_store_the_manifest_does_not_declare_is_refused(example: Path, tmp_path: Path) -> None:
    _share(example, tmp_path / "designs")
    manifest = _load(example / "manifest.yaml")
    del manifest["stores"]
    _dump(example / "manifest.yaml", manifest)
    shutil.rmtree(example / "themes")

    with pytest.raises(Exception):  # noqa: B017 - the Theme is nowhere in the example, and the shared Store is not declared
        materialize(example / "manifest.yaml", "mission-brief", tmp_path / "out", write=False)


def _workspace(tmp_path: Path) -> tuple[Path, dict]:
    """A HALCYON project with its Store config, a `shared-design` Store holding the Theme, Scheme and Layout, and the Context."""
    project = initialize_project(tmp_path / "project", example="halcyon-1").directory
    context = _load(project / CONTEXT)
    store_root = project / ".chrona" / "store"
    designs = tmp_path / "design-store"
    token = context["body"]["theme"]["revision"]["token"]
    for name in SHARED:
        reference = context["body"][name]
        reference["store"] = {"provider": "local", "identity": DESIGN}
        target = designs / f"revision-{token}" / reference["address"]
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(store_root / f"revision-{token}" / reference["address"], target)
    config = _load(project / ".chrona" / "store.yaml")
    config["stores"].append({"provider": "local", "identity": DESIGN, "root": str(designs), "integrity": "optional"})
    _dump(project / ".chrona" / "store.yaml", config)
    _dump(project / CONTEXT, context)
    return project, designs


def _context_token(project: Path) -> str:
    return str(_load(project / CONTEXT)["body"]["project"]["revision"]["token"])


def _staged_context(project: Path) -> Path:
    return snapshot_directory(project / ".chrona" / "store", _context_token(project)) / CONTEXT


def _reference(project: Path) -> dict:
    document = _load(project / CONTEXT)
    path = project / "context-reference.yaml"
    _dump(path, {"id": document["id"], "kind": "render-context", "store": {"provider": "local", "identity": "halcyon-1-example"},
                 "address": CONTEXT, "revision": {"token": _context_token(project)}})
    return load_reference(path)


def test_render_review_reads_the_shared_store_the_config_declares(tmp_path: Path) -> None:
    project, designs = _workspace(tmp_path)
    # the Context itself lives in the example Store: stage the edited copy there beside the original closure
    staged = _staged_context(project)
    shutil.copy2(project / CONTEXT, staged)
    reference = _reference(project)
    config = load_store_config(str(project / ".chrona" / "store.yaml"))
    reader, root = snapshot_reader_for(config, reference)

    closure = resolve_context_closure(reference, reader)
    drawn = render_context_closure(closure, root).artifact.content

    expected = (SOURCE / "generated" / "01-mission-brief.svg").read_bytes()
    assert drawn == expected

    _tint(designs / "revision-example-v1" / closure.context.color_scheme.address)
    edited = render_context_closure(resolve_context_closure(reference, reader), root).artifact.content
    assert edited != drawn  # the shared design edit reached the slide; the Context file was not touched


def test_a_store_the_config_does_not_declare_is_a_typed_failure(tmp_path: Path) -> None:
    project, _ = _workspace(tmp_path)
    shutil.copy2(project / CONTEXT, _staged_context(project))
    config = _load(project / ".chrona" / "store.yaml")
    config["stores"] = config["stores"][:1]
    _dump(project / ".chrona" / "store.yaml", config)
    reference = _reference(project)
    reader, _ = snapshot_reader_for(load_store_config(str(project / ".chrona" / "store.yaml")), reference)

    with pytest.raises((SnapshotReadError, ClosureError)) as raised:
        resolve_context_closure(reference, reader)
    assert "E_STORE_CONFIG_REQUIRED" in str(raised.value) + getattr(raised.value, "code", "")


def _identity(payload: bytes) -> str:
    return "sha256:" + sha256(payload).hexdigest()


def _derive(project: Path, designs: Path, *, base: dict, overrides: dict) -> dict:
    """A derived Layout in the shared design Store extending ``base``; the Context is pointed at it."""
    context = _load(project / CONTEXT)
    derived = {"version": "chrona/layout-profile/v0.10", "id": "briefing-roomy", "extends": base, "overrides": overrides}
    source = _load(project / ".chrona" / "store" / "revision-example-v1" / "layouts" / "briefing.yaml")
    for key in ("flowDirection", "dependencyNetworkFlowDirection", "requiredThemeTokens", "reviewSurface"):
        derived[key] = source[key]
    _dump(designs / "revision-example-v1" / "layouts" / "briefing-roomy.yaml", derived)
    context["body"]["layout"] = {"id": "briefing-roomy", "kind": "layout-profile", "store": {"provider": "local", "identity": DESIGN},
                                 "address": "layouts/briefing-roomy.yaml", "revision": {"token": "example-v1"}}
    _dump(project / CONTEXT, context)
    shutil.copy2(project / CONTEXT, _staged_context(project))
    return derived


def _local_base(project: Path) -> dict:
    payload = (project / ".chrona" / "store" / "revision-example-v1" / "layouts" / "briefing.yaml").read_bytes()
    return {"id": "briefing", "kind": "layout-profile", "store": {"provider": "local", "identity": "halcyon-1-example"},
            "address": "layouts/briefing.yaml", "revision": {"token": "example-v1"}, "contentIdentity": _identity(payload)}


def test_a_derived_layout_in_the_shared_store_extends_a_base_in_another_store(tmp_path: Path) -> None:
    project, designs = _workspace(tmp_path)
    _derive(project, designs, base=_local_base(project), overrides={"page": {"padding": {"token": "spacing.m"}}})
    reference = _reference(project)
    reader, root = snapshot_reader_for(load_store_config(str(project / ".chrona" / "store.yaml")), reference)

    closure = resolve_context_closure(reference, reader)
    layout = closure.layout_profile.layout_input

    assert "extends" not in layout and layout["id"] == "briefing-roomy"
    assert layout["root"]["padding"] == {"token": "spacing.m"} and layout["root"]["gap"] == {"token": "spacing.m"}
    base = (SOURCE / "generated" / "01-mission-brief.svg").read_bytes()
    assert render_context_closure(closure, root).artifact.content != base  # the override reached the slide


def test_editing_the_base_layout_moves_the_derived_profile_but_not_the_context(tmp_path: Path) -> None:
    project, designs = _workspace(tmp_path)
    _derive(project, designs, base=_local_base(project), overrides={"page": {"padding": {"token": "spacing.m"}}})
    reference = _reference(project)
    config = load_store_config(str(project / ".chrona" / "store.yaml"))
    first = resolve_context_closure(reference, snapshot_reader_for(config, reference)[0]).resource("layout-profile").content_identity

    stored = project / ".chrona" / "store" / "revision-example-v1" / "layouts" / "briefing.yaml"
    value = _load(stored)
    value["root"]["gap"] = {"token": "spacing.l"}
    _dump(stored, value)
    with pytest.raises(ClosureError) as stale:  # the extends pin names the old bytes: the edit is re-pinned inside the design
        resolve_context_closure(reference, snapshot_reader_for(config, reference)[0])
    assert stale.value.diagnostic_id == "E_CONTENT_IDENTITY"

    derived_path = designs / "revision-example-v1" / "layouts" / "briefing-roomy.yaml"
    derived = _load(derived_path)
    derived["extends"]["contentIdentity"] = _identity(stored.read_bytes())
    _dump(derived_path, derived)
    second = resolve_context_closure(reference, snapshot_reader_for(config, reference)[0]).resource("layout-profile").content_identity
    assert second != first


def test_shared_layout_inherits_thin_view_defaults_with_a_packaged_font_set(tmp_path: Path) -> None:
    """The reuse slices compose at real closure ingress, without changing drawn bytes."""
    project, designs = _workspace(tmp_path)
    reference = _reference(project)
    config = load_store_config(str(project / ".chrona" / "store.yaml"))
    shutil.copy2(project / CONTEXT, _staged_context(project))
    reader, root = snapshot_reader_for(config, reference)
    before = render_context_closure(resolve_context_closure(reference, reader), root).artifact.content

    context = _load(project / CONTEXT)
    view_reference = context["body"]["view"]
    view_path = snapshot_directory(project / ".chrona" / "store", view_reference["revision"]["token"]) / view_reference["address"]
    view = _load(view_path)
    axis = view["body"].pop("axis")
    _dump(view_path, view)
    view_reference["contentIdentity"] = _identity(view_path.read_bytes())
    _dump(project / CONTEXT, context)

    base_path = project / ".chrona" / "store" / "revision-example-v1" / "layouts" / "briefing.yaml"
    base = _load(base_path)
    base["viewDefaults"] = {"axis": axis}
    _dump(base_path, base)
    _derive(project, designs, base=_local_base(project), overrides={"page": {"padding": base["root"]["padding"]}})

    context = _load(project / CONTEXT)
    metrics = context["body"]["environment"]["fontMetrics"]
    assets = metrics.pop("assets")
    metrics["fontSet"] = "chrona.noto-sans+jp" if any(asset["family"] == "Noto Sans JP" for asset in assets) else "chrona.noto-sans"
    _dump(project / CONTEXT, context)
    shutil.copy2(project / CONTEXT, _staged_context(project))
    context_bytes = (project / CONTEXT).read_bytes()
    reader, root = snapshot_reader_for(config, reference)
    closure = resolve_context_closure(reference, reader)

    assert closure.layout_profile.layout_input["viewDefaults"]["axis"] == axis
    assert render_context_closure(closure, root).artifact.content == before
    assert (project / CONTEXT).read_bytes() == context_bytes


def test_a_derived_layout_that_extends_itself_is_refused(tmp_path: Path) -> None:
    project, designs = _workspace(tmp_path)
    cycle = {"id": "briefing-roomy", "kind": "layout-profile", "store": {"provider": "local", "identity": DESIGN},
             "address": "layouts/briefing-roomy.yaml", "revision": {"token": "example-v1"}, "contentIdentity": "sha256:" + "0" * 64}
    _derive(project, designs, base=cycle, overrides={"page": {"padding": 0}})
    reference = _reference(project)
    reader = snapshot_reader_for(load_store_config(str(project / ".chrona" / "store.yaml")), reference)[0]

    with pytest.raises(ClosureError) as raised:
        resolve_context_closure(reference, reader)
    assert raised.value.diagnostic_id in {"E_LAYOUT_BASE_CYCLE", "E_CONTENT_IDENTITY"}


def test_a_package_reference_reads_the_packaged_store_unpinned_and_verified() -> None:
    from chrona.storage.package_store import read_package_reference

    address = "presets/bundles/mission-light/layout.yaml"
    payload = (ROOT / "src/chrona/resources" / address).read_bytes()
    reference = {"id": "chrona-builtin-mission-light", "kind": "layout-profile",
                 "store": {"provider": "package", "identity": "chrona.resources"}, "address": address,
                 "revision": {"token": "bundled"}}

    assert read_package_reference(reference) == payload
    assert read_package_reference({**reference, "contentIdentity": _identity(payload)}) == payload
    for bad in ({**reference, "contentIdentity": "sha256:" + "0" * 64}, {**reference, "address": "presets/bundles/none.yaml"},
                {**reference, "address": "../pyproject.toml"}, {**reference, "store": {"provider": "package", "identity": "other"}}):
        with pytest.raises(SnapshotReadError):
            read_package_reference(bad)


def test_a_derived_layout_extends_a_packaged_layout(tmp_path: Path) -> None:
    project, designs = _workspace(tmp_path)
    address = "presets/bundles/mission-light/layout.yaml"
    payload = (ROOT / "src/chrona/resources" / address).read_bytes()
    base = {"id": "chrona-builtin-mission-light", "kind": "layout-profile",
            "store": {"provider": "package", "identity": "chrona.resources"}, "address": address,
            "revision": {"token": "bundled"}, "contentIdentity": _identity(payload)}
    _derive(project, designs, base=base, overrides={"page": {"padding": {"token": "spacing.m"}}})
    reference = _reference(project)
    reader = snapshot_reader_for(load_store_config(str(project / ".chrona" / "store.yaml")), reference)[0]

    layout = resolve_context_closure(reference, reader).layout_profile.layout_input

    assert layout["id"] == "briefing-roomy" and layout["root"]["padding"] == {"token": "spacing.m"}
    assert [child["id"] for child in layout["root"]["children"]][:2] == ["title", "review"]
