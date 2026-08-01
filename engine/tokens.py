"""Completion tokens: tamper-resistant proof that a level was really cleared.

When a level's checker passes, the engine writes a token into the profile:
an HMAC of (player_id, level_id) keyed by the profile's per-player secret.
Because the secret is random per profile and never displayed, a player can't
hand-craft a token to unlock a level they haven't solved -- which is exactly
enough anti-cheat for a local, single-player teaching game.

progression.py refuses to enter a level unless every prerequisite has a token
that re-verifies against the secret.
"""

from __future__ import annotations

import hashlib
import hmac


def make_token(secret: str, player_id: str, level_id: str) -> str:
    """Return the HMAC-SHA256 token for (player_id, level_id) under `secret`."""
    msg = f"{player_id}|{level_id}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def verify_token(secret: str, player_id: str, level_id: str, token: str) -> bool:
    """Constant-time check that `token` is valid for (player_id, level_id)."""
    if not token:
        return False
    expected = make_token(secret, player_id, level_id)
    return hmac.compare_digest(expected, token)
