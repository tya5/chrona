"""Initialization publishes only complete, available Context closures."""
from pathlib import Path

import pytest
import yaml

from chrona.usecases import local_authoring as authoring
from chrona.usecases.materialize import UnavailableFontProviders


def template(tmp_path):
    source = tmp_path / "source"
    (source / "contexts").mkdir(parents=True)
    (source / "generated").mkdir()
    slides = []
    for name in ("available", "deferred"):
        (source / "contexts" / f"{name}.yaml").write_text(name)
        (source / "generated" / f"{name}.svg").write_text(name)
        slides.append({"id": name, "context": f"contexts/{name}.yaml",
                       "evidence": "Provider deferral fixture.",
                       "expectedSvg": f"generated/{name}.svg"})
    (source / "manifest.yaml").write_text(yaml.safe_dump({
        "version": "chrona/example-materializer/v0.1", "role": "regression-corpus",
        "context": "contexts/available.yaml", "slides": slides}))
    return source


def test_missing_provider_discards_partial_staging_and_prunes_only_deferred_files(tmp_path, monkeypatch):
    source = template(tmp_path)
    monkeypatch.setattr(authoring, "template_resource", lambda _: source)

    def copy(_example, context, snapshot):
        (snapshot / context.stem).write_text("closure")
        if context.stem == "deferred":
            raise UnavailableFontProviders(("optional-font",))

    monkeypatch.setattr(authoring, "copy_context_closure", copy)
    destination = tmp_path / "initialized"
    result = authoring.initialize_project(destination, example="synthetic")
    assert result.available_slides == ("available",)
    assert result.deferred_slides[0].as_dict() == {
        "slideId": "deferred", "context": "contexts/deferred.yaml", "providers": ["optional-font"]}
    assert result.deferred_slides[0].as_diagnostic()["code"] == "W_INIT_EXAMPLE_SLIDE_DEFERRED"
    assert (destination / ".chrona/store/available").is_file()
    assert not (destination / ".chrona/store/deferred").exists()
    assert not (destination / "contexts/deferred.yaml").exists()
    assert not (destination / "generated/deferred.svg").exists()
    assert (source / "contexts/deferred.yaml").is_file()
    assert (destination / ".chrona/store.yaml").is_file()
    assert len(yaml.safe_load((destination / "manifest.yaml").read_bytes())["slides"]) == 1


@pytest.mark.parametrize("error", [UnavailableFontProviders(("optional-font",)), ValueError("bad pin")])
def test_empty_or_invalid_corpus_never_advertises_store(tmp_path, monkeypatch, error):
    source = template(tmp_path)
    monkeypatch.setattr(authoring, "template_resource", lambda _: source)

    def copy(*_args):
        raise error

    monkeypatch.setattr(authoring, "copy_context_closure", copy)
    destination = tmp_path / "initialized"
    expected = "E_INIT_EXAMPLE_UNAVAILABLE" if isinstance(error, UnavailableFontProviders) else "bad pin"
    with pytest.raises(ValueError, match=expected):
        authoring.initialize_project(destination, example="synthetic")
    assert not (destination / ".chrona/store.yaml").exists()
