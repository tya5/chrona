"""M13 immutable successor-capability release acceptance boundary."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any


EXPECTED_UCS = frozenset({"UC-16", "UC-17", "UC-18", "UC-19", "UC-20", "UC-21"})
EXPECTED_CLOSURE = {"datetime": "v0.2", "capacity": "v0.2", "collaboration": "v0.2", "extensions": "v0.2", "output": "v0.2"}
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _identity(value: Any) -> str:
    return "sha256:" + sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def validate_successor_acceptance(manifest: dict[str, Any], evidence_root: Path = REPOSITORY_ROOT) -> tuple[str, ...]:
    """Return stable diagnostics; a malformed closure can never be published."""
    diagnostics: list[str] = []
    if manifest.get("version") != "chrona/successor-release-acceptance/v0.3" or not manifest.get("releaseId"):
        diagnostics.append("E_SUCCESSOR_VERSION")
    if manifest.get("closure") != EXPECTED_CLOSURE:
        diagnostics.append("E_SUCCESSOR_CLOSURE")
    rows = manifest.get("useCases")
    if not isinstance(rows, list) or len(rows) != len(EXPECTED_UCS) or {row.get("id") for row in rows if isinstance(row, dict)} != EXPECTED_UCS:
        diagnostics.append("E_SUCCESSOR_USE_CASES")
        return tuple(diagnostics)
    for row in rows:
        evidence = row.get("evidence")
        if row.get("disposition") != "accepted" or not isinstance(evidence, list) or not evidence:
            diagnostics.append("E_SUCCESSOR_ACCEPTANCE")
            continue
        for path in evidence:
            if not isinstance(path, str):
                diagnostics.append("E_SUCCESSOR_EVIDENCE")
                break
            candidate = (evidence_root / path).resolve()
            if evidence_root not in candidate.parents or not candidate.is_file():
                diagnostics.append("E_SUCCESSOR_EVIDENCE")
                break
    return tuple(dict.fromkeys(diagnostics))


@dataclass(frozen=True)
class SuccessorReleaseResult:
    package: dict[str, Any]
    diagnostics: tuple[str, ...]


def create_successor_release(manifest: dict[str, Any], evidence_root: Path = REPOSITORY_ROOT) -> SuccessorReleaseResult:
    """Create a declared M13 release only when the full evidence closure passes."""
    diagnostics = validate_successor_acceptance(manifest, evidence_root)
    package = {"version": "chrona/successor-release/v0.3", "releaseId": manifest.get("releaseId", ""),
               "closure": manifest.get("closure"), "acceptance": {"manifestIdentity": _identity(manifest)}}
    if diagnostics:
        return SuccessorReleaseResult(package | {"status": "blocked", "diagnostics": list(diagnostics)}, diagnostics)
    return SuccessorReleaseResult(package | {"status": "published", "diagnostics": []}, ())
