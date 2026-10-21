"""Band and fill roles a Scene draws that the drawn legend does not key (#1870 row 2)."""
from __future__ import annotations

from collections.abc import Iterable

# Drawn Scene purpose -> the legend role that keys it.
KEYABLE_BAND_AND_FILL_ROLES = {
    "calendar-closed": "calendar-closed",
    "calendar-exception": "calendar-exception",
    "progress-fill": "progressFill",
}


def unkeyed_band_and_fill_roles(primitives: Iterable[object], opted_out: Iterable[str] = ()) -> tuple[tuple[str, str], ...]:
    """(drawn purpose, legend role) pairs the Scene draws, with a legend drawn, and no legend key names.

    A Scene without any legend label has no legend to key against; an author's `unkeyedLegendRoles`
    entry is an explicit choice. Both stay silent.
    """
    drawn: set[str] = set()
    keyed: set[str] = set()
    legend_drawn = False
    for primitive in primitives:
        purpose = getattr(primitive, "purpose", None)
        if purpose == "legend-label":
            legend_drawn = True
            keyed.add(str(getattr(primitive, "source_ref", "")).split(":", 1)[0])
        elif purpose in KEYABLE_BAND_AND_FILL_ROLES:
            drawn.add(purpose)
    if not legend_drawn:
        return ()
    skipped = set(opted_out)
    return tuple((purpose, role) for purpose, role in KEYABLE_BAND_AND_FILL_ROLES.items()
                 if purpose in drawn and role not in keyed and role not in skipped and purpose not in skipped)
