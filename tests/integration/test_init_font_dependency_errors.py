"""Only absent optional package font providers can defer a valid Context."""
from __future__ import annotations

from pathlib import Path
import shutil

import pytest
import yaml

from chrona.presentation.contracts.resources import SchemaContractError
from chrona.presentation.model import font_resources
from chrona.resources import safe_load
from chrona.usecases.materialize import UnavailableFontProviders, copy_context_closure
from tests.support.deck_contexts import write_explicit_context


ROOT = Path(__file__).resolve().parents[2]
CONTEXT_ADDRESS = "contexts/19-gallery-text-compression.yaml"
CONTEXT_SLIDE = "gallery-text-compression"
MISSING_PROVIDER = "chrona-fonts-noto-cjk"


def _isolated_context(tmp_path: Path, mutate) -> tuple[Path, Path]:
    example = tmp_path / "halcyon-1"
    shutil.copytree(ROOT / "examples" / "halcyon-1", example)
    context_path = write_explicit_context(example, CONTEXT_SLIDE, CONTEXT_ADDRESS)
    context = safe_load(context_path.read_bytes())
    mutate(context)
    context_path.write_text(yaml.safe_dump(context, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return example, context_path


def _without_cjk_provider(monkeypatch) -> None:
    installed = font_resources.entry_points

    def lookup(*, group: str, name: str):
        if name == MISSING_PROVIDER:
            return ()
        return installed(group=group, name=name)

    monkeypatch.setattr(font_resources, "entry_points", lookup)


def _copy(example: Path, context_path: Path, snapshot: Path) -> None:
    snapshot.mkdir()
    copy_context_closure(example, context_path, snapshot)


def test_valid_context_reports_only_the_zero_entry_point_provider(tmp_path, monkeypatch):
    example, context_path = _isolated_context(tmp_path, lambda _context: None)
    _without_cjk_provider(monkeypatch)

    with pytest.raises(UnavailableFontProviders) as unavailable:
        _copy(example, context_path, tmp_path / "snapshot")

    assert unavailable.value.code == "E_MATERIALIZER_FONT"
    assert unavailable.value.providers == (MISSING_PROVIDER,)


def test_available_asset_pin_error_wins_over_an_unavailable_provider(tmp_path, monkeypatch):
    def bad_available_pin(context):
        assets = context["body"]["environment"]["fontMetrics"]["assets"]
        assets[0]["metrics"]["contentIdentity"] = "sha256:" + "0" * 64

    example, context_path = _isolated_context(tmp_path, bad_available_pin)
    _without_cjk_provider(monkeypatch)

    with pytest.raises(ValueError, match="E_MATERIALIZER_FONT_IDENTITY"):
        _copy(example, context_path, tmp_path / "snapshot")


@pytest.mark.parametrize(
    "malformation",
    [
        "unknown-font-set",
        "missing-locator",
        "invalid-provider",
        "missing-address",
        "unsafe-address",
    ],
)
def test_invalid_context_is_not_classified_as_provider_deferral(tmp_path, monkeypatch, malformation):
    def malformed(context):
        metrics = context["body"]["environment"]["fontMetrics"]
        if malformation == "unknown-font-set":
            metrics.pop("assets")
            metrics["fontSet"] = "chrona.not-a-packaged-set"
        elif malformation == "missing-locator":
            del metrics["assets"][0]["metrics"]["locator"]
        elif malformation == "invalid-provider":
            metrics["assets"][0]["metrics"]["locator"]["provider"] = "remote"
        elif malformation == "missing-address":
            del metrics["assets"][0]["metrics"]["locator"]["address"]
        else:
            metrics["assets"][0]["metrics"]["locator"]["address"] = "../escape.json"

    example, context_path = _isolated_context(tmp_path, malformed)
    _without_cjk_provider(monkeypatch)

    with pytest.raises(SchemaContractError):
        _copy(example, context_path, tmp_path / "snapshot")
