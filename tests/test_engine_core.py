"""Tests for tokens, scoring, hints, and progression (pure logic, no VM)."""

from __future__ import annotations

from engine.hints import HintTracker
from engine.level import Scoring, build_mvp_ladder
from engine.profile import Profile
from engine.progression import LevelStatus, Progression
from engine.scoring import compute_score
from engine.tokens import make_token, verify_token


# --------------------------------------------------------------------------- #
# tokens
# --------------------------------------------------------------------------- #
def test_token_roundtrip():
    tok = make_token("secret", "player1", "t1_l1")
    assert verify_token("secret", "player1", "t1_l1", tok)


def test_token_rejects_wrong_secret():
    tok = make_token("secret", "player1", "t1_l1")
    assert not verify_token("OTHER", "player1", "t1_l1", tok)


def test_token_rejects_wrong_level():
    tok = make_token("secret", "player1", "t1_l1")
    assert not verify_token("secret", "player1", "t1_l2", tok)


def test_token_rejects_forged_and_empty():
    assert not verify_token("secret", "p", "l", "")
    assert not verify_token("secret", "p", "l", "deadbeef")


# --------------------------------------------------------------------------- #
# scoring
# --------------------------------------------------------------------------- #
def test_score_instant_clean_solve_is_max():
    s = compute_score(Scoring(base=100, par_seconds=600), elapsed_seconds=0, hints_used=0, retries=0)
    # base + full time bonus (== base) - nothing
    assert s.total == 200
    assert s.clean is True


def test_score_hints_and_retries_deduct():
    s = compute_score(
        Scoring(base=100, hint_penalty=25, par_seconds=600, retry_penalty=10),
        elapsed_seconds=600,  # zero time bonus
        hints_used=2,
        retries=1,
    )
    # 100 + 0 - 50 - 10
    assert s.total == 40
    assert s.clean is False


def test_score_never_negative():
    s = compute_score(
        Scoring(base=50, hint_penalty=100, par_seconds=1),
        elapsed_seconds=999,
        hints_used=5,
        retries=5,
    )
    assert s.total == 0


def test_time_bonus_halfway():
    s = compute_score(Scoring(base=100, par_seconds=100), elapsed_seconds=50, hints_used=0, retries=0)
    # halfway to par -> ~half bonus
    assert s.time_bonus == 50
    assert s.total == 150


# --------------------------------------------------------------------------- #
# hints
# --------------------------------------------------------------------------- #
def test_hint_tracker_reveals_in_order_then_stops():
    ladder = build_mvp_ladder()
    lvl = ladder.by_id("t0_l1_first_shift")
    h = HintTracker(lvl)
    assert h.total == 3
    first = h.next_hint()
    assert first == lvl.hints[0]
    assert h.revealed == 1
    h.next_hint()
    h.next_hint()
    assert h.exhausted
    assert h.next_hint() is None


# --------------------------------------------------------------------------- #
# progression / gating
# --------------------------------------------------------------------------- #
def _fresh():
    campaign = build_mvp_ladder()
    profile = Profile(name="test")
    return campaign, profile, Progression(campaign, profile)


def test_first_level_unlocked_rest_locked():
    campaign, profile, prog = _fresh()
    t0 = campaign.by_id("t0_l1_first_shift")
    t1l1 = campaign.by_id("t1_l1_lost_in_the_filesystem")
    t1l2 = campaign.by_id("t1_l2_the_hidden_file")
    assert prog.status(t0) == LevelStatus.UNLOCKED       # no prereqs
    assert prog.status(t1l1) == LevelStatus.LOCKED       # needs t0
    assert prog.status(t1l2) == LevelStatus.LOCKED       # needs t1l1


def test_clearing_unlocks_next():
    campaign, profile, prog = _fresh()
    t0 = campaign.by_id("t0_l1_first_shift")
    t1l1 = campaign.by_id("t1_l1_lost_in_the_filesystem")
    prog.mark_cleared(t0)
    assert prog.status(t0) == LevelStatus.CLEARED
    assert prog.status(t1l1) == LevelStatus.UNLOCKED     # prereq now met


def test_next_unlocked_level_walks_the_ladder():
    campaign, profile, prog = _fresh()
    assert prog.next_unlocked_level().id == "t0_l1_first_shift"
    prog.mark_cleared(campaign.by_id("t0_l1_first_shift"))
    assert prog.next_unlocked_level().id == "t1_l1_lost_in_the_filesystem"


def test_forged_token_does_not_unlock():
    campaign, profile, prog = _fresh()
    # Hand-write a bogus token for t0 (as if editing the save file).
    profile.tokens["t0_l1_first_shift"] = "forged-not-a-real-hmac"
    t1l1 = campaign.by_id("t1_l1_lost_in_the_filesystem")
    # t0 is not really cleared (token invalid), so t1l1 stays locked.
    assert prog.is_cleared("t0_l1_first_shift") is False
    assert prog.status(t1l1) == LevelStatus.LOCKED


def test_tier_badge_requires_all_levels():
    campaign, profile, prog = _fresh()
    assert prog.tier_complete(1) is False
    prog.mark_cleared(campaign.by_id("t1_l1_lost_in_the_filesystem"))
    assert prog.tier_complete(1) is False  # t1_l2 still open
    prog.mark_cleared(campaign.by_id("t1_l2_the_hidden_file"))
    assert prog.tier_complete(1) is True
    assert 1 in prog.badges()


def test_tokens_survive_profile_roundtrip(tmp_path):
    campaign, profile, prog = _fresh()
    prog.mark_cleared(campaign.by_id("t0_l1_first_shift"))
    profile.save(profiles_dir=tmp_path)

    reloaded = Profile.load("test", profiles_dir=tmp_path)
    prog2 = Progression(campaign, reloaded)
    assert prog2.is_cleared("t0_l1_first_shift") is True
    # and the token still verifies against the (persisted) secret
    assert prog2.status(campaign.by_id("t1_l1_lost_in_the_filesystem")) == LevelStatus.UNLOCKED
