"""Deterministic hand-wobble outline completion (#588).

Pure geometry: a primitive's Layout geometry and the declared amplitude, wavelength and seed give
the perturbed outline an adapter draws verbatim. The algorithm is fixed (Specification 07, "Stroke
wobble") and independent of the platform, the Python build, the hash seed and any iteration order:

* the generator is integer-only (the splitmix64 finalizer), converted to a double exactly
  (a 53-bit integer divided by ``2**53``);
* the only floating-point operations are ``+ - * /``, ``sqrt`` and ``floor``/``ceil``, which IEEE 754
  rounds correctly, so every conforming platform computes identical doubles; no ``sin``, ``cos``,
  ``pow``, ``exp`` or ``hypot`` (a C runtime may differ in the last bit), no ``random``, no ``hash``;
* outlines are tuples built in declaration order, and the only rounding is ``round(value, 3)``.
"""
from __future__ import annotations

from math import ceil, floor, sqrt

from chrona.presentation.layout.surface_quality import PathCommand

MAX_OUTLINE_POINTS = 8192
_MASK = (1 << 64) - 1
_TWO_53 = 9007199254740992.0
_FNV_OFFSET = 0xCBF29CE484222325
_FNV_PRIME = 0x100000001B3
_LATTICE_STRIDE = 0xD1B54A32D192ED03
Point = tuple[float, float]


class WobbleLimitError(ValueError):
    """The completed outline would exceed ``MAX_OUTLINE_POINTS``."""


def mix(value: int) -> int:
    """The splitmix64 finalizer of ``value`` taken modulo ``2**64``."""
    value = (value + 0x9E3779B97F4A7C15) & _MASK
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & _MASK
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & _MASK
    return value ^ (value >> 31)


def fnv1a64(data: bytes) -> int:
    """The 64-bit FNV-1a hash of ``data`` (never Python's randomised ``hash``)."""
    value = _FNV_OFFSET
    for byte in data:
        value = ((value ^ byte) * _FNV_PRIME) & _MASK
    return value


def stream_key(seed: int, scene_id: str, subpath: int = 0) -> int:
    """One noise stream: the declared seed, the primitive's identity and the sub-path index."""
    return mix(mix(seed) ^ fnv1a64(scene_id.encode("utf-8")) ^ ((subpath & 0xFF) << 56))


def lattice_value(stream: int, index: int) -> float:
    """An exact double in ``[-1, 1)`` for lattice point ``index`` of ``stream``."""
    return (mix(stream ^ ((index * _LATTICE_STRIDE) & _MASK)) >> 11) / _TWO_53 * 2.0 - 1.0


def _quadratic(start: Point, control: Point, end: Point, fraction: float) -> Point:
    rest = 1.0 - fraction
    return (rest * rest * start[0] + 2.0 * rest * fraction * control[0] + fraction * fraction * end[0],
            rest * rest * start[1] + 2.0 * rest * fraction * control[1] + fraction * fraction * end[1])


def _flatten_quadratic(start: Point, control: Point, end: Point, steps: int) -> list[Point]:
    return [_quadratic(start, control, end, index / steps) for index in range(1, steps + 1)]


def rect_vertices(bounds: tuple[float, float, float, float], corner_radius: float | None) -> list[Point]:
    """The nominal clockwise outline from the top-left; a rounded corner is a flattened quadratic."""
    x, y, width, height = bounds
    radius = min(float(corner_radius or 0.0), width / 2.0, height / 2.0)
    if radius <= 0:
        return [(x, y), (x + width, y), (x + width, y + height), (x, y + height)]
    right, bottom = x + width, y + height
    vertices: list[Point] = [(x + radius, y), (right - radius, y)]
    for start, control, end, next_start in (
            ((right - radius, y), (right, y), (right, y + radius), (right, bottom - radius)),
            ((right, bottom - radius), (right, bottom), (right - radius, bottom), (x + radius, bottom)),
            ((x + radius, bottom), (x, bottom), (x, bottom - radius), (x, y + radius)),
            ((x, y + radius), (x, y), (x + radius, y), None)):
        vertices.extend(_flatten_quadratic(start, control, end, 4))
        if next_start is not None:
            vertices.append(next_start)
    vertices.pop()  # the closing arc ends where the outline began
    return vertices


def path_polylines(commands: tuple[PathCommand, ...], points: tuple[Point, ...]) -> list[list[Point]]:
    """The nominal sub-paths of a Path primitive with each quadratic flattened in four steps."""
    polylines: list[list[Point]] = []
    if not commands:
        polylines.append([(float(px), float(py)) for px, py in points])
    for command in commands:
        if command.kind == "move":
            polylines.append([(float(command.points[0][0]), float(command.points[0][1]))])
        elif not polylines:
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID", "a wobbled path command has no preceding move")
        elif command.kind == "line":
            polylines[-1].append((float(command.points[0][0]), float(command.points[0][1])))
        else:
            control, end = ((float(px), float(py)) for px, py in command.points)
            polylines[-1].extend(_flatten_quadratic(polylines[-1][-1], control, end, 4))
    cleaned = []
    for polyline in polylines:
        kept = [polyline[0]] if polyline else []
        for point in polyline[1:]:
            if point != kept[-1]:
                kept.append(point)
        cleaned.append(kept)
    return cleaned


def _rounded(value: float) -> float:
    return round(value, 3) + 0.0  # + 0.0 turns -0.0 into 0.0


def wobble_polyline(vertices: list[Point], *, closed: bool, amplitude: float, wavelength: float,
                    stream: int) -> tuple[tuple[Point, ...], int]:
    """One perturbed polyline and its point count; fewer than two distinct vertices stay as given."""
    count = len(vertices)
    if closed and count > 1 and vertices[0] == vertices[-1]:
        vertices, count = vertices[:-1], count - 1
    if count < 2 or amplitude <= 0:
        return tuple((_rounded(px), _rounded(py)) for px, py in vertices), count
    segment_total = count if closed else count - 1
    lengths = []
    for index in range(segment_total):
        a, b = vertices[index], vertices[(index + 1) % count]
        lengths.append(sqrt((b[0] - a[0]) * (b[0] - a[0]) + (b[1] - a[1]) * (b[1] - a[1])))
    perimeter = 0.0
    for length in lengths:
        perimeter += length
    if perimeter <= 0:
        return tuple((_rounded(px), _rounded(py)) for px, py in vertices), count
    cells = max(2 if closed else 1, int(floor(perimeter / wavelength + 0.5)))
    realised = perimeter / cells
    step = realised / 4.0
    # Resample: every nominal vertex is kept, each edge is split into equal parts of about one step.
    samples: list[tuple[Point, float]] = []
    offset = 0.0
    for index in range(segment_total):
        a, b, length = vertices[index], vertices[(index + 1) % count], lengths[index]
        parts = max(1, int(ceil(length / step)))
        for part in range(parts):
            fraction = part / parts
            samples.append(((a[0] + (b[0] - a[0]) * fraction, a[1] + (b[1] - a[1]) * fraction),
                            offset + length * fraction))
        offset += length
    if not closed:
        samples.append((vertices[-1], perimeter))
    if len(samples) > MAX_OUTLINE_POINTS:
        raise WobbleLimitError(str(len(samples)))
    # Unit segment normals (dy, -dx): outward for a clockwise outline in y-down coordinates.
    total = len(samples)
    normals: list[Point] = []
    for index in range(total if closed else total - 1):
        a, b = samples[index][0], samples[(index + 1) % total][0]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = sqrt(dx * dx + dy * dy)
        normals.append((dy / length, -dx / length) if length > 0 else (0.0, 0.0))
    result: list[Point] = []
    for index, ((px, py), arc) in enumerate(samples):
        if closed:
            before, after = normals[index - 1], normals[index]
        else:
            before = normals[index - 1] if index > 0 else normals[index]
            after = normals[index] if index < len(normals) else normals[index - 1]
        sx, sy = before[0] + after[0], before[1] + after[1]
        norm = sqrt(sx * sx + sy * sy)
        nx, ny = (sx / norm, sy / norm) if norm > 1e-12 else after
        position = arc * cells / perimeter
        cell = int(floor(position))
        local = position - cell
        weight = local * local * (3.0 - 2.0 * local)
        first = lattice_value(stream, cell % cells if closed else cell)
        second = lattice_value(stream, (cell + 1) % cells if closed else cell + 1)
        noise = first + (second - first) * weight
        envelope = 1.0
        if not closed:
            envelope = min(1.0, arc / realised, (perimeter - arc) / realised)
            envelope = max(0.0, envelope)
        displacement = amplitude * noise * envelope
        result.append((_rounded(px + nx * displacement), _rounded(py + ny * displacement)))
    return tuple(result), total


def complete_rect_wobble(scene_id: str, bounds: tuple[float, float, float, float],
                         corner_radius: float | None, *, amplitude: float, wavelength: float,
                         seed: int) -> tuple[tuple[Point, ...], ...]:
    """The perturbed closed outline of a Rect; its amplitude is limited to a quarter of the short side."""
    effective = min(amplitude, min(bounds[2], bounds[3]) / 4.0)
    outline, _ = wobble_polyline(rect_vertices(bounds, corner_radius), closed=True, amplitude=effective,
                                 wavelength=wavelength, stream=stream_key(seed, scene_id))
    return (outline,)


def complete_path_wobble(scene_id: str, commands: tuple[PathCommand, ...], points: tuple[Point, ...], *,
                         amplitude: float, wavelength: float, seed: int) -> tuple[tuple[Point, ...], ...]:
    """The perturbed open sub-paths of a Path; each sub-path keeps both of its end points."""
    outline: list[tuple[Point, ...]] = []
    used = 0
    for index, polyline in enumerate(path_polylines(commands, points)):
        piece, total = wobble_polyline(polyline, closed=False, amplitude=amplitude, wavelength=wavelength,
                                       stream=stream_key(seed, scene_id, index))
        used += total
        if used > MAX_OUTLINE_POINTS:
            raise WobbleLimitError(str(used))
        outline.append(piece)
    return tuple(outline)
