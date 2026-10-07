"""#1150: a label chip is the text block plus its padding, or `chipMinBlockSize` when that is larger.

Synthetic Project through the packaged `executive-light` bundle; the period label's chip stands for the shared
chip rule (member, as-of and finish-delta chips use the same padding helper). No `examples/` input.
"""
from __future__ import annotations

from datetime import date

import pytest

from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr

WINDOW = {"mode": "explicit", "start": "2026-01-01", "end": "2026-04-01"}


def _parts(*, padding: float = 0.5, minimum: float | None = None) -> dict:
    parts = sr.bundle("executive-light")
    body = parts["theme"]["body"]
    body["roles"]["period-label"] = {key: value for key, value in body["roles"]["annotation-note-text"].items()
                                     if key != "contrastTreatment"} | {"contrastTreatment": "required"}
    body["colorBindings"]["period-label.fill"] = "text"
    body["values"]["period-chip-padding"] = {"type": "number", "value": padding}
    role = {"backgroundTreatment": "fill", "chipPadding": "period-chip-padding"}
    if minimum is not None:
        body["values"]["period-chip-min-block"] = {"type": "number", "value": minimum}
        role["chipMinBlockSize"] = "period-chip-min-block"
    body["roles"]["period-label-chip"] = role
    body["colorBindings"]["period-label-chip.fill"] = "surfaceRaised"
    parts["view"]["body"]["window"] = dict(WINDOW)
    parts["view"]["body"]["periods"] = [{"id": "window", "label": {"placement": "top"}}]
    return parts


def _render(tmp_path, name: str, parts: dict):
    directory = tmp_path / name
    directory.mkdir()
    source = sr.project({"a": sr.span("a", date(2026, 1, 5), 40)})
    source["periods"] = {"window": {"start": "2026-02-01", "end": "2026-03-01"}}
    return sr.render(directory, source, presentation=parts)


def _chip_and_label(rendered):
    chip = next(item for item in rendered.surface.primitives if item.scene_id == "chip:period-label:window")
    label = next(item for item in rendered.surface.primitives if item.scene_id == "period-label:window")
    return chip.bounds, label.bounds


def test_a_chip_without_a_minimum_is_the_text_block_plus_its_padding(tmp_path):
    chip, label = _chip_and_label(_render(tmp_path, "plain", _parts()))

    assert chip[3] == pytest.approx(label[3] + 2 * (label[1] - chip[1]))


def test_a_taller_minimum_grows_the_chip_equally_above_and_below_the_text(tmp_path):
    plain_chip, label = _chip_and_label(_render(tmp_path, "plain", _parts()))
    chip, grown_label = _chip_and_label(_render(tmp_path, "tall", _parts(minimum=40)))

    assert chip[3] == pytest.approx(40)
    assert grown_label[3] == pytest.approx(label[3])
    assert (grown_label[1] - chip[1]) == pytest.approx((chip[1] + chip[3]) - (grown_label[1] + grown_label[3]))
    assert chip[2] == pytest.approx(plain_chip[2])


def test_a_minimum_below_the_natural_height_changes_nothing(tmp_path):
    plain = _chip_and_label(_render(tmp_path, "plain", _parts()))
    small = _chip_and_label(_render(tmp_path, "small", _parts(minimum=4)))

    assert small == plain


def test_a_minimum_that_is_not_positive_is_a_token_diagnostic(tmp_path):
    with pytest.raises(RenderFailed) as error:
        _render(tmp_path, "zero", _parts(minimum=0))

    assert error.value.code in {"E_THEME_TOKEN_TYPE", "E_LAYOUT_TOKEN_TYPE"}
