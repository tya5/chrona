"""Deterministic declared font closure for Layout and output adapters."""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from importlib.resources import files
import json
from pathlib import Path

from chrona.presentation.model.font_resources import FontResourceError, resolve_font_resource
from chrona.resources import safe_load


class FontMetricsError(ValueError):
    """A declared font closure cannot measure the requested text exactly."""

    def __init__(self, diagnostic_id: str, detail: str | None = None):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id
        self.detail = detail


@dataclass(frozen=True)
class FontMetricsCatalog:
    """Closed exact-face metrics selection owned above Layout."""

    metrics: dict[tuple[str, int], "FontMetrics"]

    def select(self, family: str, weight: int) -> "FontMetrics":
        selected = _families(family)[0] if _families(family) else ""
        metric = self.metrics.get((selected.casefold(), weight))
        if metric is None:
            raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE",
                                   f"declared metrics are unavailable for {selected}/{weight}")
        return metric

    @property
    def warnings(self) -> tuple[FontGlyphSubstitution, ...]:
        return tuple(sorted((warning for metric in self.metrics.values() for warning in metric.warnings),
                            key=lambda item: (item.requested_family.casefold(), item.weight,
                                              item.codepoint, item.text)))


@dataclass(frozen=True)
class FontGlyphSubstitution:
    """One observable draft-only measurement substitution."""

    requested_family: str
    fallback_family: str
    weight: int
    codepoint: int
    text: str


@dataclass(frozen=True)
class FontMetrics:
    metrics_path: Path
    metrics_content_identity: str
    source_content_identity: str
    family: str
    weight: int
    units_per_em: int
    ascent: int
    descent: int
    cap_height: int
    advances: dict[int, int]
    numeric_advances: dict[str, dict[int, int]] | None
    substitute_metrics: "FontMetrics | None" = None
    substitutions: set[FontGlyphSubstitution] = field(default_factory=set, compare=False, repr=False)

    @property
    def content_identity(self) -> str:
        """The exact source face identity carried into measured placements."""
        return self.source_content_identity

    def width(self, value: str, size: float, letter_spacing: float = 0,
              numeric_spacing: str = "proportional") -> float:
        total = 0
        for character in value:
            codepoint = ord(character)
            if ord("0") <= codepoint <= ord("9"):
                self.ensure_numeric_spacing(numeric_spacing)
                advance = self.numeric_advances[numeric_spacing].get(codepoint) if self.numeric_advances else None
            else:
                advance = self.advances.get(codepoint)
            if advance is None:
                if codepoint <= 0x1F or codepoint == 0x7F:
                    continue
                # Primary faces must carry every selected numeric feature.
                # A character-level substitute never supplies numeric policy.
                if ord("0") <= codepoint <= ord("9"):
                    raise FontMetricsError(
                        "E_FONT_GLYPH_UNAVAILABLE",
                        f"{self.family} has no metric for U+{codepoint:04X} in {value!r}",
                    )
                if self.substitute_metrics is not None:
                    fallback_advance = self.substitute_metrics.advances.get(codepoint)
                    if fallback_advance is not None:
                        self.substitutions.add(FontGlyphSubstitution(
                            self.family, self.substitute_metrics.family, self.weight,
                            codepoint, value,
                        ))
                        total += fallback_advance * self.units_per_em / self.substitute_metrics.units_per_em
                        continue
                raise FontMetricsError(
                    "E_FONT_GLYPH_UNAVAILABLE",
                    f"{self.family} has no metric for U+{codepoint:04X} in {value!r}",
                )
            total += advance
        return total / self.units_per_em * size + max(0, len(value) - 1) * letter_spacing

    def ensure_numeric_spacing(self, numeric_spacing: str) -> None:
        """Reject a selected numeric feature that this primary face cannot measure."""
        if self.numeric_advances is None or numeric_spacing not in self.numeric_advances:
            raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE")

    def baseline(self, top: float, size: float, line_height: float) -> float:
        line = size * line_height
        return top + (line - size) / 2 + size * self.ascent / self.units_per_em

    def cap_height_at(self, size: float) -> float:
        return size * self.cap_height / self.units_per_em

    @property
    def warnings(self) -> tuple[FontGlyphSubstitution, ...]:
        return tuple(sorted(self.substitutions, key=lambda item: (
            item.requested_family.casefold(), item.weight, item.codepoint, item.text,
        )))


@dataclass(frozen=True)
class FontFile:
    """One identity-pinned rasterizable font asset declared by a Context."""

    path: Path
    content_identity: str
    family: str
    weight: int
    index: int = 0


def _families(font_stack: str) -> list[str]:
    return [family.strip().strip("'\"") for family in font_stack.split(",") if family.strip()]


def _identity(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def font_metrics_from_document(document: bytes, *, metrics_path: Path, family: str, weight: int,
                               source_content_identity: str | None = None,
                               require_numeric: bool = True) -> FontMetrics:
    """Validate one canonical v3 document into the shared measurement model.

    A caller must supply the selected face identity when the document was
    generated in memory, as draft system-font discovery does.  Declared
    metrics retain their own document identity and source identity checks.
    """
    try:
        table = json.loads(document)
        if (table.get("version") != "chrona/font-metrics/v3"
                or table.get("family", "").casefold() != family.casefold()
                or table.get("weight") != weight
                or not isinstance(table.get("sourceContentIdentity"), str)
                or (source_content_identity is not None
                    and table["sourceContentIdentity"] != source_content_identity)):
            raise ValueError("invalid metric identity")
        units, ascent, descent, cap_height = (int(table[key]) for key in ("unitsPerEm", "ascent", "descent", "capHeight"))
        advances = {int(code): int(value) for code, value in table["advances"].items()}
        raw_numeric = table.get("numericAdvances")
        numeric_advances = ({
            mode: {int(code): int(value) for code, value in values.items()}
            for mode, values in raw_numeric.items()
        } if isinstance(raw_numeric, dict) else None)
        digits = set(range(ord("0"), ord("9") + 1))
        if (units <= 0 or cap_height <= 0 or cap_height > units
                or any(code < 0 or value < 0 for code, value in advances.items())
                or (require_numeric and (numeric_advances is None
                                         or set(numeric_advances) != {"proportional", "tabular"}))
                or (numeric_advances is not None and (
                    not numeric_advances or not set(numeric_advances) <= {"proportional", "tabular"}
                    or "proportional" not in numeric_advances
                    or
                    any(set(values) != digits or any(value <= 0 for value in values.values())
                        for values in numeric_advances.values())
                    or ("tabular" in numeric_advances
                        and len(set(numeric_advances["tabular"].values())) != 1)))):
            raise ValueError("invalid metrics")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE") from error
    return FontMetrics(metrics_path, "sha256:" + sha256(document).hexdigest(), str(table["sourceContentIdentity"]),
                       family, weight, units, ascent, descent, cap_height, advances, numeric_advances)


def resolve_font_metrics(font_stack: str, descriptor: dict, *, weight: int = 400,
                         asset_root: Path | None = None, _allow_substitute: bool = True,
                         _require_numeric: bool = True) -> FontMetrics:
    """Resolve one exact metrics/font pair from a declared Context closure."""
    if descriptor.get("algorithm") != "declared-metrics-v3":
        raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE")
    assets = descriptor.get("assets")
    families = _families(font_stack)
    if not isinstance(assets, list) or not assets or not families:
        raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE")
    for family in families:
        asset = next((item for item in assets if isinstance(item, dict)
                      and item.get("family", "").casefold() == family.casefold()
                      and item.get("weight") == weight), None)
        if asset is None:
            continue
        metrics = asset.get("metrics")
        if not isinstance(metrics, dict):
            continue
        try:
            metrics_path = resolve_font_resource(metrics.get("locator"), asset_root=asset_root)
        except FontResourceError:
            continue
        metrics_identity = _identity(metrics_path)
        if metrics.get("contentIdentity") != metrics_identity:
            continue
        try:
            metric = font_metrics_from_document(metrics_path.read_bytes(), metrics_path=metrics_path,
                                                family=family, weight=weight,
                                                require_numeric=_require_numeric)
        except FontMetricsError:
            continue
        fallback = None
        if descriptor.get("missingFont") == "substitute" and _allow_substitute:
            substitute_descriptor = _packaged_substitute_descriptor()
            fallback = resolve_font_metrics(_declared_substitute_family(substitute_descriptor), substitute_descriptor,
                                            _allow_substitute=False, _require_numeric=False)
        return FontMetrics(metric.metrics_path, metrics_identity, metric.source_content_identity, family, weight,
                           metric.units_per_em, metric.ascent, metric.descent, metric.cap_height,
                           metric.advances, metric.numeric_advances, fallback)
    raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE")


def resolve_font_metrics_catalog(descriptor: dict, *, asset_root: Path | None = None) -> FontMetricsCatalog:
    """Validate every declared face before Layout can select a Theme treatment."""
    assets = descriptor.get("assets")
    if descriptor.get("algorithm") != "declared-metrics-v3" or not isinstance(assets, list) or not assets:
        raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE")
    resolved: dict[tuple[str, int], FontMetrics] = {}
    for asset in assets:
        if not isinstance(asset, dict) or not isinstance(asset.get("family"), str) or not isinstance(asset.get("weight"), int):
            raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE")
        family, weight = asset["family"], asset["weight"]
        key = (family.casefold(), weight)
        if key in resolved:
            raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE")
        # A one-family stack makes this exact asset selection, while retaining
        # the established descriptor validation and glyph-substitute policy.
        resolved[key] = resolve_font_metrics(family, descriptor, weight=weight, asset_root=asset_root)
    return FontMetricsCatalog(resolved)


def _packaged_substitute_descriptor() -> dict:
    value = safe_load(files("chrona.resources").joinpath("fonts", "draft-substitute-font-metrics.yaml").read_bytes())
    if not isinstance(value, dict):
        raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE")
    return value


def _declared_substitute_family(descriptor: dict) -> str:
    """Return the fallback family from the packaged descriptor, never code."""
    assets = descriptor.get("assets")
    if not isinstance(assets, list) or not assets:
        raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE")
    family = assets[0].get("family") if isinstance(assets[0], dict) else None
    if not isinstance(family, str) or not family:
        raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE")
    return family


def resolve_font_files(descriptor: dict, *, asset_root: Path | None) -> tuple[tuple[FontFile, ...], tuple[str, ...]]:
    """Return the unique, identity-checked font files declared by one Context."""
    if descriptor.get("algorithm") != "declared-metrics-v3":
        raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE")
    assets = descriptor.get("assets")
    if not isinstance(assets, list) or not assets:
        raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE")
    files_by_identity: dict[str, FontFile] = {}
    for asset in assets:
        font = asset.get("font") if isinstance(asset, dict) else None
        if not isinstance(font, dict):
            raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE")
        family = asset.get("family") if isinstance(asset, dict) else None
        try:
            path = resolve_font_resource(font.get("locator"), asset_root=asset_root)
        except FontResourceError as error:
            locator = font.get("locator")
            address = locator.get("address") if isinstance(locator, dict) else None
            raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE", str(address or "declared font bytes")) from error
        if not isinstance(family, str) or not family or font.get("contentIdentity") != _identity(path):
            raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE", str(font.get("locator", {}).get("address", "declared font bytes")))
        identity = str(font["contentIdentity"])
        declared = FontFile(path, identity, family, int(asset["weight"]))
        previous = files_by_identity.setdefault(identity, declared)
        if previous.family.casefold() != declared.family.casefold() or previous.weight != declared.weight:
            raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE")
    return tuple(files_by_identity[key] for key in sorted(files_by_identity)), tuple(sorted(files_by_identity))
