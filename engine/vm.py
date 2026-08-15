"""Sandbox + hypervisor abstractions for sysadmin-zork.

`Sandbox` pairs a `Transport` (runs commands on the VM/fake) with a
`Hypervisor` (snapshot/reset). `LocalHypervisor` is an in-memory fake used by
tests. The `LocalTransport` lives in `engine/transport.py`.
"""
from __future__ import annotations

import pathlib
from dataclasses import dataclass, field

from engine.transport import LocalTransport, Result


@dataclass
class VMInfo:
    name: str
    host: str
    port: int = 22
    user: str = "student"
    key_path: str | None = None


class LocalHypervisor:
    """In-memory fake hypervisor: snapshots are just file markers."""

    def __init__(self, root: pathlib.Path | None = None):
        self.root = pathlib.Path(root) if root else pathlib.Path("/tmp/zork-sbx")

    def connect(self, vm: VMInfo | None = None) -> VMInfo:
        return vm or VMInfo(name="localhost", host="127.0.0.1")

    def snapshot(self, name: str) -> str:
        snap_dir = self.root / ".snapshots" / name
        snap_dir.mkdir(parents=True, exist_ok=True)
        return name

    def restore_snapshot(self, name: str) -> bool:
        return True

    def vm_path(self, name: str) -> pathlib.Path:
        return self.root / "vms" / name


class Sandbox:
    """Pairs a transport with a hypervisor + root for a single player session."""

    def __init__(self, transport: LocalTransport, hypervisor: LocalHypervisor | None = None,
                 root: pathlib.Path | None = None):
        self.transport = transport
        self.hypervisor = hypervisor or LocalHypervisor(root or getattr(transport, "root", None))
        self.root = getattr(transport, "root", root)

    def run(self, cmd: str, timeout: float = 30.0) -> Result:
        return self.transport.run(cmd, timeout=timeout)

    def read_file(self, path: str) -> str:
        return self.transport.read_file(path)

    def snapshot(self, name: str) -> str:
        return self.hypervisor.snapshot(name)

    def restore_snapshot(self, name: str) -> bool:
        return self.hypervisor.restore_snapshot(name)
