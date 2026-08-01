"""The game loop: state machine over levels, meta-commands, and shell passthrough.

The player experiences: narrated incident -> real shell on the VM -> `check`.
Meta-commands (prefixed conceptually, matched exactly here) are handled by the
engine; everything else is passed straight to the sandbox shell.

Meta-commands:
    check        run the level's checker; on pass, score + unlock + advance
    hint         reveal the next hint (costs score)
    map          show the tier ladder with lock/unlock/cleared status
    look         re-print the current incident
    objectives   show the level's objective checklist
    reset        restore the clean snapshot and re-apply setup (a retry)
    score        show current potential score
    save         persist progress
    quit         save and exit

The loop is driven entirely through the Narrator, so a ScriptedNarrator makes
the whole thing testable without a terminal or a real VM.
"""

from __future__ import annotations

from dataclasses import dataclass

from engine.checker import apply_setup, run_checks
from engine.level import Campaign, Level
from engine.narrator import Narrator
from engine.profile import Profile
from engine.progression import LevelStatus, Progression
from engine.scoring import compute_score
from engine.session import LevelSession
from engine.vm import Sandbox

META_COMMANDS = {
    "check", "hint", "map", "look", "objectives", "reset", "score", "save", "quit", "help",
}


@dataclass
class Game:
    campaign: Campaign
    profile: Profile
    sandbox: Sandbox
    narrator: Narrator
    profiles_dir: object = None  # Path | None; kept loose to avoid import churn

    def __post_init__(self) -> None:
        self.progression = Progression(self.campaign, self.profile)
        self.session: LevelSession | None = None

    # -- level lifecycle ----------------------------------------------------- #
    def enter_level(self, level: Level) -> None:
        self.session = LevelSession(level)
        # Reset to a clean box, then break it into this level's puzzle state.
        self.sandbox.reset_to(self.profile.connection.baseline_snapshot)
        self.sandbox.reconnect()
        apply_setup(self.sandbox, level)
        self._narrate_intro(level)

    def _narrate_intro(self, level: Level) -> None:
        self.narrator.rule(f"{level.title}")
        self.narrator.say(level.intro)
        self.narrator.blank()
        self.narrator.status("Type real shell commands to solve it. Type `check` when ready. `help` for meta-commands.")

    # -- meta-command handlers ----------------------------------------------- #
    def cmd_look(self) -> None:
        assert self.session
        self.narrator.say(self.session.level.intro)

    def cmd_objectives(self) -> None:
        assert self.session
        self.narrator.say("Objectives:")
        for obj in self.session.level.objectives:
            self.narrator.say(f"  - {obj}")

    def cmd_hint(self) -> None:
        assert self.session
        hint = self.session.reveal_hint()
        if hint is None:
            self.narrator.say("No more hints. You're on your own now -- you've got this.")
        else:
            n, total = self.session.hints_used, self.session.hints.total
            self.narrator.say(f"Hint {n}/{total}: {hint}")

    def cmd_map(self) -> None:
        self.narrator.say("The night ahead:")
        for tier_title, level_title, status in self.progression.map_rows():
            mark = {"cleared": "[x]", "unlocked": "[ ]", "locked": "[-]"}[status]
            self.narrator.say(f"  {mark} {tier_title:<26} {level_title}  ({status})")
        badges = self.progression.badges()
        if badges:
            self.narrator.say(f"Badges earned: {', '.join('Tier ' + str(b) for b in badges)}")

    def cmd_score(self) -> None:
        assert self.session
        s = compute_score(
            self.session.level.scoring,
            elapsed_seconds=self.session.elapsed_seconds,
            hints_used=self.session.hints_used,
            retries=self.session.retries,
        )
        self.narrator.say(
            f"Current potential: {s.total}  "
            f"(base {s.base} + time {s.time_bonus} "
            f"- hints {s.hint_deduction} - retries {s.retry_deduction})"
        )

    def cmd_reset(self) -> None:
        assert self.session
        self.narrator.status("Restoring the clean baseline and rebuilding the scene...")
        self.sandbox.reset_to(self.profile.connection.baseline_snapshot)
        self.sandbox.reconnect()
        apply_setup(self.sandbox, self.session.level)
        self.session.restart()
        self.narrator.status("Reset. The box is clean again. Try again.")

    def cmd_save(self) -> None:
        self.profile.save(profiles_dir=self.profiles_dir)
        self.narrator.status("Progress saved.")

    def cmd_help(self) -> None:
        self.narrator.say("Meta-commands: " + ", ".join(sorted(META_COMMANDS)))
        self.narrator.say("Anything else goes straight to the box's shell.")

    def cmd_check(self) -> bool:
        """Run the checker. Return True if the level was cleared (advance)."""
        assert self.session
        level = self.session.level
        report = run_checks(self.sandbox, level)
        if not report.passed:
            self.narrator.say("Not solved yet:")
            for f in report.failures:
                self.narrator.say(f"  {f}")
            self.narrator.say("Keep at it. `hint` if you're stuck.")
            return False

        # Cleared! Score, token, narrate victory.
        s = compute_score(
            level.scoring,
            elapsed_seconds=self.session.elapsed_seconds,
            hints_used=self.session.hints_used,
            retries=self.session.retries,
        )
        self.progression.mark_cleared(level)
        self.profile.save(profiles_dir=self.profiles_dir)
        self.narrator.rule("SOLVED")
        self.narrator.say(level.victory_text)
        clean = " [CLEAN: no hints]" if s.clean else ""
        self.narrator.say(f"Score: {s.total}{clean}")
        if self.progression.tier_complete(level.tier):
            self.narrator.say(f"*** TIER {level.tier} CLEARED -- badge earned ***")
        return True

    # -- the loop ------------------------------------------------------------ #
    def _handle(self, command: str) -> bool | None:
        """Dispatch one input line.

        Returns:
            True  -> level cleared (advance)
            False -> quit requested
            None  -> continue in the same level
        """
        cmd = command.strip()
        if not cmd:
            return None
        if cmd == "quit":
            self.cmd_save()
            self.narrator.status("Shift's over. See you next time.")
            return False
        if cmd == "check":
            return True if self.cmd_check() else None
        dispatch = {
            "hint": self.cmd_hint,
            "map": self.cmd_map,
            "look": self.cmd_look,
            "objectives": self.cmd_objectives,
            "reset": self.cmd_reset,
            "score": self.cmd_score,
            "save": self.cmd_save,
            "help": self.cmd_help,
        }
        if cmd in dispatch:
            dispatch[cmd]()
            return None
        # Not a meta-command: pass through to the real shell.
        result = self.sandbox.run(cmd)
        if result.stdout:
            self.narrator.say(result.stdout.rstrip("\n"))
        if result.stderr:
            self.narrator.say(result.stderr.rstrip("\n"))
        return None

    def play(self, *, start_level_id: str | None = None, max_commands: int = 10_000) -> None:
        """Run the game from the given (or next-unlocked) level until quit/done."""
        level = (
            self.campaign.by_id(start_level_id)
            if start_level_id
            else self.progression.next_unlocked_level()
        )
        if level is None:
            self.narrator.say("Nothing to play -- every unlocked level is cleared. Nice work.")
            return
        if self.progression.status(level) == LevelStatus.LOCKED:
            self.narrator.say(f"'{level.title}' is locked. Clear its prerequisites first.")
            return

        self.enter_level(level)
        issued = 0
        while issued < max_commands:
            issued += 1
            line = self.narrator.ask("box$")
            outcome = self._handle(line)
            if outcome is False:  # quit
                return
            if outcome is True:  # cleared -> advance
                nxt = self.campaign.next_level(level.id)
                if nxt is None or self.progression.status(nxt) == LevelStatus.LOCKED:
                    self.narrator.say("\nThat's as far as the road goes for now. Well played.")
                    return
                level = nxt
                self.enter_level(level)
