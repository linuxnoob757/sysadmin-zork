"""Player profile: durable per-player state, saved as JSON.

The profile is what the prologue produces and every later phase consumes. It
holds three things:

- **connection** -- how to reach the player's VM (host/port/user/key + the
  VirtualBox VM name / VBoxManage path / baseline snapshot). Phase 0 took these
  as CLI flags; from Phase 1 on they live here.
- **secret** -- a per-profile random key used in Phase 2 to HMAC-sign level
  completion tokens, so a save file can't be hand-edited to skip levels.
- **progression** -- prologue_complete plus (later) the signed tokens.

Profiles live under `profiles/<name>.json` (gitignored -- they contain the
secret and connection details).
"""

from __future__ import annotations

import json
import secrets
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

PROFILES_DIR = Path(__file__).resolve().parent.parent / "profiles"
DEFAULT_PROFILE = "default"


@dataclass
class Connection:
    """Everything needed to reach and reset the player's VM."""

    host: str = ""
    port: int = 22
    user: str = "student"
    key_path: str = ""
    vm_name: str = ""
    vboxmanage: str | None = None
    baseline_snapshot: str = "clean-baseline"

    def is_complete(self) -> bool:
        return bool(self.host and self.key_path and self.vm_name)


@dataclass
class Profile:
    """A player's durable game state."""

    name: str = DEFAULT_PROFILE
    player_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    # per-profile secret for Phase 2 token signing; never displayed to the player
    secret: str = field(default_factory=lambda: secrets.token_hex(32))
    connection: Connection = field(default_factory=Connection)
    prologue_complete: bool = False
    # Phase 2 will populate this with HMAC-signed level tokens.
    tokens: dict[str, str] = field(default_factory=dict)

    # -- persistence --------------------------------------------------------- #
    @staticmethod
    def path_for(name: str, *, profiles_dir: Path | None = None) -> Path:
        base = profiles_dir or PROFILES_DIR
        return base / f"{name}.json"

    @classmethod
    def load(cls, name: str = DEFAULT_PROFILE, *, profiles_dir: Path | None = None) -> "Profile":
        """Load a profile, or return a fresh one if none exists yet."""
        path = cls.path_for(name, profiles_dir=profiles_dir)
        if not path.exists():
            return cls(name=name)
        data = json.loads(path.read_text(encoding="utf-8"))
        conn = Connection(**data.pop("connection", {}))
        return cls(connection=conn, **data)

    @classmethod
    def exists(cls, name: str = DEFAULT_PROFILE, *, profiles_dir: Path | None = None) -> bool:
        return cls.path_for(name, profiles_dir=profiles_dir).exists()

    def save(self, *, profiles_dir: Path | None = None) -> Path:
        path = self.path_for(self.name, profiles_dir=profiles_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")
        return path
