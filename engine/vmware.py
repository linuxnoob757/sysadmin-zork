"""VMware Workstation/Player hypervisor backend.

Drives VM power/state via `vmrun` (the binary VMware Player installs).
Satisfies the `Hypervisor` Protocol from `engine.vm` so it drops into
`Sandbox` unchanged:

    - take_snapshot(name)    -> no-op (Player has no snapshot API; see note)
    - restore_snapshot(name) -> power off -> restore pristine .vmdk -> power on
    - list_snapshots()       -> returns [] (Player has no snapshot enumeration)

Reset model
-----------
VMware Workstation/Player's `vmrun` does NOT support snapshots (`snapshot`,
`revertToSnapshot`, `listSnapshots` all return "operation not supported").
So unlike `VBoxHypervisor` (which uses named snapshots for per-level reset),
`VMwareHypervisor` resets by restoring a **pristine copy of the VM's `.vmdk`**
that was captured once, while the VM was powered off, during setup.

``take_snapshot(name)`` is a no-op kept only so the ``Hypervisor`` Protocol and
``Sandbox.snapshot()`` call sites are unchanged -- callers still "take" a
snapshot before mutating the box; the reset actually rolls the disk back.

``restore_snapshot(name)`` is the real reset: power off -> copy the pristine
disk over the live disk -> power on. Heavier than VBox's ~8s paused-snapshot
resume (full disk overwrite + OS boot), but the only correct reset path on
Player.

The pristine disk path is ``pristine_disk`` (default: ``<vm_dir>/<base>-clean.vmdk``).

No vSphere/ESXi (that needs `-T esx` + auth -- out of scope for the
Player-based MVP).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time

from engine.vm import Hypervisor


class VMwareHypervisor:
    """Reset control for a VMware Workstation/Player VM via `vmrun`.

    The VM is addressed by path to its `.vmx` file (how vmrun identifies a VM
    -- NOT a name, as VirtualBox uses). Pass the full path as `vm_path`.

    `vmrun` is auto-discovered at its Player default path on Windows, else via
    PATH; override with `vmrun=`.

    `pristine_disk` is the path to a pristine copy of the VM's main `.vmdk`
    that `restore_snapshot` copies back over the live disk to reset the box.
    If omitted, defaults to ``<vm_dir>/<base-name>-clean.vmdk``.
    """

    _DEFAULT_WINDOWS_PATHS = (
        r"C:\Program Files (x86)\VMware\VMware Player\vmrun.exe",
        r"C:\Program Files (x86)\VMware\VMware Workstation\vmrun.exe",
        r"C:\Program Files\VMware\VMware Player\vmrun.exe",
        r"C:\Program Files\VMware\VMware Workstation\vmrun.exe",
    )

    def __init__(
        self,
        vm_path: str,
        *,
        vmrun: str | None = None,
        pristine_disk: str | None = None,
        _runner=None,
        _copyfile=None,
    ) -> None:
        if not vm_path:
            raise ValueError("VMwareHypervisor requires a non-empty .vmx vm_path")
        self.vm_path = vm_path
        self.vmrun = vmrun or self._discover_vmrun()
        self.pristine_disk = pristine_disk or self._default_pristine_disk()
        # Inject a runner so tests can patch subprocess without touching the fs.
        self._runner = _runner or self._subprocess
        # Inject a copier so tests can patch the disk overwrite too.
        self._copyfile = _copyfile or shutil.copyfile

    @classmethod
    def _discover_vmrun(cls) -> str:
        found = shutil.which("vmrun") or shutil.which("vmrun.exe")
        if found:
            return found
        for candidate in cls._DEFAULT_WINDOWS_PATHS:
            if os.path.exists(candidate):
                return candidate
        raise RuntimeError(
            "vmrun not found. Install VMware Workstation/Player or pass the "
            "full path to vmrun(.exe) via the profile/connection "
            "(connection.vmrun)."
        )

    def _default_pristine_disk(self) -> str:
        """Pristine disk path: <same dir as .vmx>/<base-name>-clean.vmdk."""
        vmx_dir = os.path.dirname(self.vm_path)
        base = os.path.splitext(os.path.basename(self.vm_path))[0]
        return os.path.join(vmx_dir, base + "-clean.vmdk")

    def _subprocess(self, cmd):
        return subprocess.run(cmd, capture_output=True, text=True)

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        """Run a vmrun subcommand. vmrun's exit code is the contract."""
        return self._runner((self.vmrun, *args))

    def _vm_state(self) -> str:
        """Return 'running' / 'notrunning'.

        vmrun doesn't expose state directly; `vmrun list` prints the running
        VMs, so membership == running. (Note: `vmrun list` is unreliable for
        nogui-started Player VMs, so we also accept 'unknown' as not-running
        and let power_on retry.)
        """
        result = self._run("list")
        running = [ln.strip() for ln in result.stdout.splitlines()[1:] if ln.strip()]
        if self.vm_path in running:
            return "running"
        return "notrunning"

    def _power_off(self, *, wait: float = 30.0) -> None:
        """Stop the VM if it's running (`vmrun stop` is idempotent)."""
        if self._vm_state() != "running":
            return
        self._run("stop", self.vm_path, "nogui")
        deadline = time.time() + wait
        while time.time() < deadline:
            if self._vm_state() != "running":
                return
            time.sleep(1)

    def _power_on(self, *, wait: float = 120.0) -> None:
        """Start the VM headless and wait for it to come up."""
        self._run("start", self.vm_path, "nogui")
        deadline = time.time() + wait
        while time.time() < deadline:
            if self._vm_state() == "running":
                return
            time.sleep(1)

    # ------------------------------------------------------------- the Protocol impl
    def take_snapshot(self, name: str) -> None:
        """No-op.

        VMware Workstation/Player's `vmrun` has no snapshot API, so there is
        nothing to 'take'. The pristine disk copy that restore_snapshot relies
        on is captured once during setup (a plain file copy while the VM is
        powered off). We accept `name` only to keep the `Hypervisor` Protocol
        and `Sandbox.snapshot()` call sites unchanged.
        """
        return None

    def restore_snapshot(self, name: str) -> None:
        """Reset the VM to its pristine state, power-cycling it.

        Since Player can't revert named snapshots, this restores the pristine
        `.vmdk` copy captured during setup:

            power off -> copy pristine disk over live disk -> power on

        The power-cycle IS the per-level reset; afterwards Sandbox.reconnect()
        re-establishes SSH. Leaves the VM running on return, mirroring
        VBoxHypervisor.restore_snapshot's contract.

        Note: this ignores `name` (there is one pristine baseline, not a set
        of named snapshots). The parameter exists only for Protocol symmetry.
        """
        self._power_off()
        # Overwrite the live disk with the pristine copy. Must happen while the
        # VM is powered off (VMware locks open disks).
        if not os.path.exists(self.pristine_disk):
            raise FileNotFoundError(
                f"No pristine disk to restore from: {self.pristine_disk!r}. "
                "Run setup to capture one (power off the VM, then copy its "
                ".vmdk to <base>-clean.vmdk)."
            )
        self._copyfile(self.pristine_disk, self._live_disk_path())
        self._power_on()

    def _live_disk_path(self) -> str:
        """The VM's main .vmdk (same dir/name as the .vmx, minus extension)."""
        base = os.path.splitext(self.vm_path)[0]
        return base + ".vmdk"

    def list_snapshots(self) -> list[str]:
        """Player exposes no snapshot enumeration. Returns []."""
        return []
