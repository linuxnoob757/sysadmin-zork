"""Tests for the interactive launcher (engine/launcher.py)."""
from __future__ import annotations

import io

from engine.launcher import GameSession, parse_command, render_level_start


# ── parse_command ──────────────────────────────────────────────

def test_parse_command_plain_shell():
    kind, payload = parse_command("ls /srv")
    assert kind == "shell"
    assert payload == "ls /srv"


def test_parse_command_metacommands():
    for mc in ("check", "hint", "objectives", "solution", "quit", "exit", "undo"):
        kind, _ = parse_command(mc)
        assert kind == mc


def test_parse_command_casefold_and_empty():
    kind, _ = parse_command("  CHECK  ")
    assert kind == "check"
    kind, _ = parse_command("")
    assert kind == "null"


# ── render_level_start ─────────────────────────────────────────

def test_render_level_start_prints_intro_and_tier():
    out = render_level_start(
        lv_id="t0_l1_first_shift", tier=0, title="First Shift",
        intro="00:00. Pager rings.", objectives=["find the marker"], n_hints=3,
    )
    assert "First Shift" in out
    assert "Tier 0" in out
    assert "Pager rings" in out
    assert "find the marker" in out


# ── GameSession ───────────────────────────────────────────────

def test_session_start_breaks_then_solves():
    """Full cycle: setup → broken check → solve commands → solved."""
    session = GameSession.for_level("t0_l1_first_shift")
    assert session.is_broken(), "level must start in broken state"
    # feed solution commands through the shell handler
    for cmd in session.level.solution:
        session.run_shell(cmd)
    assert session.is_solved(), f"level should solve; {session.checks().failures}"
    assert session.solved is True
    # score reflects no hints used
    assert session.score == session.level.scoring.base


def test_session_hint_advances_and_penalizes():
    session = GameSession.for_level("t0_l1_first_shift")
    assert session.next_hint() == session.level.hints[0]
    assert session.next_hint() == session.level.hints[1]
    # 2 hints used → base minus 2× hint_penalty
    expected = session.level.scoring.base - 2 * session.level.scoring.hint_penalty
    assert session.score == expected


def test_session_undo_resets_state():
    session = GameSession.for_level("t0_l1_first_shift")
    for cmd in session.level.solution:
        session.run_shell(cmd)
    assert session.is_solved()
    session.undo()
    assert session.is_broken(), "undo must re-break the box"
    assert session.solved is False
