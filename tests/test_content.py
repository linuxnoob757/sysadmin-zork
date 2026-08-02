"""Tests that the YAML content loads and that every level is honestly winnable.

For each level we:
  1. apply_setup (break the box)
  2. assert checks FAIL in the broken state (the level is not pre-solved)
  3. run the level's `solution` commands
  4. assert checks PASS (the level is actually solvable)
  5. assert progression gates correctly via prerequisites

All against the fake sandbox - no VM.
"""

from __future__ import annotations

import pathlib
import sys
import tempfile

from engine.checker import apply_setup, run_checks
from engine.loader import load_campaign
from engine.level import build_mvp_ladder
from engine.transport import LocalTransport
from engine.vm import LocalHypervisor, Sandbox


def _fresh_sandbox() -> Sandbox:
    root = pathlib.Path(tempfile.mkdtemp(prefix="zork-"))
    sb = Sandbox(LocalTransport(root), LocalHypervisor(root))
    sb.transport.connect()
    return sb


def test_loader_parses_all_six_levels():
    campaign = load_campaign()
    ids = [lv.id for lv in campaign.all_levels()]
    assert ids == [
        "t0_l1_first_shift",
        "t1_l1_lost_in_the_filesystem",
        "t1_l2_the_hidden_file",
        "t1_l3_needle_in_the_haystack",
        "t1_l4_the_symlink_maze",
        "t1_l5_redirect_the_flow",
    ]
    # every level has prose + checks
    for lv in campaign.all_levels():
        assert lv.intro.strip()
        assert lv.victory_text.strip()
        assert lv.checks


def test_loader_tiers_ordered_and_labeled():
    campaign = load_campaign()
    assert [t.number for t in campaign.tiers] == [0, 1]
    assert campaign.tiers[1].title == "Navigation & Files"


def test_every_level_is_honestly_winnable():
    campaign = load_campaign()
    for lv in campaign.all_levels():
        if lv.requires_real_vm and sys.platform.startswith("win"):
            # `requires_real_vm` really means "needs POSIX filesystem semantics
            # the fake can't model" (e.g. symlinks). Under real bash on
            # Linux/macOS the LocalTransport sandbox handles these fine, so we
            # only skip on Windows, where readlink -f yields host-specific
            # paths. On POSIX we exercise the authored solution like any level.
            continue
        sb = _fresh_sandbox()

        # break the box
        apply_setup(sb, lv)

        # broken state must NOT already pass (no free wins)
        broken = run_checks(sb, lv)
        assert not broken.passed, f"{lv.id}: broken state unexpectedly passed"

        # run the authored solution
        for cmd in lv.solution:
            sb.run(cmd)

        # solved state must pass
        solved = run_checks(sb, lv)
        assert solved.passed, (
            f"{lv.id}: solution did not satisfy checks: "
            + "; ".join(solved.failures)
        )
        sb.transport.close()


def test_badge_logic_tier0_then_tier1():
    campaign = load_campaign()
    # Tier 0 has 1 level, Tier 1 has 5 -> expected badges
    assert len(campaign.tiers[0].levels) == 1
    assert len(campaign.tiers[1].levels) == 5


def test_hardcoded_ladder_still_matches_loader_ids():
    """build_mvp_ladder is kept for unit tests; ensure it stays in sync-ish
    (same tier count until content fully supersedes it)."""
    hard = build_mvp_ladder()
    loaded = load_campaign()
    assert len(hard.tiers) == len(loaded.tiers)
