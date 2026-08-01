"""Progression: the gating brain.

Decides which levels are locked/unlocked/cleared, using signed completion
tokens verified against the profile secret. A level is unlocked only when every
prerequisite has a valid token. Completing a level writes its token; clearing
every level in a tier earns that tier's badge.

All state lives in the Profile (tokens dict), so progression survives restarts
and can't be advanced by editing the save file without knowing the secret.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from engine.level import Campaign, Level
from engine.profile import Profile
from engine.tokens import make_token, verify_token


class LevelStatus(str, Enum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    CLEARED = "cleared"


@dataclass
class Progression:
    campaign: Campaign
    profile: Profile

    # -- token-backed queries ------------------------------------------------ #
    def is_cleared(self, level_id: str) -> bool:
        token = self.profile.tokens.get(level_id, "")
        return verify_token(self.profile.secret, self.profile.player_id, level_id, token)

    def is_unlocked(self, level: Level) -> bool:
        """Unlocked iff every prerequisite is cleared (valid token)."""
        return all(self.is_cleared(pre) for pre in level.prerequisites)

    def status(self, level: Level) -> LevelStatus:
        if self.is_cleared(level.id):
            return LevelStatus.CLEARED
        if self.is_unlocked(level):
            return LevelStatus.UNLOCKED
        return LevelStatus.LOCKED

    # -- mutations ----------------------------------------------------------- #
    def mark_cleared(self, level: Level) -> None:
        """Write the signed completion token for a level."""
        token = make_token(self.profile.secret, self.profile.player_id, level.id)
        self.profile.tokens[level.id] = token

    # -- navigation ---------------------------------------------------------- #
    def next_unlocked_level(self) -> Level | None:
        """The first not-yet-cleared, unlocked level in ladder order."""
        for lv in self.campaign.all_levels():
            if self.status(lv) == LevelStatus.UNLOCKED:
                return lv
        return None

    def can_enter(self, level_id: str) -> bool:
        lv = self.campaign.by_id(level_id)
        if lv is None:
            return False
        return self.status(lv) in (LevelStatus.UNLOCKED, LevelStatus.CLEARED)

    # -- badges -------------------------------------------------------------- #
    def tier_complete(self, tier_number: int) -> bool:
        tier = self.campaign.tier(tier_number)
        if tier is None or not tier.levels:
            return False
        return all(self.is_cleared(lv.id) for lv in tier.levels)

    def badges(self) -> list[int]:
        """Tier numbers whose every level is cleared."""
        return [t.number for t in self.campaign.tiers if self.tier_complete(t.number)]

    # -- map ----------------------------------------------------------------- #
    def map_rows(self) -> list[tuple[str, str, str]]:
        """(tier_title, level_title, status) rows for the `map` command."""
        rows: list[tuple[str, str, str]] = []
        for tier in sorted(self.campaign.tiers, key=lambda t: t.number):
            for lv in tier.ordered():
                rows.append((f"T{tier.number} {tier.title}", lv.title, self.status(lv).value))
        return rows
