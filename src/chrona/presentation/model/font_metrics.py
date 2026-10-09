"""Deterministic declared font closure for Layout and output adapters."""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from importlib.resources import files
import json
from pathlib import Path

from chrona.presentation.model.font_resources import FontAssetResolver, FontResourceError, resolve_font_resource
from chrona.resources import safe_load


def _shown(value: object) -> str:
    """Render a bounded scalar operand; never include whole font data."""
    if isinstance(value, (str, int, float, bool, type(None))):
        text = repr(value)
        return text if len(text) <= 96 else text[:93] + "..."
    return f"<{type(value).__name__}>"


class FontMetricsError(ValueError):
    """A declared font closure cannot measure the requested text exactly."""

    def __init__(self, diagnostic_id: str, detail: str | None = None):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id
        self.detail = detail


@dataclass(frozen=True)
class FontTabularWarning:
    """One exact-face draft numeric-feature degradation, by Theme role."""

    role: str
    family: str
    weight: int
    requested_spacing: str = "tabular"
    effective_spacing: str = "proportional"


@dataclass(frozen=True)
class FontMetricsCatalog:
    """Closed exact-face metrics selection owned above Layout."""

    metrics: dict[tuple[str, int], "FontMetrics"]

    def select(self, family: str, weight: int) -> "FontMetrics":
        selected = _families(family)[0] if _families(family) else ""
        metric = self.metrics.get((selected.casefold(), weight))
        if metric is None:
            available = sorted((item.family, item.weight) for item in self.metrics.values())
            raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE",
                                   f"family stack={_shown(family)} selected={_shown(selected)} weight={weight} has no exact declared face; available={available}")
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
                        f"family={_shown(self.family)} weight={self.weight} codepoint=U+{codepoint:04X} has no numeric advance; text_length={len(value)}",
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
                    f"family={_shown(self.family)} weight={self.weight} codepoint=U+{codepoint:04X} has no advance; text_length={len(value)}",
                )
            total += advance
        return total / self.units_per_em * size + max(0, len(value) - 1) * letter_spacing

    def ensure_numeric_spacing(self, numeric_spacing: str) -> None:
        """Reject a selected numeric feature that this primary face cannot measure."""
        if self.numeric_advances is None or numeric_spacing not in self.numeric_advances:
            available = sorted(self.numeric_advances) if self.numeric_advances is not None else []
            raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE",
                                   f"family={_shown(self.family)} weight={self.weight} numeric_spacing={_shown(numeric_spacing)} unavailable; expected one of proportional/tabular, available={available}")

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
    field = "/document"
    table: dict = {}
    try:
        table = json.loads(document)
        field = "/version"
        if table.get("version") != "chrona/font-metrics/v3":
            raise ValueError(f"{field} expected chrona/font-metrics/v3; got {_shown(table.get('version'))}")
        field = "/family"
        if table.get("family", "").casefold() != family.casefold():
            raise ValueError(f"{field} expected {_shown(family)}; got {_shown(table.get('family'))}")
        field = "/weight"
        if table.get("weight") != weight:
            raise ValueError(f"{field} expected {weight}; got {_shown(table.get('weight'))}")
        field = "/sourceContentIdentity"
        if not isinstance(table.get("sourceContentIdentity"), str):
            raise ValueError(f"{field} expected a string identity; got {type(table.get('sourceContentIdentity')).__name__}")
        if source_content_identity is not None and table["sourceContentIdentity"] != source_content_identity:
            raise ValueError(f"{field} expected {_shown(source_content_identity)}; got {_shown(table['sourceContentIdentity'])}")
        field = "/unitsPerEm|ascent|descent|capHeight"
        units, ascent, descent, cap_height = (int(table[key]) for key in ("unitsPerEm", "ascent", "descent", "capHeight"))
        field = "/advances/<codepoint>"
        advances = {int(code): int(value) for code, value in table["advances"].items()}
        field = "/numericAdvances/<spacing>/<codepoint>"
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
            raise ValueError(_invalid_metrics_detail(
                units, cap_height, advances, numeric_advances, digits, require_numeric,
            ))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        if isinstance(error, json.JSONDecodeError):
            detail = f"metrics={_shown(str(metrics_path))} name={_shown(metrics_path.name)} JSON parse failed at line={error.lineno}, column={error.colno}; expected a v3 metrics object"
        elif isinstance(error, ValueError) and error.args and isinstance(error.args[0], str) and error.args[0].startswith("/"):
            detail = f"metrics={_shown(str(metrics_path))} name={_shown(metrics_path.name)} family={_shown(family)} weight={weight}: {error.args[0]}"
        else:
            detail = f"metrics={_shown(str(metrics_path))} name={_shown(metrics_path.name)} family={_shown(family)} weight={weight}: {field} could not be read as required numeric metric data ({type(error).__name__})"
        raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE", detail) from error
    return FontMetrics(metrics_path, "sha256:" + sha256(document).hexdigest(), str(table["sourceContentIdentity"]),
                       family, weight, units, ascent, descent, cap_height, advances, numeric_advances)


def _invalid_metrics_detail(units: int, cap_height: int, advances: dict[int, int],
                            numeric_advances: dict[str, dict[int, int]] | None,
                            digits: set[int], require_numeric: bool) -> str:
    """Name the first already-rejected metric field without serializing tables."""
    if units <= 0:
        return f"/unitsPerEm={units} must be greater than zero"
    if cap_height <= 0 or cap_height > units:
        return f"/capHeight={cap_height} must be within 1..unitsPerEm ({units})"
    invalid_advance = next(((code, value) for code, value in advances.items() if code < 0 or value < 0), None)
    if invalid_advance is not None:
        code, value = invalid_advance
        return f"/advances/{code}={value} requires a nonnegative codepoint and advance"
    if require_numeric and (numeric_advances is None or set(numeric_advances) != {"proportional", "tabular"}):
        return f"/numericAdvances keys={sorted(numeric_advances) if numeric_advances is not None else None} must be proportional and tabular"
    if numeric_advances is not None:
        if not numeric_advances:
            return "/numericAdvances must contain at least one spacing mode"
        if not set(numeric_advances) <= {"proportional", "tabular"}:
            return f"/numericAdvances has unsupported spacing keys={sorted(numeric_advances)}; expected proportional/tabular"
        if "proportional" not in numeric_advances:
            return f"/numericAdvances/proportional is required; available={sorted(numeric_advances)}"
        for mode, values in numeric_advances.items():
            if set(values) != digits:
                missing = sorted(digits - set(values))
                extra = sorted(set(values) - digits)
                return f"/numericAdvances/{mode} must map all ten digit codepoints; missing={missing[:4]}, extra={extra[:4]}"
            invalid = next(((code, value) for code, value in values.items() if value <= 0), None)
            if invalid is not None:
                code, value = invalid
                return f"/numericAdvances/{mode}/{code}={value} must be positive"
        if "tabular" in numeric_advances and len(set(numeric_advances["tabular"].values())) != 1:
            return "/numericAdvances/tabular must use one shared advance for all digit codepoints"
    return "/metrics violates the declared v3 metric constraints"


def resolve_font_metrics(font_stack: str, descriptor: dict, *, weight: int = 400,
                         asset_root: Path | None = None, _allow_substitute: bool = True,
                         _require_numeric: bool = True,
                         asset_resolver: FontAssetResolver | None = None) -> FontMetrics:
    """Resolve one exact metrics/font pair from a declared Context closure."""
    if descriptor.get("algorithm") != "declared-metrics-v3":
        raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE", f"/algorithm={_shown(descriptor.get('algorithm'))}; expected declared-metrics-v3 for family={_shown(font_stack)} weight={weight}")
    assets = descriptor.get("assets")
    families = _families(font_stack)
    if not isinstance(assets, list) or not assets or not families:
        raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE", f"family stack={_shown(font_stack)} weight={weight}; assets must be a nonempty list and family stack must contain a family (assets={type(assets).__name__})")
    rejected: list[str] = []
    for family in families:
        asset = next((item for item in assets if isinstance(item, dict)
                      and item.get("family", "").casefold() == family.casefold()
                      and item.get("weight") == weight), None)
        if asset is None:
            rejected.append(f"{_shown(family)}/{weight}: no matching face declaration")
            continue
        metrics = asset.get("metrics")
        if not isinstance(metrics, dict):
            rejected.append(f"{_shown(family)}/{weight}: metrics field must be an object; got {type(metrics).__name__}")
            continue
        try:
            metrics_path = resolve_font_resource(metrics.get("locator"), asset_root=asset_root,
                                                 asset_resolver=asset_resolver,
                                                 expected_identity=metrics.get("contentIdentity"))
        except FontResourceError as error:
            rejected.append(f"{_shown(family)}/{weight}: {error.detail or error.diagnostic_id}")
            continue
        metrics_identity = _identity(metrics_path)
        if metrics.get("contentIdentity") != metrics_identity:
            rejected.append(f"{_shown(family)}/{weight}: metrics/contentIdentity expected {_shown(metrics_identity)}; got {_shown(metrics.get('contentIdentity'))}")
            continue
        try:
            metric = font_metrics_from_document(metrics_path.read_bytes(), metrics_path=metrics_path,
                                                family=family, weight=weight,
                                                require_numeric=_require_numeric)
        except FontMetricsError as error:
            rejected.append(f"{_shown(family)}/{weight}: {error.detail or error.diagnostic_id}")
            continue
        fallback = None
        if descriptor.get("missingFont") == "substitute" and _allow_substitute:
            substitute_descriptor = _packaged_substitute_descriptor()
            fallback = resolve_font_metrics(_declared_substitute_family(substitute_descriptor), substitute_descriptor,
                                            _allow_substitute=False, _require_numeric=False)
        return FontMetrics(metric.metrics_path, metrics_identity, metric.source_content_identity, family, weight,
                           metric.units_per_em, metric.ascent, metric.descent, metric.cap_height,
                           metric.advances, metric.numeric_advances, fallback)
    summary = "; ".join(rejected[:4]) or "no matching family candidates"
    raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE", f"family stack={_shown(font_stack)} weight={weight} unavailable; candidates: {summary}")


def resolve_font_metrics_catalog(descriptor: dict, *, asset_root: Path | None = None,
                                asset_resolver: FontAssetResolver | None = None) -> FontMetricsCatalog:
    """Validate every declared face before Layout can select a Theme treatment."""
    assets = descriptor.get("assets")
    if descriptor.get("algorithm") != "declared-metrics-v3" or not isinstance(assets, list) or not assets:
        raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE", f"/algorithm={_shown(descriptor.get('algorithm'))}, /assets type={type(assets).__name__}; expected declared-metrics-v3 with nonempty assets list")
    resolved: dict[tuple[str, int], FontMetrics] = {}
    for asset_index, asset in enumerate(assets):
        if not isinstance(asset, dict) or not isinstance(asset.get("family"), str) or not isinstance(asset.get("weight"), int):
            raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE", f"/assets/{asset_index} requires string family and integer weight; found {type(asset).__name__}")
        family, weight = asset["family"], asset["weight"]
        key = (family.casefold(), weight)
        if key in resolved:
            raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE", f"/assets/{asset_index} family={_shown(family)} weight={weight} duplicates an already-declared face")
        # A one-family stack makes this exact asset selection, while retaining
        # the established descriptor validation and glyph-substitute policy.
        resolved[key] = resolve_font_metrics(family, descriptor, weight=weight, asset_root=asset_root,
                                             asset_resolver=asset_resolver)
    return FontMetricsCatalog(resolved)


def _packaged_substitute_descriptor() -> dict:
    value = safe_load(files("chrona.resources").joinpath("fonts", "draft-substitute-font-metrics.yaml").read_bytes())
    if not isinstance(value, dict):
        raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE", f"packaged fonts/draft-substitute-font-metrics.yaml must contain an object; found {type(value).__name__}")
    return value


def _declared_substitute_family(descriptor: dict) -> str:
    """Return the fallback family from the packaged descriptor, never code."""
    assets = descriptor.get("assets")
    if not isinstance(assets, list) or not assets:
        raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE", f"packaged substitute /assets must be a nonempty list; found {type(assets).__name__}")
    family = assets[0].get("family") if isinstance(assets[0], dict) else None
    if not isinstance(family, str) or not family:
        raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE", f"packaged substitute /assets/0/family must be a nonempty string; got {_shown(family)}")
    return family


def resolve_font_files(descriptor: dict, *, asset_root: Path | None,
                       asset_resolver: FontAssetResolver | None = None) -> tuple[tuple[FontFile, ...], tuple[str, ...]]:
    """Return the unique, identity-checked font files declared by one Context."""
    if descriptor.get("algorithm") != "declared-metrics-v3":
        raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE", f"/algorithm={_shown(descriptor.get('algorithm'))}; expected declared-metrics-v3 before resolving font files")
    assets = descriptor.get("assets")
    if not isinstance(assets, list) or not assets:
        raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE", f"/assets must be a nonempty list before resolving font files; found {type(assets).__name__}")
    files_by_identity: dict[str, FontFile] = {}
    for asset_index, asset in enumerate(assets):
        font = asset.get("font") if isinstance(asset, dict) else None
        if not isinstance(font, dict):
            raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE", f"/assets/{asset_index}/font must be an object; found {type(font).__name__}")
        family = asset.get("family") if isinstance(asset, dict) else None
        try:
            path = resolve_font_resource(font.get("locator"), asset_root=asset_root,
                                         asset_resolver=asset_resolver,
                                         expected_identity=font.get("contentIdentity"))
        except FontResourceError as error:
            locator = font.get("locator")
            address = locator.get("address") if isinstance(locator, dict) else None
            raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE", f"family={_shown(family)} weight={_shown(asset.get('weight'))} font locator address={_shown(address)} unavailable: {error.detail or error.diagnostic_id}") from error
        if not isinstance(family, str) or not family or font.get("contentIdentity") != _identity(path):
            locator = font.get("locator")
            address = locator.get("address") if isinstance(locator, dict) else None
            raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE", f"family={_shown(family)} weight={_shown(asset.get('weight'))} font address={_shown(address)} identity expected={_shown(_identity(path))} got={_shown(font.get('contentIdentity'))}")
        identity = str(font["contentIdentity"])
        declared = FontFile(path, identity, family, int(asset["weight"]))
        previous = files_by_identity.setdefault(identity, declared)
        if previous.family.casefold() != declared.family.casefold() or previous.weight != declared.weight:
            raise FontMetricsError("E_FONT_METRICS_UNAVAILABLE", f"font identity={_shown(identity)} is shared by conflicting faces {previous.family}/{previous.weight} and {declared.family}/{declared.weight}")
    return tuple(files_by_identity[key] for key in sorted(files_by_identity)), tuple(sorted(files_by_identity))
