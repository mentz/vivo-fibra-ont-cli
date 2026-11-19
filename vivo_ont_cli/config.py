"""Configuration loading and model selection inputs.

Precedence, highest first:

1. command-line ``--model``
2. ``VIVO_MODEL``
3. ``model`` in the JSON config file
4. the default model
"""

from __future__ import annotations

import getpass
import json
import os
from dataclasses import dataclass
from pathlib import Path

from .models.base import OntModel

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "vivo-fibra-ont.json"


@dataclass(frozen=True)
class Config:
    host: str
    user: str
    password: str
    model: str


def config_path() -> Path:
    override = os.environ.get("VIVO_CONFIG")
    return Path(override).expanduser() if override else DEFAULT_CONFIG_PATH


def read_config_file(path: Path | None = None) -> dict:
    path = path or config_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def load_config(model: OntModel, raw: dict | None = None) -> Config:
    raw = raw if raw is not None else read_config_file()
    host = os.environ.get("VIVO_HOST") or raw.get("host") or model.default_host
    user = os.environ.get("VIVO_USER") or raw.get("user") or "admin"
    password = os.environ.get("VIVO_PASS") or raw.get("password")
    if not password:
        password = getpass.getpass(f"password for {user}@{host}: ")
    return Config(host=str(host).rstrip("/"), user=str(user),
                  password=str(password), model=model.id)
