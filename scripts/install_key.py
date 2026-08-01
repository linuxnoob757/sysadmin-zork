"""One-off bootstrap: install the engine's public key onto the VM over SSH.

Uses paramiko (the same lib the engine uses) to connect with a password once,
drop the public key into student's authorized_keys with correct perms + SELinux
context, then it's key-only from then on. Not part of the shipped engine --
this is the manual step the game's install *prologue* will eventually automate.
"""

import pathlib
import sys

import paramiko

HOST = "192.168.56.101"
USER = "student"
PASSWORD = "student123"

pubkey = pathlib.Path.home().joinpath(".ssh", "sysadmin-zork.pub").read_text().strip()

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(
    HOST, username=USER, password=PASSWORD, timeout=15,
    allow_agent=False, look_for_keys=False,
)
print("[1] password login OK")

commands = (
    "mkdir -p ~/.ssh && chmod 700 ~/.ssh",
    f"grep -qxF '{pubkey}' ~/.ssh/authorized_keys 2>/dev/null "
    f"|| echo '{pubkey}' >> ~/.ssh/authorized_keys",
    "chmod 600 ~/.ssh/authorized_keys",
    "restorecon -R ~/.ssh 2>/dev/null || true",  # RHEL/SELinux: fix context
)
for cmd in commands:
    _in, out, err = client.exec_command(cmd)
    rc = out.channel.recv_exit_status()
    e = err.read().decode().strip()
    label = cmd[:55].replace("\n", " ")
    print(f"[2] rc={rc} :: {label}" + (f"  ERR:{e}" if e else ""))

client.close()
print("[3] public key installed")
