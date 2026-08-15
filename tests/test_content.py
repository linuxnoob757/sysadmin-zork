"""Verify the LocalTransport sandbox isolates writes into the temp root."""
from __future__ import annotations

import pathlib
import sys
import tempfile

from engine.checker import CheckReport, apply_setup, run_checks
from engine.level import Level, load_campaign
from engine.vm import LocalTransport, LocalHypervisor, Sandbox


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


def test_t0_l1_is_honestly_winnable():
    sb = _fresh_sandbox()
    c = load_campaign()
    lv = c.get_level("t0_l1_first_shift")
    assert lv is not None
    apply_setup(sb, lv)
    broken = run_checks(sb, lv)
    assert broken.passed is False, f"level should not be pre-solved: {broken.failures}"
    for cmd in lv.solution:
        sb.run(cmd, timeout=5.0)
    solved = run_checks(sb, lv)
    assert solved.passed, f"level should be solvable: {solved.failures}"
    sb.transport.close()
