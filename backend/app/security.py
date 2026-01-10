"""
Utilities for redacting sensitive data in logs and errors.
"""
from __future__ import annotations

import re
from typing import Iterable

_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{10,}"),
]


def mask_value(value: str) -> str:
    if not value:
        return value
    if len(value) <= 4:
        return "****"
    return f"{value[:2]}****{value[-2:]}"


def sanitize_message(message: str, secrets: Iterable[str] | None = None) -> str:
    sanitized = message
    for pattern in _SECRET_PATTERNS:
        sanitized = pattern.sub("sk-****", sanitized)
    if secrets:
        for secret in secrets:
            if secret:
                sanitized = sanitized.replace(secret, mask_value(secret))
    return sanitized

