"""CLI entry point.

    python -m engine spike --fake
    python -m engine spike --host H --user U --key ~/.ssh/id_ed25519 --vm NAME
    python -m engine prologue --vm NAME     (guided VM-install first mission)

Subcommands: `spike` (Phase 0), `prologue` (Phase 1).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _add_spike_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--fake",
        action="store_true",
        help="Run against in-memory fakes (no VM/VirtualBox needed).",
    )
    p.add_argument("--host", help="VM SSH host/IP.")
    p.add_argument("--user", default="student", help="SSH user (default: student).")
    p.add_argument("--key", help="Path to SSH private key.")
    p.add_argument("--port", type=int, default=22, help="SSH port (default: 22).")
    p.add_argument("--vm", help="VirtualBox VM name.")
    p.add_argument("--snapshot", default="clean-baseline", help="Baseline snapshot name.")
    p.add_argument("--vboxmanage", help="Full path to VBoxManage(.exe) if not on PATH.")


def _cmd_spike(args: argparse.Namespace) -> int:
    from engine import spike as spike_mod

    if args.fake:
        print("=== Sysadmin Zork :: Phase 0 spike (FAKE transport) ===\n")
        sandbox = spike_mod.build_fake_sandbox()
    else:
        missing = [f for f in ("host", "key", "vm") if not getattr(args, f)]
        if missing:
            print(
                "Real run needs --host, --key and --vm "
                f"(missing: {', '.join('--' + m for m in missing)}).\n"
                "Or run against fakes with:  python -m engine spike --fake",
                file=sys.stderr,
            )
            return 2
        print("=== Sysadmin Zork :: Phase 0 spike (REAL VM over SSH) ===\n")
        sandbox = spike_mod.build_real_sandbox(
            host=args.host,
            user=args.user,
            key=args.key,
            vm=args.vm,
            port=args.port,
            vboxmanage=args.vboxmanage,
        )

    # Allow a custom baseline snapshot name to flow through.
    try:
        with sandbox:
            report = spike_mod.run_spike(sandbox, snapshot_name=args.snapshot)
    except Exception as exc:  # surface real connection/hypervisor errors clearly
        print(f"\nSPIKE ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print("\n--- result ---")
    if report.passed:
        print("SPIKE PASSED: SSH command ran, snapshot taken, change made, "
              "and rollback removed it. The VM/SSH/snapshot loop works.")
        return 0
    print("SPIKE FAILED. Step-by-step:")
    for field_name, value in vars(report).items():
        print(f"  {field_name}: {value}")
    return 1


def _ensure_keypair(key_path: Path) -> str:
    """Ensure an SSH keypair exists at key_path; return the public key text."""
    pub_path = key_path.with_suffix(key_path.suffix + ".pub") if key_path.suffix else Path(str(key_path) + ".pub")
    if key_path.exists() and pub_path.exists():
        return pub_path.read_text(encoding="utf-8").strip()
    key_path.parent.mkdir(parents=True, exist_ok=True)
    import subprocess

    subprocess.run(
        ["ssh-keygen", "-t", "ed25519", "-f", str(key_path), "-N", "", "-C", "sysadmin-zork-engine"],
        check=True,
        capture_output=True,
        text=True,
    )
    return pub_path.read_text(encoding="utf-8").strip()


def _cmd_prologue(args: argparse.Namespace) -> int:
    from engine.narrator import Narrator
    from engine.profile import Profile
    from engine.prologue import run_prologue

    key_path = Path(args.key).expanduser() if args.key else (Path.home() / ".ssh" / "sysadmin-zork")
    try:
        public_key = _ensure_keypair(key_path)
    except Exception as exc:
        print(f"Could not create/read SSH key at {key_path}: {exc}", file=sys.stderr)
        return 1

    profile = Profile.load(args.profile)
    narrator = Narrator()
    result = run_prologue(
        narrator,
        profile=profile,
        public_key=public_key,
        key_path=str(key_path),
        vm_name=args.vm,
        vboxmanage=args.vboxmanage,
    )
    if result.complete:
        return 0
    print("\nPrologue did not complete. See messages above.", file=sys.stderr)
    return 1


def _cmd_play(args: argparse.Namespace) -> int:
    from engine.game import Game
    from engine.loader import load_campaign
    from engine.narrator import Narrator
    from engine.profile import Profile

    profile = Profile.load(args.profile)
    campaign = load_campaign()  # content/*.yaml
    narrator = Narrator()

    if args.fake:
        from engine.transport import FakeTransport
        from engine.vm import FakeHypervisor, Sandbox

        transport = FakeTransport()
        transport.connect()
        hypervisor = FakeHypervisor(transport)
        sandbox = Sandbox(transport, hypervisor)
        hypervisor.take_snapshot(profile.connection.baseline_snapshot)
    else:
        if not profile.prologue_complete or not profile.connection.is_complete():
            print(
                "No provisioned VM in this profile. Run the prologue first:\n"
                "    python -m engine prologue\n"
                "Or try the game logic against fakes:  python -m engine play --fake",
                file=sys.stderr,
            )
            return 2
        from engine.transport import SSHTransport
        from engine.vm import Sandbox, VBoxHypervisor

        conn = profile.connection
        transport = SSHTransport(host=conn.host, user=conn.user, key_path=conn.key_path, port=conn.port)
        hypervisor = VBoxHypervisor(conn.vm_name, vboxmanage=conn.vboxmanage)
        sandbox = Sandbox(transport, hypervisor)
        transport.connect()

    game = Game(campaign=campaign, profile=profile, sandbox=sandbox, narrator=narrator)
    try:
        game.play(start_level_id=args.level)
    finally:
        try:
            sandbox.transport.close()
        except Exception:
            pass
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="engine", description="Sysadmin Zork engine.")
    sub = parser.add_subparsers(dest="command", required=True)

    spike_p = sub.add_parser("spike", help="Run the Phase 0 VM/SSH/snapshot spike.")
    _add_spike_args(spike_p)
    spike_p.set_defaults(func=_cmd_spike)

    prologue_p = sub.add_parser("prologue", help="Run the guided VM-install prologue (Phase 1).")
    prologue_p.add_argument("--vm", default="sysadmin-zork", help="VirtualBox VM name.")
    prologue_p.add_argument("--key", help="SSH private key path (created if absent).")
    prologue_p.add_argument("--profile", default="default", help="Player profile name.")
    prologue_p.add_argument("--vboxmanage", help="Full path to VBoxManage(.exe) if not on PATH.")
    prologue_p.set_defaults(func=_cmd_prologue)

    play_p = sub.add_parser("play", help="Play the game (Phase 2 engine core).")
    play_p.add_argument("--profile", default="default", help="Player profile name.")
    play_p.add_argument("--level", help="Start at a specific level id (default: next unlocked).")
    play_p.add_argument("--fake", action="store_true", help="Play against fakes (no VM needed).")
    play_p.set_defaults(func=_cmd_play)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
