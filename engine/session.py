"""Session: live state for the current level attempt.

Tracks the wall-clock start (for time bonus), hints revealed, and retries
(resets), and pairs with a HintTracker. The clock is injectable so tests can
control elapsed time deterministically.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

from engine.hints import HintTracker
from engine.level import Level


@dataclass
class LevelSession:
    """Everything that resets when a player enters (or restarts) a level."""

    level: Level
    clock: Callable[[], float] = time.monotonic
    started_at: float = field(default=0.0)
    retries: int = 0
    hints: HintTracker = field(init=False)

    def __post_init__(self) -> None:
        self.hints = HintTracker(self.level)
        self.started_at = self.clock()

    @property
    def elapsed_seconds(self) -> float:
        return max(0.0, self.clock() - self.started_at)

    @property
    def hints_used(self) -> int:
        return self.hints.revealed

    def reveal_hint(self) -> str | None:
        return self.hints.next_hint()

    def restart(self) -> None:
        """A `reset`: keep hint count (it was already 'spent'), bump retries,
        restart the clock. Hints stay revealed-count-wise so score reflects help
        already taken this level."""
        self.retries += 1
        self.started_at = self.clock()
