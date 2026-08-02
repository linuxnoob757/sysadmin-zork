"""Transport layer: how the engine runs commands on the VM.

The engine talks to the puzzle VM through a small `Transport` protocol. Two
implementations exist:

- `SSHTransport`  -- the real thing, over SSH (paramiko).
- `FakeTransport` -- an in-memory Linux-ish shell good enough to prove the
  orchestration logic (and snapshot rollback) without a real VM.

Keeping this behind a protocol is what lets the whole engine be unit-tested
with no hypervisor present, and is the core bet of the Phase 0 spike.
"""

from __future__ import annotations

import os
import pathlib
import socket
import subprocess
import time

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class CommandResult:
    """Result of running one command on the VM."""

    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


@runtime_checkable
class Transport(Protocol):
    """Runs commands on the puzzle machine and moves files onto it."""

    def connect(self) -> None:
        """Establish the connection. Idempotent."""
        ...

    def run(self, command: str, *, timeout: float | None = None) -> CommandResult:
        """Run a shell command, return its result."""
        ...

    def put_file(self, remote_path: str, content: str, *, mode: int = 0o644) -> None:
        """Write `content` to `remote_path` on the VM."""
        ...

    def close(self) -> None:
        """Tear down the connection. Idempotent."""
        ...


# --------------------------------------------------------------------------- #
# Real transport: SSH via paramiko
# --------------------------------------------------------------------------- #
class SSHTransport:
    """Talks to a real VM over SSH using key-based auth.

    Auth is key-based for normal play (the game hardens the VM to keys-only in
    Tier 4, and the engine lives by the rules it teaches). A one-time
    `password` may be supplied so the prologue can make its very first
    connection and install the engine's public key; after that, key auth is
    used everywhere.
    """

    def __init__(
        self,
        host: str,
        user: str,
        key_path: str,
        *,
        port: int = 22,
        password: str | None = None,
        connect_timeout: float = 15.0,
        retries: int = 4,
        retry_delay: float = 2.0,
    ) -> None:
        self.host = host
        self.user = user
        self.key_path = key_path
        self.port = port
        self.password = password
        self.connect_timeout = connect_timeout
        self.retries = retries
        self.retry_delay = retry_delay
        self._client = None  # lazy: paramiko only imported/used for real runs

    def connect(self) -> None:
        if self._client is not None:
            return
        try:
            import paramiko
        except ImportError as exc:  # pragma: no cover - environment guard
            raise RuntimeError(
                "paramiko is required for real SSH transport. "
                "Install it (`uv pip install paramiko`) or use --fake."
            ) from exc

        import time

        # Password mode (first prologue handshake) vs key mode (everything else).
        use_password = bool(self.password)

        last_exc: Exception | None = None
        for attempt in range(1, self.retries + 1):
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                kwargs = dict(
                    hostname=self.host,
                    port=self.port,
                    username=self.user,
                    timeout=self.connect_timeout,
                    banner_timeout=self.connect_timeout,
                    auth_timeout=self.connect_timeout,
                    allow_agent=False,
                    look_for_keys=False,
                )
                if use_password:
                    kwargs["password"] = self.password
                else:
                    kwargs["key_filename"] = self.key_path
                client.connect(**kwargs)
                self._client = client
                return
            except paramiko.AuthenticationException:
                # A real credential problem -- retrying won't fix it.
                client.close()
                raise
            except paramiko.SSHException as exc:
                # Transient on freshly-booted VMs: sshd is slow to send its
                # banner. Close, wait, and retry a few times before giving up.
                last_exc = exc
                client.close()
                if attempt < self.retries:
                    time.sleep(self.retry_delay)
        raise RuntimeError(
            f"SSH connect to {self.user}@{self.host}:{self.port} failed after "
            f"{self.retries} attempts: {last_exc}"
        )

    def append_authorized_key(self, public_key: str) -> None:
        """Install an SSH public key into the connected user's authorized_keys.

        Idempotent, and fixes perms + SELinux context (the latter matters on
        RHEL -- without restorecon, sshd refuses the key). This is the prologue
        handshake step that flips the VM from password auth to key auth.
        """
        pub = public_key.strip().replace("'", "'\\''")
        script = (
            "mkdir -p ~/.ssh && chmod 700 ~/.ssh && "
            f"(grep -qxF '{pub}' ~/.ssh/authorized_keys 2>/dev/null || "
            f"echo '{pub}' >> ~/.ssh/authorized_keys) && "
            "chmod 600 ~/.ssh/authorized_keys && "
            "restorecon -R ~/.ssh 2>/dev/null || true"
        )
        result = self.run(script)
        if not result.ok:
            raise RuntimeError(f"Failed to install public key: {result.stderr}")

    def run_with_input(
        self, command: str, stdin_text: str, *, timeout: float | None = None
    ) -> CommandResult:
        """Run a command, feeding `stdin_text` to its stdin, then closing it.

        This is how we hand a password to `sudo -S` without ever placing it in
        the command string (where quoting bugs or `ps`/history could leak it).
        """
        if self._client is None:
            raise RuntimeError("connect() must be called before run_with_input().")
        stdin, stdout, stderr = self._client.exec_command(command, timeout=timeout)
        try:
            stdin.write(stdin_text)
            stdin.flush()
            stdin.channel.shutdown_write()
        except OSError:
            pass
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        return CommandResult(exit_code=exit_code, stdout=out, stderr=err)

    def enable_passwordless_sudo(self, password: str, *, user: str | None = None) -> bool:
        """Install a sudoers drop-in granting the user passwordless sudo.

        The engine runs privileged setup/reset commands (create system paths,
        break/repair services) non-interactively over SSH. The player already
        holds sudo; this only removes the interactive prompt for the account
        that's already an administrator -- the standard automated-provisioning
        pattern on a dedicated throwaway VM.

        Security-sensitive by nature (it writes a sudoers file), so:
          - the password is passed ONLY on stdin to `sudo -S`, never embedded
            in the command string;
          - the drop-in content is staged via SFTP to a temp file (no shell
            interpolation of the username), then moved into place and validated
            with `visudo -c` before it counts.
        """
        if self._client is None:
            raise RuntimeError("connect() must be called before enable_passwordless_sudo().")
        who = user or self.user
        # A sudoers username is a restricted token; reject anything that could
        # smuggle syntax into the file rather than trying to escape it.
        if not who or not all(c.isalnum() or c in "._-" for c in who):
            raise ValueError(f"unsafe sudoers user name: {who!r}")

        drop = f"{who} ALL=(ALL) NOPASSWD: ALL\n"
        staging = "/tmp/sysadmin-zork.sudoers"
        target = "/etc/sudoers.d/sysadmin-zork"

        # 1. Stage the exact file contents via SFTP -- no shell quoting at all.
        self.put_file(staging, drop, mode=0o440)

        # 2. Validate BEFORE installing, move into place, re-validate. The
        #    password reaches sudo only through stdin (-S), never the argv.
        script = (
            f"visudo -cf {staging} && "
            f"sudo -S -p '' install -m 0440 -o root -g root {staging} {target} && "
            f"sudo -S -p '' visudo -cf {target} && "
            f"rm -f {staging}"
        )
        result = self.run_with_input(script, password + "\n")
        # Confirm it actually works now, without a password.
        return result.ok and self.run("sudo -n true").ok

    def run(self, command: str, *, timeout: float | None = None) -> CommandResult:
        if self._client is None:
            raise RuntimeError("connect() must be called before run().")
        _stdin, stdout, stderr = self._client.exec_command(command, timeout=timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        return CommandResult(exit_code=exit_code, stdout=out, stderr=err)

    def put_file(self, remote_path: str, content: str, *, mode: int = 0o644) -> None:
        if self._client is None:
            raise RuntimeError("connect() must be called before put_file().")
        sftp = self._client.open_sftp()
        try:
            with sftp.file(remote_path, "w") as fh:
                fh.write(content)
            sftp.chmod(remote_path, mode)
        finally:
            sftp.close()

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None


# --------------------------------------------------------------------------- #
# Fake transport: an in-memory Linux-ish box for tests and `spike --fake`
# --------------------------------------------------------------------------- #
@dataclass
class FakeTransport:
    """A tiny in-memory stand-in for a Linux VM.

    It models just enough of a filesystem and a handful of commands to prove
    the spike loop AND the prologue handshake: writing/checking a marker file,
    sudo, SELinux state, sshd enablement, installing an authorized_key, and
    -- crucially -- having its entire state snapshotted and restored by
    `FakeHypervisor`. It is NOT a real shell; it recognizes only the specific
    commands the engine issues.
    """

    files: dict[str, str] = field(default_factory=dict)
    connected: bool = False
    # Prologue knobs: emulate a VM that (optionally) needs a password first and
    # has the student user in the wheel group (sudo works).
    password: str | None = None
    expected_password: str | None = None
    has_sudo: bool = True
    passwordless_sudo: bool = False
    authorized_keys: list[str] = field(default_factory=list)
    _history: list[str] = field(default_factory=list)

    def connect(self) -> None:
        # If the fake VM expects a password and one is set, it must match.
        if self.expected_password is not None and self.password is not None:
            if self.password != self.expected_password:
                raise RuntimeError("Authentication failed (fake): bad password")
        self.connected = True

    def _require_connected(self) -> None:
        if not self.connected:
            raise RuntimeError("connect() must be called before use.")

    def run(self, command: str, *, timeout: float | None = None) -> CommandResult:
        self._require_connected()
        self._history.append(command)
        cmd = command.strip()

        # Transparently strip a leading `sudo` (and `sudo -n`) so setup commands
        # that run privileged on the real VM still work against the fake. Keep
        # the sudo-probe commands intact so they exercise the sudo model below.
        _sudo_probes = ("sudo whoami", "sudo -n whoami", "sudo -n true")
        if cmd not in _sudo_probes:
            if cmd.startswith("sudo -n "):
                cmd = cmd[len("sudo -n ") :].strip()
            elif cmd.startswith("sudo "):
                cmd = cmd[len("sudo ") :].strip()

        # Output redirection: `<cmd> > path` or `<cmd> >> path`. Model the two
        # the game/levels actually use: `echo TEXT > path` and `touch ... > path`
        # is unusual, so handle echo-redirect and generic-append here.
        if ">>" in cmd or (">" in cmd and not cmd.startswith("test ")):
            append = ">>" in cmd
            op = ">>" if append else ">"
            left, _, right = cmd.partition(op)
            path = right.strip()
            left = left.strip()
            # determine the content being written
            if left.startswith("echo "):
                content = left[len("echo ") :]
                # strip surrounding quotes if present
                if len(content) >= 2 and content[0] in "'\"" and content[-1] == content[0]:
                    content = content[1:-1]
                content = content + "\n"
            elif left.startswith("cat ") and left[len("cat "):].strip() in self.files:
                content = self.files[left[len("cat "):].strip()]
            else:
                content = ""
            if append and path in self.files:
                self.files[path] = self.files[path] + content
            else:
                self.files[path] = content
            return CommandResult(0, "", "")

        # `touch <path>` (possibly multiple) -- create empty files
        if cmd.startswith("touch "):
            for path in cmd[len("touch ") :].split():
                self.files.setdefault(path, "")
            return CommandResult(0, "", "")

        # `mkdir -p <path>` / `mkdir <path>` -- no real dirs modeled; succeed
        if cmd.startswith("mkdir"):
            return CommandResult(0, "", "")

        # `chown ...` / `chmod ...` -- ownership/perms not modeled; succeed
        if cmd.startswith("chown") or cmd.startswith("chmod"):
            return CommandResult(0, "", "")

        # `test -f <path>` / `test ! -f <path>` -- existence checks (exit code)
        if cmd.startswith("test -f "):
            path = cmd[len("test -f ") :].strip()
            return CommandResult(0 if path in self.files else 1, "", "")
        if cmd.startswith("test ! -f "):
            path = cmd[len("test ! -f ") :].strip()
            return CommandResult(1 if path in self.files else 0, "", "")

        # `rm -f <path>`
        if cmd.startswith("rm -f "):
            path = cmd[len("rm -f ") :].strip()
            self.files.pop(path, None)
            return CommandResult(0, "", "")

        # `cat <path>`
        if cmd.startswith("cat "):
            path = cmd[len("cat ") :].strip()
            if path in self.files:
                return CommandResult(0, self.files[path], "")
            return CommandResult(1, "", f"cat: {path}: No such file or directory")

        # `sudo whoami` / `sudo -n whoami` -- succeeds as root iff passwordless
        if cmd in ("sudo whoami", "sudo -n whoami"):
            if self.has_sudo and self.passwordless_sudo:
                return CommandResult(0, "root\n", "")
            return CommandResult(1, "", "sudo: a password is required")

        # `sudo -n true` -- passwordless-sudo probe
        if cmd == "sudo -n true":
            return CommandResult(0 if (self.has_sudo and self.passwordless_sudo) else 1, "", "")

        # `id -nG` / `groups` -- group membership (wheel confers sudo on RHEL)
        if cmd in ("id -nG", "groups"):
            groups = "student"
            if self.has_sudo:
                groups += " wheel"
            return CommandResult(0, groups + "\n", "")

        # `getenforce` -- SELinux status (RHEL default)
        if cmd == "getenforce":
            return CommandResult(0, "Enforcing\n", "")

        # sshd enablement check
        if "is-enabled sshd" in cmd:
            return CommandResult(0, "enabled\n", "")

        # `echo hello` / `echo <x>` -- echo its argument
        if cmd.startswith("echo "):
            return CommandResult(0, cmd[len("echo ") :] + "\n", "")

        # `whoami`
        if cmd == "whoami":
            return CommandResult(0, "student\n", "")

        # The authorized_key install script (multi-part, joined by &&). Detect it
        # by signature and record the key so tests can assert it was installed.
        if "authorized_keys" in cmd and "echo '" in cmd:
            start = cmd.index("echo '") + len("echo '")
            end = cmd.index("'", start)
            key = cmd[start:end].replace("'\\''", "'")
            if key not in self.authorized_keys:
                self.authorized_keys.append(key)
            return CommandResult(0, "", "")

        # `true` / `false`
        if cmd == "true":
            return CommandResult(0, "", "")
        if cmd == "false":
            return CommandResult(1, "", "")

        # Unknown command: behave like a shell that can't find it.
        return CommandResult(127, "", f"{cmd.split()[0] if cmd else ''}: command not found")

    def append_authorized_key(self, public_key: str) -> None:
        """Mirror of SSHTransport.append_authorized_key for the fake VM."""
        self._require_connected()
        key = public_key.strip()
        if key not in self.authorized_keys:
            self.authorized_keys.append(key)

    def enable_passwordless_sudo(self, password: str, *, user: str | None = None) -> bool:
        """Mirror of SSHTransport.enable_passwordless_sudo for the fake VM.

        Succeeds (and flips passwordless_sudo on) only if the user has sudo and
        the supplied password matches the fake's expected password.
        """
        self._require_connected()
        if not self.has_sudo:
            return False
        if self.expected_password is not None and password != self.expected_password:
            return False
        self.passwordless_sudo = True
        return True

    def put_file(self, remote_path: str, content: str, *, mode: int = 0o644) -> None:
        self._require_connected()
        self.files[remote_path] = content

    def get_file(self, remote_path: str) -> str:
        self._require_connected()
        return self.files.get(remote_path, "")

    # -- helpers used by FakeHypervisor to snapshot/restore this state -------- #
    def _snapshot_state(self) -> dict[str, str]:
        return dict(self.files)

    def _restore_state(self, state: dict[str, str]) -> None:
        self.files = dict(state)

    def close(self) -> None:
        self.connected = False


class LocalTransport(Transport):
    """Run commands in a local temp directory via the real system shell.

    Used for unit-testing filesystem/shell-heavy content (Tier 1 levels that
    lean on grep/sed/ln/readlink/loops) without spinning up the VM. HOME is
    faked to the sandbox dir so `~/...` references resolve locally. Commands
    run through `bash -c` with a cwd rooted at `root`, so relative paths and
    ~ behave like a real (throwaway) machine.
    """

    def __init__(self, root: pathlib.Path):
        self.root = root
        self._connected = False

    def connect(self) -> None:
        self._connected = True
        # Ensure the VM's home exists locally so ~-based content works.
        (self.root / "home" / "student").mkdir(parents=True, exist_ok=True)

    def close(self) -> None:
        self._connected = False

    def run(self, command: str, *, timeout: float | None = None) -> CommandResult:
        if not self._connected:
            raise RuntimeError("connect() must be called before run().")
        env = dict(os.environ)
        env["HOME"] = (self.root / "home" / "student").as_posix()
        # Remap the VM's absolute paths into our temp root so content authored
        # for the real box runs in a hermetic local sandbox. We rewrite each
        # known prefix (/home/student, /srv, /etc, /var) to <root>/<rest>.
        cmd = command.strip()
        if cmd.startswith("sudo "):
            cmd = cmd[len("sudo "):].strip()
        cmd = self._remap_paths(cmd)
        try:
            proc = subprocess.run(
                ["bash", "-c", cmd],
                cwd=str(self.root),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return CommandResult(proc.returncode, proc.stdout, proc.stderr)
        except subprocess.TimeoutExpired:
            return CommandResult(124, "", "timeout")

    def _local_path(self, remote_path: str) -> pathlib.Path:
        # Go through the same remap the shell uses, then treat the result as a
        # path. If it already points inside root (post-remap) use it directly;
        # otherwise fall back to root-relative for any un-mapped absolute path.
        remapped = self._remap_paths(remote_path)
        if remapped != remote_path:
            return pathlib.Path(remapped)
        return self.root / remote_path.lstrip("/")

    # Prefixes rewritten from "VM absolute" to "inside the temp sandbox root".
    # /home/student maps to <root>/home/student; everything else to <root>/<rest>.
    _REMAP_PREFIXES = ("/home/student/", "/srv/", "/etc/", "/var/")

    def _remap_paths(self, text: str) -> str:
        """Rewrite known VM absolute paths into the sandbox root.

        Used for both shell commands (`run`) and file paths (`_local_path`), so
        a command and a later put_file/get_file agree on where a path lives.
        """
        for prefix in self._REMAP_PREFIXES:
            text = text.replace(prefix, (self.root / prefix.lstrip("/")).as_posix() + "/")
        return text

    def append_authorized_key(self, public_key: str) -> None:  # pragma: no cover
        raise NotImplementedError("LocalTransport is test-only")

    def enable_passwordless_sudo(self, password: str, *, user: str | None = None) -> bool:
        return True

    def put_file(self, remote_path: str, content: str, *, mode: int = 0o644) -> None:
        target = self._local_path(remote_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def get_file(self, remote_path: str) -> str:
        target = self._local_path(remote_path)
        return target.read_text(encoding="utf-8") if target.exists() else ""


# --------------------------------------------------------------------------- #
