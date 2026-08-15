"""LocalTransport: isolates /etc /home /srv /var under a temp sandbox root.

POSIX: uses `chroot` for true isolation.
Windows (Git-bash): no chroot, so absolute path *arguments* and redirect
targets (`/etc/x`, `> /srv/x`) are rewritten to prefix the sandbox root,
and the temp root is converted to MSYS-posix form (`C:\...` → `/c/...`)
so `$HOME`/`~` expansions resolve inside the sandbox.
"""
from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class Result:
    exit_code: int
    stdout: str
    stderr: str


class LocalTransport:
    def __init__(self, root: pathlib.Path | str):
        self.root = pathlib.Path(root)
        self._connected = False

    def connect(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        for sub in ("etc", "home/student", "srv", "var/lib", "var/log", "tmp", "opt"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)
        self._connected = True

    def close(self) -> None:
        self._connected = False

    def abs_path(self, path: str | pathlib.Path) -> pathlib.Path:
        if isinstance(path, pathlib.Path):
            if path.is_absolute():
                return self.root / path.relative_to(path.anchor)
            return self.root / path
        p = str(path)
        p = p.lstrip("/")
        if len(p) >= 2 and p[1] == ":":
            p = p[2:].lstrip("/\\")
        return self.root / p

    def _msys(self, p: pathlib.Path) -> str:
        s = str(p).replace("\\", "/")
        if len(s) >= 2 and s[1] == ":":
            s = "/" + s[0].lower() + s[2:]
        return s

    def _rewrite(self, cmd: str) -> str:
        if sys.platform.startswith("win"):
            root_msys = self._msys(self.root)
            # Rewrite bare /path references and redirect targets to sandbox root.
            # (Rewrite the USER command only, then prepend the preamble — do not
            # let the regex mangle the already-correct HOME/PATH exports.)
            cmd = re.sub(r"(^|\s)(/)([\w/.-]+)",
                         lambda m: m.group(1) + root_msys + m.group(2) + m.group(3), cmd)
            preamble = (
                f'cd "{root_msys}" && '
                f'export HOME="{root_msys}/home/student" && '
                f'export PATH="/usr/bin:/bin:/usr/sbin:/sbin:$PATH" && '
            )
            return preamble + cmd
        bash_bin = "/bin/bash" if pathlib.Path("/bin/bash").exists() else "/usr/bin/bash"
        quoted = "'" + cmd.replace("'", "'\\''") + "'"
        return f"chroot {self.root} {bash_bin} -c {quoted}"

    def run(self, cmd: str, timeout: float = 30.0) -> Result:
        if not self._connected:
            self.connect()
        wrapped = self._rewrite(cmd)
        try:
            proc = subprocess.run(
                ["bash", "-c", wrapped],
                capture_output=True, text=True, timeout=timeout,
            )
            return Result(proc.returncode, proc.stdout, proc.stderr)
        except subprocess.TimeoutExpired:
            return Result(124, "", "timeout")
        except FileNotFoundError:
            return Result(127, "", "bash not found")

    def read_file(self, path: str) -> str:
        p = self.abs_path(path)
        return p.read_text(errors="replace") if p.exists() else ""

    def write_file(self, path: str, content: str) -> None:
        p = self.abs_path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
