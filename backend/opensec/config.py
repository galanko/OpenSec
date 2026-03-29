"""Application configuration via environment variables and defaults."""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path

from pydantic_settings import BaseSettings


def _find_repo_root() -> Path:
    """Walk up from this file to find the repo root (contains .opencode-version)."""
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / ".opencode-version").exists():
            return current
        current = current.parent
    return Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    # OpenSec
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # OpenCode engine (singleton)
    opencode_host: str = "127.0.0.1"
    opencode_port: int = 4096
    opencode_bin: str = ""  # Auto-resolved if empty

    # Workspace process pool
    opencode_port_range_start: int = 4100
    opencode_port_range_end: int = 4199
    workspace_idle_timeout_seconds: int = 600

    # Paths
    repo_root: Path = _find_repo_root()
    data_dir: Path = Path(os.getenv("OPENSEC_DATA_DIR", ""))
    static_dir: str = ""  # Path to built frontend assets (set in Docker)

    model_config = {"env_prefix": "OPENSEC_"}

    @property
    def opencode_url(self) -> str:
        return f"http://{self.opencode_host}:{self.opencode_port}"

    @property
    def opencode_binary_path(self) -> Path:
        if self.opencode_bin:
            return Path(self.opencode_bin)
        # Check common locations
        home_bin = Path.home() / ".opensec" / "bin" / "opencode"
        if home_bin.exists():
            return home_bin
        # Check PATH
        from shutil import which

        found = which("opencode")
        if found:
            return Path(found)
        return home_bin  # Default install location

    @property
    def opencode_version(self) -> str:
        version_file = self.repo_root / ".opencode-version"
        if version_file.exists():
            return version_file.read_text().strip()
        return "latest"

    @property
    def opencode_model(self) -> str:
        """Read the configured model from opencode.json."""
        config_file = self.repo_root / "opencode.json"
        if config_file.exists():
            try:
                data = json.loads(config_file.read_text())
                return data.get("model", "")
            except (json.JSONDecodeError, OSError):
                pass
        return ""

    def write_opencode_config(self, model: str) -> None:
        """Update the model in opencode.json, preserving other fields."""
        config_file = self.repo_root / "opencode.json"
        data: dict = {}
        if config_file.exists():
            with contextlib.suppress(json.JSONDecodeError, OSError):
                data = json.loads(config_file.read_text())
        data["model"] = model
        config_file.write_text(json.dumps(data, indent=2) + "\n")

    def resolve_data_dir(self) -> Path:
        d = self.data_dir if self.data_dir and str(self.data_dir) else self.repo_root / "data"
        d.mkdir(parents=True, exist_ok=True)
        return d


settings = Settings()
