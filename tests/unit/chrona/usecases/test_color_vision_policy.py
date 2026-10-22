"""A Theme's explicit simulated-vision claim is enforced before adapter output."""

from dataclasses import replace
from pathlib import Path
import tempfile
import pytest

from chrona.presentation.model.color_separability import ScaleCollision
import chrona.presentation.model.color_separability as color_separability
from chrona.presentation.model.diagnostic_sources import (
    ColorPairFinding, DiagnosticProvenance, DiagnosticSubject,
)
import chrona.usecases.render_review as render_usecase
from chrona.usecases.render_review import RenderFailed, RenderRequest, _enforce_color_vision_claims, render_review
from chrona.presentation.model.closure import resolve_render_context
from chrona.presentation.contracts.resources import freeze
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.storage.revision_store import LocalSnapshotReader
from tools.materialize_example import _copy_context_closure
from tests.support.deck_contexts import slide_context


VISIONS = ("protanopia", "deuteranopia", "tritanopia")


def _theme(*claims):
    return {"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
            "body": {"roles": {}, "values": {}, "colorVision": tuple(claims)}}


def _collision(vision, delta_e=4.999):
    return ScaleCollision("status-colors", "ready", "blocked", vision, delta_e)


@pytest.mark.parametrize("vision", VISIONS)
def test_each_explicit_simulated_vision_claim_blocks_its_scale_collision(vision):
    collision = _collision(vision)

    with pytest.raises(RenderFailed) as captured:
        _enforce_color_vision_claims(_theme(vision), (collision,), ())

    error = captured.value
    assert error.code == "E_PRESENTATION_SCALE_NOT_SEPARABLE"
    assert error.component == "presentation"
    assert error.source_ref == "/body/suitability/colorVision"
    assert error.details == {
        "vision": vision, "deltaE": collision.delta_e, "minimumDeltaE": 5.0,
        "claim": vision, "scaleId": "status-colors", "first": "ready", "second": "blocked",
    }


@pytest.mark.parametrize("claims", [(), ("deuteranopia",), ("tritanopia",)])
def test_unclaimed_simulated_collisions_remain_nonblocking(claims):
    _enforce_color_vision_claims(_theme(*claims), (_collision("protanopia"),), ())


def test_normal_vision_collision_does_not_claim_or_block_simulated_vision_suitability():
    _enforce_color_vision_claims(_theme("protanopia", "deuteranopia", "tritanopia"),
                                 (_collision("normal", 0.0),), ())


def test_only_a_claimed_collision_blocks_when_other_modes_are_also_present():
    _enforce_color_vision_claims(_theme("protanopia"), (_collision("deuteranopia"),), ())

    with pytest.raises(RenderFailed) as captured:
        _enforce_color_vision_claims(
            _theme("protanopia"), (_collision("deuteranopia"), _collision("protanopia")), ())
    assert captured.value.details["vision"] == "protanopia"
    assert captured.value.details["claim"] == "protanopia"


def test_claimed_legend_pair_failure_keeps_exact_source_subjects():
    subjects = (DiagnosticSubject("/objects/ready", "Ready"),
                DiagnosticSubject("/objects/blocked", "Blocked"))
    provenance = (DiagnosticProvenance(
        "W_LEGEND_COLOR_NOT_SEPARABLE", subjects,
        ColorPairFinding("tritanopia", 4.999)),)

    with pytest.raises(RenderFailed) as captured:
        _enforce_color_vision_claims(_theme("tritanopia"), (), provenance)

    error = captured.value
    assert error.code == "E_LEGEND_COLOR_NOT_SEPARABLE"
    assert error.component == "presentation"
    assert error.source_ref == "/body/suitability/colorVision"
    assert error.details == {
        "vision": "tritanopia", "deltaE": 4.999, "minimumDeltaE": 5.0,
        "claim": "tritanopia",
        "sourceSubjects": [{"sourceRef": "/objects/ready", "title": "Ready"},
                           {"sourceRef": "/objects/blocked", "title": "Blocked"}],
    }


@pytest.mark.parametrize("carrier", ("scale", "legend"))
def test_typed_below_floor_finding_still_blocks_when_display_delta_rounds_to_floor(carrier):
    if carrier == "scale":
        finding = _collision("protanopia", 5.0)
        args = ((finding,), ())
    else:
        provenance = (DiagnosticProvenance(
            "W_LEGEND_COLOR_NOT_SEPARABLE",
            (DiagnosticSubject("/objects/a", "A"), DiagnosticSubject("/objects/b", "B")),
            ColorPairFinding("protanopia", 5.0)),)
        args = ((), provenance)

    with pytest.raises(RenderFailed) as captured:
        _enforce_color_vision_claims(_theme("protanopia"), *args)
    assert captured.value.details["deltaE"] == 5.0
    assert captured.value.details["minimumDeltaE"] == 5.0


def test_scale_producer_retains_raw_below_floor_value_that_rounds_to_floor_and_policy_blocks(monkeypatch):
    monkeypatch.setattr(color_separability, "delta_e_2000",
                        lambda _first, _second, *, vision: 4.9999999 if vision == "protanopia" else 8.0)
    collisions = color_separability.scale_collisions("near-floor", (("a", "#000000"), ("b", "#FFFFFF")))
    finding = next(item for item in collisions if item.vision == "protanopia")
    assert finding.delta_e == 4.9999999
    assert round(finding.delta_e, 3) == 5.0

    with pytest.raises(RenderFailed) as captured:
        _enforce_color_vision_claims(_theme("protanopia"), collisions, ())
    assert captured.value.code == "E_PRESENTATION_SCALE_NOT_SEPARABLE"
    assert captured.value.details["deltaE"] == 4.9999999


def test_unclaimed_wallboard_simulated_collisions_reach_real_warning_ledger(tmp_path):
    from datetime import date
    from tests.support import synthetic_review as sr
    from tests.integration.test_wallboard_dark_preset import ROOT
    import yaml

    scheme = yaml.safe_load((ROOT / "src/chrona/resources/presets/bundles/wallboard-dark/scheme.yaml").read_bytes())
    assert scheme["body"]["suitability"]["colorVision"] == ["none-claimed"]
    project = sr.project({
        f"task-{index}": sr.span(f"task-{index}", date(2026, 1, 1 + index * 3), 3, owner=value)
        for index, value in enumerate(("pm", "鈴木", "佐藤", "Lena"))
    })

    rendered = sr.render(tmp_path, project, presentation=sr.bundle("wallboard-dark"))

    records = [item.payload for item in rendered.warning_records
               if item.payload["code"] == "W_PRESENTATION_SCALE_NOT_SEPARABLE"]
    assert any(item["vision"] == "deuteranopia" and item["scaleId"] == "series"
               for item in records)
    assert all(item.payload["severity"] == "warning" for item in rendered.warning_records
               if item.payload["code"] == "W_PRESENTATION_SCALE_NOT_SEPARABLE")
    assert rendered.artifact.content


class _RendererSpy:
    def __init__(self):
        self.calls = 0

    def render(self, _surface):
        self.calls += 1
        raise AssertionError("renderer must not be called after a claimed color-vision failure")


def test_claim_failure_from_the_real_render_use_case_precedes_renderer_invocation(monkeypatch):
    """Exercise the real render order while injecting one typed finding at its policy seam."""
    from tests.unit.chrona.usecases.test_render_review import EXAMPLE

    original_enforce = render_usecase._enforce_color_vision_claims
    collision = _collision("deuteranopia")
    renderer = _RendererSpy()

    def enforce(theme, collisions, provenance):
        # Inject one finding at the real policy seam; the claim is present in
        # the resolved Theme passed through the normal render closure.
        assert "deuteranopia" in theme["body"]["colorVision"]
        return original_enforce(theme, (*collisions, collision), provenance)

    monkeypatch.setattr(render_usecase, "_enforce_color_vision_claims", enforce)
    with tempfile.TemporaryDirectory() as temporary:
        snapshot = Path(temporary) / "snapshot"
        snapshot.mkdir()
        reference, _ = _copy_context_closure(EXAMPLE.resolve(), slide_context(EXAMPLE, "programme-board"), snapshot)
        closure = resolve_render_context(
            reference, LocalSnapshotReader(snapshot, reference["store"]["identity"],
                                           require_content_identity=False))
        resolved_theme = dict(closure.resolved_theme.resolved_input)
        theme_body = dict(resolved_theme["body"])
        theme_body["colorVision"] = ("deuteranopia",)
        resolved_theme["body"] = theme_body
        closure = replace(closure, resolved_theme=replace(
            closure.resolved_theme, resolved_input=freeze(resolved_theme)))
        request = RenderRequest(closure, snapshot, ReferenceScheduler(), renderer)

        with pytest.raises(RenderFailed) as captured:
            render_review(request)

    assert captured.value.code == "E_PRESENTATION_SCALE_NOT_SEPARABLE"
    assert renderer.calls == 0


def test_real_planned_actual_legend_warning_becomes_claim_error_before_svg(monkeypatch, tmp_path):
    """A measured planned/actual key pair warns by default and enforces a Scheme claim."""
    from copy import deepcopy

    from chrona.presentation.renderers.v05_svg import V05SvgRenderer
    from tests.integration.test_realized_legends import ACTUAL, _detail, _parts, _render, _source

    parts = _parts()
    # This fixture is specifically a same-shape colour-separability proof.
    # The preset's Actual role has a rounded mark while Planned is square;
    # normalize their geometry so the CVD warning is attributable to colour.
    parts["theme"]["body"]["roles"]["actual"]["markCornerRadius"] = "mark-radius-square"
    scheme = parts["scheme"]["body"]
    scheme["colors"]["accent"] = "#8957E5"
    scheme["colors"]["positive"] = "#2F81F7"
    scheme["suitability"]["colorVision"] = ["none-claimed"]
    detail = _detail()

    warning_render = _render(tmp_path / "unclaimed", _source(), actual=ACTUAL,
                             parts=parts, detail=detail)
    warnings = [item.payload for item in warning_render.warning_records
                if item.payload["code"] == "W_LEGEND_COLOR_NOT_SEPARABLE"
                and item.payload["vision"] != "grayscale"]
    assert len(warnings) == 2
    assert {item["vision"] for item in warnings} == {"deuteranopia"}
    assert {item["diagnostic"] for item in warnings} == {
        "W_LEGEND_COLOR_NOT_SEPARABLE:deuteranopia:3.699",
    }
    warning_pairs = {
        frozenset(subject["title"] for subject in item["sourceSubjects"])
        for item in warnings
    }
    assert warning_pairs == {
        frozenset({"Planned (planned)", "On track (actual)"}),
        frozenset({"Planned · Milestone (planned)", "Actual · Milestone (actual)"}),
    }
    assert all(next(subject for subject in item["sourceSubjects"]
                    if subject["title"].startswith("Planned"))["sourceRef"].startswith(
                        "legend-key:planned") for item in warnings)
    assert all(any(subject["sourceRef"].startswith("legend-key:actual:")
                    for subject in item["sourceSubjects"]) for item in warnings)

    claimed_parts = deepcopy(parts)
    claimed_parts["scheme"]["body"]["suitability"]["colorVision"] = ["deuteranopia"]
    adapter_calls = []

    def fail_if_adapter_runs(_renderer, _surface):
        adapter_calls.append(True)
        raise AssertionError("claimed color-vision error must precede SVG rendering")

    monkeypatch.setattr(V05SvgRenderer, "render", fail_if_adapter_runs)
    with pytest.raises(RenderFailed) as captured:
        _render(tmp_path / "claimed", _source(), actual=ACTUAL,
                parts=claimed_parts, detail=detail)

    error = captured.value
    assert error.code == "E_LEGEND_COLOR_NOT_SEPARABLE"
    assert error.source_ref == "/body/suitability/colorVision"
    assert error.details["vision"] == error.details["claim"] == "deuteranopia"
    assert {item["title"] for item in error.details["sourceSubjects"]} == {
        "Planned (planned)", "On track (actual)"}
    assert adapter_calls == []
