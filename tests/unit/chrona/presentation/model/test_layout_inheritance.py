"""Layout chain identity includes the pinned revision, not just its address."""
from hashlib import sha256
from copy import deepcopy

import yaml

from chrona.presentation.model.layout_inheritance import resolve_snapshot_layout
from chrona.presentation.layout.profile import compose_layout_profile
from chrona.resources import builtin_preset_source_root, safe_load
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.storage.snapshot_paths import snapshot_directory


def test_same_layout_address_at_distinct_revisions_is_not_a_cycle(tmp_path):
    base = safe_load(builtin_preset_source_root("presets/bundles/mission-light").joinpath("layout.yaml").read_bytes())
    address = "layouts/shared.yaml"

    def store(token, value):
        payload = yaml.safe_dump(value, sort_keys=False).encode()
        path = snapshot_directory(tmp_path, token) / address
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return {"id": value["id"], "kind": "layout-profile",
                "store": {"provider": "local", "identity": "shared-design"},
                "address": address, "revision": {"token": token},
                "contentIdentity": "sha256:" + sha256(payload).hexdigest()}

    def derived(reference, overrides):
        return {**{name: base[name] for name in
                   ("version", "id", "flowDirection", "dependencyNetworkFlowDirection",
                    "requiredThemeTokens", "reviewSurface")},
                "extends": reference, "overrides": overrides}

    old = store("r1", base)
    middle = derived(old, {"page": {"padding": {"token": "spacing.l"}}})
    current = derived(store("r2", middle), {"page": {"gap": {"token": "spacing.m"}}})

    resolved = resolve_snapshot_layout(current, LocalSnapshotReader(tmp_path, "shared-design"))

    assert "extends" not in resolved
    assert resolved["root"]["padding"] == {"token": "spacing.l"}
    assert resolved["root"]["gap"] == {"token": "spacing.m"}


def test_completed_base_composition_keeps_input_declarations_immutable():
    base = safe_load(builtin_preset_source_root("presets/bundles/mission-light").joinpath("layout.yaml").read_bytes())
    derived = {**{name: base[name] for name in
                  ("version", "id", "flowDirection", "dependencyNetworkFlowDirection",
                   "requiredThemeTokens", "reviewSurface")},
               "extends": {"id": base["id"], "kind": "layout-profile",
                           "store": {"provider": "local", "identity": "design"},
                           "address": "layouts/shared.yaml", "revision": {"token": "r1"},
                           "contentIdentity": "sha256:" + "a" * 64},
               "overrides": {"page": {"padding": {"token": "spacing.l"}}},
               "relationRouting": {**base["relationRouting"], "maxBends": 2}}
    before_base, before_derived = deepcopy(base), deepcopy(derived)

    resolved = compose_layout_profile(derived, base)

    assert resolved["root"]["padding"] == {"token": "spacing.l"}
    assert resolved["relationRouting"] == derived["relationRouting"]
    resolved["root"]["padding"]["token"] = "changed"
    resolved["relationRouting"]["maxBends"] = 5
    assert base == before_base and derived == before_derived
