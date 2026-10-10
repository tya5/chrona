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
from chrona.presentation.model.font_resources import FontAssetResolver
from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView
from chrona.resources import safe_load

PACKAGED_FAMILY = "Noto Sans"
_installed_cache: dict[tuple[str, int, int, int], tuple[FontMetrics, FontFile]] = {}


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
                              installed: InstalledFontIndex | None = None) -> DraftFontResolution | None:
    """Resolve every Theme role's font stack, or None when every role is already one declared exact face.

    Returns the declared catalog extended with one entry per resolved stack (under the stack's own text), the font
    files to rasterize with, the roles whose tabular figures degrade, and one note per resolved or fallen-back role.
    """
    try:
        view = ThemeTokenView(theme)
        roles = theme.get("body", {}).get("roles", {})
        treatments = {role: view.text_treatment(role) for role, binding in roles.items()
                      if isinstance(binding, Mapping) and "fontFamily" in binding and "fontWeight" in binding}
        declared = resolve_font_metrics_catalog(descriptor, asset_root=asset_root, asset_resolver=asset_resolver)
        declared_files = resolve_font_files(descriptor, asset_root=asset_root, asset_resolver=asset_resolver)[0]
    except (AttributeError, ThemeTokenError, TypeError, ValueError, FontMetricsError):
        return None  # the established path reports a malformed Theme or descriptor
    pending = {role: item for role, item in treatments.items() if not (
        len(named_families(item.family)) == 1
        and (named_families(item.family)[0].casefold(), item.weight) in declared.metrics)}
    if not pending:
        return None
    index = installed if installed is not None else installed_fonts()
    metrics = dict(declared.metrics)
    extra_files: list[FontFile] = []
    notes: list[str] = []
    tabular: list[FontTabularWarning] = []
    for role, treatment in sorted(pending.items()):
        families, weight = named_families(treatment.family), treatment.weight
        found: list[tuple[FontMetrics, FontFile | None]] = []
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
                    continue  # an unreadable or unmeasurable installed face is skipped, as if it were not installed
        packaged_metric, packaged_file = _packaged(weight)
        fell_back = not found
        stack = [item[0] for item in found]
        if all(item.family.casefold() != PACKAGED_FAMILY.casefold() for item in stack):
            stack.append(packaged_metric)
        chained = stack[-1]
        for item in reversed(stack[:-1]):
            chained = replace(item, substitute_metrics=chained)
        metrics[(treatment.family.strip().casefold() if "," in treatment.family else families[0].casefold(), weight)] = chained
        if families and "," in treatment.family:
            metrics.setdefault((families[0].casefold(), weight), chained)
        extra_files.extend(item[1] for item in found if item[1] is not None)
        if any(item.family.casefold() == PACKAGED_FAMILY.casefold() for item in stack):
            extra_files.append(packaged_file)
        if fell_back:
            notes.append(f"W_FONT_FALLBACK_PACKAGED:role={role};requested={treatment.family};face={packaged_metric.family}")
        else:
            notes.append(f"I_FONT_ROLE_RESOLVED:role={role};requested={treatment.family};face={chained.family}")
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
