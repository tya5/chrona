"""Closed, pure count text forms; no selection, Layout or Core formatting."""
from __future__ import annotations

from dataclasses import dataclass

from chrona.presentation.number_names import kanji_number

COUNT_TEXT_FORMS = ("digits", "english-words", "kanji", "kanji-formal")
_SMALL = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
          "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
          "seventeen", "eighteen", "nineteen")
_TENS = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")
_SCALES = ("", "thousand", "million", "billion", "trillion", "quadrillion", "quintillion")


class CountTextError(ValueError):
    """A typed declaration/value/name-range error, without a fallback form."""
    def __init__(self, code: str, detail: str, *, value: int | None = None,
                 form: str | None = None, supported_range: tuple[int, int] | None = None):
        super().__init__(f"{code}:{detail}")
        self.code, self.detail = code, detail
        self.value, self.form, self.supported_range = value, form, supported_range


@dataclass(frozen=True)
class CountTextFormat:
    form: str = "digits"
    minimum_digits: int = 1
    capitalize: bool = False

    def __post_init__(self):
        if (self.form not in COUNT_TEXT_FORMS or not isinstance(self.capitalize, bool)
                or isinstance(self.minimum_digits, bool) or not isinstance(self.minimum_digits, int)
                or not 1 <= self.minimum_digits <= 80
                or (self.form != "digits" and self.minimum_digits != 1)
                or (self.form != "english-words" and self.capitalize)):
            raise CountTextError("E_VIEW_FIGURE_FORMAT_INVALID", "invalid count text form/options")


def _under_thousand(value: int) -> str:
    parts = []
    hundreds, remainder = divmod(value, 100)
    if hundreds:
        parts.append(_SMALL[hundreds] + " hundred")
    if remainder:
        if remainder < 20:
            parts.append(_SMALL[remainder])
        else:
            tens, ones = divmod(remainder, 10)
            parts.append(_TENS[tens] + ("-" + _SMALL[ones] if ones else ""))
    return " ".join(parts)


def _english(value: int) -> str:
    if value == 0:
        return _SMALL[0]
    groups = []
    for scale in _SCALES:
        value, group = divmod(value, 1000)
        if group:
            groups.append(_under_thousand(group) + (" " + scale if scale else ""))
    return " ".join(reversed(groups))


def format_count(value: int, text_format: CountTextFormat = CountTextFormat()) -> str:
    """Format a neutral integer only when a text consumer requests its names."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CountTextError("E_VIEW_FIGURE_FORMAT_INVALID", f"count must be a nonnegative integer, got {value!r}")
    form = text_format.form
    if form == "digits":
        return str(value).zfill(text_format.minimum_digits)
    high = 10**21 - 1 if form == "english-words" else 99
    if value > high:
        raise CountTextError("E_VIEW_FIGURE_FORMAT_RANGE",
            f"value={value}; form={form}; range=0..{high}",
            value=value, form=form, supported_range=(0, high))
    if form == "english-words":
        text = _english(value)
        return text.capitalize() if text_format.capitalize else text
    return kanji_number(value, formal=form == "kanji-formal")
