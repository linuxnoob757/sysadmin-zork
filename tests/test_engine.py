"""Tests for the level loader model."""
from __future__ import annotations

import pathlib

from engine.level import Level, load_campaign, load_levels


def test_level_from_yaml_parses_fields():
    lv = Level.from_yaml("content/levels/t0_l1_first_shift.yaml")
    assert lv.id == "t0_l1_first_shift"
    assert lv.tier == 0
    assert lv.order == 1
    assert "Pager" in lv.title or "first shift" in lv.title.lower() or "Pager" in lv.intro
    assert len(lv.setup) > 0
    assert len(lv.solution) > 0
    assert len(lv.checks) > 0


def test_load_levels_sorts_by_tier_order():
    levels = load_levels("content/levels")
    assert len(levels) >= 1
    for a, b in zip(levels, levels[1:]):
        assert (a.tier, a.order) <= (b.tier, b.order)


def test_load_campaign_has_tiers_and_ids():
    c = load_campaign()
    assert c.levels  # non-empty
    assert isinstance(c.by_id, dict)
    assert "t0_l1_first_shift" in c.by_id
    tiers = c.tiers
    assert tiers[0].title == "Onboarding"
