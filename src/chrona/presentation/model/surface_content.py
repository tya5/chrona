"""Normalized presentation content inputs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

@dataclass(frozen=True)
class SurfaceContentInput:
    """Selected presentation facts normalized once before Scene construction."""

    table_columns: tuple[tuple[str, str], ...] = ()
    table_cells: tuple[tuple[str, str, str], ...] = ()
    relations: tuple[dict, ...] = ()
    annotations: tuple[dict, ...] = ()
    notes: tuple[tuple[str, str], ...] = ()
    legend_entries: tuple[tuple[str, str], ...] = ()
    coverage_text: str = ""
    summary_panels: tuple[tuple[str, str, tuple[tuple[str, str], ...]], ...] = ()
    template_values: tuple[tuple[str, str], ...] = ()
    group_details: tuple[tuple[str, str, str], ...] = ()
    milestones: tuple[tuple[str, str, date], ...] = ()
    observation_columns: tuple[tuple[str, str], ...] = ()
    observation_rows: tuple[tuple[str, str, str, tuple[tuple[str, str], ...]], ...] = ()


@dataclass(frozen=True)
class ResolvedPresentationInput:
    """One derived input boundary between authoring resources and Scene geometry."""

    title: str
    window: tuple[date, date]
    items: tuple[object, ...]
    settings: dict
    surface_content: SurfaceContentInput
