"""Theme font stacks resolved to declared, installed or packaged faces on every render path (#1281).

A Theme `fontFamily` is an ordered list (`Hiragino Sans, Yu Gothic, Noto Sans JP`). For each role Layout uses the first
family that is declared by the Context's font descriptor or installed on this machine; with none, the packaged Noto Sans
at the role's weight. The faces behind the first one, and the packaged face last, supply a character the first lacks.
Declared faces keep their precedence and their exact metrics: a role whose single family is declared is left alone, so a
Context that declares everything it uses renders exactly as before.
"""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from importlib.resources import files
import logging
from pathlib import Path
from typing import Any, Mapping

from fontTools.ttLib import TTFont

from chrona.presentation.fonts.importer import FontImportError, font_metrics_document
from chrona.presentation.fonts.installed import InstalledFace, InstalledFontIndex, installed_fonts
from chrona.presentation.fonts.system import DraftFontResolution
from chrona.presentation.model.font_metrics import (
    FontFile, FontMetrics, FontMetricsCatalog, FontMetricsError, FontTabularWarning, _families,
    font_metrics_from_document, named_families, resolve_font_files, resolve_font_metrics, resolve_font_metrics_catalog,
)
from chrona.presentation.model.font_resources import FontAssetResolver, FontProviderUnavailable, resolve_font_resource
from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView
from chrona.resources import safe_load

PACKAGED_FAMILY = "Noto Sans"
_installed_cache: dict[tuple[str, int, int, int], tuple[FontMetrics, FontFile]] = {}

# Platform families by script, not by preset or Project. Coverage in the closed
# chain chooses the face; a Japanese fallback need not cover Korean text.
CJK_FAMILIES = ("Noto Sans JP", "Noto Sans CJK JP", "Hiragino Sans", "Yu Gothic", "Meiryo",
                "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei",
                "Noto Sans CJK KR", "Malgun Gothic", "Apple SD Gothic Neo")


def _cjk_faces(weight: int, index: InstalledFontIndex) -> list[tuple[FontMetrics, FontFile]]:
    """Close optional package then OS CJK faces using existing resource owners."""
    root = Path(str(files("chrona.resources")))
    records = safe_load(root.joinpath("fonts", "font-sets.yaml").read_bytes())["sets"]["chrona.noto-sans+jp"]
    nearest = 700 if weight >= 600 else 400
    assets = [item for item in records if item["family"] == "Noto Sans JP" and item["weight"] == nearest]
    descriptor = {"algorithm": "declared-metrics-v3", "missingFont": "diagnose", "assets": assets}
    result = []
    try:
        resolve_font_resource(assets[0]["font"]["locator"], asset_root=root)
        font_file = resolve_font_files(descriptor, asset_root=root)[0][0]
        metric = resolve_font_metrics("Noto Sans JP", descriptor, weight=nearest, asset_root=root,
                                      _allow_substitute=False, _require_numeric=False)
        result.append((replace(metric, informational_fallback=True), font_file))
    except FontProviderUnavailable:
        pass
    for family in CJK_FAMILIES:
        if any(item.family.casefold() == family.casefold() for item, _ in result):
            continue
        face = index.find(family, weight)
        if face is not None:
            try:
                metric, font_file = _installed_metric(face)
                result.append((replace(metric, informational_fallback=True), font_file))
            except (OSError, ValueError, FontImportError, FontMetricsError):
                continue
    return result


def _installed_metric(face: InstalledFace) -> tuple[FontMetrics, FontFile]:
    """Measure one installed face once per process (a CJK collection is large)."""
    stat = face.path.stat()
    key = (str(face.path), face.index, stat.st_size, stat.st_mtime_ns)
    if key not in _installed_cache:
        payload = face.path.read_bytes()
        identity = "sha256:" + sha256(payload).hexdigest()
        logger = logging.getLogger("fontTools")
        previous, logger.level = logger.level, logging.ERROR
        try:
            document = font_metrics_document(TTFont(face.path, fontNumber=face.index, recalcTimestamp=False), payload,
                                             face.family, face.weight, allow_partial_numeric=True,
                                             allow_outline_cap_height=True)
            metric = font_metrics_from_document(document, metrics_path=face.path, family=face.family,
                                                weight=face.weight, source_content_identity=identity,
                                                require_numeric=False)
        finally:
            logger.level = previous
        _installed_cache[key] = (metric, FontFile(face.path, identity, face.family, face.weight, face.index))
    return _installed_cache[key]


def _packaged(weight: int) -> tuple[FontMetrics, FontFile]:
    """The packaged Noto Sans at the weight nearest the role's (regular or bold)."""
    root = Path(str(files("chrona.resources")))
    descriptor = safe_load(root.joinpath("fonts", "default-font-metrics.yaml").read_bytes())
    nearest = 700 if weight >= 600 else 400
    metric = resolve_font_metrics(PACKAGED_FAMILY, descriptor, weight=nearest, asset_root=root, _allow_substitute=False,
                                  _require_numeric=False)
    declared = next(item for item in resolve_font_files(descriptor, asset_root=root)[0]
                    if item.family.casefold() == PACKAGED_FAMILY.casefold() and item.weight == nearest)
    return replace(metric, substitute_metrics=None), declared


def resolve_theme_font_stacks(theme: Mapping[str, Any], descriptor: dict[str, Any], *, asset_root: Path | None,
                              asset_resolver: FontAssetResolver | None = None,
                              installed: InstalledFontIndex | None = None,
                              font_files_required: bool = True) -> DraftFontResolution | None:
    """Resolve every Theme role's font stack, or None when every role is already one declared exact face.

    Returns the declared catalog extended with one entry per resolved stack (under the stack's own text), the font
    files to rasterize with, the roles whose tabular figures degrade, and one note per resolved or fallen-back role.
    A target that draws no font file (SVG) passes ``font_files_required=False``: declared font files its Context did not
    stage are then skipped instead of abandoning the whole resolution (#1842), so an installed or packaged CJK face
    still joins the stack.
    """
    try:
        view = ThemeTokenView(theme)
        roles = theme.get("body", {}).get("roles", {})
        treatments = {role: view.text_treatment(role) for role, binding in roles.items()
                      if isinstance(binding, Mapping) and "fontFamily" in binding and "fontWeight" in binding}
        declared = resolve_font_metrics_catalog(descriptor, asset_root=asset_root, asset_resolver=asset_resolver)
        declared_files = ()
        try:
            declared_files = resolve_font_files(descriptor, asset_root=asset_root, asset_resolver=asset_resolver)[0]
        except FontMetricsError:
            if font_files_required:
                raise
    except (AttributeError, ThemeTokenError, TypeError, ValueError, FontMetricsError):
        return None  # the established path reports a malformed Theme or descriptor
    pending = {role: item for role, item in treatments.items() if not (
        len(named_families(item.family)) == 1
        and (named_families(item.family)[0].casefold(), item.weight) in declared.metrics)}
    index = installed if installed is not None else installed_fonts()
    cjk_by_weight = {weight: _cjk_faces(weight, index) for weight in {item.weight for item in treatments.values()}}
    if not pending and not any(cjk_by_weight.values()):
        return None
    # Even one exact declared Latin face needs the general per-glyph closure.
    automatic_roles = set(treatments) - set(pending)
    pending = treatments
    metrics = dict(declared.metrics)
    extra_files: list[FontFile] = []
    notes: list[str] = []
    tabular: list[FontTabularWarning] = []
    for role, treatment in sorted(pending.items()):
        families, weight = named_families(treatment.family), treatment.weight
        found: list[tuple[FontMetrics, FontFile | None]] = []
        skipped: list[str] = []
        for family in families:
            key = (family.casefold(), weight)
            if key in declared.metrics:
                found.append((declared.metrics[key], next((item for item in declared_files
                                                            if (item.family.casefold(), item.weight) == key), None)))
                continue
            face = index.find(family, weight)
            if face is not None:
                try:
                    found.append(_installed_metric(face))
                except (OSError, ValueError, FontImportError, FontMetricsError):
                    if not found:
                        skipped.append(family)
                    continue  # an unreadable or unmeasurable installed face is skipped, as if it were not installed
            elif not found:
                skipped.append(family)
        packaged_metric, packaged_file = _packaged(weight)
        fell_back = not found
        stack = []
        for metric, _ in found:
            while metric is not None:
                if all(item.content_identity != metric.content_identity for item in stack):
                    stack.append(replace(metric, informational_fallback=True)
                                 if metric.family in CJK_FAMILIES else metric)
                metric = metric.substitute_metrics
        if role not in automatic_roles and all(item.family.casefold() != PACKAGED_FAMILY.casefold() for item in stack):
            stack.append(packaged_metric)
        # Preserve explicit stack precedence; append only unseen fallback faces.
        for metric, font_file in cjk_by_weight[weight]:
            if all(item.content_identity != metric.content_identity for item in stack):
                stack.append(metric)
                extra_files.append(font_file)
        chained = stack[-1]
        for item in reversed(stack[:-1]):
            chained = replace(item, substitute_metrics=chained, substitutions=set())
        tried = tuple(families) + (() if PACKAGED_FAMILY.casefold() in {name.casefold() for name in families}
                                   else (PACKAGED_FAMILY,))
        chained = replace(chained, tried_families=tried, substitutions=set())
        metrics[(treatment.family.strip().casefold() if "," in treatment.family else families[0].casefold(), weight)] = chained
        # Completed text carries the selected face name; viewer-fit must resolve
        # that name too, even when earlier requested families were unavailable.
        metrics.setdefault((chained.family.casefold(), weight), chained)
        if families and "," in treatment.family:
            metrics.setdefault((families[0].casefold(), weight), chained)
        extra_files.extend(item[1] for item in found if item[1] is not None)
        if any(item.family.casefold() == PACKAGED_FAMILY.casefold() for item in stack):
            extra_files.append(packaged_file)
        if role in automatic_roles:
            pass  # No new diagnostic for text that never uses automatic fallback.
        elif fell_back:
            notes.append(f"W_FONT_FALLBACK_PACKAGED:role={role};requested={treatment.family};face={packaged_metric.family}")
        else:
            notes.append(f"I_FONT_ROLE_RESOLVED:role={role};requested={treatment.family};face={chained.family}")
            if skipped:
                notes.append(f"W_FONT_FAMILY_SKIPPED:role={role};requested={treatment.family};"
                             f"skipped={', '.join(skipped)};face={chained.family}")
        try:
            chained.ensure_numeric_spacing(treatment.numeric_spacing)
        except FontMetricsError as error:
            if treatment.numeric_spacing != "tabular":
                raise
            chained.ensure_numeric_spacing("proportional")
            tabular.append(FontTabularWarning(role, treatment.family, weight))
    files = {(item.content_identity, item.index): item for item in (*declared_files, *extra_files)}
    return DraftFontResolution((), FontMetricsCatalog(metrics), tuple(files[key] for key in sorted(files)),
                               tuple(tabular), tuple(notes))
