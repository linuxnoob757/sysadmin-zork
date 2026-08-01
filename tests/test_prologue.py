"""Tests for the install prologue -- driven entirely against fakes.

Proves the full prologue orchestration without any real VM: briefing, spec,
guided-install waits, the handshake (connect -> install key -> verify sudo ->
confirm sshd), baseline snapshot, and profile persistence. Also covers the two
failure modes that matter: no sudo, and a bad password.
"""

from __future__ import annotations

import pytest

from engine.narrator import ScriptedNarrator
from engine.profile import Profile
from engine.prologue import run_prologue
from engine.transport import FakeTransport
from engine.vm import FakeHypervisor

PUBKEY = "ssh-ed25519 AAAATESTKEY sysadmin-zork-engine"

# The prologue asks, in order: [wait_enter build, wait_enter install,
# host, port, user, password]. ScriptedNarrator consumes these for every
# ask/wait_enter call.
HAPPY_ANSWERS = ["", "", "192.168.56.101", "22", "student", "student123"]


def _factories(*, has_sudo=True, expected_password=None):
    """Build a shared fake transport + a factory that returns it.

    A single FakeTransport instance is reused so state (authorized_keys, files)
    persists across the prologue's connect/close/reconnect cycle -- mirroring one
    real VM.
    """
    vm = FakeTransport(has_sudo=has_sudo, expected_password=expected_password)

    def transport_factory(*, host, port, user, key_path, password):
        vm.password = password
        return vm

    hypervisor = FakeHypervisor(vm)

    def hypervisor_factory():
        return hypervisor

    return vm, transport_factory, hypervisor, hypervisor_factory


def test_prologue_happy_path(tmp_path):
    vm, tf, hv, hvf = _factories(expected_password="student123")
    profile = Profile(name="p1")
    narrator = ScriptedNarrator(HAPPY_ANSWERS)

    result = run_prologue(
        narrator,
        profile=profile,
        public_key=PUBKEY,
        key_path="/home/adam/.ssh/sysadmin-zork",
        vm_name="sysadmin-zork",
        transport_factory=tf,
        hypervisor_factory=hvf,
        profiles_dir=tmp_path,
        skip_hypervisor_check=True,
    )

    assert result.passed, result
    assert result.connected
    assert result.key_installed
    assert result.sudo_verified
    assert result.sshd_enabled
    assert result.snapshot_taken
    assert result.profile_saved
    assert result.complete

    # The engine's public key really landed on the (fake) VM.
    assert PUBKEY in vm.authorized_keys
    # The baseline snapshot exists.
    assert "clean-baseline" in hv.list_snapshots()


def test_prologue_persists_profile(tmp_path):
    vm, tf, hv, hvf = _factories(expected_password="student123")
    profile = Profile(name="persisted")
    narrator = ScriptedNarrator(HAPPY_ANSWERS)

    run_prologue(
        narrator,
        profile=profile,
        public_key=PUBKEY,
        key_path="/keys/zork",
        vm_name="sysadmin-zork",
        transport_factory=tf,
        hypervisor_factory=hvf,
        profiles_dir=tmp_path,
        skip_hypervisor_check=True,
    )

    reloaded = Profile.load("persisted", profiles_dir=tmp_path)
    assert reloaded.prologue_complete is True
    assert reloaded.connection.host == "192.168.56.101"
    assert reloaded.connection.port == 22
    assert reloaded.connection.user == "student"
    assert reloaded.connection.vm_name == "sysadmin-zork"
    assert reloaded.connection.key_path == "/keys/zork"


def test_prologue_fails_without_sudo(tmp_path):
    vm, tf, hv, hvf = _factories(has_sudo=False, expected_password="student123")
    profile = Profile(name="nosudo")
    narrator = ScriptedNarrator(HAPPY_ANSWERS)

    result = run_prologue(
        narrator,
        profile=profile,
        public_key=PUBKEY,
        key_path="/keys/zork",
        vm_name="sysadmin-zork",
        transport_factory=tf,
        hypervisor_factory=hvf,
        profiles_dir=tmp_path,
        skip_hypervisor_check=True,
    )

    assert result.connected
    assert result.key_installed
    assert result.sudo_verified is False
    assert result.complete is False
    # No snapshot, no completed profile when sudo is missing.
    assert result.snapshot_taken is False
    assert Profile.load("nosudo", profiles_dir=tmp_path).prologue_complete is False
    # The player is told why.
    assert any("administrator" in line for line in narrator.output)


def test_prologue_fails_on_bad_password(tmp_path):
    # VM expects student123 but the player types the wrong thing.
    vm, tf, hv, hvf = _factories(expected_password="student123")
    profile = Profile(name="badpw")
    answers = ["", "", "192.168.56.101", "22", "student", "wrongpass"]
    narrator = ScriptedNarrator(answers)

    result = run_prologue(
        narrator,
        profile=profile,
        public_key=PUBKEY,
        key_path="/keys/zork",
        vm_name="sysadmin-zork",
        transport_factory=tf,
        hypervisor_factory=hvf,
        profiles_dir=tmp_path,
        skip_hypervisor_check=True,
    )

    assert result.connected is False
    assert result.complete is False
    assert any("Handshake failed" in line for line in narrator.output)


def test_prologue_stops_when_hypervisor_absent(tmp_path):
    vm, tf, hv, hvf = _factories()
    profile = Profile(name="nohv")
    narrator = ScriptedNarrator(HAPPY_ANSWERS)

    # Force the hypervisor check to run and fail by pointing at a bogus path
    # and NOT skipping the check.
    result = run_prologue(
        narrator,
        profile=profile,
        public_key=PUBKEY,
        key_path="/keys/zork",
        vm_name="sysadmin-zork",
        vboxmanage=None,
        transport_factory=tf,
        hypervisor_factory=hvf,
        profiles_dir=tmp_path,
        skip_hypervisor_check=False,
    )
    # On a CI/dev box without VirtualBox, this returns early; if VBox IS
    # present, the check passes but the scripted answers still drive it. Either
    # way it must not crash and must not falsely complete without a snapshot.
    if not result.hypervisor_present:
        assert result.complete is False
        assert result.connected is False


def test_narrator_scripting_records_output():
    n = ScriptedNarrator(["yes"])
    n.say("hello")
    assert n.confirm("proceed?") is True
    assert "hello" in n.text


def test_prologue_installs_passwordless_sudo(tmp_path):
    vm, tf, hv, hvf = _factories(expected_password="student123")
    profile = Profile(name="pwless")
    narrator = ScriptedNarrator(HAPPY_ANSWERS)

    result = run_prologue(
        narrator,
        profile=profile,
        public_key=PUBKEY,
        key_path="/keys/zork",
        vm_name="sysadmin-zork",
        transport_factory=tf,
        hypervisor_factory=hvf,
        profiles_dir=tmp_path,
        skip_hypervisor_check=True,
    )
    assert result.complete
    # the fake VM now has passwordless sudo enabled by the prologue
    assert vm.passwordless_sudo is True
