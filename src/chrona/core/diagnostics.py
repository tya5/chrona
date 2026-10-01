from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class Diagnostic:
    """A stable Core diagnostic identifier with optional implementation detail.

    ``details`` is an optional machine-readable object for the few codes that
    document one (for example ``E_FIXED_TARGET_VIOLATION``). It is keyword-only
    so a subclass that adds positional fields keeps its constructor, and it is
    left out of equality and hashing: two diagnostics are the same finding when
    their identifier, message and pointer agree.
    """

    id: str
    message: str
    path: str | None = None
    details: Mapping[str, Any] | None = field(default=None, kw_only=True, compare=False, hash=False)

    def as_dict(self) -> dict[str, Any]:
        return {key: value for key, value in asdict(self).items() if value is not None}
