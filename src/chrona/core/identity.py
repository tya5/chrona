"""Canonical content identity shared across application and persistence layers."""
from __future__ import annotations

from datetime import date
from hashlib import sha256
import json
from typing import Any, Mapping


def json_value(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_value(item) for item in value]
    return value


def canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(json_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def content_identity(value: Mapping[str, Any]) -> str:
    return "sha256:" + sha256(canonical_bytes(value)).hexdigest()
