"""YAML content loader: build a Campaign from content/ files.

Layout:
    content/
      tiers.yaml            # tier order + titles
      levels/
        t0_l1_first_shift.yaml
        t1_l1_lost_in_the_filesystem.yaml
        ...

Each level YAML maps directly onto the Level dataclass. `checks` is a list of
CheckSpec dicts (kind + optional path/command/expect/describe). `solution` is a
list of shell commands that solve the level -- used ONLY by the test suite to
prove the level is solvable and the checker is honest.

Keeping content in YAML means new levels need no engine changes -- the whole
point of the data-driven design.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from engine.level import Campaign, CheckSpec, Level, Scoring, Tier

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"

_VALID_CHECK_KINDS = {
    "file_exists", "file_absent", "file_contains",
    "cmd_succeeds", "cmd_fails", "cmd_stdout_eq", "cmd_stdout_contains",
    "symlink_resolves",
}


class ContentError(Exception):
    """Raised when content YAML is malformed or fails validation."""


def _parse_check(raw: dict, level_id: str) -> CheckSpec:
    kind = raw.get("kind")
    if kind not in _VALID_CHECK_KINDS:
        raise ContentError(f"{level_id}: invalid check kind {kind!r}")
    return CheckSpec(
        kind=kind,
        path=raw.get("path", ""),
        command=raw.get("command", ""),
        expect=str(raw.get("expect", "")),
        describe=raw.get("describe", ""),
    )


def _parse_scoring(raw: dict | None) -> Scoring:
    raw = raw or {}
    return Scoring(
        base=int(raw.get("base", 100)),
        hint_penalty=int(raw.get("hint_penalty", 25)),
        par_seconds=int(raw.get("par_seconds", 600)),
        retry_penalty=int(raw.get("retry_penalty", 10)),
    )


def _parse_level(data: dict, path: Path) -> Level:
    required = ("id", "tier", "order", "title")
    for key in required:
        if key not in data:
            raise ContentError(f"{path.name}: missing required field {key!r}")
    level_id = data["id"]
    checks = [_parse_check(c, level_id) for c in data.get("checks", [])]
    return Level(
        id=level_id,
        tier=int(data["tier"]),
        order=int(data["order"]),
        title=data["title"],
        intro=data.get("intro", ""),
        victory_text=data.get("victory_text", ""),
        objectives=list(data.get("objectives", [])),
        hints=list(data.get("hints", [])),
        checks=checks,
        setup=list(data.get("setup", [])),
        solution=list(data.get("solution", [])),
        requires_real_vm=bool(data.get("requires_real_vm", False)),
        scoring=_parse_scoring(data.get("scoring")),
        prerequisites=list(data.get("prerequisites", [])),
    )


def load_campaign(content_dir: Path | None = None) -> Campaign:
    """Load the full campaign from YAML content."""
    base = content_dir or CONTENT_DIR
    tiers_file = base / "tiers.yaml"
    if not tiers_file.exists():
        raise ContentError(f"missing {tiers_file}")

    tiers_meta = yaml.safe_load(tiers_file.read_text(encoding="utf-8")) or {}
    tier_defs = tiers_meta.get("tiers", [])

    # Load every level file, group by tier number.
    levels_dir = base / "levels"
    by_tier: dict[int, list[Level]] = {}
    for lvl_path in sorted(levels_dir.glob("*.yaml")):
        data = yaml.safe_load(lvl_path.read_text(encoding="utf-8"))
        if not data:
            continue
        level = _parse_level(data, lvl_path)
        by_tier.setdefault(level.tier, []).append(level)

    tiers: list[Tier] = []
    for tdef in tier_defs:
        num = int(tdef["number"])
        tiers.append(Tier(number=num, title=tdef.get("title", f"Tier {num}"),
                          levels=by_tier.get(num, [])))

    campaign = Campaign(tiers=tiers)
    _validate_campaign(campaign)
    return campaign


def _validate_campaign(campaign: Campaign) -> None:
    """Sanity checks: unique ids, prerequisites resolve, checks present."""
    ids = [lv.id for lv in campaign.all_levels()]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ContentError(f"duplicate level ids: {sorted(dupes)}")
    id_set = set(ids)
    for lv in campaign.all_levels():
        for pre in lv.prerequisites:
            if pre not in id_set:
                raise ContentError(f"{lv.id}: prerequisite {pre!r} does not exist")
        if not lv.checks:
            raise ContentError(f"{lv.id}: has no checks (unwinnable)")
