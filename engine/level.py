"""Content model: Level and Tier.

These are the in-memory shapes the engine runs on. Phase 4 will load them from
YAML (content/levels/*.yaml); for now `build_mvp_ladder()` provides a hardcoded
Tier 0 + Tier 1 ladder so the engine core can be built and tested end-to-end.

A level's win condition is a `CheckSpec`: a small, data-driven description of
what the checker verifies on the VM. Keeping it declarative means the game loop
never contains level-specific logic, and the fake sandbox can satisfy checks in
tests without a real shell.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CheckSpec:
    """Declarative win condition, evaluated by checker.py against a sandbox.

    kind:
      - 'file_exists'    : path must exist
      - 'file_absent'    : path must not exist
      - 'file_contains'  : path must exist and contain `expect`
      - 'cmd_succeeds'   : `command` exits 0
      - 'cmd_stdout_eq'  : `command` stdout (stripped) == `expect`
    """

    kind: str
    path: str = ""
    command: str = ""
    expect: str = ""
    describe: str = ""  # human-readable, shown on failure


@dataclass
class Scoring:
    base: int = 100
    hint_penalty: int = 25
    par_seconds: int = 600
    retry_penalty: int = 10


@dataclass
class Level:
    id: str
    tier: int
    order: int
    title: str
    intro: str = ""
    victory_text: str = ""
    objectives: list[str] = field(default_factory=list)
    hints: list[str] = field(default_factory=list)
    checks: list[CheckSpec] = field(default_factory=list)
    setup: list[str] = field(default_factory=list)  # commands to break the box
    scoring: Scoring = field(default_factory=Scoring)
    prerequisites: list[str] = field(default_factory=list)


@dataclass
class Tier:
    number: int
    title: str
    levels: list[Level] = field(default_factory=list)

    def ordered(self) -> list[Level]:
        return sorted(self.levels, key=lambda lv: lv.order)


@dataclass
class Campaign:
    """The whole ladder: tiers in order, plus id lookups."""

    tiers: list[Tier] = field(default_factory=list)

    def all_levels(self) -> list[Level]:
        out: list[Level] = []
        for tier in sorted(self.tiers, key=lambda t: t.number):
            out.extend(tier.ordered())
        return out

    def by_id(self, level_id: str) -> Level | None:
        for lv in self.all_levels():
            if lv.id == level_id:
                return lv
        return None

    def first_level(self) -> Level | None:
        levels = self.all_levels()
        return levels[0] if levels else None

    def next_level(self, level_id: str) -> Level | None:
        levels = self.all_levels()
        for i, lv in enumerate(levels):
            if lv.id == level_id and i + 1 < len(levels):
                return levels[i + 1]
        return None

    def tier(self, number: int) -> Tier | None:
        for t in self.tiers:
            if t.number == number:
                return t
        return None


# --------------------------------------------------------------------------- #
# Hardcoded MVP ladder (Tier 0 + Tier 1) -- Phase 4 replaces this with YAML.
# Kept minimal but faithful to the design's level list so the engine can run.
# --------------------------------------------------------------------------- #
def build_mvp_ladder() -> Campaign:
    t0 = Tier(
        number=0,
        title="Onboarding",
        levels=[
            Level(
                id="t0_l1_first_shift",
                tier=0,
                order=1,
                title="First Shift",
                intro=(
                    "Prove you can touch the box and leave a mark: drop a file "
                    "called 'badge' in your home directory. Then say 'check'.\n"
                    "    (Cold hands? `touch ~/badge` and it's done.)"
                ),
                victory_text="There it is. ~/badge -- your name on the wall. (+50)",
                objectives=["Create a file named 'badge' in your home directory"],
                hints=[
                    "This one's a freebie. `touch` creates an empty file.",
                    "`touch` followed by the path. Home is `~`.",
                    "Type exactly: `touch ~/badge`, then `check`.",
                ],
                checks=[CheckSpec("file_exists", path="/home/student/badge",
                                  describe="~/badge should exist")],
                scoring=Scoring(base=50, hint_penalty=10, par_seconds=300),
                prerequisites=[],
            )
        ],
    )
    t1 = Tier(
        number=1,
        title="Navigation & Files",
        levels=[
            Level(
                id="t1_l1_lost_in_the_filesystem",
                tier=1,
                order=1,
                title="Lost in the Filesystem",
                intro=(
                    "Get to /srv/company/vault, stand in it, and leave proof: "
                    "drop a file named 'found' inside the vault."
                ),
                victory_text="/srv/company/vault/found -- signed by your presence. (+100)",
                objectives=[
                    "Navigate to /srv/company/vault",
                    "Create a file named 'found' inside it",
                ],
                hints=[
                    "`pwd` prints where you are; `ls` shows what's around you.",
                    "One step with an absolute path: `cd /srv/company/vault`.",
                    "`cd /srv/company/vault`, then `touch found`.",
                ],
                setup=["mkdir -p /srv/company/vault"],
                checks=[CheckSpec("file_exists", path="/srv/company/vault/found",
                                  describe="/srv/company/vault/found should exist")],
                scoring=Scoring(base=100, hint_penalty=25, par_seconds=600),
                prerequisites=["t0_l1_first_shift"],
            ),
            Level(
                id="t1_l2_the_hidden_file",
                tier=1,
                order=2,
                title="The Hidden File",
                intro=(
                    "A recovery code hides in a dotfile in your home directory. "
                    "Read it, then write just the code into ~/answer."
                ),
                victory_text="You saw what was there all along. (+120)",
                objectives=[
                    "Find the hidden dotfile containing the recovery code",
                    "Write the code into ~/answer",
                ],
                hints=[
                    "A plain `ls` won't show it. What flag shows all files?",
                    "`ls -a ~` reveals dotfiles. `cat` the odd one.",
                    "Read it with `cat`, then `echo 'CODE' > ~/answer`.",
                ],
                setup=["echo 'ZORK-4213' > /home/student/.recovery"],
                checks=[CheckSpec("file_contains", path="/home/student/answer",
                                  expect="ZORK-4213",
                                  describe="~/answer should contain the code")],
                scoring=Scoring(base=120, hint_penalty=25, par_seconds=600),
                prerequisites=["t1_l1_lost_in_the_filesystem"],
            ),
        ],
    )
    return Campaign(tiers=[t0, t1])
