"""Level model + YAML loading for sysadmin-zork quests."""
from __future__ import annotations

import pathlib
from dataclasses import dataclass, field

import yaml


@dataclass
class CheckSpec:
    kind: str
    path: str = ""
    command: str = ""
    expect: str = ""
    describe: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "CheckSpec":
        return cls(
            kind=d.get("kind", ""),
            path=d.get("path", ""),
            command=d.get("command", ""),
            expect=d.get("expect", ""),
            describe=d.get("describe", ""),
        )


@dataclass
class ScoreSpec:
    base: int = 100
    hint_penalty: int = 0
    par_seconds: int = 120


@dataclass
class Level:
    id: str
    tier: int
    order: int
    title: str
    intro: str = ""
    victory_text: str = ""
    objectives: list = field(default_factory=list)
    hints: list = field(default_factory=list)
    setup: list = field(default_factory=list)
    checks: list = field(default_factory=list)
    solution: list = field(default_factory=list)
    scoring: ScoreSpec = field(default_factory=ScoreSpec)
    prerequisites: list = field(default_factory=list)
    requires_real_vm: bool = False
    # deprecated / aliased field
    require_real_vm: bool = False

    @classmethod
    def from_dict(cls, d: dict) -> "Level":
        if "require_real_vm" in d and "requires_real_vm" not in d:
            d = dict(d, requires_real_vm=d["require_real_vm"])
        checks_raw = d.get("checks") or d.get("expect", []) or []
        if isinstance(checks_raw, dict):
            checks_raw = [checks_raw]
        checks = [CheckSpec.from_dict(c) if isinstance(c, dict) else c for c in checks_raw]
        scoring = d.get("scoring") or {}
        if isinstance(scoring, dict):
            scoring = ScoreSpec(**{k: v for k, v in scoring.items() if k in ScoreSpec.__annotations__})
        return cls(
            id=d["id"],
            tier=int(d["tier"]),
            order=int(d["order"]),
            title=d.get("title", ""),
            intro=d.get("intro", ""),
            victory_text=d.get("victory_text", ""),
            objectives=d.get("objectives") or [],
            hints=d.get("hints") or [],
            setup=d.get("setup") or [],
            checks=checks,
            solution=d.get("solution") or [],
            scoring=scoring,
            prerequisites=d.get("prerequisites") or [],
            requires_real_vm=bool(d.get("requires_real_vm") or d.get("require_real_vm")),
        )

    @classmethod
    def from_yaml(cls, path: pathlib.Path | str) -> "Level":
        path = pathlib.Path(path)
        with path.open() as f:
            d = yaml.safe_load(f)
        return cls.from_dict(d)


def load_levels(levels_dir: str | pathlib.Path = "content/levels") -> list[Level]:
    """Load all levels/*.yaml, sorted by (tier, order)."""
    levels_dir = pathlib.Path(levels_dir)
    levels: list[Level] = []
    for p in sorted(levels_dir.glob("*.yaml")):
        levels.append(Level.from_yaml(p))
    levels.sort(key=lambda lv: (lv.tier, lv.order))
    return levels


def load_campaign(levels_dir: str | pathlib.Path = "content/levels"):
    """Load levels + build a Campaign with tier metadata."""
    levels = load_levels(levels_dir)
    tier_meta: dict[int, dict] = {}
    tiers_path = pathlib.Path("content/tiers.yaml")
    if tiers_path.exists():
        for t in yaml.safe_load(tiers_path.read_text()).get("tiers", []):
            tier_meta[int(t["number"])] = t
    # group
    by_tier: dict[int, list[Level]] = {}
    by_id: dict[str, Level] = {}
    for lv in levels:
        by_tier.setdefault(lv.tier, []).append(lv)
        by_id[lv.id] = lv
    return Campaign(levels=levels, by_tier=by_tier, by_id=by_id, tier_meta=tier_meta)


@dataclass
class Tier:
    number: int
    title: str
    levels: list[Level] = field(default_factory=list)


@dataclass
class Campaign:
    levels: list[Level]
    by_tier: dict
    by_id: dict
    tier_meta: dict

    @property
    def tiers(self) -> list[Tier]:
        return [
            Tier(number=n, title=self.tier_meta.get(n, {}).get("title", f"Tier {n}"),
                 levels=self.by_tier.get(n, []))
            for n in sorted(self.by_tier)
        ]

    def all_levels(self) -> list[Level]:
        return self.levels

    def by_level_id(self, lid: str) -> Level | None:
        return self.by_id.get(lid)

    def get_level(self, lid: str) -> Level | None:
        """Look up a single level by its id."""
        return self.by_id.get(lid)
