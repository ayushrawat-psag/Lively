"""Family invite code generation.

Supports ENV-driven formats:
- alphanumeric: collision-friendly alphabet excluding 0/O and 1/I/L
- numeric: zero-padded decimal digits

Callers should enforce uniqueness at the DB layer and retry on rare collisions.
Existing stored codes remain valid regardless of the current format setting.
"""

from __future__ import annotations

import secrets

from app.core.config import get_settings

INVITE_CODE_LENGTH = 6
# Excludes 0, O, 1, I, L for readability when typing/sharing codes.
INVITE_CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def generate_invite_code(
    *,
    format: str | None = None,
    length: int | None = None,
) -> str:
    settings = get_settings()
    fmt = (format or settings.invite_code_format).lower()
    n = length if length is not None else settings.invite_code_length

    if fmt == "numeric":
        return str(secrets.randbelow(10**n)).zfill(n)

    return "".join(secrets.choice(INVITE_CODE_ALPHABET) for _ in range(n))
