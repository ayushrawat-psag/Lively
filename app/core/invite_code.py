"""Family invite code generation.

Uses a collision-friendly alphabet that excludes visually confusing characters
(0/O, 1/I/L). Callers should enforce uniqueness at the DB layer and retry on
rare collisions.
"""

from __future__ import annotations

import secrets

INVITE_CODE_LENGTH = 6
# Excludes 0, O, 1, I, L for readability when typing/sharing codes.
INVITE_CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def generate_invite_code(*, length: int = INVITE_CODE_LENGTH) -> str:
    return "".join(secrets.choice(INVITE_CODE_ALPHABET) for _ in range(length))
