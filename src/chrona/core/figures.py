"""Derived figures: a closed set of derivations over declared facts (#586).

A day figure is a signed whole number of days computed from dates the Project and the Actual Set already
state: the as-of, a named period's boundary, an object's placed endpoint, or an injected selected-group date.
Selection and group membership stay caller-owned. The set of facts and the set of
derivations are closed here; nothing is an expression and nothing reads a field by name. This module is
pure: the caller gathers the as-of, the placements, the resolved periods and the calendars and passes them
in, and a fact that cannot be read is a diagnostic naming the figure, the fact and what is declared, never
a blank, a zero or a guess.

Count figures select an immutable caller-gathered integer fact. Selection and observation-state
interpretation belong to View projection, not Core; an unavailable count is a diagnostic, not zero.

Conventions (Specification 05, "Derived figures"):

* ``daysUntil`` from ``a`` to ``b`` is ``b - a`` in calendar days (negative once the target has passed, 0 on
  the same day). In working days it is the number of working days ``d`` with ``a < d <= b`` (the days in
  ``(b, a]``, negated, when ``b`` is before ``a``). That is the scheduler's ``advance`` convention, which
  counts days strictly after its start, so ``daysUntil(d, advance(d, k wd)) == k``.
* ``daysIn`` a period is the days it covers: ``end - start`` in calendar days, the working days ``d`` with
  ``start <= d < end`` otherwise. ``end`` is exclusive, as everywhere a period is (Specification 05).
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from chrona.core.diagnostics import Diagnostic
from chrona.core.periods import ResolvedPeriod
from chrona.core.temporal import Calendar

KINDS = ("daysUntil", "daysIn", "count")
COUNT_SOURCES = ("selected", "recorded", "dueUnobserved", "notYetDue", "unavailable",
                 "missingActual", "knownFinishVariance", "behind", "ahead")
DAY_BASES = ("calendar", "working")
PERIOD_SIDES = ("start", "end", "last")
OBJECT_ENDPOINTS = ("at", "start", "end")


@dataclass(frozen=True)
class AsOfFact:
    """The Actual Set as-of date."""


@dataclass(frozen=True)
class PeriodFact:
    """A named period's start, exclusive end, or final covered calendar day."""

    period_id: str
    side: str


@dataclass(frozen=True)
class ObjectFact:
    """The placed (completed) date of one endpoint of a Project object."""

    object_id: str
    endpoint: str


@dataclass(frozen=True)
class GroupStartFact:
    """The caller-gathered first planned start/point in the current selected group."""


Fact = AsOfFact | PeriodFact | ObjectFact | GroupStartFact


@dataclass(frozen=True)
class FigureSpec:
    """One declared figure, already typed. ``path`` is the pointer diagnostics carry."""

    figure_id: str
    kind: str
    to: Fact | None = None
    origin: Fact = AsOfFact()
    period_id: str | None = None
    days: str = "calendar"
    calendar_id: str | None = None
    path: str = ""
    scope: str = "global"
    source: str | None = None


@dataclass(frozen=True)
class FigureCounts:
    """Immutable neutral count facts; the caller owns selection and state interpretation."""

    selected: int
    recorded: int
    due_unobserved: int
    not_yet_due: int
    unavailable: int
    missing_actual: int | None
    known_finish_variance: int
    behind: int
    ahead: int

    def value(self, source: str) -> int | None:
        values = (self.selected, self.recorded, self.due_unobserved, self.not_yet_due,
                  self.unavailable, self.missing_actual, self.known_finish_variance, self.behind, self.ahead)
        return dict(zip(COUNT_SOURCES, values, strict=True))[source]


@dataclass(frozen=True)
class FigureResolution:
    """Every figure that resolved, by id in declaration order, and every finding that stopped one."""

    values: Mapping[str, int]
    diagnostics: tuple[Diagnostic, ...]


def calendar_days_until(origin: date, target: date) -> int:
    """``target - origin`` in days: negative when the target has passed, 0 on the same day."""
    return (target - origin).days


def working_days_until(origin: date, target: date, calendar: Calendar) -> int:
    """The working days strictly after ``origin`` up to and including ``target``; negated when it is earlier."""
    if target >= origin:
        return _working_in(origin + timedelta(days=1), target + timedelta(days=1), calendar)
    return -_working_in(target + timedelta(days=1), origin + timedelta(days=1), calendar)


def working_days_in(start: date, end: date, calendar: Calendar) -> int:
    """The working days ``d`` with ``start <= d < end``; a range with none is 0."""
    return _working_in(start, end, calendar)


def _working_in(first: date, stop: date, calendar: Calendar) -> int:
    """Working days in ``[first, stop)``."""
    return sum(calendar.is_working(first + timedelta(days=offset)) for offset in range((stop - first).days))


def resolve_figures(specs: Sequence[FigureSpec], *, as_of: date | None,
                    placements: Mapping[str, Mapping[str, date]], periods: Sequence[ResolvedPeriod],
                    calendars: Mapping[str, Calendar], default_calendar: str | None,
                    group_first_start: date | None = None,
                    counts: FigureCounts | None = None) -> FigureResolution:
    """Resolve every declared figure; report every finding, not only the first.

    A figure with a finding yields no value, so a consumer can never read a made-up number for it; the
    caller refuses the render on any diagnostic.
    """
    declared = {item.period_id: item for item in periods}
    values: dict[str, int] = {}
    diagnostics: list[Diagnostic] = []
    for spec in specs:
        found: list[Diagnostic] = []
        if spec.kind == "count":
            if spec.source not in COUNT_SOURCES:
                raise TypeError(f"figure {spec.figure_id}: unknown count source {spec.source!r}")
            value = counts.value(spec.source) if counts is not None else None
            if value is None:
                diagnostics.append(Diagnostic(
                    "E_FIGURE_COUNT_UNAVAILABLE",
                    f"Figure {spec.figure_id} reads count {spec.source}, but that projected fact is unavailable",
                    f"{spec.path}/source", details={"figure": spec.figure_id, "source": spec.source}))
            else:
                values[spec.figure_id] = value
            continue
        resolve = _Reader(spec, as_of, placements, declared, found, group_first_start)
        calendar = _calendar(spec, calendars, default_calendar, found) if spec.days == "working" else None
        if spec.kind == "daysUntil":
            origin, target = resolve.read(spec.origin, "from"), resolve.read(spec.to, "to")
            if not found and origin is not None and target is not None:
                values[spec.figure_id] = (calendar_days_until(origin, target) if calendar is None
                                          else working_days_until(origin, target, calendar))
        elif spec.kind == "daysIn":
            period = declared.get(spec.period_id or "")
            if period is None:
                found.append(_period_unknown(spec, spec.period_id, declared, "/period"))
            elif not found:
                values[spec.figure_id] = ((period.end - period.start).days if calendar is None
                                          else working_days_in(period.start, period.end, calendar))
        else:
            raise TypeError(f"figure {spec.figure_id}: unknown kind {spec.kind!r}")
        diagnostics.extend(found)
    return FigureResolution(values, tuple(diagnostics))


class _Reader:
    """Reads one fact of one figure, appending a diagnostic when it cannot."""

    def __init__(self, spec: FigureSpec, as_of: date | None, placements: Mapping[str, Mapping[str, date]],
                 periods: Mapping[str, ResolvedPeriod], found: list[Diagnostic], group_first_start: date | None) -> None:
        self._spec, self._as_of, self._placements, self._periods, self._found = spec, as_of, placements, periods, found
        self._group_first_start = group_first_start

    def read(self, fact: Fact | None, where: str) -> date | None:
        spec = self._spec
        if isinstance(fact, GroupStartFact):
            if self._group_first_start is None:
                self._found.append(Diagnostic(
                    "E_FIGURE_GROUP_START_MISSING",
                    f"Figure {spec.figure_id} reads the current group's first planned start, but none is available",
                    f"{spec.path}/{where}/group", details={"figure": spec.figure_id}))
            return self._group_first_start
        if isinstance(fact, AsOfFact):
            if self._as_of is None:
                self._found.append(Diagnostic(
                    "E_FIGURE_ASOF_MISSING",
                    f"Figure {spec.figure_id} reads the as-of, but the Actual Set declares none",
                    f"{spec.path}/{where}", details={"figure": spec.figure_id}))
            return self._as_of
        if isinstance(fact, PeriodFact):
            period = self._periods.get(fact.period_id)
            if period is None:
                self._found.append(_period_unknown(spec, fact.period_id, self._periods, f"/{where}/period"))
                return None
            if fact.side == "start":
                return period.start
            if fact.side == "end":
                return period.end
            if fact.side == "last":
                return period.end - timedelta(days=1)
            raise TypeError(f"figure {spec.figure_id}: unknown period side {fact.side!r}")
        if isinstance(fact, ObjectFact):
            placement = self._placements.get(fact.object_id)
            if placement is None:
                self._found.append(Diagnostic(
                    "E_FIGURE_OBJECT_UNKNOWN",
                    f"Figure {spec.figure_id} reads object {fact.object_id}, which the Project does not place",
                    f"{spec.path}/{where}/object", details={"figure": spec.figure_id, "object": fact.object_id}))
                return None
            if fact.endpoint not in placement:
                offered = ", ".join(name for name in OBJECT_ENDPOINTS if name in placement)
                self._found.append(Diagnostic(
                    "E_FIGURE_ENDPOINT_UNAVAILABLE",
                    f"Figure {spec.figure_id}: endpoint {fact.endpoint} is unavailable on object {fact.object_id}; "
                    f"its schedule offers {offered}",
                    f"{spec.path}/{where}/endpoint",
                    details={"figure": spec.figure_id, "object": fact.object_id, "offered": offered}))
                return None
            return placement[fact.endpoint]
        raise TypeError(f"figure {spec.figure_id}: {where} is not a fact")


def _period_unknown(spec: FigureSpec, period_id: str | None, declared: Mapping[str, ResolvedPeriod],
                    suffix: str) -> Diagnostic:
    known = ", ".join(declared) if declared else "none"
    return Diagnostic(
        "E_FIGURE_PERIOD_UNKNOWN",
        f"Figure {spec.figure_id} reads period {period_id}, which the Project does not declare (declared: {known})",
        f"{spec.path}{suffix}", details={"figure": spec.figure_id, "period": period_id, "declared": known})


def _calendar(spec: FigureSpec, calendars: Mapping[str, Calendar], default_calendar: str | None,
              found: list[Diagnostic]) -> Calendar | None:
    calendar_id = spec.calendar_id or default_calendar
    if calendar_id is not None and calendar_id in calendars:
        return calendars[calendar_id]
    known = ", ".join(calendars) if calendars else "none"
    reason = (f"calendar {calendar_id} is not declared" if calendar_id is not None
              else "the Project declares no default calendar and the figure names none")
    found.append(Diagnostic(
        "E_FIGURE_CALENDAR_UNAVAILABLE",
        f"Figure {spec.figure_id} counts working days, but {reason} (declared: {known})",
        f"{spec.path}/calendar", details={"figure": spec.figure_id, "calendar": calendar_id, "declared": known}))
    return None
