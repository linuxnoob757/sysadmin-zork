"""Verify every level is honestly winnable: RED (broken state) → GREEN (solution).

On Windows, levels with `requires_real_vm: true` are skipped — the sandbox
fake doesn't provide real systemd/tar/systemctl. Tier 0+1 are sandbox-safe.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

import pytest

from engine.checker import apply_setup, run_checks
from engine.level import Level, load_campaign
from engine.vm import LocalTransport, LocalHypervisor, Sandbox


SKIP_REQUIRE_REAL_VM = sys.platform.startswith("win")


def _fresh_sandbox() -> Sandbox:
    root = pathlib.Path(tempfile.mkdtemp(prefix="zork-"))
    sb = Sandbox(LocalTransport(root), LocalHypervisor(root))
    sb.transport.connect()
    return sb


def test_isolation_writes_stay_in_sandbox():
    sb = _fresh_sandbox()
    sb.run("printf 'hello\\n' > /srv/testfile", timeout=3.0)
    f = sb.transport.abs_path("/srv/testfile")
    assert f.exists()
    assert f.read_text() == "hello\n"
    sb.transport.close()


def _all_levels():
    return load_campaign().levels


@pytest.mark.parametrize("level_id", [lv.id for lv in _all_levels()])
def test_every_level_is_honestly_winnable(level_id: str):
    c = load_campaign()
    lv = c.get_level(level_id)
    assert lv is not None, f"level {level_id} not in campaign"
    if lv.requires_real_vm and SKIP_REQUIRE_REAL_VM:
        pytest.skip(f"{level_id} requires a real VM (skipped on Windows)")
    sb = _fresh_sandbox()
    apply_setup(sb, lv)
    broken = run_checks(sb, lv)
    assert not broken.passed, (
        f"{level_id} is pre-solved (setup already satisfies all checks):\n"
        f"{broken.observations}"
    )
    for cmd in lv.solution:
        sb.run(cmd, timeout=5.0)
    solved = run_checks(sb, lv)
    assert solved.passed, (
        f"{level_id} is NOT solvable — checks still fail after solution:\n"
        f"{solved.failures}"
    )
    sb.transport.close()


@pytest.mark.parametrize("level_id", [lv.id for lv in _all_levels()])
def test_each_level_has_required_fields(level_id: str):
    lv = load_campaign().get_level(level_id)
    assert lv is not None
    for f in ("title", "intro", "victory_text", "objectives", "checks", "solution"):
        assert getattr(lv, f, None), f"{level_id} missing/empty: {f}"
    assert lv.checks, f"{level_id} has no checks"
    assert lv.solution, f"{level_id} has no solution"
