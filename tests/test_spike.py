"""Tests for the Phase 0 spike.

These prove the orchestration logic and, critically, the snapshot-rollback
contract that the whole VM-over-SSH architecture depends on -- all without a
real VM. If these pass, the real run is exercising already-proven logic through
a swapped-in transport/hypervisor.
"""

from __future__ import annotations

import pytest

from engine.spike import (
    BASELINE_SNAPSHOT,
    MARKER_PATH,
    build_fake_sandbox,
    run_spike,
)
from engine.transport import FakeTransport
from engine.vm import FakeHypervisor, Sandbox


def _silent(*_args, **_kwargs) -> None:
    """A no-op logger so tests don't spam stdout."""


# --------------------------------------------------------------------------- #
# The headline test: the full spike passes against fakes
# --------------------------------------------------------------------------- #
def test_spike_passes_end_to_end():
    with build_fake_sandbox() as sandbox:
        report = run_spike(sandbox, log=_silent)
    assert report.passed, report
    assert report.command_output == "student"


def test_spike_report_each_step_true():
    with build_fake_sandbox() as sandbox:
        report = run_spike(sandbox, log=_silent)
    assert report.connected_ok
    assert report.ran_command_ok
    assert report.snapshot_taken
    assert report.marker_created
    assert report.marker_present_before_restore
    assert report.marker_absent_after_restore


# --------------------------------------------------------------------------- #
# The contract that matters most: snapshot restore truly rolls state back
# --------------------------------------------------------------------------- #
def test_snapshot_restore_removes_changes_made_after_snapshot():
    transport = FakeTransport()
    hypervisor = FakeHypervisor(transport)
    sandbox = Sandbox(transport, hypervisor)

    with sandbox:
        sandbox.snapshot("clean")
        sandbox.put_file("/tmp/added-after", "boom\n")
        assert sandbox.file_exists("/tmp/added-after")

        sandbox.reset_to("clean")
        assert not sandbox.file_exists("/tmp/added-after")


def test_snapshot_restore_brings_back_deleted_file():
    transport = FakeTransport()
    hypervisor = FakeHypervisor(transport)
    sandbox = Sandbox(transport, hypervisor)

    with sandbox:
        sandbox.put_file("/etc/important.conf", "keepme\n")
        sandbox.snapshot("clean")

        # Destroy it, as a careless learner might.
        assert sandbox.run(f"rm -f /etc/important.conf").ok
        assert not sandbox.file_exists("/etc/important.conf")

        # Reset heals it.
        sandbox.reset_to("clean")
        assert sandbox.file_exists("/etc/important.conf")
        assert sandbox.run("cat /etc/important.conf").stdout == "keepme\n"


def test_restoring_unknown_snapshot_raises():
    transport = FakeTransport()
    hypervisor = FakeHypervisor(transport)
    sandbox = Sandbox(transport, hypervisor)
    with sandbox:
        with pytest.raises(KeyError):
            sandbox.reset_to("does-not-exist")


# --------------------------------------------------------------------------- #
# Transport-level behavior the spike relies on
# --------------------------------------------------------------------------- #
def test_fake_transport_requires_connect():
    t = FakeTransport()
    with pytest.raises(RuntimeError):
        t.run("whoami")


def test_file_exists_reflects_put_and_rm():
    with build_fake_sandbox() as sandbox:
        assert not sandbox.file_exists("/tmp/x")
        sandbox.put_file("/tmp/x", "hi\n")
        assert sandbox.file_exists("/tmp/x")
        sandbox.run("rm -f /tmp/x")
        assert not sandbox.file_exists("/tmp/x")


def test_snapshots_are_independent_copies():
    """Mutating state after a snapshot must not retroactively change it."""
    transport = FakeTransport()
    hypervisor = FakeHypervisor(transport)
    sandbox = Sandbox(transport, hypervisor)
    with sandbox:
        sandbox.put_file("/tmp/a", "one\n")
        sandbox.snapshot("s1")
        sandbox.put_file("/tmp/b", "two\n")
        sandbox.snapshot("s2")

        # Restore s1: only /tmp/a should exist.
        sandbox.reset_to("s1")
        assert sandbox.file_exists("/tmp/a")
        assert not sandbox.file_exists("/tmp/b")

        # Restore s2: both exist.
        sandbox.reset_to("s2")
        assert sandbox.file_exists("/tmp/a")
        assert sandbox.file_exists("/tmp/b")


def test_marker_path_and_baseline_constants_are_sane():
    assert MARKER_PATH.startswith("/tmp/")
    assert BASELINE_SNAPSHOT == "clean-baseline"
