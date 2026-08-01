"""Hints: reveal a level's hint ladder one rung at a time.

Each level defines an ordered list of hints (nudge -> concept -> near-answer).
The player reveals them one at a time with `hint`; each reveal costs score. The
HintTracker records how many have been shown for the current level so scoring
and the game loop stay in sync.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.level import Level


@dataclass
class HintTracker:
    """Tracks hint reveal progress for the current level attempt."""

    level: Level
    revealed: int = 0

    @property
    def total(self) -> int:
        return len(self.level.hints)

    @property
    def exhausted(self) -> bool:
        return self.revealed >= self.total

    def next_hint(self) -> str | None:
        """Reveal and return the next hint, or None if all are shown."""
        if self.exhausted:
            return None
        hint = self.level.hints[self.revealed]
        self.revealed += 1
        return hint

    def reset(self) -> None:
        self.revealed = 0
