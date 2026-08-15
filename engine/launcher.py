"""Interactive launcher for sysadmin-zork.

The launcher presents the tier/level ladder, spins up a sandboxed shell for the
selected level, and interprets meta-commands (`check`, `hint`, `objectives`,
`quit`, `undo`) interleaved with ordinary shell commands run against the
LocalTransport sandbox.

Player flow:
    sysadmin-zork                 → shows the tier ladder, prompts for a choice
    sysadmin-zork t0_l1           → jumps straight to a level
    zork> <shell command>         → piped to bash on the sandbox
    zork> check                   → runs win-conditions, prints PASS/FAIL
    zork> hint                    → reveals the next hint (costs points)
    zork> objectives              → lists the level's goals
    zork> solution                → (debug) replays the author's solution
    zork> undo                    → restores the broken baseline
    zork> quit|exit               → ends the session
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

from engine.checker import CheckReport, apply_setup, run_checks
from engine.level import Campaign, Level, load_campaign
from engine.transport import LocalTransport
from engine.vm import LocalHypervisor, Sandbox


# ── meta-command parser ────────────────────────────────────────

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

def render_tier_ladder(c: Campaign) -> str:
    lines = ["Sysadmin Zork — Tier Ladder", "=" * 24, ""]
    for tier in c.tiers:
        lines.append(f"  Tier {tier.number}: {tier.title}")
        for lv in tier.levels:
            tag = "VM" if lv.requires_real_vm else "sandbox"
            prereq = f"  ← {', '.join(lv.prerequisites)}" if lv.prerequisites else ""
            lines.append(f"    [{lv.order}] {lv.id}  ({tag}){prereq}")
        lines.append("")
    lines.append("Pick:  <t#>  or  <level_id>  or  quit")
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

    def __init__(self, level: Level, sandbox: Sandbox):
        self.level = level
        self.sandbox = sandbox
        self.hints_used = 0
        self.solved = False
        self._apply_setup()

    # lifecycle ──────────────────────────────────────────────
    @classmethod
    def for_level(cls, level_id: str, campaign: Campaign | None = None) -> "GameSession":
        c = campaign or load_campaign()
        lv = c.get_level(level_id)
        if lv is None:
            raise KeyError(f"level not found: {level_id}")
        root = pathlib.Path(tempfile.mkdtemp(prefix="zork-session-"))
        sb = Sandbox(LocalTransport(root), LocalHypervisor(root))
        sb.transport.connect()
        return cls(lv, sb)

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


# ── interactive loop ───────────────────────────────────────────

def run_level(level_id: str) -> None:
    session = GameSession.for_level(level_id)
    campaign = session  # alias for clarity
    lv = session.level
    print(render_level_start(lv.id, lv.tier, lv.title, lv.intro,
                             lv.objectives, len(lv.hints)))
    print(f"\n> box ready. type `check` to verify, `quit` to exit.\n")
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
                print(f"  score: {session.score}  hints: {session.hints_used}")
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


def pick_and_run() -> None:
    c = load_campaign()
    print(render_tier_ladder(c))
    while True:
        choice = input("choice> ").strip()
        if choice.lower() in ("quit", "exit", "q"):
            return
        # tier number
        if choice.isdigit():
            tier_num = int(choice)
            tier = next((t for t in c.tiers if t.number == tier_num), None)
            if not tier:
                print("  no such tier")
                continue
            print(f"  Tier {tier_num}: {tier.title}")
            for lv in tier.levels:
                print(f"    [{lv.order}] {lv.id} — {lv.title}")
            sub = input(f"  tier {tier_num} level> ").strip()
            if sub.lower() in ("back", "b"):
                continue
            # accept order number or id
            for lv in tier.levels:
                if sub == str(lv.order) or sub == lv.id:
                    run_level(lv.id)
                    return
            print("  not found")
            continue
        # level id
        lv = c.get_level(choice)
        if lv:
            run_level(lv.id)
            return
        print("  not found — try a level id or tier number")


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if argv and argv[0] in ("-h", "--help", "help"):
        print("sysadmin-zork — a noir Linux training game")
        print("usage: sysadmin-zork [level_id]")
        return 0
    if argv:
        run_level(argv[0])
    else:
        pick_and_run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
