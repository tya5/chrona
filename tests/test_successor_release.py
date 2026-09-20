from copy import deepcopy
from pathlib import Path

import yaml

from chrona.successor_release import create_successor_release, validate_successor_acceptance


ROOT = Path(__file__).resolve().parents[1]


def _manifest():
    return yaml.safe_load((ROOT / "conformance/successor-release-acceptance-v0.3.yaml").read_text())


def test_successor_release_publishes_only_complete_fixed_evidence_closure():
    manifest = _manifest()
    result = create_successor_release(manifest)
    assert result.package["status"] == "published"
    assert result.package["acceptance"]["manifestIdentity"].startswith("sha256:")


def test_successor_release_blocks_missing_or_duplicate_use_cases_and_evidence():
    manifest = _manifest()
    manifest["useCases"][-1]["id"] = "UC-20"
    assert validate_successor_acceptance(manifest) == ("E_SUCCESSOR_USE_CASES",)
    manifest = _manifest()
    manifest["useCases"][0]["evidence"] = ["does-not-exist"]
    assert create_successor_release(manifest).diagnostics == ("E_SUCCESSOR_EVIDENCE",)
    manifest = _manifest()
    manifest["useCases"][0]["evidence"] = [None]
    assert create_successor_release(manifest).diagnostics == ("E_SUCCESSOR_EVIDENCE",)


def test_successor_release_blocks_exclusion_and_changed_closure():
    manifest = deepcopy(_manifest())
    manifest["useCases"][0]["disposition"] = "excluded"
    manifest["closure"]["output"] = "v0.1"
    result = create_successor_release(manifest)
    assert result.package["status"] == "blocked"
    assert result.diagnostics == ("E_SUCCESSOR_CLOSURE", "E_SUCCESSOR_ACCEPTANCE")
