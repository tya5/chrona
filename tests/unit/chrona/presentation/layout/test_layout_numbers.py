from decimal import Decimal, ROUND_UP, localcontext
from fractions import Fraction

import pytest

from chrona.presentation.layout.numbers import LayoutNumber, NumericConversionError, from_source_float


def test_exact_operations_are_closed_and_keep_large_translated_local_offsets():
    origin = LayoutNumber(10**20) / 3
    local = LayoutNumber(1, 7) + Decimal("0.125")
    translated = origin + local

    assert isinstance(origin, LayoutNumber)
    assert isinstance(local, LayoutNumber)
    assert isinstance(translated, LayoutNumber)
    assert translated - origin == local
    assert LayoutNumber(1, 3) == LayoutNumber(2, 6)
    assert LayoutNumber(1, 3) + Fraction(2, 3) == 1
    huge_origin = LayoutNumber(10**30) / 3
    huge_translated = huge_origin + 1000 + LayoutNumber(1, 3)
    assert huge_translated - huge_origin == LayoutNumber(3001, 3)
    assert isinstance(+origin, LayoutNumber)


def test_reflected_arithmetic_and_decimal_comparisons_are_exact():
    third = LayoutNumber(1, 3)
    assert Decimal("0.5") + third == LayoutNumber(5, 6)
    assert Decimal("0.5") - third == LayoutNumber(1, 6)
    assert Decimal("0.5") * third == LayoutNumber(1, 6)
    assert Decimal("0.5") / third == LayoutNumber(3, 2)
    assert LayoutNumber(1, 10) == Decimal("0.1")
    assert LayoutNumber(1, 10) < Decimal("0.1000000000000000000000000001")
    assert LayoutNumber(1, 3) < Decimal("0.3333333333333333333333333334")
    assert LayoutNumber(1, 10).ceil() == 1
    assert LayoutNumber(-11, 10).ceil() == -1


def test_source_float_uses_its_decimal_spelling_and_rejects_invalid_sources():
    assert from_source_float(0.1) == Decimal("0.1")
    for value in (True, float("nan"), float("inf"), 1):
        with pytest.raises(TypeError):
            from_source_float(value)  # type: ignore[arg-type]
    for value in (True, 0.1, "1/3", Decimal("NaN"), Decimal("Infinity")):
        with pytest.raises((TypeError, ValueError)):
            LayoutNumber(value)


def test_float_arithmetic_is_not_implicitly_admitted():
    value = LayoutNumber(1, 3)
    with pytest.raises(TypeError):
        _ = value + 0.1
    with pytest.raises(TypeError):
        _ = 0.1 + value


@pytest.mark.parametrize(("value", "precision", "expected"), [
    (Fraction(1, 8), 2, "0.12"),
    (Fraction(3, 8), 2, "0.38"),
    (Fraction(-1, 8), 2, "-0.12"),
    (Fraction(-3, 8), 2, "-0.38"),
    (Fraction(1, 2), 0, "0"),
    (Fraction(-1, 2), 0, "-0"),
    (Fraction(149, 1), -2, "100"),
    (Fraction(150, 1), -2, "200"),
    (Fraction(250, 1), -2, "200"),
    (Fraction(-150, 1), -2, "-200"),
    (Fraction(123456789012345678901, 1), 3, "123456789012345678901.000"),
])
def test_decimal_formatter_rounds_exactly_with_signed_half_even(value, precision, expected):
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_UP
        assert LayoutNumber(value).format_decimal(precision) == expected


def test_float_projection_rejects_overflow_and_precision_is_validated():
    assert LayoutNumber(1, 2).to_float() == 0.5
    with pytest.raises(NumericConversionError):
        LayoutNumber(10**10000).to_float()
    with pytest.raises(NumericConversionError):
        float(LayoutNumber(10**10000))
    with pytest.raises(ValueError):
        LayoutNumber(1, 3).format_decimal(True)
    with pytest.raises(ValueError):
        LayoutNumber(1, 3).format_decimal(1.5)  # type: ignore[arg-type]


def test_division_by_zero_preserves_fraction_semantics_and_huge_format_is_typed():
    with pytest.raises(ZeroDivisionError):
        LayoutNumber(1, 3) / 0
    with pytest.raises(NumericConversionError):
        LayoutNumber(10**5000).format_decimal(0)
