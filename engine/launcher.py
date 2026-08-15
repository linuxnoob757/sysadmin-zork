"""Interactive launcher for sysadmin-zork.

The launcher presents the tier/level ladder, spins up a sandboxed shell for the
selected level, and interprets meta-commands (`check`, `hint`, `objectives`,
`quit`) interleaved with ordinary shell commands run against the
LocalTransport sandbox.

Player flow:
    sysadmin-zork                 → shows the tier ladder, prompts for a choice
    sysadmin-zork t0_l1           → jumps straight to a level
    sysadmin-zork prologue [--fake] → guided OS install + SSH handshake
    zork> <shell command>         → piped to bash on the sandbox
    zork> check                   → runs win-conditions, prints PASS/FAIL
    zork> hint                    → reveals the next hint (costs points)
    zork> objectives              → lists the level's goals
    zork> solution                → (debug) replays the author's solution
    zork> undo                    → restores the broken baseline
    zork> quit|exit               → ends the session

Progress gating:
    Levels unlock sequentially. t0_l1 is unlocked by default; each subsequent
    level requires its `prerequisites` to be marked complete in the player's
    progress file (~/.sysadmin-zork/progress.json). Completing a level (check
    → PASS) records it and unlocks the next.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import tempfile

# When run directly (`python engine/launcher.py`), sys.path[0] is the engine/
# dir, not the project root — so `from engine.checker` would fail. Prepend the
# project root (parent of this file's package) when running as a script.
if __package__ in (None, ""):
    _root = pathlib.Path(__file__).resolve().parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

from engine.checker import CheckReport, apply_setup, run_checks
from engine.level import Campaign, Level, load_campaign
from engine.transport import LocalTransport
from engine.vm import LocalHypervisor, Sandbox


# ── progress model ──────────────────────────────────────────────
# Gating: a level is *playable* only after all its prerequisites are complete.

def _progress_dir() -> pathlib.Path:
    return pathlib.Path(os.path.expanduser("~/.sysadmin-zork"))


def load_campaign_for_progress(levels_dir: str | pathlib.Path | None = None,
                               tiers_path: str | pathlib.Path | None = None):
    """Load campaign without choking if content/ isn't on the cwd."""
    if levels_dir is None:
        levels_dir = pathlib.Path(__file__).resolve().parents[1] / "content" / "levels"
    if tiers_path is None:
        tiers_path = pathlib.Path(__file__).resolve().parents[1] / "content" / "tiers.yaml"
    return load_campaign(levels_dir)


class Progress:
    """Player's completed-level registry — gates progression story-style.

    `completed` is the set of level ids the player has solved. A level
    unlocks when all its `prerequisites` are in `completed`. t0_l1 (the
    very first, no-prereqs level) is always unlocked.
    """

    DEFAULT_PATH = _progress_dir() / "progress.json"
    SEED_LEVEL = "t0_l1_first_shift"

    def __init__(self, root: pathlib.Path | None = None,
                 campaign: Campaign | None = None):
        if root is None:
            root = self.DEFAULT_PATH
        root = pathlib.Path(root)
        # allow callers to pass a directory (e.g. tmp_path) — resolve to
        # <dir>/progress.json inside it.
        if root.is_dir() or root.suffix == "":
            root = root / "progress.json"
        self.root = root
        self.campaign = campaign or load_campaign_for_progress()
        self._completed: set[str] = set()
        self._unlocked: set[str] | None = None

    # persistence ──────────────────────────────────────────────
    def load(self) -> "Progress":
        self._completed = set()
        if self.root.exists():
            data = json.loads(self.root.read_text())
            self._completed = {e for e in data.get("completed", []) if isinstance(e, str)}
        return self

    def save(self) -> None:
        self.root.parent.mkdir(parents=True, exist_ok=True)
        self.root.write_text(json.dumps(
            {"completed": sorted(self._completed)}, indent=2))

    # state ────────────────────────────────────────────────────
    @property
    def completed_ids(self) -> set[str]:
        return set(self._completed)

    def complete(self, level_id: str) -> None:
        self._completed.add(level_id)
        self._unlocked = None  # invalidate cache

    def _compute_unlocked(self) -> set[str]:
        levels = {lv.id: lv for lv in self.campaign.levels}
        # t0_l1 (the seed) is the only level unlocked with zero completions.
        # Every other level unlocks only when its prerequisites are *completed*.
        unlocked: set[str] = set()
        if self.SEED_LEVEL in levels:
            unlocked.add(self.SEED_LEVEL)
        # iterate to closure: a level unlocks when all its prereqs are completed
        changed = True
        while changed:
            changed = False
            for lv_id, lv in levels.items():
                if lv_id in unlocked:
                    continue
                if all(p in self._completed for p in lv.prerequisites):
                    unlocked.add(lv_id)
                    changed = True
        # completed levels are always "unlocked" (replayable)
        unlocked |= self._completed
        return unlocked

    @property
    def unlocked_ids(self) -> set[str]:
        if self._unlocked is None:
            self._unlocked = self._compute_unlocked()
        return self._unlocked  # type: ignore

    def is_unlocked(self, level_id: str) -> bool:
        return level_id in self.unlocked_ids

    def can_play(self, level: Level | None) -> bool:
        """Unlocked AND runnable on this OS (real_vm levels skip on Windows)."""
        if level is None or not self.is_unlocked(level.id):
            return False
        if level.requires_real_vm and sys.platform.startswith("win"):
            return False
        return True


def default_progress() -> Progress:
    """One Progress instance for the real user dir (auto-loaded)."""
    return Progress().load()


# ── meta-command parser ─────────────────────────────────────────

_META = {"check", "hint", "objectives", "solution", "quit", "exit", "undo",
         "score", "help"}


def parse_command(line: str) -> tuple[str, str]:
    """Return (meta_kind, payload).

    `meta_kind` is one of the meta-commands, "shell", or "null" for empty input
    / whitespace only.
    """
    stripped = line.strip()
    if not stripped:
        return "null", ""
    # bare meta-command (no args)
    if stripped.lower() in _META:
        return stripped.lower(), ""
    # meta-command with args (only a few accept args; treat generically)
    head = stripped.split(None, 1)[0].lower()
    if head in _META:
        return head, stripped.split(None, 1)[1]
    return "shell", stripped


# ── rendering ──────────────────────────────────────────────────

def render_tier_ladder(c: Campaign, progress: Progress | None = None) -> str:
    """Flat numbered menu of all levels, gated by completion progress.

    Locked levels show a ✺ and can't be selected; completed ones show ✓.
    The player just types the number — no need to remember level ids.
    """
    prog = progress or default_progress()
    lines = ["Sysadmin Zork — Mission Ladder", "=" * 24, ""]
    n = 0
    for tier in c.tiers:
        lines.append(f"  ─ Tier {tier.number}: {tier.title}")
        for lv in tier.levels:
            n += 1
            tag = "VM" if lv.requires_real_vm else "sandbox"
            if lv.id in prog.completed_ids:
                mark = "✓"
                status = "DONE"
            elif prog.is_unlocked(lv.id):
                mark = "·"
                status = tag
            else:
                mark = "✺"
                status = f"locked ← {', '.join(lv.prerequisites)}"
            lines.append(f"    [{n:>2}] {mark} {lv.title}  ({status})")
        lines.append("")
    lines.append("Legend: ✓ = done  · = ready  ✺ = locked")
    lines.append("Pick a number, or  P  Prologue  /  Q  Quit")
    return "\n".join(lines)


def render_level_start(lv_id: str, tier: int, title: str, intro: str,
                       objectives: list[str], n_hints: int) -> str:
    bar = "—" * 60
    out = [
        bar,
        f"  {title}  (Tier {tier})",
        bar,
        "",
        intro.rstrip(),
        "",
        f"Objectives ({len(objectives)}):",
    ]
    for i, obj in enumerate(objectives, 1):
        out.append(f"  {i}. {obj}")
    out += [
        "",
        f"Hints available: {n_hints}  (cost: -per hint)",
        "",
        "Commands: <shell cmd> | check | hint | objectives | solution(debug)",
        "          | undo | score | quit  — the pager's always watching.",
        bar,
    ]
    return "\n".join(out)


def render_check(report: CheckReport) -> str:
    if report.passed:
        return "✓ ALL CHECKS PASS"
    lines = ["✗ NOT YET —", *[f"  - {f}" for f in report.failures]]
    return "\n".join(lines)


# ── game session ───────────────────────────────────────────────

class GameSession:
    """Single playable level session backed by a LocalTransport sandbox."""

    def __init__(self, level: Level, sandbox: Sandbox, progress: Progress | None = None):
        self.level = level
        self.sandbox = sandbox
        self.progress = progress
        self.hints_used = 0
        self.solved = False
        self._apply_setup()

    # lifecycle ──────────────────────────────────────────────
    @classmethod
    def for_level(cls, level_id: str, campaign: Campaign | None = None,
                  progress: Progress | None = None) -> "GameSession":
        c = campaign or load_campaign()
        lv = c.get_level(level_id)
        if lv is None:
            raise KeyError(f"level not found: {level_id}")
        root = pathlib.Path(tempfile.mkdtemp(prefix="zork-session-"))
        sb = Sandbox(LocalTransport(root), LocalHypervisor(root))
        sb.transport.connect()
        return cls(lv, sb, progress)

    def _apply_setup(self) -> None:
        apply_setup(self.sandbox, self.level)
        self.sandbox.snapshot("baseline")

    def undo(self) -> None:
        """Restore the broken baseline snapshot."""
        try:
            self.sandbox.transport.root  # noqa
        except Exception:
            pass
        # re-run setup in a fresh sandbox to truly reset
        self.sandbox = Sandbox(LocalTransport(self.sandbox.transport.root),
                              LocalHypervisor(self.sandbox.transport.root))
        self.sandbox.transport.connect()
        apply_setup(self.sandbox, self.level)
        self.solved = False
        self.hints_used = 0

    # shell ──────────────────────────────────────────────────
    def run_shell(self, cmd: str) -> str:
        """Run an arbitrary shell command in the sandbox; return stdout."""
        r = self.sandbox.run(cmd, timeout=15.0)
        if r.stderr:
            return (r.stdout + r.stderr).rstrip("\n")
        return r.stdout.rstrip("\n")

    # checks ─────────────────────────────────────────────────
    def checks(self) -> CheckReport:
        return run_checks(self.sandbox, self.level)

    def is_broken(self) -> bool:
        return not self.checks().passed

    def is_solved(self) -> bool:
        if self.solved:
            return True
        report = self.checks()
        if report.passed:
            self.solved = True
        return self.solved

    # hints ──────────────────────────────────────────────────
    def next_hint(self) -> str | None:
        if self.hints_used < len(self.level.hints):
            hint = self.level.hints[self.hints_used]
            self.hints_used += 1
            return hint
        return None

    # scoring ────────────────────────────────────────────────
    @property
    def score(self) -> int:
        base = self.level.scoring.base
        return max(0, base - self.hints_used * self.level.scoring.hint_penalty)

    # teardown ───────────────────────────────────────────────
    def close(self) -> None:
        self.sandbox.transport.close()


# ── prologue ───────────────────────────────────────────────────

def run_prologue(fake: bool = True) -> int:
    """Guided OS install + SSH handshake.

    Delegates to engine.__main__._cmd_prologue so the bat's `prologue`
    subcommand and the interactive ladder share one implementation.
    """
    from engine.__main__ import _cmd_prologue
    return _cmd_prologue(fake)


# ── interactive loop ───────────────────────────────────────────

def run_level(level_id: str, progress: Progress | None = None) -> bool:
    """Run a level session. Returns True if the player won, False if
    the level was locked / the player quit without solving."""
    prog = progress or default_progress()
    c = prog.campaign
    lv = c.get_level(level_id)
    if lv is None:
        print(f"  no such level: {level_id}")
        return False
    if not prog.is_unlocked(level_id):
        print(f"\n  ✺ {level_id} is LOCKED — complete its prerequisites: {lv.prerequisites}")
        return False
    if lv.requires_real_vm and sys.platform.startswith("win"):
        print(f"\n  {level_id} requires a real VM — use launch.bat with VirtualBox.")
        return False
    session = GameSession.for_level(level_id, campaign=c, progress=prog)
    print(render_level_start(lv.id, lv.tier, lv.title, lv.intro,
                             lv.objectives, len(lv.hints)))
    print(f"\n> box ready. type `check` to verify, `quit` to exit.\n")
    won = False
    try:
        while True:
            try:
                line = input("zork> ").strip()
            except EOFError:
                break
            if not line:
                continue
            kind, payload = parse_command(line)
            if kind == "shell":
                out = session.run_shell(payload)
                if out:
                    print(out)
            elif kind == "check":
                report = session.checks()
                print(render_check(report))
                if report.passed:
                    print("\n" + lv.victory_text.strip())
                    session.solved = True
                    won = True
                    if prog:
                        prog.complete(level_id)
                        prog.save()
                    break
            elif kind == "hint":
                h = session.next_hint()
                print(h if h else "No more hints.")
            elif kind == "objectives":
                for i, o in enumerate(lv.objectives, 1):
                    print(f"  {i}. {o}")
            elif kind == "solution":
                for i, s in enumerate(lv.solution, 1):
                    print(f"  [{i}] {s}")
            elif kind == "score":
                print(f"  score: {session.score}  hints: {session.hints_used}  "
                      f"completed: {len(prog.completed_ids) if prog else 0}")
            elif kind == "undo":
                session.undo()
                print("  box reset to broken state.")
            elif kind in ("quit", "exit"):
                break
            elif kind == "help":
                print("  check | hint | objectives | solution | undo | score | quit")
            else:
                out = session.run_shell(line)
                if out:
                    print(out)
    finally:
        session.close()
    if prog and won:
        print(f"  [{level_id}] marked complete — next tier unlocks.")
    return won


def pick_and_run() -> None:
    """Interactive tier ladder. Player picks a number → level starts.

    Numbers are flat (1…N across the whole campaign), so the player never
    types a level id — they just read the menu and enter a digit.
    """
    c = load_campaign()
    prog = default_progress()
    while True:
        print("\n" + render_tier_ladder(c, prog))
        choice = input("choice> ").strip()
        if choice.lower() in ("quit", "exit", "q"):
            return
        if choice.lower() in ("p", "prologue"):
            run_prologue(fake=True)
            continue
        if choice.isdigit():
            n = int(choice)
            flat = []
            for tier in c.tiers:
                flat.extend(tier.levels)
            if 1 <= n <= len(flat):
                lv = flat[n - 1]
                if lv.id in prog.completed_ids:
                    print(f"  ✓ {lv.title} — already complete.")
                    continue
                if prog.is_unlocked(lv.id):
                    run_level(lv.id, prog)
                    # after completing, re-show the ladder
                    prog.load()
                else:
                    print(f"  ✺ {lv.title} is LOCKED — finish: {', '.join(lv.prerequisites)}")
                continue
            print("  pick a valid number")
            continue
        # fallback: accept a level id too
        lv = c.get_level(choice)
        if lv and prog.is_unlocked(lv.id):
            run_level(lv.id, prog)
            prog.load()
            continue
        print("  not found — try a number from the menu")


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if argv and argv[0] in ("-h", "--help", "help"):
        print("sysadmin-zork — a noir Linux training game")
        print("usage: sysadmin-zork [level_id]")
        print("       sysadmin-zork prologue [--fake]")
        return 0
    if argv and argv[0] == "prologue":
        fake = "--fake" in argv[1:]
        return run_prologue(fake)
    if argv:
        return 1 if not run_level(argv[0]) else 0
    pick_and_run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
