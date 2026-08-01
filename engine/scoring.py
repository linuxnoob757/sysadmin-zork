"""Scoring: reward diagnose-first play and penalize hints/retries.

    score = base - hints_used*hint_penalty + time_bonus - retries*retry_penalty

- time_bonus scales linearly from full `base` bonus (solved instantly) down to
  0 at par_seconds, and stays 0 beyond par. This rewards speed without ever
  going negative from time alone.
- The final score is clamped to >= 0.
- A "clean" clear (zero hints) earns a badge flag the UI can surface.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.level import Scoring


@dataclass
class ScoreResult:
    total: int
    base: int
    hint_deduction: int
    time_bonus: int
    retry_deduction: int
    clean: bool  # solved with zero hints


def compute_score(
    scoring: Scoring,
    *,
    elapsed_seconds: float,
    hints_used: int,
    retries: int,
) -> ScoreResult:
    base = scoring.base

    hint_deduction = hints_used * scoring.hint_penalty
    retry_deduction = retries * scoring.retry_penalty

    # time bonus: fraction of base, linear from 1.0 (instant) to 0.0 (>= par)
    par = max(scoring.par_seconds, 1)
    frac = max(0.0, 1.0 - (elapsed_seconds / par))
    time_bonus = int(round(base * frac))

    total = base + time_bonus - hint_deduction - retry_deduction
    total = max(0, total)

    return ScoreResult(
        total=total,
        base=base,
        hint_deduction=hint_deduction,
        time_bonus=time_bonus,
        retry_deduction=retry_deduction,
        clean=(hints_used == 0),
    )
