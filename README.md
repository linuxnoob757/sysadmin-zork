# Sysadmin Zork

A Zork-style text adventure that teaches real Linux system administration. You
solve narrative "incidents" using genuine shell commands on a **real Rocky/Alma
Linux VM** you install yourself. Gated difficulty tiers, real victory checks, a
light-noir story. Targets RHCSA-flavored skills.

> **Status: Phase 0 — the VM/SSH/snapshot spike.** No game yet. This phase
> proves the single riskiest assumption of the whole project: that Python can
> drive a real VM over SSH and use hypervisor snapshots to reset it between
> levels.

## Architecture (why a VM, not Docker)

The game engine never runs the puzzle itself — it orchestrates a persistent VM:

```
engine (Python)  ──SSH──▶  your Rocky/Alma VM   (runs the real Linux commands)
      │
      └──VBoxManage──▶  snapshots   (restore-to-clean before each level)
```

Everything above the transport layer (story, gating, scoring) is hypervisor-
agnostic. `transport.py` and `vm.py` isolate all the SSH/VirtualBox specifics
behind small protocols, each with a **fake** implementation so the engine logic
is fully testable without a real VM.

## The Phase 0 spike

The spike proves this loop end-to-end:

1. Connect to the VM over SSH and run a command.
2. Take a snapshot (`clean-baseline`).
3. Make a destructive change (drop a marker file).
4. Restore the snapshot.
5. Confirm the change is **gone** — proving snapshot rollback works.

### Run it against fakes (works anywhere, no VM needed)

```bash
uv run python -m engine spike --fake
```

This runs the identical spike logic against an in-memory fake VM whose snapshot
restore genuinely rolls back state. It's how we prove the orchestration is
correct before any hardware is involved. This is also what CI runs.

### Run it against a real VM (needs VirtualBox + an installed Rocky/Alma VM)

```bash
uv run python -m engine spike \
    --host 192.168.56.10 --user student --key ~/.ssh/id_ed25519 \
    --vm "sysadmin-zork" --snapshot clean-baseline
```

Prerequisites for the real run:
- VirtualBox installed (`VBoxManage` on PATH, or pass `--vboxmanage <path>`).
- A Rocky/Alma VM created, with `sshd` enabled and your SSH key installed
  (this is exactly what the game's install *prologue* will guide a player
  through; for the spike you do it by hand once).

## Tests

```bash
uv run pytest
```

The suite proves the spike and the snapshot-rollback contract against the fake
transport/hypervisor — fast, deterministic, no VM.

## Layout

```
engine/
  transport.py   Transport protocol + SSHTransport (paramiko) + FakeTransport
  vm.py          Hypervisor protocol + VBoxHypervisor + FakeHypervisor + Sandbox
  spike.py       the Phase 0 proof
  __main__.py    CLI entry point
tests/
  test_spike.py  proves the loop + rollback against fakes
```
