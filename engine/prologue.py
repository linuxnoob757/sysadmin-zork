"""The install prologue: the guided, hands-on first mission.

Runs once on first launch. Walks the player (co-pilot, never autopilot) through
standing up their own Rocky/Alma VM, then performs the engine's side:

    briefing -> hypervisor check -> spec sheet -> guided install (player does it)
      -> handshake (connect, install key, verify sudo, confirm sshd)
      -> baseline snapshot -> save profile -> "server is live"

The player performs every real action (installing VirtualBox, driving Anaconda).
The engine instructs, waits, and VERIFIES -- it never does the install for them.

Design ref: game-design plan section 12a. Prose ref: narrative-draft prologue.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from engine.narrator import Narrator
from engine.profile import Connection, Profile
from engine.transport import SSHTransport, Transport
from engine.vm import Hypervisor, Sandbox, VBoxHypervisor

VBOX_DOWNLOAD = "https://www.virtualbox.org/wiki/Downloads"
ROCKY_DOWNLOAD = "https://rockylinux.org/download"
ALMA_DOWNLOAD = "https://almalinux.org/get-almalinux"


@dataclass
class PrologueResult:
    """Structured outcome so tests (and the CLI) can assert on each stage."""

    hypervisor_present: bool = False
    connected: bool = False
    key_installed: bool = False
    sudo_verified: bool = False
    sshd_enabled: bool = False
    snapshot_taken: bool = False
    profile_saved: bool = False
    complete: bool = False

    @property
    def passed(self) -> bool:
        return all(
            (
                self.connected,
                self.key_installed,
                self.sudo_verified,
                self.snapshot_taken,
                self.profile_saved,
                self.complete,
            )
        )


# --------------------------------------------------------------------------- #
# Narrative beats (light sysadmin-noir; condensed from the narrative draft)
# --------------------------------------------------------------------------- #
BRIEFING = """\
11:52 PM. The elevator climbs to fourteen like it's got nowhere better to be,
and neither do you. A floor built for machines, not men -- cold, blue-lit,
humming that low server-room hymn that gets into your teeth.

Nobody's here to meet you. Of course not. Just a desk with your name taped to
the edge (spelled wrong) and a sticky note in a hand you'll come to loathe:

    "Kid -- the shift's yours. Something came up. Build your own box first;
     I'm not letting a rookie breathe on prod. Try not to burn it down.
                                                          -- G."

Welcome to the night shift. Somewhere out there, GREERSON is not answering his
phone. In here, you're going to build a server."""

SPEC_SHEET = """\
GREERSON's build sheet, because god forbid the man used a wiki. The numbers are
right even if the ego isn't. Your box needs to be:

    CPU .......... 2 cores
    Memory ....... 2048 MB   (4096 if your host can spare it)
    Disk ......... 20 GB
    Network ...... Host-Only or NAT   (NO shared folders -- this box stays
                   quarantined from your real machine)
    OS ........... Rocky Linux or AlmaLinux, minimal ISO

Download the ISO if you haven't:
    Rocky ....... {rocky}
    Alma ........ {alma}

Build the VM in VirtualBox to those specs, attach the ISO, and boot it.""".format(
    rocky=ROCKY_DOWNLOAD, alma=ALMA_DOWNLOAD
)

INSTALL_STEPS = """\
This next part you do with your own two hands. I call the shots; you make the
clicks. Nobody automates their way into knowing this. Work down the installer:

  [ ] Language & Keyboard -- whatever gets you typing fastest.
  [ ] Time & Date -- set your timezone. Future-you, reading logs at 4 AM, will
      thank you for honest timestamps.
  [ ] Installation Destination -- click in, accept the disk, click Done.
  [ ] Root Account -- leave it DISABLED. You'll run as a real user with sudo,
      the way the pros do.
  [ ] User Creation -- make a user named 'student'. CHECK "Make this user
      administrator" -- that checkbox is your sudo. Set a password you'll
      remember; you'll type it once in a minute.
  [ ] Software Selection -- Minimal Install. No desktop. We need a witness,
      not wallpaper.

Begin installation. Reboot when it's done. Log in once as 'student' to prove
you exist, then enable the one door I need to reach you:

    sudo systemctl enable --now sshd
    ip a        # find the inet address that isn't 127.0.0.1"""


def check_hypervisor(narrator: Narrator, *, vboxmanage: str | None = None) -> bool:
    """Detect VirtualBox. We guide its install but never do it for the player."""
    narrator.status("Checking whether VirtualBox is installed...")
    found = vboxmanage or shutil.which("VBoxManage") or shutil.which("VBoxManage.exe")
    if not found:
        import os

        for candidate in (
            r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe",
            r"C:\Program Files (x86)\Oracle\VirtualBox\VBoxManage.exe",
        ):
            if os.path.exists(candidate):
                found = candidate
                break
    if found:
        narrator.status("VirtualBox is on the machine. One thing that works on the first try.")
        return True
    narrator.say(
        f"\nNot installed. No shame in it. Grab it here:\n    {VBOX_DOWNLOAD}\n"
        "Install it, then run the prologue again. Waiting is most of the job."
    )
    return False


def handshake(
    narrator: Narrator,
    *,
    host: str,
    port: int,
    user: str,
    password: str,
    public_key: str,
    key_path: str,
    transport_factory=None,
) -> tuple[Transport, PrologueResult]:
    """First contact: connect with the password, install the key, verify sudo.

    Returns the (key-based) transport to reuse for the snapshot, plus a partial
    result recording connected/key_installed/sudo_verified/sshd_enabled.
    """
    result = PrologueResult()
    factory = transport_factory or _default_transport_factory

    # 1. Connect with the password (the only time we use it).
    narrator.status(f"Knocking on {host}:{port} as '{user}'...")
    pw_transport = factory(host=host, port=port, user=user, key_path=key_path, password=password)
    pw_transport.connect()
    result.connected = True
    narrator.status("Somebody's home.")

    # 2. Install the engine's public key.
    narrator.status("Installing my key so I quit rattling the handle like a stranger...")
    pw_transport.append_authorized_key(public_key)
    result.key_installed = True

    # 3. Verify the user CAN sudo. On RHEL, sudo is granted via the 'wheel'
    #    group -- and a normal wheel user is (correctly) required to enter a
    #    password, so we CANNOT verify by running `sudo` non-interactively over
    #    SSH. Instead we check wheel-group membership, which is what actually
    #    confers sudo and needs no password.
    groups = pw_transport.run("id -nG")
    in_wheel = "wheel" in groups.stdout.split()
    # Bonus: if the user happens to have passwordless sudo, that's fine too.
    passwordless = pw_transport.run("sudo -n true").ok
    result.sudo_verified = in_wheel or passwordless
    if result.sudo_verified:
        narrator.status("Checking sudo... 'student' is in wheel. Keys to the kingdom.")
    else:
        narrator.say(
            "\n'student' is NOT in the wheel group, so sudo won't work. You likely "
            "missed the \"Make this user administrator\" checkbox during install. "
            "Fix that (add student to wheel) and run the prologue again."
        )

    # 4. Confirm sshd is enabled (survives reboot).
    enabled = pw_transport.run("systemctl is-enabled sshd")
    result.sshd_enabled = "enabled" in enabled.stdout
    pw_transport.close()

    # 5. Reconnect using the KEY, proving password-free access works now.
    narrator.status("Reconnecting with the key alone...")
    key_transport = factory(host=host, port=port, user=user, key_path=key_path, password=None)
    key_transport.connect()
    return key_transport, result


def _default_transport_factory(*, host, port, user, key_path, password):
    return SSHTransport(host=host, user=user, key_path=key_path, port=port, password=password)


def run_prologue(
    narrator: Narrator,
    *,
    profile: Profile,
    public_key: str,
    key_path: str,
    vm_name: str,
    vboxmanage: str | None = None,
    transport_factory=None,
    hypervisor_factory=None,
    profiles_dir: Path | None = None,
    skip_hypervisor_check: bool = False,
) -> PrologueResult:
    """Drive the full prologue. Returns a PrologueResult."""
    result = PrologueResult()

    # --- Briefing ---
    narrator.rule("PROLOGUE  --  First Night on the Job")
    narrator.say(BRIEFING)
    narrator.blank()

    # --- Hypervisor check ---
    if not skip_hypervisor_check:
        result.hypervisor_present = check_hypervisor(narrator, vboxmanage=vboxmanage)
        if not result.hypervisor_present:
            return result
    else:
        result.hypervisor_present = True

    # --- Spec sheet ---
    narrator.rule("THE SPEC SHEET")
    narrator.say(SPEC_SHEET)
    narrator.wait_enter("Build the VM and reach the installer, then press ENTER")

    # --- Guided install (player does this by hand) ---
    narrator.rule("THE INSTALL  (your hands, my instructions)")
    narrator.say(INSTALL_STEPS)
    narrator.wait_enter("When you're at a login prompt with sshd enabled, press ENTER")

    # --- Collect connection details ---
    narrator.rule("THE HANDSHAKE")
    host = narrator.ask("VM address", default="192.168.56.101")
    port = int(narrator.ask("SSH port", default="22") or "22")
    user = narrator.ask("Username", default="student")
    password = narrator.ask_secret(f"Password for {user} (used once, then keys only)")

    # --- Handshake ---
    try:
        key_transport, hs = handshake(
            narrator,
            host=host,
            port=port,
            user=user,
            password=password,
            public_key=public_key,
            key_path=key_path,
            transport_factory=transport_factory,
        )
    except Exception as exc:
        narrator.say(f"\nHandshake failed: {exc}")
        return result

    result.connected = hs.connected
    result.key_installed = hs.key_installed
    result.sudo_verified = hs.sudo_verified
    result.sshd_enabled = hs.sshd_enabled
    if not (result.connected and result.key_installed and result.sudo_verified):
        key_transport.close()
        return result

    # --- Baseline snapshot ---
    narrator.status("Taking a snapshot. Clean, honest, and unbroken. Look at it while it lasts.")
    hv_factory = hypervisor_factory or (lambda: VBoxHypervisor(vm_name, vboxmanage=vboxmanage))
    hypervisor = hv_factory()
    sandbox = Sandbox(key_transport, hypervisor)
    sandbox.snapshot(profile.connection.baseline_snapshot)
    result.snapshot_taken = profile.connection.baseline_snapshot in hypervisor.list_snapshots()
    key_transport.close()

    # --- Persist profile ---
    profile.connection = Connection(
        host=host,
        port=port,
        user=user,
        key_path=key_path,
        vm_name=vm_name,
        vboxmanage=vboxmanage,
        baseline_snapshot=profile.connection.baseline_snapshot,
    )
    profile.prologue_complete = result.snapshot_taken and result.sudo_verified
    profile.save(profiles_dir=profiles_dir)
    result.profile_saved = True
    result.complete = profile.prologue_complete

    # --- Server is live ---
    if result.complete:
        narrator.rule("SERVER IS LIVE")
        narrator.say(
            "12:40 AM. You've got a server, a seat on the network, and a senior\n"
            "admin who is somehow, impossibly, still not picking up his phone.\n\n"
            "The pager on the desk buzzes. Once. Then it starts screaming.\n\n"
            "Your shift starts now.            [ Tier 0 unlocked ]"
        )
    return result
