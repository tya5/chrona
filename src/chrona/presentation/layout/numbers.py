"""Exact scalar values and explicit numeric boundary conversions for Layout."""
from __future__ import annotations

from decimal import Decimal
from fractions import Fraction
import math
from typing import Any


class NumericConversionError(ValueError):
    """A finite native Layout number cannot be represented at an output boundary."""


def _supported(value: Any) -> bool:
    return isinstance(value, (LayoutNumber, Fraction, Decimal, int)) and not isinstance(value, bool)


class LayoutNumber(Fraction):
    """Immutable exact rational scalar; floats enter and leave only explicitly."""

    __slots__ = ()

    def __new__(cls, numerator: Any = 0, denominator: Any = None) -> "LayoutNumber":
        if not _supported(numerator):
            raise TypeError(f"LayoutNumber requires int, finite Decimal, or Fraction; got {type(numerator).__name__}")
        if isinstance(numerator, Decimal) and not numerator.is_finite():
            raise ValueError("LayoutNumber requires a finite Decimal")
        if denominator is not None:
            if not isinstance(numerator, int) or isinstance(numerator, bool):
                raise TypeError("two-argument LayoutNumber construction requires integer numerator and denominator")
            if not isinstance(denominator, int) or isinstance(denominator, bool):
                raise TypeError("LayoutNumber denominator must be an integer")
        value = super().__new__(cls, numerator, denominator) if denominator is not None else super().__new__(cls, numerator)
        return value

    @staticmethod
    def _operand(value: Any) -> Fraction:
        if not _supported(value):
            raise TypeError(f"unsupported LayoutNumber operand: {type(value).__name__}")
        if isinstance(value, Decimal) and not value.is_finite():
            raise ValueError("LayoutNumber arithmetic requires finite Decimal operands")
        return Fraction(value)

    def __add__(self, other: Any) -> Any:
        value = self._operand(other)
        return LayoutNumber(Fraction(self) + value)

    def __radd__(self, other: Any) -> Any:
        return self.__add__(other)

    def __sub__(self, other: Any) -> Any:
        value = self._operand(other)
        return LayoutNumber(Fraction(self) - value)

    def __rsub__(self, other: Any) -> Any:
        value = self._operand(other)
        return LayoutNumber(value - Fraction(self))

    def __mul__(self, other: Any) -> Any:
        value = self._operand(other)
        return LayoutNumber(Fraction(self) * value)

    def __rmul__(self, other: Any) -> Any:
        return self.__mul__(other)

    def __truediv__(self, other: Any) -> Any:
        value = self._operand(other)
        return LayoutNumber(Fraction(self) / value)

    def __rtruediv__(self, other: Any) -> Any:
        value = self._operand(other)
        return LayoutNumber(value / Fraction(self))

    def __pos__(self) -> "LayoutNumber":
        return self

    def __neg__(self) -> "LayoutNumber":
        return LayoutNumber(-Fraction(self))

    def __abs__(self) -> "LayoutNumber":
        return LayoutNumber(abs(Fraction(self)))

    def ceil(self) -> int:
        """Return the exact mathematical ceiling without Decimal context use."""
        return -((-self.numerator) // self.denominator)

    def to_float(self) -> float:
        """Project to a finite binary float, rejecting overflow and infinities."""
        return float(self)

    def __float__(self) -> float:
        """Make every explicit float conversion obey the typed finite-output boundary."""
        try:
            result = Fraction.__float__(self)
        except OverflowError as error:
            raise NumericConversionError("Layout number exceeds finite float range") from error
        if not math.isfinite(result):
            raise NumericConversionError("Layout number does not convert to a finite float")
        return result

    def format_decimal(self, precision: int = 3) -> str:
        """Format fixed decimal places with exact, context-independent half-even rounding."""
        if isinstance(precision, bool) or not isinstance(precision, int):
            raise ValueError("precision must be an integer")
        if precision >= 0:
            numerator = abs(self.numerator) * 10 ** precision
            denominator = self.denominator
        else:
            numerator = abs(self.numerator)
            denominator = self.denominator * 10 ** -precision
        magnitude, remainder = divmod(numerator, denominator)
        doubled = remainder * 2
        if doubled > denominator or (doubled == denominator and magnitude % 2):
            magnitude += 1
        sign = "-" if self.numerator < 0 else ""
        try:
            if precision <= 0:
                rounded = magnitude * (10 ** -precision)
                return sign + str(rounded)
            scale = 10 ** precision
            whole, fractional = divmod(magnitude, scale)
            return f"{sign}{whole}.{fractional:0{precision}d}"
        except ValueError as error:
            raise NumericConversionError("Formatted Layout number exceeds Python's decimal digit limit") from error


def from_source_float(value: float) -> LayoutNumber:
    """Admit a source float by its written decimal value, never its binary ratio."""
    if isinstance(value, bool) or not isinstance(value, float) or not math.isfinite(value):
        raise TypeError("source float must be a finite float (not bool)")
    return LayoutNumber(Decimal(str(value)))

