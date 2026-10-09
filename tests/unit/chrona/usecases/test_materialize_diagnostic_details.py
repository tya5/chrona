"""Owner-local diagnostic operands for immutable example materialization."""
from hashlib import sha256
import pytest
import yaml

from chrona.core.ports import SnapshotReadError
from chrona.usecases import materialize as m


def identity(data: bytes) -> str:
    return "sha256:" + sha256(data).hexdigest()


def ref(*, kind="view", id="view-main", address="views/main.yaml", provider="local",
        store_identity="example", token="rev-1", content=None):
    result = {"id": id, "kind": kind, "store": {"provider": provider, "identity": store_identity},
              "address": address, "revision": {"token": token}}
    if content is not None:
        result["contentIdentity"] = content
    return result


def assert_detail(error, code, *needles):
    actual_code = getattr(error, "diagnostic_id", getattr(error, "code", str(error).partition(":")[0]))
    detail = getattr(error, "detail", "") or str(error)
    assert actual_code == code
    for needle in needles:
        assert needle in detail


def test_overlay_reference_identity_and_lookup_details(tmp_path):
    builder = m._OverlayBuilder(tmp_path)
    item = ref(content=identity(b"expected"))
    with pytest.raises(ValueError) as mismatch:
        builder.add_reference(item, b"actual")
    assert_detail(mismatch.value, "E_CONTENT_IDENTITY", "view-main", "views/main.yaml", identity(b"expected"), identity(b"actual"))

    with pytest.raises(SnapshotReadError) as missing:
        builder.finish().read(item)
    assert_detail(missing.value, "E_STORE_REFERENCE", "view-main", "views/main.yaml")

    builder.add_reference(item, b"expected")
    missing_path = builder.references[m._reference_key(item)][0]
    missing_path.unlink()
    with pytest.raises(SnapshotReadError) as missing_file:
        builder.finish().read(item)
    assert_detail(missing_file.value, "E_STORE_REFERENCE", "view-main", "views/main.yaml", "missing")

    builder.add_reference(item, b"expected")
    overlay = builder.finish()
    path = overlay._references[m._reference_key(item)][0]
    path.write_bytes(b"tampered")
    with pytest.raises(SnapshotReadError) as changed:
        overlay.read(item)
    assert_detail(changed.value, "E_CONTENT_IDENTITY", "view-main", "views/main.yaml", identity(b"expected"), identity(b"tampered"))


def test_overlay_asset_identity_missing_and_collision_details(tmp_path):
    builder = m._OverlayBuilder(tmp_path)
    locator = {"provider": "context", "identity": "ctx-1", "address": "fonts/metrics.json"}
    with pytest.raises(ValueError) as mismatch:
        builder.add_asset(locator, identity(b"wanted"), b"wrong")
    assert_detail(mismatch.value, "E_MATERIALIZER_FONT_IDENTITY", "ctx-1", "fonts/metrics.json", identity(b"wanted"), identity(b"wrong"))

    builder.add_asset(locator, None, b"first")
    with pytest.raises(ValueError) as collision:
        builder.add_asset(locator, None, b"second")
    assert_detail(collision.value, "E_MATERIALIZER_OVERLAY_COLLISION", "staging key sha256:", identity(b"first"), identity(b"second"))

    with pytest.raises(KeyError):
        builder.finish().resolve_asset({**locator, "identity": "other-context"}, None)


def test_staged_path_and_preexisting_overlay_collisions_identify_resource(tmp_path):
    builder = m._OverlayBuilder(tmp_path)
    item = ref(content=identity(b"first"))
    other = tmp_path / "unrelated"
    other.write_bytes(b"different")
    with pytest.raises(ValueError) as staged:
        builder.add_reference(item, b"first", staged_path=other)
    assert_detail(staged.value, "E_MATERIALIZER_OVERLAY_COLLISION", "view-main", "views/main.yaml", identity(b"first"))

    builder.add_reference(ref(content=None), b"first")
    with pytest.raises(ValueError) as duplicate:
        builder.add_reference(ref(content=None), b"second")
    assert_detail(duplicate.value, "E_MATERIALIZER_OVERLAY_COLLISION", "staging key sha256:", identity(b"first"), identity(b"second"))

    key = "forced-stage-key"
    builder._stage(key, b"first")
    with pytest.raises(ValueError) as staged_collision:
        builder._stage(key, b"second")
    assert_detail(staged_collision.value, "E_MATERIALIZER_OVERLAY_COLLISION", "staging key sha256:", identity(b"first"), identity(b"second"))


def test_reference_provider_package_identity_and_address_details(tmp_path, monkeypatch):
    with pytest.raises(ValueError) as bad_path:
        m._inside(tmp_path, "../escape")
    assert_detail(bad_path.value, "E_MATERIALIZER_PATH", "../escape")

    with pytest.raises(ValueError) as provider:
        m._reference_payload(tmp_path, ref(provider="remote", store_identity="foreign"))
    assert_detail(provider.value, "E_MATERIALIZER_PROVIDER", "view-main", "views/main.yaml", "remote")

    wrong_store = ref(provider="package", store_identity="other.package")
    with pytest.raises(ValueError) as package_store:
        m._reference_payload(tmp_path, wrong_store)
    assert_detail(package_store.value, "E_MATERIALIZER_PACKAGE_RESOURCE", "views/main.yaml", "other.package")

    real_package_resource = m._package_resource
    package = ref(provider="package", store_identity="chrona.resources", content=identity(b"declared"))
    monkeypatch.setattr(m, "_package_resource", lambda _: _BytesResource(b"actual"))
    with pytest.raises(ValueError) as package_identity:
        m._reference_payload(tmp_path, package)
    assert_detail(package_identity.value, "E_MATERIALIZER_PACKAGE_IDENTITY", "view-main", "views/main.yaml", identity(b"declared"), identity(b"actual"))

    monkeypatch.setattr(m, "_package_resource", real_package_resource)
    monkeypatch.setattr(m, "files", lambda _package: tmp_path)
    with pytest.raises(ValueError) as absent:
        m._package_resource("absent.yaml")
    assert_detail(absent.value, "E_MATERIALIZER_PACKAGE_RESOURCE", "absent.yaml")


class _BytesResource:
    def __init__(self, data):
        self.data = data

    def read_bytes(self):
        return self.data


def test_package_lookup_and_theme_source_identity_keep_context(tmp_path, monkeypatch):
    with pytest.raises(ValueError) as missing:
        m._package_resource("not/a/real/resource")
    assert_detail(missing.value, "E_MATERIALIZER_PACKAGE_RESOURCE", "not/a/real/resource")

    base = ref(kind="theme", id="base-theme", address="themes/base.yaml", content=identity(b"base"))
    derived_payload = b"kind: theme\nbody:\n  inheritance:\n    base: true\n"
    derived = ref(kind="theme", id="derived-theme", address="themes/derived.yaml", content=identity(derived_payload))
    derived_path = tmp_path / "themes/derived.yaml"
    derived_path.parent.mkdir(parents=True)
    derived_path.write_bytes(derived_payload)
    (tmp_path / "themes/base.yaml").write_bytes(b"changed base")
    # A local theme inheritance lookup reads the declared base through the same copier.
    monkeypatch.setattr(m, "theme_base_reference", lambda *_: base)
    monkeypatch.setattr(m, "is_derived_theme", lambda _: True)
    with pytest.raises(ValueError) as source:
        m._copy_reference(tmp_path, derived, tmp_path / "snapshot")
    assert_detail(source.value, "E_THEME_INHERITANCE_SOURCE_IDENTITY", "derived-theme", "themes/derived.yaml", "base-theme", "themes/base.yaml")


@pytest.mark.parametrize("theme_stack,base_exists,expected_code", [
    (("themes/derived.yaml",), True, "E_THEME_INHERITANCE_CYCLE"),
    ((), False, "E_THEME_INHERITANCE_BASE_MISSING"),
])
def test_theme_cycle_and_missing_base_name_owner(tmp_path, monkeypatch, theme_stack, base_exists, expected_code):
    derived_payload = b"version: chrona/theme/v0.16\nbody: {}\n"
    derived = ref(kind="theme", id="derived-theme", address="themes/derived.yaml", content=identity(derived_payload))
    source = tmp_path / "themes/derived.yaml"
    source.parent.mkdir(parents=True)
    source.write_bytes(derived_payload)
    base = ref(kind="theme", id="base-theme", address="themes/base.yaml", content=identity(b"base"))
    if base_exists:
        (tmp_path / "themes/base.yaml").write_bytes(b"base")
    monkeypatch.setattr(m, "is_derived_theme", lambda _: True)
    monkeypatch.setattr(m, "theme_base_reference", lambda *_: base)
    with pytest.raises(ValueError) as error:
        m._copy_reference(tmp_path, derived, tmp_path / "snapshot", theme_stack=theme_stack)
    assert_detail(error.value, expected_code, "derived-theme", "themes/derived.yaml")


def test_icon_catalog_schema_and_asset_path_identity_details(tmp_path, monkeypatch):
    catalog_ref = ref(kind="icon-catalog", id="icons-main", address="icons/catalog.yaml")
    with pytest.raises(ValueError) as shape:
        m._copy_icon_assets(tmp_path, catalog_ref, tmp_path / "snapshot", b"body: {}\n")
    assert_detail(shape.value, "E_ICON_CATALOG_SCHEMA", "icons-main", "icons/catalog.yaml")

    catalog = {"body": {"icons": {"pin": {"kind": "raster", "source": {"address": "../pin.png", "contentIdentity": identity(b"pin")}}}}}
    with pytest.raises(ValueError) as path:
        m._copy_icon_assets(tmp_path, catalog_ref, tmp_path / "snapshot", yaml.safe_dump(catalog).encode())
    assert_detail(path.value, "E_ICON_ASSET_PATH", "pin", "../pin.png")

    catalog["body"]["icons"]["pin"]["source"]["address"] = "pin.png"
    (tmp_path / "pin.png").write_bytes(b"different")
    with pytest.raises(ValueError) as identity_error:
        m._copy_icon_assets(tmp_path, catalog_ref, tmp_path / "snapshot", yaml.safe_dump(catalog).encode())
    assert_detail(identity_error.value, "E_ICON_ASSET_IDENTITY", "pin", "pin.png", identity(b"pin"), identity(b"different"))

    source = tmp_path / "real.png"
    source.write_bytes(b"different")
    (tmp_path / "pin.png").unlink()
    (tmp_path / "pin.png").symlink_to(source)
    monkeypatch.setattr(m, "_inside", lambda root, address: root / address)
    with pytest.raises(ValueError) as symlink:
        m._copy_icon_assets(tmp_path, catalog_ref, tmp_path / "snapshot", yaml.safe_dump(catalog).encode())
    assert_detail(symlink.value, "E_ICON_ASSET_PATH", "pin", "pin.png", "symlink")


def _minimal_context(path, *, target="svg", font_asset=None):
    references = {name: ref(kind=name, id=f"{name}-1", address=f"{name}/one.yaml")
                  for name in ("project", "view", "theme", "colorScheme", "layout")}
    references["project"]["revision"]["token"] = "project-rev"
    body = {**references, "inputs": {}, "environment": {"fontMetrics": {"assets": [font_asset or {"id": "metrics-1", "metrics": {"locator": {"provider": "context", "address": "font.json"}, "contentIdentity": identity(b"font")}}]}},
            "target": {"kind": target}}
    document = {"id": "context-1", "kind": "render-context", "version": "chrona/render-context/v0.17", "body": body}
    path.write_text(yaml.safe_dump(document), encoding="utf-8")
    return document


@pytest.mark.parametrize("asset, resolver, code, detail", [
    ({"id": "metrics-7", "metrics": {"path": "missing"}}, None, "E_MATERIALIZER_FONT", ("metrics-7", "metrics")),
    ({"id": "metrics-7", "metrics": {"locator": {"provider": "bad", "address": "m.json"}}}, "raise", "E_MATERIALIZER_FONT", ("metrics-7", "m.json")),
    ({"id": "metrics-7", "metrics": {"locator": {"provider": "context", "address": "m.json"}, "contentIdentity": identity(b"expected")}}, "wrong-bytes", "E_MATERIALIZER_FONT_IDENTITY", ("metrics-7", "metrics", "m.json", identity(b"expected"), identity(b"font"))),
    ({"id": "metrics-7", "metrics": {"locator": {"provider": "context"}, "contentIdentity": identity(b"font")}}, "font-bytes", "E_MATERIALIZER_FONT", ("metrics-7", "metrics", "None")),
])
def test_context_font_failures_name_asset_and_field(tmp_path, monkeypatch, asset, resolver, code, detail):
    context_path = tmp_path / "context.yaml"
    _minimal_context(context_path, font_asset=asset)
    monkeypatch.setattr(m, "_copy_reference", lambda *_args, **_kwargs: b"resource")
    monkeypatch.setattr(m, "_copy_extension_packages", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(m, "snapshot_directory", lambda *_args: tmp_path / "destination")
    font_path = tmp_path / "font.bin"
    font_path.write_bytes(b"font")
    if resolver == "raise":
        def resolve(*_args, **_kwargs):
            raise m.FontResourceError("E_FONT_RESOURCE", "missing m.json")
    elif resolver == "wrong-bytes":
        font_path.write_bytes(b"font")
        resolve = lambda *_args, **_kwargs: font_path
    elif resolver == "font-bytes":
        resolve = lambda *_args, **_kwargs: font_path
    else:
        resolve = m.resolve_font_resource
    monkeypatch.setattr(m, "resolve_font_resource", resolve)
    with pytest.raises(ValueError) as error:
        m.copy_context_closure(tmp_path, context_path, tmp_path / "snapshot")
    assert_detail(error.value, code, *detail)


def test_manifest_slide_and_nonempty_output_diagnostics_name_requested_values(tmp_path):
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text("version: wrong\nrole: wrong\nslides: []\ncontext: context.yaml\n", encoding="utf-8")
    with pytest.raises(ValueError) as bad_manifest:
        m.materialize(manifest, "slide-x", tmp_path / "out")
    assert_detail(bad_manifest.value, "E_MATERIALIZER_MANIFEST", "manifest.yaml", "wrong")

    manifest.write_text("version: chrona/example-materializer/v0.1\nrole: regression-corpus\nslides: []\ncontext: context.yaml\n", encoding="utf-8")
    with pytest.raises(ValueError) as missing_slide:
        m.materialize(manifest, "slide-x", tmp_path / "out")
    assert_detail(missing_slide.value, "E_MATERIALIZER_SLIDE", "slide-x")

    manifest.write_text("version: chrona/example-materializer/v0.1\nrole: regression-corpus\ncontext: context.yaml\nslides:\n- id: slide-x\n  evidence: evidence\n  expectedSvg: expected.svg\n", encoding="utf-8")
    output = tmp_path / "nonempty"
    output.mkdir()
    (output / "existing").write_text("keep")
    with pytest.raises(ValueError) as occupied:
        m.materialize(manifest, "slide-x", output)
    assert_detail(occupied.value, "E_MATERIALIZER_OUTPUT", "nonempty")


def test_context_shape_detail_reports_keys_not_payload_repr():
    error = m._context_error("context inputs", "reference object", {"id": "x", "private": "DO-NOT-ECHO"})
    assert_detail(error, "E_MATERIALIZER_CONTEXT", "context inputs", "reference object", "id", "private")
    assert "DO-NOT-ECHO" not in error.detail
