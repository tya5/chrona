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
    # The offending node's position in a YAML input: {line, column, endLine, endColumn} (#1303); not part of equality.
    source_range: Mapping[str, int] | None = field(default=None, kw_only=True, compare=False, hash=False)

    def as_dict(self) -> dict[str, Any]:
        record = {key: value for key, value in asdict(self).items() if value is not None and key != "source_range"}
        if self.source_range is not None:
            record["sourceRange"] = dict(self.source_range)
        return record
