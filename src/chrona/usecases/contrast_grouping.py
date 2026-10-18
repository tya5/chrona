"""Stable grouping for repeated realised encoded-fill contrast warnings."""
from __future__ import annotations

from collections.abc import Sequence

from chrona.presentation.scene.contrast_policy import SceneContrastFinding


def group_contrast_findings(
    findings: Sequence[SceneContrastFinding],
) -> tuple[tuple[SceneContrastFinding, ...], ...]:
    """Group only equivalent computed encoded-fill warnings; preserve input order.

    Every other finding is an independent observation. In particular, policy
    errors, accepted exceptions, unknown grounds and informational findings
    never collapse into a warning group.
    """
    groups: list[list[SceneContrastFinding]] = []
    indices: dict[tuple[object, ...], int] = {}
    for finding in findings:
        if (finding.code == "W_SCENE_ENCODING_CONTRAST"
                and finding.severity == "warning"
                and finding.encoding is not None
                and finding.encoding_pair is not None):
            key = (finding.scene_path, finding.encoding, finding.encoding_pair)
            index = indices.get(key)
            if index is not None:
                groups[index].append(finding)
                continue
            indices[key] = len(groups)
        groups.append([finding])
    return tuple(tuple(group) for group in groups)
