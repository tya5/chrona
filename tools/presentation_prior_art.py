"""Generate the reviewed presentation-capability prior-art matrix."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Mapping

from chrona.presentation.scene.capabilities import CapabilityDisposition, capability_ceiling


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "docs/research/presentation/presentation-capability-prior-art.md"


class Observation(StrEnum):
    """One deliberately narrow statement about a named primary source."""

    DOCUMENTED = "documented"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not-applicable"


@dataclass(frozen=True)
class ReferenceSource:
    identifier: str
    title: str
    url: str


@dataclass(frozen=True)
class SourceObservation:
    """A source fact, with a reason only when scope excludes a category."""

    value: Observation
    reason: str | None = None


SOURCES = (
    ReferenceSource("editorial-gantt", "Editorial Gantt", "https://github.com/cathrynlavery/diagram-design"),
    ReferenceSource("mermaid", "Mermaid Gantt", "https://mermaid.js.org/syntax/gantt.html"),
    ReferenceSource("microsoft-project", "Microsoft Project Gantt", "https://support.microsoft.com/en-us/project/format-the-bar-chart-of-a-gantt-chart-view"),
)


def _observations(**values: Observation | SourceObservation) -> Mapping[str, SourceObservation]:
    """Make an explicit complete row; omitted sources are reviewed unknown."""
    unknown = set(values) - {source.identifier for source in SOURCES}
    if unknown:
        raise ValueError(f"E_PRIOR_ART_SOURCE:{sorted(unknown)[0]}")
    return {
        source.identifier: value if isinstance(value := values.get(source.identifier, Observation.UNKNOWN), SourceObservation)
        else SourceObservation(value)
        for source in SOURCES
    }


# A row is required for every typed ceiling capability. ``documented`` means
# only that the named source explicitly documents this finite category; it
# never asserts semantic equivalence or portability.
OBSERVATIONS: Mapping[str, Mapping[str, SourceObservation]] = {
    "label.typography": _observations(**{"editorial-gantt": Observation.DOCUMENTED, "mermaid": Observation.DOCUMENTED}),
    "label.editorial-typography": _observations(**{"editorial-gantt": Observation.DOCUMENTED}),
    "mark.treatment": _observations(**{"editorial-gantt": Observation.DOCUMENTED, "mermaid": Observation.DOCUMENTED, "microsoft-project": Observation.DOCUMENTED}),
    "mark.role-geometry": _observations(**{"mermaid": Observation.DOCUMENTED, "microsoft-project": Observation.DOCUMENTED}),
    "mark.arbitrary-asset": _observations(),
    "line.treatment": _observations(**{"microsoft-project": Observation.DOCUMENTED}),
    "line.adapter-routing": _observations(),
    "decoration.treatment": _observations(**{"mermaid": Observation.DOCUMENTED, "microsoft-project": Observation.DOCUMENTED}),
    "decoration.row-band": _observations(),
    "paint.linear-gradient": _observations(),
    "effect.drop-shadow": _observations(),
    "stroke.line-cap": _observations(),
    "stroke.line-join": _observations(),
    "icon.vector": _observations(),
    "icon.raster": _observations(),
    "icon.generic-image": _observations(),
    "mark.marker-geometry": _observations(**{"microsoft-project": Observation.DOCUMENTED}),
    "paint.pattern-geometry": _observations(**{"microsoft-project": Observation.DOCUMENTED}),
    "mark.symbol-outline": _observations(**{"microsoft-project": Observation.DOCUMENTED}),
}

CHRONA_DISPOSITIONS = {
    CapabilityDisposition.ADMITTED: "supported",
    CapabilityDisposition.DEFERRED: "deferred",
    CapabilityDisposition.DELIBERATELY_REJECTED: "deliberately-rejected",
}


def validate_observations() -> None:
    """Reject stale capability/source coverage before publishing the matrix."""
    capability_ids = {item.identifier for item in capability_ceiling()}
    rows = set(OBSERVATIONS)
    if missing := capability_ids - rows:
        raise ValueError(f"E_PRIOR_ART_CAPABILITY_MISSING:{sorted(missing)[0]}")
    if stale := rows - capability_ids:
        raise ValueError(f"E_PRIOR_ART_CAPABILITY_STALE:{sorted(stale)[0]}")
    sources = {source.identifier for source in SOURCES}
    if len(sources) != len(SOURCES):
        raise ValueError("E_PRIOR_ART_SOURCE_DUPLICATE")
    for identifier, row in OBSERVATIONS.items():
        if missing := sources - set(row):
            raise ValueError(f"E_PRIOR_ART_OBSERVATION_MISSING:{identifier}:{sorted(missing)[0]}")
        if stale := set(row) - sources:
            raise ValueError(f"E_PRIOR_ART_OBSERVATION_STALE:{identifier}:{sorted(stale)[0]}")
        for observation in row.values():
            if not isinstance(observation, SourceObservation) or observation.value not in Observation:
                raise ValueError(f"E_PRIOR_ART_OBSERVATION_VALUE:{identifier}")
            if observation.value is Observation.NOT_APPLICABLE and not observation.reason:
                raise ValueError(f"E_PRIOR_ART_NOT_APPLICABLE_REASON:{identifier}")
            if observation.value is not Observation.NOT_APPLICABLE and observation.reason is not None:
                raise ValueError(f"E_PRIOR_ART_OBSERVATION_REASON:{identifier}")


def render() -> str:
    validate_observations()
    headings = " | ".join(f"[{source.title}]({source.url})" for source in SOURCES)
    lines = [
        "# Presentation capability prior-art matrix", "",
        "Generated by `tools/presentation_prior_art.py` from the typed #391 capability registry.",
        "External columns are curated review observations, not runtime inputs or feature commitments.", "",
        "## Observation values", "",
        "- `documented`: the named primary source explicitly documents the finite capability category.",
        "- `unknown`: review has not established the fact; it is not evidence of absence.",
        "- `not-applicable`: the source scope makes the category inapplicable, with a source-local reason required when introduced.", "",
        "## Capability dispositions", "",
        f"| Capability | Primitive family | Chrona | Owner | Reason | Reference | {headings} |",
        "| --- | --- | --- | --- | --- | --- | " + " | ".join("---" for _source in SOURCES) + " |",
    ]
    for item in capability_ceiling():
        observations = OBSERVATIONS[item.identifier]
        cells = " | ".join(observations[source.identifier].value.value for source in SOURCES)
        lines.append(f"| `{item.identifier}` | {item.primitive_family} | {CHRONA_DISPOSITIONS[item.disposition]} | {item.owner} | {item.reason} | {item.reference} | {cells} |")
    lines.extend(("", "## Review rule", "", "Every new presentation capability must first add a typed ceiling row, a complete observation row, and refresh this matrix against its named primary sources. `unknown` external behavior is recorded as unknown, never inferred as absence."))
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = render()
    if args.check:
        return 0 if args.output.is_file() and args.output.read_text(encoding="utf-8") == rendered else 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
