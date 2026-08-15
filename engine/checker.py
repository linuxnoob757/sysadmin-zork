"""Checker: evaluate a level's win condition against the sandbox.

Turns a level's declarative `CheckSpec` list into real commands run on the VM
(or the fake sandbox), and reports a structured pass/fail. The game loop calls
`run_checks()` when the player types `check`.

Check kinds:
  - file_exists:         path must exist.
  - file_absent:         path must NOT exist.
  - file_contains:       file contains `expect` substring.
  - cmd_succeeds:        command exits 0.
  - cmd_fails:           command exits non-zero.
  - cmd_stdout_eq:       command stdout equals `expect` (after strip).
  - cmd_stdout_contains: command stdout contains `expect`.
  - symlink_resolves:    symlink at `path` resolves to `expect`.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys

from dataclasses import dataclass, field

from engine.level import CheckSpec, Level
from engine.vm import LocalTransport, Sandbox


@dataclass
class CheckReport:
    passed: bool = True
    failures: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)

    def fail(self, msg: str) -> None:
        self.failures.append(msg)
        self.passed = False
        self.observations.append("FAIL: " + msg)

    def note(self, msg: str) -> None:
        self.observations.append(msg)


@dataclass
class Result:
    exit_code: int
    stdout: str
    stderr: str


def _resolve(sb: Sandbox, spec: CheckSpec) -> pathlib.Path:
    """Resolve a check `path` against the sandbox root."""
    t = sb.transport
    if hasattr(t, "abs_path"):
        return t.abs_path(spec.path)
    return pathlib.Path(spec.path)


def _run_check_one(sb: Sandbox, spec: CheckSpec) -> tuple[bool, str]:
    kind = spec.kind
    if kind == "file_exists":
        p = _resolve(sb, spec)
        return p.exists(), f"file_exists {spec.path}"
    if kind == "file_absent":
        p = _resolve(sb, spec)
        return not p.exists(), f"file_absent {spec.path}"
    if kind == "file_contains":
        p = _resolve(sb, spec)
        if not p.exists():
            return False, f"file_contains {spec.path} (missing)"
        text = p.read_text(errors="replace")
        return spec.expect in text, f"file_contains {spec.path} expect={spec.expect!r}"
    if kind in ("cmd_succeeds", "cmd_fails", "cmd_stdout_eq", "cmd_stdout_contains"):
        r = sb.run(spec.command, timeout=10.0)
        if kind == "cmd_succeeds":
            return r.exit_code == 0, f"cmd_succeeds exit={r.exit_code}"
        if kind == "cmd_fails":
            return r.exit_code != 0, f"cmd_fails exit={r.exit_code}"
        if kind == "cmd_stdout_eq":
            return r.stdout.strip() == spec.expect, f"cmd_stdout_eq got={r.stdout.strip()!r}"
        # cmd_stdout_contains
        return spec.expect in r.stdout, f"cmd_stdout_contains expect={spec.expect!r}"
    if kind == "symlink_resolves":
        real = os.path.realpath(spec.path)
        target = os.path.realpath(spec.expect) if spec.expect else ""
        return bool(target) and real == target, f"symlink_resolves {spec.path} -> {real}"
    return False, f"unknown check kind: {kind}"


def run_checks(sb: Sandbox, level: Level) -> CheckReport:
    report = CheckReport(passed=True)
    for spec in level.checks:
        if not isinstance(spec, CheckSpec):
            report.fail(f"malformed check: {spec}")
            continue
        ok, detail = _run_check_one(sb, spec)
        if ok:
            report.note(f"PASS: {spec.describe or detail}")
        else:
            report.fail(f"NOT YET — {spec.describe or detail}")
    return report


def apply_setup(sb: Sandbox, level: Level) -> None:
    """Apply the level's `setup` directives (break the box)."""
    for cmd in level.setup or []:
        try:
            sb.run(cmd, timeout=10.0)
        except Exception:
            pass
