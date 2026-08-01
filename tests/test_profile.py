"""Tests for the Profile (durable player state)."""

from __future__ import annotations

from engine.profile import Connection, Profile


def test_new_profile_has_defaults_and_secret(tmp_path):
    p = Profile(name="alice")
    assert p.name == "alice"
    assert p.player_id  # uuid assigned
    assert len(p.secret) == 64  # 32 bytes hex
    assert p.prologue_complete is False
    assert p.connection.is_complete() is False


def test_save_and_load_roundtrip(tmp_path):
    p = Profile(name="bob")
    p.connection = Connection(
        host="192.168.56.101", key_path="/k", vm_name="sysadmin-zork"
    )
    p.prologue_complete = True
    path = p.save(profiles_dir=tmp_path)
    assert path.exists()

    loaded = Profile.load("bob", profiles_dir=tmp_path)
    assert loaded.name == "bob"
    assert loaded.player_id == p.player_id
    assert loaded.secret == p.secret
    assert loaded.connection.host == "192.168.56.101"
    assert loaded.connection.is_complete() is True
    assert loaded.prologue_complete is True


def test_load_missing_returns_fresh(tmp_path):
    assert Profile.exists("ghost", profiles_dir=tmp_path) is False
    p = Profile.load("ghost", profiles_dir=tmp_path)
    assert p.name == "ghost"
    assert p.prologue_complete is False


def test_connection_completeness():
    assert Connection().is_complete() is False
    assert Connection(host="h").is_complete() is False
    assert Connection(host="h", key_path="k", vm_name="v").is_complete() is True
