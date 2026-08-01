"""Checker: evaluate a level's win condition against the sandbox.

Turns a level's declarative `CheckSpec` list into real commands run on the VM
(or the fake), and reports a structured pass/fail with per-check detail. The
game loop calls `run_checks()` when the player types `check`.

Checkers are read-only where possible, so a player can `check` as often as they
like without side effects.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from engine.level import CheckSpec, Level
from engine.vm import Sandbox


@dataclass
class CheckReport:
    passed: bool
    failures: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)


def _eval_one(sandbox: Sandbox, spec: CheckSpec) -> tuple[bool, str]:
    """Return (ok, message) for a single check."""
    kind = spec.kind
    if kind == "file_exists":
        ok = sandbox.file_exists(spec.path)
        return ok, spec.describe or f"{spec.path} exists"
    if kind == "file_absent":
        ok = not sandbox.file_exists(spec.path)
        return ok, spec.describe or f"{spec.path} is absent"
    if kind == "file_contains":
        res = sandbox.run(f"cat {spec.path}")
        ok = res.ok and spec.expect in res.stdout
        return ok, spec.describe or f"{spec.path} contains '{spec.expect}'"
    if kind == "cmd_succeeds":
        ok = sandbox.run(spec.command).ok
        return ok, spec.describe or f"`{spec.command}` succeeds"
    if kind == "cmd_stdout_eq":
        res = sandbox.run(spec.command)
        ok = res.ok and res.stdout.strip() == spec.expect
        return ok, spec.describe or f"`{spec.command}` outputs '{spec.expect}'"
    return False, f"unknown check kind: {kind!r}"


def run_checks(sandbox: Sandbox, level: Level) -> CheckReport:
    """Evaluate all of a level's checks; pass only if every check passes."""
    failures: list[str] = []
    observations: list[str] = []
    for spec in level.checks:
        ok, msg = _eval_one(sandbox, spec)
        if ok:
            observations.append(f"OK   {msg}")
        else:
            failures.append(f"NOT YET  {msg}")
    return CheckReport(passed=not failures, failures=failures, observations=observations)


def apply_setup(sandbox: Sandbox, level: Level) -> None:
    """Run a level's setup commands to break the box into the puzzle state."""
    for cmd in level.setup:
        sandbox.run(cmd)
