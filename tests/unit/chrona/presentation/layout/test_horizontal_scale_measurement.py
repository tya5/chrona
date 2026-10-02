"""#585 I585-1: the measured horizontal compression at the Layout and Theme boundaries."""
from decimal import Decimal

import pytest

from chrona.presentation.color_scheme import ColorSchemeError, _horizontal_scales, _writing_modes
from chrona.presentation.layout.text import (
    ScaledMetric, ellipsize_text, measure_text_width, metric_for_family, metric_for_role, place_text, scaled_metric,
    wrap_text,
)
from chrona.presentation.model.theme_tokens import (
    HORIZONTAL_SCALE_CEILING, HORIZONTAL_SCALE_FLOOR, TextTreatment, ThemeTokenError, ThemeTokenView,
    checked_horizontal_scale,
)
from chrona.presentation.scene.model import TextLayout


class _Font:
    content_identity = "sha256:test"
    ascent = 900

    def width(self, content, size, letter_spacing=0, numeric_spacing="proportional"):
        return len(content) * size / 2 + max(0, len(content) - 1) * letter_spacing

    def ensure_numeric_spacing(self, _spacing):
        return None


class _Catalog:
    def __init__(self):
        self.font = _Font()

    def select(self, _family, _weight):
        return self.font


def _theme(scale):
    class Theme:
        def text_treatment(self, _role):
            return TextTreatment("Test Sans", 400, 12, Decimal("1.5"), Decimal("0.25"), "none", "proportional", scale)
    return Theme()


def test_scale_one_returns_the_very_same_metric_object():
    font = _Font()
    assert scaled_metric(font, 1) is font and scaled_metric(font, Decimal(1)) is font
    assert metric_for_family("Test Sans", 400, _Catalog()).__class__ is _Font


def test_a_scaled_metric_multiplies_the_whole_run_including_letter_spacing():
    metric = scaled_metric(_Font(), Decimal("0.6"))
    assert isinstance(metric, ScaledMetric)
    natural = measure_text_width("ABCD", font_size=12, font_metrics=_Font(), letter_spacing=3)
    assert natural == 4 * 6 + 3 * 3
    assert measure_text_width("ABCD", font_size=12, font_metrics=metric, letter_spacing=3) == pytest.approx(natural * 0.6)
    assert metric.content_identity == "sha256:test" and metric.ascent == 900  # everything else is the face's
    assert hasattr(metric, "ensure_numeric_spacing")


def test_a_scale_is_applied_once_never_stacked():
    inner = scaled_metric(_Font(), Decimal("0.5"))
    again = scaled_metric(inner, Decimal("0.5"))
    assert again.base.__class__ is _Font and again.scale == 0.5
    assert metric_for_family("Test Sans", 400, inner, Decimal("0.8")).scale == 0.8
    assert scaled_metric(inner, 1).__class__ is _Font


def test_metric_for_role_reads_the_role_scale():
    scaled = metric_for_role(_theme(Decimal("0.7")), "text", _Catalog())
    assert isinstance(scaled, ScaledMetric) and scaled.scale == 0.7
    assert metric_for_role(_theme(Decimal(1)), "text", _Catalog()).__class__ is _Font


def test_place_text_places_the_compressed_width_and_records_the_factor():
    natural = place_text(placement_id="a", source_ref="a", content="ABCD", inline=10, baseline_block=30,
                         typography_role="text", theme_tokens=_theme(Decimal(1)), font_metrics=_Catalog())
    squeezed = place_text(placement_id="a", source_ref="a", content="ABCD", inline=10, baseline_block=30,
                          typography_role="text", theme_tokens=_theme(Decimal("0.6")), font_metrics=_Catalog())
    assert natural.horizontal_scale == 1.0 and squeezed.horizontal_scale == 0.6
    assert float(squeezed.bounds.inline_size) == pytest.approx(float(natural.bounds.inline_size) * 0.6)
    assert squeezed.bounds.block_size == natural.bounds.block_size and squeezed.bounds.inline == natural.bounds.inline
    assert squeezed.letter_spacing == natural.letter_spacing  # the painted spacing; the transform scales it


def test_a_rotated_run_is_compressed_along_its_own_axis():
    clockwise = place_text(placement_id="a", source_ref="a", content="ABCD", inline=10, baseline_block=30,
                           typography_role="text", theme_tokens=_theme(Decimal("0.5")), font_metrics=_Catalog(),
                           orientation="rotate-cw")
    natural = place_text(placement_id="a", source_ref="a", content="ABCD", inline=10, baseline_block=30,
                         typography_role="text", theme_tokens=_theme(Decimal(1)), font_metrics=_Catalog(),
                         orientation="rotate-cw")
    assert float(clockwise.bounds.block_size) == pytest.approx(float(natural.bounds.block_size) * 0.5)  # the run's length
    assert clockwise.bounds.inline_size == natural.bounds.inline_size  # its line box is untouched


def test_wrap_and_ellipsis_decide_on_the_compressed_width():
    content = "alpha beta gamma delta"
    plain, squeezed = _Font(), scaled_metric(_Font(), Decimal("0.5"))
    assert len(wrap_text(content, available_inline=60, font_size=10, font_metrics=plain)) > len(
        wrap_text(content, available_inline=60, font_size=10, font_metrics=squeezed))
    assert ellipsize_text(content, available_inline=80, font_size=10, font_metrics=plain).endswith("…")
    assert ellipsize_text(content, available_inline=80, font_size=10, font_metrics=squeezed) == content


def test_the_range_is_a_closed_compression_only_interval():
    assert (HORIZONTAL_SCALE_FLOOR, HORIZONTAL_SCALE_CEILING) == (Decimal("0.5"), Decimal(1))
    for accepted in ("0.5", "0.6", "1"):
        assert checked_horizontal_scale(Decimal(accepted), "/p") == Decimal(accepted)
    for rejected in ("0.49", "0", "-1", "1.01", "NaN", "Infinity"):
        with pytest.raises(ThemeTokenError) as failure:
            checked_horizontal_scale(Decimal(rejected), "/body/roles/heading/horizontalScale")
        assert failure.value.diagnostic_id == "E_THEME_TEXT_SCALE_RANGE"
        assert failure.value.path == "/body/roles/heading/horizontalScale"


def _view(role, scale="0.7"):
    values = {"family": {"type": "fontFamily", "value": "Test Sans"}, "weight": {"type": "fontWeight", "value": 400},
              "size": {"type": "number", "value": 12}, "line": {"type": "number", "value": 1.5},
              "ls": {"type": "number", "value": 0}, "tr": {"type": "textTransform", "value": "none"},
              "num": {"type": "numericSpacing", "value": "proportional"},
              "scale": {"type": "number", "value": scale}, "word": {"type": "textTransform", "value": "none"}}
    base = {"fontFamily": "family", "fontWeight": "weight", "fontSize": "size", "lineHeight": "line",
            "letterSpacing": "ls", "textTransform": "tr", "numericSpacing": "num"}
    return ThemeTokenView({"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme",
                           "body": {"values": values, "roles": {"r": {**base, **role}}}})


def test_text_treatment_reads_the_declared_scale_and_defaults_to_one():
    assert _view({}).text_treatment("r").horizontal_scale == Decimal(1)
    assert _view({"horizontalScale": "scale"}).text_treatment("r").horizontal_scale == Decimal("0.7")
    with pytest.raises(ThemeTokenError) as failure:
        _view({"horizontalScale": "word"}).text_treatment("r")
    assert failure.value.diagnostic_id == "E_THEME_TOKEN_TYPE"
    assert failure.value.path == "/body/roles/r/horizontalScale"


def test_text_treatment_rejects_an_out_of_range_scale_at_its_pointer():
    with pytest.raises(ThemeTokenError) as failure:
        _view({"horizontalScale": "scale"}, scale="0.3").text_treatment("r")
    assert (failure.value.diagnostic_id, failure.value.path) == ("E_THEME_TEXT_SCALE_RANGE", "/body/roles/r/horizontalScale")


def test_theme_resolution_checks_every_declared_role_used_or_not():
    roles = {"unused": {"horizontalScale": "s"}}
    _horizontal_scales(declared_roles=roles, values={"s": {"type": "number", "value": 0.5}})
    with pytest.raises(ColorSchemeError) as failure:
        _horizontal_scales(declared_roles=roles, values={"s": {"type": "number", "value": 0.25}})
    assert failure.value.diagnostic_id == "E_THEME_TEXT_SCALE_RANGE"
    assert failure.value.source_ref == "/body/roles/unused/horizontalScale" and failure.value.detail == "0.25"
    with pytest.raises(ColorSchemeError) as failure:
        _horizontal_scales(declared_roles=roles, values={"s": {"type": "textTransform", "value": "none"}})
    assert failure.value.diagnostic_id == "E_THEME_TOKEN_TYPE"


def _layout(scale, **kwargs):
    return TextLayout((0.0, 0.0, 10.0, 12.0), (0.0, 12.0), ("a",), "F", 400, 12.0, 1.2, "sha256:x",
                      horizontal_scale=scale, **kwargs)


def test_the_scene_text_layout_only_admits_the_declared_range():
    assert _layout(1.0).horizontal_scale == 1.0 and _layout(0.5).horizontal_scale == 0.5
    for bad in (0.49, 1.01, True, "0.6", float("nan")):
        with pytest.raises(ValueError, match="E_PRESENTATION_TEXT_LAYOUT_INVALID"):
            _layout(bad)


def test_theme_resolution_rejects_a_scale_on_a_vertical_role_and_a_bad_writing_mode():
    values = {"v": {"type": "writingMode", "value": "vertical"}, "h": {"type": "writingMode", "value": "horizontal"},
              "s": {"type": "number", "value": 0.8}, "one": {"type": "number", "value": 1}}
    _writing_modes(declared_roles={"r": {"writingMode": "v"}}, values=values)
    _writing_modes(declared_roles={"r": {"writingMode": "h", "horizontalScale": "s"}}, values=values)
    _writing_modes(declared_roles={"r": {"writingMode": "v", "horizontalScale": "one"}}, values=values)
    with pytest.raises(ColorSchemeError) as failure:
        _writing_modes(declared_roles={"r": {"writingMode": "v", "horizontalScale": "s"}}, values=values)
    assert (failure.value.diagnostic_id, failure.value.source_ref) == (
        "E_THEME_TEXT_TREATMENT_CONFLICT", "/body/roles/r/horizontalScale")
    for bad in ({"type": "writingMode", "value": "diagonal"}, {"type": "textTransform", "value": "vertical"}):
        with pytest.raises(ColorSchemeError) as failure:
            _writing_modes(declared_roles={"r": {"writingMode": "bad"}}, values={"bad": bad})
        assert failure.value.diagnostic_id == "E_THEME_TOKEN_TYPE"
