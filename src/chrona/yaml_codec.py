"""Safe YAML decoding shared by production ingress boundaries."""
from __future__ import annotations

from typing import Any

import yaml


_SAFE_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def safe_load(source: Any) -> Any:
    """Decode YAML with libyaml when available, without widening safe YAML."""
    return yaml.load(source, Loader=_SAFE_LOADER)
