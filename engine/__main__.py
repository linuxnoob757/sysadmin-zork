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
    """Guided OS install + SSH handshake.

    Real VM (no --fake): prints the interactive install checklist and waits
    for the player to confirm each step after installing Rocky Linux by hand.

    --fake: simulates the handshake steps against a fresh sandbox so the
    engine's path to the game (hostname → user → sshd → /etc/hosts → verify)
    is provable without a VM.
    """
    if not fake:
        return _prologue_interactive()
    return _prologue_fake()


def _prologue_interactive() -> int:
    print("""\
PROLOGUE — Guided OS Install + SSH Handshake
=============================================
Install Rocky Linux 9 in the VM, then confirm each step:

  1. Hostname:      hostnamectl set-hostname zork-prod
  2. User:           useradd -m -G wheel student && passwd student
  3. SSHD:           sudo systemctl enable --now sshd
  4. Network:        ensure 192.168.56.x on the host-only adapter
  5. Handshake:      ssh student@192.168.56.<host>

Type the step number + ENTER after completing each. `q` when done.
""")
    steps = ["hostname", "user", "sshd", "network", "handshake"]
    done = [False] * 5
    while True:
        print("  status:", " ".join(f"[{i+1}{'*' if done[i] else ' '}]" for i in range(5)))
        try:
            line = input("step?> ").strip()
        except EOFError:
            break
        if line.lower() in ("q", "quit", "exit"):
            break
        if line.isdigit() and 1 <= int(line) <= 5:
            i = int(line) - 1
            done[i] = True
            print(f"  marked {steps[i]} done. Next?")
        else:
            print("  enter 1-5, or q")
    all_done = all(done)
    print("\nPROLOGUE:", "ALL STEPS CONFIRMED — the box is yours." if all_done
          else "incomplete — re-run prologue to continue.")
    return 0 if all_done else 1


def _prologue_fake() -> int:
    """Fake handshake: prove the handshake path end-to-end in a sandbox."""
    import pathlib, tempfile
    from engine.transport import LocalTransport
    from engine.vm import LocalHypervisor, Sandbox

    print("""\
PROLOGUE (fake) — Simulated OS Install + SSH Handshake
=======================================================
Walking the install path in a sandbox:
  1. hostname → /etc/hostname
  2. user     → /etc/passwd entry for `student`
  3. sshd     → /etc/ssh/sshd_config exists
  4. network  → /etc/hosts with the box IP
  5. handshake→ /tmp/.ssh-handshake confirms the route
""")
    root = pathlib.Path(tempfile.mkdtemp(prefix="zork-prologue-"))
    sb = Sandbox(LocalTransport(root), LocalHypervisor(root))
    sb.transport.connect()

    # step 1: hostname
    sb.run("printf 'zork-prod\\n' > /etc/hostname", timeout=5.0)
    # step 2: user
    sb.run("printf 'student:x:1000:1000::/home/student:/bin/bash\\n' >> /etc/passwd", timeout=5.0)
    # step 3: sshd config
    sb.run("mkdir -p /etc/ssh && printf 'Port 22\\n' > /etc/ssh/sshd_config", timeout=5.0)
    # step 4: network hosts
    sb.run("printf '127.0.0.1 localhost\\n192.168.56.10 zork-prod\\n' > /etc/hosts", timeout=5.0)
    # step 5: handshake marker
    sb.run("printf 'handshake: ssh student@192.168.56.10 OK\\n' > /tmp/.ssh-handshake", timeout=5.0)

    checks = [
        ("/etc/hostname", "zork-prod", "hostname set"),
        ("/etc/passwd", "/home/student", "student user present"),
        ("/etc/ssh/sshd_config", "Port 22", "sshd configured"),
        ("/etc/hosts", "192.168.56.10", "network configured"),
        ("/tmp/.ssh-handshake", "OK", "handshake confirmed"),
    ]
    all_ok = True
    for path, expect, label in checks:
        p = sb.transport.abs_path(path)
        ok = p.exists() and expect in p.read_text(errors="replace")
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
        if not ok:
            all_ok = False
    sb.transport.close()
    print("\nPROLOGUE:", "PASS — handshake path verified." if all_ok
          else "FAIL — something broke in the install path.")
    return 0 if all_ok else 1


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
        # no subcommand → drop into the interactive tier ladder
        from engine.launcher import pick_and_run
        pick_and_run()
        return 0

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
