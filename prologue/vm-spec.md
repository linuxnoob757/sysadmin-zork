# VM Spec Sheet

The required configuration for your Sysadmin Zork VM. The prologue prints a
condensed version of this; the full detail lives here.

## Hardware

| Setting  | Value                        | Why |
|----------|------------------------------|-----|
| CPU      | 2 cores                      | Enough for services + a responsive shell |
| Memory   | 2048 MB (4096 if you can)    | Rocky/Alma minimal is light; 4 GB is comfortable |
| Disk     | 20 GB, dynamically allocated | Room for later tiers (services, logs, LVM) |
| Firmware | EFI                          | Matches modern RHEL installs |

## Networking

- **NIC 1:** NAT — gives the VM internet during install (package downloads).
- **NIC 2:** Host-Only (`VirtualBox Host-Only Ethernet Adapter`, `192.168.56.x`)
  — this is how the game engine reaches the VM over SSH.
- **NO shared folders.** The VM stays quarantined from your real machine; that
  isolation is what makes it safe to break things.

## OS

- **Rocky Linux** or **AlmaLinux**, the **minimal** ISO (RHEL-family, RHCSA-aligned).
- Software selection: **Minimal Install** (no desktop).

## Accounts

- **root:** disabled (recommended RHEL posture).
- **student:** create this user, and **check "Make this user administrator"**
  (this puts `student` in the `wheel` group so `sudo` works — the whole game
  depends on it).

## Before the handshake

On the VM, enable SSH so the engine can connect:

```bash
sudo systemctl enable --now sshd
ip a    # note the 192.168.56.x address under the host-only adapter
```
