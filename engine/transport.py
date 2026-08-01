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

    Password auth is intentionally unsupported: the game hardens the VM to
    keys-only in Tier 4, and the engine should live by the same rules it
    teaches.
    """

    def __init__(
        self,
        host: str,
        user: str,
        key_path: str,
        *,
        port: int = 22,
        connect_timeout: float = 15.0,
        retries: int = 4,
        retry_delay: float = 2.0,
    ) -> None:
        self.host = host
        self.user = user
        self.key_path = key_path
        self.port = port
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

        last_exc: Exception | None = None
        for attempt in range(1, self.retries + 1):
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                client.connect(
                    hostname=self.host,
                    port=self.port,
                    username=self.user,
                    key_filename=self.key_path,
                    timeout=self.connect_timeout,
                    banner_timeout=self.connect_timeout,
                    auth_timeout=self.connect_timeout,
                    allow_agent=False,
                    look_for_keys=False,
                )
                self._client = client
                return
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
    the spike loop: writing a marker file, checking whether it exists, and
    -- crucially -- having its entire state snapshotted and restored by
    `FakeHypervisor`. It is NOT a real shell; it recognizes only the specific
    commands the spike uses.
    """

    files: dict[str, str] = field(default_factory=dict)
    connected: bool = False
    _history: list[str] = field(default_factory=list)

    def connect(self) -> None:
        self.connected = True

    def _require_connected(self) -> None:
        if not self.connected:
            raise RuntimeError("connect() must be called before use.")

    def run(self, command: str, *, timeout: float | None = None) -> CommandResult:
        self._require_connected()
        self._history.append(command)
        cmd = command.strip()

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

        # `echo hello` / `echo <x>` -- echo its argument
        if cmd.startswith("echo "):
            return CommandResult(0, cmd[len("echo ") :] + "\n", "")

        # `whoami`
        if cmd == "whoami":
            return CommandResult(0, "student\n", "")

        # `true` / `false`
        if cmd == "true":
            return CommandResult(0, "", "")
        if cmd == "false":
            return CommandResult(1, "", "")

        # Unknown command: behave like a shell that can't find it.
        return CommandResult(127, "", f"{cmd.split()[0] if cmd else ''}: command not found")

    def put_file(self, remote_path: str, content: str, *, mode: int = 0o644) -> None:
        self._require_connected()
        self.files[remote_path] = content

    def close(self) -> None:
        self.connected = False

    # -- helpers used by FakeHypervisor to snapshot/restore this state -------- #
    def _snapshot_state(self) -> dict[str, str]:
        return dict(self.files)

    def _restore_state(self, state: dict[str, str]) -> None:
        self.files = dict(state)
