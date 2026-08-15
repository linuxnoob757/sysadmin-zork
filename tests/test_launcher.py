"""Tests for the interactive launcher (engine/launcher.py)."""
from __future__ import annotations

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


# ── progress gating ───────────────────────────────────────────

def test_progress_unlocks_in_order():
    """t0_l1 unlocked by default; t1_l1 unlocks after t0_l1."""
    from engine.launcher import Progress, load_campaign_for_progress
    c = load_campaign_for_progress()
    p = Progress(root=None, campaign=c)
    assert "t0_l1_first_shift" in p.unlocked_ids
    assert "t1_l1_directory_layout" not in p.unlocked_ids  # needs t0 done
    p.complete("t0_l1_first_shift")
    assert "t1_l1_directory_layout" in p.unlocked_ids
    assert "t1_l2_permissions" not in p.unlocked_ids  # needs t1_l1


def test_progress_skips_real_vm_on_windows(tmp_path):
    """requires_real_vm levels are never 'playable_on_this_os' but stay gated."""
    from engine.launcher import Progress, load_campaign_for_progress
    import sys
    c = load_campaign_for_progress()
    p = Progress(root=tmp_path, campaign=c)
    p.complete("t0_l1_first_shift")
    p.complete("t1_l1_directory_layout")
    # t1_l2 is gated behind t1_l1 (which is done) — it's "unlocked"
    assert "t1_l2_permissions" in p.unlocked_ids
    # but on Windows it can't be *played* (requires real VM)
    level = c.get_level("t1_l2_permissions")
    can_play = p.can_play(level)
    assert can_play == (not level.requires_real_vm or not sys.platform.startswith("win"))


def test_progress_persists_completed_levels(tmp_path):
    """Completed levels survive across Progress instances (saved to disk)."""
    from engine.launcher import Progress, load_campaign_for_progress
    c = load_campaign_for_progress()
    p1 = Progress(root=tmp_path, campaign=c)
    p1.complete("t0_l1_first_shift")
    p1.complete("t1_l1_directory_layout")
    p1.save()
    # new instance reads the same file → t1_l1, t1_l2 now unlocked
    p2 = Progress(root=tmp_path, campaign=c)
    p2.load()
    assert "t0_l1_first_shift" in p2.completed_ids
    assert "t1_l2_permissions" in p2.unlocked_ids


def test_progress_can_play_unlocked_sandbox_level(tmp_path):
    """After prerequisites, a sandbox-safe level passes can_play."""
    from engine.launcher import Progress, load_campaign_for_progress
    c = load_campaign_for_progress()
    p = Progress(root=tmp_path, campaign=c)
    p.complete("t0_l1_first_shift")
    p.complete("t1_l1_directory_layout")
    p.complete("t1_l2_permissions")
    assert p.can_play(c.get_level("t1_l3_pipes_redirects"))


# ── current/next ladder rendering ──────────────────────────────

def test_render_tier_ladder_shows_current_and_next(tmp_path):
    """Ladder shows the ready current level as [1] and the next locked level."""
    from engine.launcher import Progress, load_campaign_for_progress, render_tier_ladder
    c = load_campaign_for_progress()
    p = Progress(root=tmp_path, campaign=c)
    out = render_tier_ladder(c, p)
    # at the start: current = First Shift [1], next = Directory Layout (locked)
    assert "[1]" in out
    assert "· First Shift" in out
    assert "✺" in out  # next level is locked
    assert "Directory Layout" in out


def test_render_tier_ladder_advances_after_complete(tmp_path):
    """After completing t0_l1, the ladder promotes t1_l1 to current [1]."""
    from engine.launcher import Progress, load_campaign_for_progress, render_tier_ladder
    c = load_campaign_for_progress()
    p = Progress(root=tmp_path, campaign=c)
    p.complete("t0_l1_first_shift")
    out = render_tier_ladder(c, p)
    assert "· Directory Layout" in out  # now the current ready mission

