# Sysadmin Zork — Implementation Plan (rebuilt from scratch)

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.
> TDD: RED (setup produces pre-solved state? fix it) → GREEN (solution passes checks).
> Windows constraint: `chmod`/`stat` mode-bit checks DON'T work on NTFS temp dirs
> (chmod is a no-op, stat returns 644 regardless). Tier 1 avoids mode-bit checks;
> Tier 2+ uses `requires_real_vm: true` and is skipped on Windows.

**Goal:** Build all 5 tiers from scratch (Onboarding → The Observatory).

---

## Ground Zero — DONE (commit 4ac38a9)
- `pyproject.toml` (uv, `package=false`, pytest `pythonpath=["."]`)
- `engine/level.py` — `Level`/`CheckSpec`/`Campaign` dataclasses + `load_campaign`
- `engine/transport.py` — `LocalTransport` (chroot POSIX, MSYS-remap Windows)
- `engine/vm.py` — `Sandbox` + `LocalHypervisor`
- `engine/checker.py` — `run_checks`/`apply_setup` (8 check kinds)
- `content/levels/t0_l1_first_shift.yaml` + `tiers.yaml`
- `tests/test_engine.py` (3) + `tests/test_content.py` (harness) → 5/5 green

## Tier 1 — Navigation & Files — DONE
t1_l1 directory_layout, t1_l2 permissions (file-log checks — no stat mode bits),
t1_l3 pipes_redirects, t1_l4 find_grep_awk, t1_l5 users_groups (etc/group+passwd)
→ 16/16 green (3 engine + 2 isolation/win checks + 2 levels × 2 harness checks + 10 level tests)
