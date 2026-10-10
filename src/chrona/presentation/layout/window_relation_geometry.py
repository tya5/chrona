"""Contain completed route and terminal geometry; never alter semantic ports."""
from chrona.presentation.layout.relation_terminals import project_marker_outline
from chrona.presentation.layout.surface_quality import MarkerGeometry, PaintClip, PathCommand


def relation_geometry_inside_plot(
    clip: PaintClip, points: tuple[tuple[float, float], ...], *,
    path_commands: tuple[PathCommand, ...] = (), marker_start: MarkerGeometry | None = None,
    marker_end: MarkerGeometry | None = None, stroke_width: float,
) -> bool:
    """Read absolute completed contours; stroke/effects are contained by paint clip."""
    x, y, width, height = clip.bounds
    geometry = [*points, *(point for command in path_commands for point in command.points)]
    for marker, side in ((marker_start, "start"), (marker_end, "end")):
        if marker is not None:
            outline = project_marker_outline(marker, side=side, points=points,
                path_commands=path_commands, stroke_width=stroke_width)
            geometry.extend(point for command in outline for point in command.points)
    return bool(points) and all(x <= px <= x + width and y <= py <= y + height for px, py in geometry)
