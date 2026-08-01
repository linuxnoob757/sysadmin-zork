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

    def take_snapshot(self, name: str) -> None:
        # Replace an existing snapshot of the same name so the operation is
        # idempotent -- deleting a missing snapshot is not an error we care about.
        if name in self.list_snapshots():
            try:
                self._run("snapshot", self.vm_name, "delete", name)
            except subprocess.CalledProcessError:
                pass
        self._run("snapshot", self.vm_name, "take", name, "--pause")

    def restore_snapshot(self, name: str) -> None:
        self._run("snapshot", self.vm_name, "restore", name)

    def list_snapshots(self) -> list[str]:
        result = subprocess.run(
            [self.vboxmanage, "snapshot", self.vm_name, "list", "--machinereadable"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            # No snapshots yet -> VBoxManage exits non-zero with a known message.
            if "does not have any snapshots" in (result.stderr + result.stdout):
                return []
            raise subprocess.CalledProcessError(
                result.returncode, result.args, result.stdout, result.stderr
            )
        names: list[str] = []
        for line in result.stdout.splitlines():
            # Lines look like: SnapshotName="clean-baseline"
            if line.startswith("SnapshotName") and "=" in line:
                names.append(line.split("=", 1)[1].strip().strip('"'))
        return names


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

    def put_file(self, remote_path: str, content: str, *, mode: int = 0o644) -> None:
        self.transport.put_file(remote_path, content, mode=mode)

    def file_exists(self, path: str) -> bool:
        return self.run(f"test -f {path}").ok

    def snapshot(self, name: str) -> None:
        self.hypervisor.take_snapshot(name)

    def reset_to(self, name: str) -> None:
        """Restore a clean snapshot -- the per-level reset the whole game hinges on."""
        self.hypervisor.restore_snapshot(name)
