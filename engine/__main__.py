"""CLI entry point.

    python -m engine spike --fake
    python -m engine spike --host H --user U --key ~/.ssh/id_ed25519 --vm NAME

Phase 0 exposes exactly one subcommand: `spike`.
"""

from __future__ import annotations

import argparse
import sys


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
    spike_mod.BASELINE_SNAPSHOT = args.snapshot

    try:
        with sandbox:
            report = spike_mod.run_spike(sandbox)
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="engine", description="Sysadmin Zork engine.")
    sub = parser.add_subparsers(dest="command", required=True)
    spike_p = sub.add_parser("spike", help="Run the Phase 0 VM/SSH/snapshot spike.")
    _add_spike_args(spike_p)
    spike_p.set_defaults(func=_cmd_spike)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
