"""Build the checked-in Noto Sans JP provider from explicit offline inputs."""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil

import yaml
from fontTools.ttLib import TTFont

from chrona.presentation.fonts.importer import _metrics


FAMILY = "Noto Sans JP"
PROVIDER = "chrona-fonts-noto-cjk"
FACES = (("regular", 400, "Regular"), ("bold", 700, "Bold"))


class ProviderBuildError(ValueError):
    """An offline provider input cannot produce a trustworthy artifact."""


def _identity(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _rename_face(source: Path, output: Path, *, weight: int, subfamily: str) -> None:
    font = TTFont(source)
    if font["OS/2"].usWeightClass != weight:
        raise ProviderBuildError(f"E_PROVIDER_SOURCE_WEIGHT:{source}:{font['OS/2'].usWeightClass}:{weight}")
    names = {
        1: FAMILY,
        2: subfamily,
        3: f"2.004;CHRA;NotoSansJP-{subfamily}",
        4: f"{FAMILY} {subfamily}",
        6: f"NotoSansJP-{subfamily}",
    }
    for record in font["name"].names:
        if record.nameID in names:
            record.string = names[record.nameID].encode(record.getEncoding())
    output.parent.mkdir(parents=True, exist_ok=True)
    font.save(output)
    verified = TTFont(output)
    if verified["OS/2"].usWeightClass != weight:
        raise ProviderBuildError(f"E_PROVIDER_OUTPUT_WEIGHT:{output}")
    values = {record.nameID: record.toUnicode() for record in verified["name"].names if record.nameID in names}
    if any(values.get(name_id) != value for name_id, value in names.items()) or any("Source" in value for value in values.values()):
        raise ProviderBuildError(f"E_PROVIDER_OUTPUT_NAME:{output}")


def _descriptor(records: list[dict]) -> dict:
    return {"algorithm": "declared-metrics-v3", "missingFont": "diagnose", "assets": records}


def build(*, regular_source: Path, bold_source: Path, notice_source: Path, output_root: Path,
          source_repository: str, source_revision: str) -> None:
    """Build provider assets without network access or destination-as-input reads."""
    inputs = (regular_source, bold_source, notice_source)
    if any(not item.is_file() for item in inputs) or any(_inside(item, output_root) for item in inputs):
        raise ProviderBuildError("E_PROVIDER_BUILD_INPUT")
    fonts = output_root / "fonts"
    metrics = output_root / "font_metrics"
    records, provenance_faces = [], []
    for source, (slug, weight, subfamily) in zip((regular_source, bold_source), FACES, strict=True):
        output = fonts / f"noto-sans-jp-{slug}-v1.ttf"
        _rename_face(source, output, weight=weight, subfamily=subfamily)
        payload = output.read_bytes()
        metric_output = metrics / f"noto-sans-jp-{slug}-v2.json"
        metric_output.parent.mkdir(parents=True, exist_ok=True)
        metric_output.write_bytes(_metrics(TTFont(output), payload, FAMILY, weight))
        font_identity, metrics_identity = _identity(output), _identity(metric_output)
        records.append({
            "family": FAMILY, "weight": weight,
            "metrics": {"locator": {"provider": "package", "identity": PROVIDER,
                         "address": f"font_metrics/{metric_output.name}"}, "contentIdentity": metrics_identity},
            "font": {"locator": {"provider": "package", "identity": PROVIDER,
                     "address": f"fonts/{output.name}"}, "contentIdentity": font_identity},
        })
        provenance_faces.append({"weight": weight, "sourceContentIdentity": _identity(source),
                                 "contentIdentity": font_identity, "metricsContentIdentity": metrics_identity})
    shutil.copyfile(notice_source, fonts / "NotoSansJP.LICENSE")
    (output_root / "font-metrics.yaml").write_text(yaml.safe_dump(_descriptor(records), sort_keys=False), encoding="utf-8")
    provenance = {"version": "chrona/font-provider-source/v0.1", "provider": PROVIDER,
                  "family": FAMILY, "source": {"repository": source_repository, "revision": source_revision,
                  "noticeContentIdentity": _identity(notice_source)}, "faces": provenance_faces}
    (output_root / "FONT-SOURCE.json").write_text(json.dumps(provenance, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--regular-source", required=True, type=Path)
    parser.add_argument("--bold-source", required=True, type=Path)
    parser.add_argument("--notice-source", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--source-repository", required=True)
    parser.add_argument("--source-revision", required=True)
    args = parser.parse_args()
    build(**vars(args))


if __name__ == "__main__":
    main()
