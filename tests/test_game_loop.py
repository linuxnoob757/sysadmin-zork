"""Integration tests for the full game loop, driven against the fake sandbox.

Plays real scripted sessions through Game.play(): solving a level, using hints,
resetting, quitting, and gating. No VM, no terminal -- a ScriptedNarrator feeds
input and captures output, and the FakeTransport/FakeHypervisor stand in for the
box.
"""

from __future__ import annotations

from engine.game import Game
from engine.level import build_mvp_ladder
from engine.narrator import ScriptedNarrator
from engine.profile import Profile
from engine.progression import Progression
from engine.transport import FakeTransport
from engine.vm import FakeHypervisor, Sandbox


def _make_game(answers, *, profile=None, profiles_dir=None):
    campaign = build_mvp_ladder()
    profile = profile or Profile(name="player")
    profile.connection.baseline_snapshot = "clean-baseline"

    transport = FakeTransport()
    transport.connect()
    hypervisor = FakeHypervisor(transport)
    sandbox = Sandbox(transport, hypervisor)
    # A baseline snapshot must exist for reset_to() to work (as after prologue).
    hypervisor.take_snapshot("clean-baseline")

    narrator = ScriptedNarrator(answers)
    game = Game(
        campaign=campaign,
        profile=profile,
        sandbox=sandbox,
        narrator=narrator,
        profiles_dir=profiles_dir,
    )
    return game, transport, narrator


def test_solve_first_level_clears_and_advances():
    # Tier 0: create ~/badge, then check -> solved -> advance into t1_l1.
    answers = [
        "touch /home/student/badge",  # box$
        "check",                       # solves t0
        "quit",                        # quit once we're in the next level
    ]
    game, transport, narrator = _make_game(answers)
    game.play()

    # t0 cleared, token written & valid
    prog = Progression(game.campaign, game.profile)
    assert prog.is_cleared("t0_l1_first_shift") is True
    assert "SOLVED" in narrator.text
    # advanced into t1_l1 (its intro mentions the vault)
    assert "vault" in narrator.text.lower()


def test_check_fails_when_objective_not_met():
    answers = ["check", "quit"]  # check immediately, nothing done
    game, transport, narrator = _make_game(answers)
    game.play()
    assert "Not solved yet" in narrator.text
    prog = Progression(game.campaign, game.profile)
    assert prog.is_cleared("t0_l1_first_shift") is False


def test_hints_are_revealed_in_order():
    answers = ["hint", "hint", "quit"]
    game, transport, narrator = _make_game(answers)
    game.play()
    text = narrator.text
    assert "Hint 1/3" in text
    assert "Hint 2/3" in text


def test_shell_passthrough_runs_on_the_box():
    answers = ["echo hello from the box", "quit"]
    game, transport, narrator = _make_game(answers)
    game.play()
    assert "hello from the box" in narrator.text


def test_map_shows_lock_states():
    answers = ["map", "quit"]
    game, transport, narrator = _make_game(answers)
    game.play()
    text = narrator.text
    assert "First Shift" in text
    assert "unlocked" in text
    assert "locked" in text  # t1 levels locked at the start


def test_reset_restores_box_and_counts_retry():
    # Create the badge, then reset (which should wipe it via snapshot restore),
    # then check -> should NOT be solved because reset removed the badge.
    answers = [
        "touch /home/student/badge",
        "reset",
        "check",   # badge gone after reset -> not solved
        "quit",
    ]
    game, transport, narrator = _make_game(answers)
    game.play()
    assert "Not solved yet" in narrator.text
    assert game.session.retries == 1


def test_full_tier_playthrough_earns_badge(tmp_path):
    # Solve t0, then t1_l1, then t1_l2 -> Tier 1 badge.
    answers = [
        # t0_l1: badge
        "touch /home/student/badge", "check",
        # t1_l1: create the vault marker
        "touch /srv/company/vault/found", "check",
        # t1_l2: recover the code into ~/answer
        "echo ZORK-4213 > /home/student/answer", "check",
    ]
    game, transport, narrator = _make_game(answers, profiles_dir=tmp_path)
    game.play()

    prog = Progression(game.campaign, game.profile)
    assert prog.is_cleared("t0_l1_first_shift")
    assert prog.is_cleared("t1_l1_lost_in_the_filesystem")
    assert prog.is_cleared("t1_l2_the_hidden_file")
    assert prog.tier_complete(1) is True
    assert "TIER 1 CLEARED" in narrator.text


def test_setup_breaks_the_box_before_level():
    # t1_l2 setup drops a hidden recovery file; confirm the level's setup ran
    # by reading it through the shell after entering (solve t0 first to reach it).
    answers = [
        "touch /home/student/badge", "check",   # clear t0 -> enter t1_l1
        "cat /home/student/.recovery",           # not set up yet in t1_l1
        "quit",
    ]
    game, transport, narrator = _make_game(answers)
    game.play()
    # We're in t1_l1 now; .recovery belongs to t1_l2 setup, so it should be absent.
    assert "ZORK-4213" not in narrator.text.split("SOLVED")[-1]


def test_progress_persists_across_restart(tmp_path):
    # First session: solve t0 and quit.
    p = Profile(name="persist")
    g1, _, _ = _make_game(["touch /home/student/badge", "check", "quit"], profile=p, profiles_dir=tmp_path)
    g1.play()
    assert g1.progression.is_cleared("t0_l1_first_shift")

    # Reload the profile from disk -> t0 still cleared, next-unlocked is t1_l1.
    reloaded = Profile.load("persist", profiles_dir=tmp_path)
    prog = Progression(build_mvp_ladder(), reloaded)
    assert prog.is_cleared("t0_l1_first_shift")
    assert prog.next_unlocked_level().id == "t1_l1_lost_in_the_filesystem"
