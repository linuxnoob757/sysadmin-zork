"""The Phase 0 spike: prove the VM/SSH/snapshot loop end-to-end.

This is the single most important piece of de-risking in the project. If this
loop works, the whole VM-over-SSH architecture is viable. The steps:

    1. Connect to the VM and run a command (SSH works).
    2. Take a clean-baseline snapshot.
    3. Make a destructive change (drop a marker file).
    4. Restore the snapshot.
    5. Confirm the marker is GONE (snapshot rollback works).

The exact same function runs against the real VM and against the fakes, which
is the point: the fakes prove the orchestration; the real run proves the plumbing.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.vm import Sandbox

MARKER_PATH = "/tmp/sysadmin-zork-spike-marker"
BASELINE_SNAPSHOT = "clean-baseline"


@dataclass
class SpikeReport:
    """Structured result of a spike run, so tests can assert on each step."""

    connected_ok: bool
    ran_command_ok: bool
    command_output: str
    snapshot_taken: bool
    marker_created: bool
    marker_present_before_restore: bool
    marker_absent_after_restore: bool

    @property
    def passed(self) -> bool:
        return all(
            (
                self.connected_ok,
                self.ran_command_ok,
                self.snapshot_taken,
                self.marker_created,
                self.marker_present_before_restore,
                self.marker_absent_after_restore,
            )
        )


def run_spike(
    sandbox: Sandbox, *, snapshot_name: str = BASELINE_SNAPSHOT, log=print
) -> SpikeReport:
    """Execute the five-step spike against an (already-open) Sandbox."""

    # 1. Prove we can run a command.
    log("[1/5] Running a command over the transport...")
    whoami = sandbox.run("whoami")
    connected_ok = whoami.ok
    who = whoami.stdout.strip()
    log(f"      -> whoami = {who!r} (exit {whoami.exit_code})")

    # Make sure we start from a known-clean marker state.
    sandbox.run(f"rm -f {MARKER_PATH}")

    # 2. Take the baseline snapshot (clean state, no marker).
    log(f"[2/5] Taking snapshot {snapshot_name!r}...")
    sandbox.snapshot(snapshot_name)
    snaps = sandbox.hypervisor.list_snapshots()
    snapshot_taken = snapshot_name in snaps
    log(f"      -> baseline snapshot present: {snapshot_taken}")

    # 3. Make a destructive change AFTER the snapshot.
    log(f"[3/5] Creating marker file {MARKER_PATH} (the 'damage')...")
    sandbox.put_file(MARKER_PATH, "the kid was here\n", mode=0o644)
    marker_present_before_restore = sandbox.file_exists(MARKER_PATH)
    marker_created = marker_present_before_restore
    log(f"      -> marker present after creation: {marker_present_before_restore}")

    # 4. Restore the clean snapshot.
    log(f"[4/5] Restoring snapshot {snapshot_name!r} (the 'reset')...")
    sandbox.reset_to(snapshot_name)

    # A real restore power-cycles the VM, killing the SSH session -- reconnect
    # to the rebooted box before we can inspect it. (No-op-ish on fakes.)
    log("      -> reconnecting after reset...")
    sandbox.reconnect()

    # 5. The whole point: the marker must be gone.
    log("[5/5] Checking that the marker is gone after restore...")
    marker_absent_after_restore = not sandbox.file_exists(MARKER_PATH)
    log(f"      -> marker absent after restore: {marker_absent_after_restore}")

    report = SpikeReport(
        connected_ok=connected_ok,
        ran_command_ok=connected_ok,
        command_output=who,
        snapshot_taken=snapshot_taken,
        marker_created=marker_created,
        marker_present_before_restore=marker_present_before_restore,
        marker_absent_after_restore=marker_absent_after_restore,
    )
    return report


def build_fake_sandbox() -> Sandbox:
    """A Sandbox backed entirely by in-memory fakes -- no VM required."""
    from engine.transport import FakeTransport
    from engine.vm import FakeHypervisor

    transport = FakeTransport()
    hypervisor = FakeHypervisor(transport)
    return Sandbox(transport, hypervisor)


def build_real_sandbox(
    *,
    host: str,
    user: str,
    key: str,
    vm: str,
    port: int = 22,
    vboxmanage: str | None = None,
) -> Sandbox:
    """A Sandbox wired to a real VM over SSH with VirtualBox snapshots."""
    from engine.transport import SSHTransport
    from engine.vm import VBoxHypervisor

    transport = SSHTransport(host=host, user=user, key_path=key, port=port)
    hypervisor = VBoxHypervisor(vm, vboxmanage=vboxmanage)
    return Sandbox(transport, hypervisor)
