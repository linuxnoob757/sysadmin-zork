"""Narrator: renders the game's text and collects player input.

All player-facing output and input funnels through a `Narrator` so that:
- tests can drive the game with scripted input and capture output (no real
  terminal), and
- styling/formatting lives in one place.

The default `Narrator` uses stdin/stdout. Tests use `ScriptedNarrator`, which
feeds a queue of canned answers and records everything printed.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Iterable


class Narrator:
    """Prints narrative text and reads player input from a real terminal."""

    def __init__(self, *, out=sys.stdout, in_=sys.stdin, slow: bool = False) -> None:
        self._out = out
        self._in = in_
        self._slow = slow  # reserved: typewriter effect later; off by default

    # -- output -------------------------------------------------------------- #
    def say(self, text: str = "") -> None:
        """Print a block of narrative text."""
        self._out.write(text + "\n")
        self._out.flush()

    def blank(self) -> None:
        self.say("")

    def rule(self, label: str = "") -> None:
        line = "-" * 62
        self.say(f"\n{line}")
        if label:
            self.say(label)

    def status(self, text: str) -> None:
        """A system/engine status line (distinct from story narration)."""
        self.say(f"  > {text}")

    def beat(self, seconds: float = 0.0) -> None:
        """A dramatic pause (skipped when slow output is disabled)."""
        if self._slow and seconds > 0:
            time.sleep(seconds)

    # -- input --------------------------------------------------------------- #
    def ask(self, prompt: str, *, default: str | None = None) -> str:
        """Prompt for a line of input; return default on empty when provided."""
        suffix = f" [{default}]" if default is not None else ""
        self._out.write(f"{prompt}{suffix}: ")
        self._out.flush()
        line = self._in.readline()
        if line == "":  # EOF
            return default or ""
        answer = line.rstrip("\n")
        if not answer and default is not None:
            return default
        return answer

    def ask_secret(self, prompt: str) -> str:
        """Prompt for sensitive input (password). Falls back to plain read.

        Uses getpass on a real TTY so the password isn't echoed; tests inject a
        ScriptedNarrator which overrides this.
        """
        import getpass

        try:
            return getpass.getpass(f"{prompt}: ")
        except (EOFError, OSError):
            return self.ask(prompt)

    def confirm(self, prompt: str) -> bool:
        answer = self.ask(f"{prompt} (y/n)", default="y").strip().lower()
        return answer in ("y", "yes")

    def wait_enter(self, prompt: str = "Press ENTER when ready") -> None:
        self._out.write(f"{prompt}...")
        self._out.flush()
        self._in.readline()


class ScriptedNarrator(Narrator):
    """A Narrator for tests: canned answers in, captured output recorded.

    `answers` is consumed in order for every ask/ask_secret/confirm/wait_enter.
    Everything printed is appended to `.output` (also joined via `.text`).
    """

    def __init__(self, answers: Iterable[str] | None = None) -> None:
        self._answers = list(answers or [])
        self._idx = 0
        self.output: list[str] = []

    # capture output
    def say(self, text: str = "") -> None:
        self.output.append(text)

    def status(self, text: str) -> None:
        self.output.append(f"  > {text}")

    def rule(self, label: str = "") -> None:
        self.output.append("-" * 62)
        if label:
            self.output.append(label)

    def beat(self, seconds: float = 0.0) -> None:
        pass

    # scripted input
    def _next(self, default: str | None = None) -> str:
        if self._idx < len(self._answers):
            val = self._answers[self._idx]
            self._idx += 1
            return val
        return default or ""

    def ask(self, prompt: str, *, default: str | None = None) -> str:
        self.output.append(f"?? {prompt}")
        return self._next(default)

    def ask_secret(self, prompt: str) -> str:
        self.output.append(f"?? {prompt}")
        return self._next()

    def confirm(self, prompt: str) -> bool:
        self.output.append(f"?? {prompt}")
        return self._next("y").strip().lower() in ("y", "yes")

    def wait_enter(self, prompt: str = "Press ENTER when ready") -> None:
        self.output.append(f"?? {prompt}")
        self._next()

    @property
    def text(self) -> str:
        return "\n".join(self.output)
