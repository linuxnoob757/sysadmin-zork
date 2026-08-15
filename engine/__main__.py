"""Package entry point: `python -m engine <subcommand> [...]`.

Subcommands understood by the launcher:
  play [--fake] [--level <id>]   Start the interactive zork> session.
                                  --fake  → LocalTransport sandbox (no VM).
                                  --level → jump to a specific quest id.
  prologue                       Guided OS install + SSH handshake (future).
  spike [--fake]                 Self-check: proves VM/SSH/snapshot loop (future).

The interactive loop lives in engine.launcher.run_level / GameSession.
This module just parses argv and dispatches — the bat calls us.
"""
from __future__ import annotations

import sys

from engine.launcher import GameSession, pick_and_run, run_level


def _cmd_play(fake: bool, level_id: str | None) -> int:
    if level_id:
        if fake:
            run_level(level_id)
        else:
            # Real-VM transport dispatch lives in engine.prologue / a future
            # vm transport; for now delegate to the fake loop with a notice.
            print("[play] real-VM transport is not wired yet — falling back to "
                  "the sandbox loop. (Implement engine/vm.py SSH transport "
                  "for 'play' without --fake.)")
            run_level(level_id)
        return 0
    # no level → show the ladder and let the player pick
    pick_and_run()
    return 0


def _cmd_prologue(fake: bool) -> int:
    msg = "prologue: guided OS install + SSH handshake (not yet implemented)"
    if fake:
        msg += " — the --fake prologue self-check is available via `spike`."
    print(msg)
    return 0


def _cmd_spike(fake: bool) -> int:
    if not fake:
        print("spike: real-VM mode not available yet; rerun with --fake.")
        return 1
    # Minimal self-check: load campaign, build a sandbox, run setup+solver on
    # the first sandbox-safe level, and report PASS/FAIL.
    from engine.checker import apply_setup, run_checks
    from engine.level import load_campaign
    from engine.transport import LocalTransport
    from engine.vm import LocalHypervisor, Sandbox
    import pathlib, tempfile

    c = load_campaign()
    first = next(lv for lv in c.levels if not lv.requires_real_vm)
    root = pathlib.Path(tempfile.mkdtemp(prefix="zork-spike-"))
    sb = Sandbox(LocalTransport(root), LocalHypervisor(root))
    sb.transport.connect()
    # 1) broken state: setup should make checks fail
    apply_setup(sb, first)
    broken = run_checks(sb, first)
    if broken.passed:
        sb.transport.close()
        return (print(f"spike: WARN — {first.id} is pre-solved"), 0)[1]
    # 2) solution should make checks pass
    for cmd in first.solution:
        sb.run(cmd, timeout=5.0)
    solved = run_checks(sb, first)
    sb.transport.close()
    if solved.passed:
        print(f"spike: PASS — {first.id} (broken→solved) on {root}")
        return 0
    print(f"spike: FAIL — {first.id} still broken after solution: {solved.failures}")
    return 1


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    if not argv:
        print(__doc__.strip().splitlines()[0])
        return 1

    cmd, rest = argv[0], argv[1:]
    fake = "--fake" in rest
    rest = [a for a in rest if a != "--fake"]
    level_id = None
    if "--level" in rest:
        i = rest.index("--level")
        level_id = rest[i + 1] if i + 1 < len(rest) else None

    if cmd == "play":
        return _cmd_play(fake, level_id)
    elif cmd == "prologue":
        return _cmd_prologue(fake)
    elif cmd == "spike":
        return _cmd_spike(fake)
    elif cmd in ("-h", "--help", "help"):
        print(__doc__.strip().splitlines()[0])
        return 0
    print(f"unknown subcommand: {cmd}  (try: play, prologue, spike)")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
