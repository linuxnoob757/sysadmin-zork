"""Create/refresh the persistent 'default' profile for the real VM.

The engine key is already installed on the VM (Phase 0/1), so we don't need the
password again -- we just record the known-good connection details and a clean
prologue_complete=True profile into profiles/default.json.
"""

import pathlib

from engine.profile import Connection, Profile

KEY = r"C:\Users\Adam\.ssh\sysadmin-zork"
VBM = r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe"

profile = Profile.load("default")  # fresh if none
profile.connection = Connection(
    host="192.168.56.101",
    port=22,
    user="student",
    key_path=KEY,
    vm_name="sysadmin-zork",
    vboxmanage=VBM,
    baseline_snapshot="clean-baseline",
)
profile.prologue_complete = True
path = profile.save()
print(f"Saved profile to: {path}")
print(f"  player_id: {profile.player_id}")
print(f"  connection complete: {profile.connection.is_complete()}")
print(f"  prologue_complete: {profile.prologue_complete}")
