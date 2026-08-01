"""VM lifecycle: snapshots + the Sandbox that pairs a hypervisor with a transport.

`Hypervisor` is the snapshot-control protocol. Two implementations:

- `VBoxHypervisor`  -- drives VirtualBox via the `VBoxManage` CLI.
- `FakeHypervisor`  -- snapshots the in-memory state of a `FakeTransport`, so
  the full restore-to-clean loop can be proven without VirtualBox.

`Sandbox` is the object the rest of the engine will use: it owns a transport and
a hypervisor and exposes the two operations every level needs -- run commands,
and reset to a clean snapshot.
"""

from __future__ import annotations

import shutil
import subprocess
from typing import Protocol, runtime_checkable

from engine.transport import CommandResult, FakeTransport, Transport


@runtime_checkable
class Hypervisor(Protocol):
    """Controls VM snapshots for a single named VM."""

    def take_snapshot(self, name: str) -> None:
        """Create (or replace) a snapshot with the given name."""
        ...

    def restore_snapshot(self, name: str) -> None:
        """Roll the VM back to the named snapshot."""
        ...

    def list_snapshots(self) -> list[str]:
        """Return existing snapshot names."""
        ...


# --------------------------------------------------------------------------- #
# Real hypervisor: VirtualBox via VBoxManage
# --------------------------------------------------------------------------- #
class VBoxHypervisor:
    """Snapshot control for a VirtualBox VM through the `VBoxManage` CLI.

    On Windows `VBoxManage.exe` is often not on PATH; pass its full path as
    `vboxmanage=` or rely on the default install location fallback.
    """

    _DEFAULT_WINDOWS_PATHS = (
        r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe",
        r"C:\Program Files (x86)\Oracle\VirtualBox\VBoxManage.exe",
    )

    def __init__(self, vm_name: str, *, vboxmanage: str | None = None) -> None:
        self.vm_name = vm_name
        self.vboxmanage = vboxmanage or self._discover_vboxmanage()

    @classmethod
    def _discover_vboxmanage(cls) -> str:
        found = shutil.which("VBoxManage") or shutil.which("VBoxManage.exe")
        if found:
            return found
        import os

        for candidate in cls._DEFAULT_WINDOWS_PATHS:
            if os.path.exists(candidate):
                return candidate
        raise RuntimeError(
            "VBoxManage not found. Install VirtualBox or pass --vboxmanage "
            "with the full path to VBoxManage(.exe)."
        )

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [self.vboxmanage, *args],
            capture_output=True,
            text=True,
            check=True,
        )

    def _vm_state(self) -> str:
        """Return the VM's current state, e.g. 'running', 'poweroff', 'saved'."""
        result = subprocess.run(
            [self.vboxmanage, "showvminfo", self.vm_name, "--machinereadable"],
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines():
            if line.startswith("VMState="):
                return line.split("=", 1)[1].strip().strip('"')
        return "unknown"

    def _power_off(self, *, wait: float = 30.0) -> None:
        import time

        if self._vm_state() in ("poweroff", "aborted"):
            return
        self._run("controlvm", self.vm_name, "poweroff")
        deadline = time.time() + wait
        while time.time() < deadline:
            if self._vm_state() in ("poweroff", "aborted"):
                return
            time.sleep(1)

    def _power_on(self, *, wait: float = 90.0) -> None:
        import time

        if self._vm_state() == "running":
            return
        # 'poweroff', 'saved' and 'aborted' are all startable via startvm.
        # headless: no GUI window needed for engine-driven resets.
        self._run("startvm", self.vm_name, "--type", "headless")
        deadline = time.time() + wait
        while time.time() < deadline:
            if self._vm_state() == "running":
                return
            time.sleep(1)

    def list_snapshots(self) -> list[str]:
        return [name for name, _uuid in self._list_snapshots_with_uuids()]

    def _list_snapshots_with_uuids(self) -> list[tuple[str, str]]:
        """Return [(name, uuid), ...] for every snapshot on the VM."""
        result = subprocess.run(
            [self.vboxmanage, "snapshot", self.vm_name, "list", "--machinereadable"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            if "does not have any snapshots" in (result.stderr + result.stdout):
                return []
            raise subprocess.CalledProcessError(
                result.returncode, result.args, result.stdout, result.stderr
            )
        names: dict[int, str] = {}
        uuids: dict[int, str] = {}
        for line in result.stdout.splitlines():
            if "=" not in line:
                continue
            key, val = line.split("=", 1)
            val = val.strip().strip('"')
            # keys look like SnapshotName, SnapshotName-1, SnapshotUUID-1, ...
            if key.startswith("SnapshotName") and not key.startswith("CurrentSnapshot"):
                idx = int(key.split("-", 1)[1]) if "-" in key else 0
                names[idx] = val
            elif key.startswith("SnapshotUUID") and not key.startswith("CurrentSnapshot"):
                idx = int(key.split("-", 1)[1]) if "-" in key else 0
                uuids[idx] = val
        return [(names[i], uuids[i]) for i in sorted(names) if i in uuids]

    def _delete_all_named(self, name: str, *, max_passes: int = 10) -> None:
        """Delete every snapshot with the given name, by UUID.

        Deleting a snapshot reshapes the tree (a parent's deletion merges its
        child), so we re-read and retry until no snapshot of this name remains
        or we run out of passes. This keeps repeated resets from accumulating
        nested same-named duplicates.
        """
        for _ in range(max_passes):
            matches = [
                uuid
                for snap_name, uuid in self._list_snapshots_with_uuids()
                if snap_name == name
            ]
            if not matches:
                return
            # Delete the deepest/last one first to avoid parent-merge surprises.
            uuid = matches[-1]
            try:
                self._run("snapshot", self.vm_name, "delete", uuid)
            except subprocess.CalledProcessError:
                # If a specific delete fails, stop rather than spin forever.
                return

    def take_snapshot(self, name: str) -> None:
        # Delete ALL existing snapshots of this name (by UUID) first, so repeated
        # resets over hundreds of levels never accumulate duplicates or nest a
        # new snapshot under an old same-named one.
        self._delete_all_named(name)
        # Take an ONLINE snapshot with --pause: reliable on Windows (unlike
        # --live, which can hang). The VM is briefly paused, the snapshot
        # captures its running state, then it resumes. Restoring returns the VM
        # to a 'saved' state that startvm resumes from.
        self._run("snapshot", self.vm_name, "take", name, "--pause")

    def restore_snapshot(self, name: str) -> None:
        # VBoxManage refuses to restore a running VM: power it off first, then
        # power it back on afterward. This power-cycle IS the per-level reset.
        was_active = self._vm_state() in ("running", "saved", "paused")
        self._power_off()
        self._run("snapshot", self.vm_name, "restore", name)
        if was_active:
            self._power_on()


# --------------------------------------------------------------------------- #
# Fake hypervisor: snapshots a FakeTransport's in-memory state
# --------------------------------------------------------------------------- #
class FakeHypervisor:
    """Snapshots the state of a `FakeTransport` in memory.

    This is what makes `spike --fake` a real proof rather than a stub: taking a
    snapshot deep-copies the fake VM's filesystem, and restoring puts it back
    exactly -- so a change made after the snapshot genuinely disappears on
    restore, the same contract VirtualBox provides.
    """

    def __init__(self, transport: FakeTransport) -> None:
        self._transport = transport
        self._snapshots: dict[str, dict[str, str]] = {}

    def take_snapshot(self, name: str) -> None:
        self._snapshots[name] = self._transport._snapshot_state()

    def restore_snapshot(self, name: str) -> None:
        if name not in self._snapshots:
            raise KeyError(f"No such snapshot: {name!r}")
        self._transport._restore_state(self._snapshots[name])

    def list_snapshots(self) -> list[str]:
        return list(self._snapshots)


# --------------------------------------------------------------------------- #
# Sandbox: the pairing the rest of the engine will consume
# --------------------------------------------------------------------------- #
class Sandbox:
    """A connected transport + hypervisor, exposing the level primitives.

    The engine never touches SSH or VBoxManage directly; it goes through here.
    """

    def __init__(self, transport: Transport, hypervisor: Hypervisor) -> None:
        self.transport = transport
        self.hypervisor = hypervisor

    def __enter__(self) -> "Sandbox":
        self.transport.connect()
        return self

    def __exit__(self, *exc) -> None:
        self.transport.close()

    def run(self, command: str, *, timeout: float | None = None) -> CommandResult:
        return self.transport.run(command, timeout=timeout)

    def reconnect(self) -> None:
        """Drop and re-establish the transport.

        Required after a snapshot restore on a real VM: the power-cycle kills
        the old SSH session, so the engine must reconnect to the rebooted box
        before it can talk to it again. On fakes this is a cheap no-op cycle.
        """
        self.transport.close()
        self.transport.connect()

    def put_file(self, remote_path: str, content: str, *, mode: int = 0o644) -> None:
        self.transport.put_file(remote_path, content, mode=mode)

    def file_exists(self, path: str) -> bool:
        return self.run(f"test -f {path}").ok

    def snapshot(self, name: str) -> None:
        self.hypervisor.take_snapshot(name)

    def reset_to(self, name: str) -> None:
        """Restore a clean snapshot -- the per-level reset the whole game hinges on."""
        self.hypervisor.restore_snapshot(name)
