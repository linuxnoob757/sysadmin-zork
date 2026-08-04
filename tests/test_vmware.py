"""Tests for the VMware Workstation/Player hypervisor backend.

These prove the clean-reinstall reset contract against a fake `vmrun`/filesystem,
mirroring how test_spike.py proves the VBox snapshot contract without VirtualBox.
The real-VM path (disk copy + power-cycle) is validated separately on hardware.
"""

from __future__ import annotations

import pathlib

import pytest

from engine.vmware import VMwareHypervisor
from engine.vm import Hypervisor, Sandbox
from engine.transport import FakeTransport


class _Completed:
    """A minimal CompletedProcess stand-in."""

    def __init__(self, stdout: str, stderr: str, returncode: int = 0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


class _FakeVmrun:
    """Mimics vmrun's stdout/stderr/exit-code surface for the test harness."""

    def __init__(self, vm_path: str, running: bool = False):
        self.vm_path = vm_path
        self.running = running
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, cmd):
        args = tuple(cmd)
        self.calls.append(args)
        sub = args[1] if len(args) > 1 else ""
        if sub == "list":
            if self.running:
                return _Completed(f"Total running VMs: 1\n{self.vm_path}\n", "")
            return _Completed("Total running VMs: 0\n", "")
        if sub == "start":
            self.running = True
            return _Completed("", "")
        if sub == "stop":
            self.running = False
            return _Completed("", "")
        # snapshot / revertToSnapshot / listSnapshots / deletesnapshot: no-ops.
        return _Completed("", "")


def _make(tmp: pathlib.Path, *, running: bool = False):
    """Build a VMwareHypervisor wired to a fake vmrun + real temp disk files."""
    vmx = tmp / "test.vmx"
    vmx.write_text("[vmx]")
    pristine = tmp / "test-clean.vmdk"
    pristine.write_bytes(b"pristine")
    (tmp / "test.vmdk").write_bytes(b"damage")

    fake_vmrun = _FakeVmrun(str(vmx), running=running)

    def _copyfile(src, dst):
        pathlib.Path(dst).write_bytes(pathlib.Path(src).read_bytes())

    hv = VMwareHypervisor(
        str(vmx),
        vmrun="fake-vmrun",
        pristine_disk=str(pristine),
        _runner=fake_vmrun,
        _copyfile=_copyfile,
    )
    return hv, fake_vmrun, pristine


def _subs(fake_vmrun: _FakeVmrun) -> list[str]:
    return [c[1] for c in fake_vmrun.calls if len(c) > 1]


# --------------------------------------------------------------------------- #
# Protocol + construction
# --------------------------------------------------------------------------- #
def test_satisfies_protocol():
    hv = VMwareHypervisor("x.vmx", vmrun="/bin/true", _runner=lambda c: _Completed("", ""))
    assert isinstance(hv, Hypervisor)


def test_requires_vm_path():
    with pytest.raises(ValueError):
        VMwareHypervisor("", vmrun="/bin/true", _runner=lambda c: _Completed("", ""))


def test_default_pristine_disk_path():
    hv = VMwareHypervisor(
        r"C:\VMs\Rocky\Rocky.vmx",
        vmrun="/bin/true",
        _runner=lambda c: _Completed("", ""),
    )
    assert hv.pristine_disk == r"C:\VMs\Rocky\Rocky-clean.vmdk"


# --------------------------------------------------------------------------- #
# The reset contract: restore_snapshot rolls the live disk back + power-cycles
# --------------------------------------------------------------------------- #
def test_restore_power_cycles_and_restores_disk(tmp_path):
    hv, fake, pristine = _make(tmp_path, running=True)
    hv.restore_snapshot("clean")

    # Power off requested, pristine copied over live disk, power on requested.
    subs = _subs(fake)
    assert "stop" in subs
    assert "start" in subs
    assert (tmp_path / "test.vmdk").read_bytes() == b"pristine"


def test_restore_raises_without_pristine_disk(tmp_path):
    hv, _fake, _pristine = _make(tmp_path, running=False)
    hv.pristine_disk = str(tmp_path / "missing.vmdk")
    with pytest.raises(FileNotFoundError):
        hv.restore_snapshot("clean")


def test_take_snapshot_is_noop(tmp_path):
    """Player has no snapshot API; take_snapshot must not issue vmrun snapshot."""
    hv, fake, _pristine = _make(tmp_path, running=True)
    hv.take_snapshot("anything")

    subs = _subs(fake)
    # No snapshot/revert/listSnapshots commands -- Player can't snapshot.
    assert "snapshot" not in subs
    assert "revertToSnapshot" not in subs
    assert "listSnapshots" not in subs
    # And no power cycle either (it's a pure no-op; doesn't even touch power).
    assert "stop" not in subs
    assert "start" not in subs


def test_list_snapshots_empty(tmp_path):
    hv, _fake, _pristine = _make(tmp_path, running=False)
    assert hv.list_snapshots() == []


# --------------------------------------------------------------------------- #
# End-to-end through Sandbox (mirrors how the VBox spike test uses Sandbox)
# --------------------------------------------------------------------------- #
def test_sandbox_reset_invokes_hypervisor(tmp_path):
    """Sandbox.reset_to delegates to restore_snapshot (which power-cycles +
    restores the disk). We assert the vmrun calls fire; the FakeTransport is
    independent of the .vmdk, so we can't observe disk state through it, but the
    hypervisor invocation + power cycle is the contract."""
    hv, fake, _pristine = _make(tmp_path, running=True)
    transport = FakeTransport()
    transport.connect()
    sandbox = Sandbox(transport, hv)

    sandbox.reset_to("clean")

    subs = _subs(fake)
    assert "stop" in subs  # power off before disk overwrite
    assert "start" in subs  # power back on after
    # The live disk was overwritten with the pristine content.
    assert (tmp_path / "test.vmdk").read_bytes() == b"pristine"
    transport.close()
