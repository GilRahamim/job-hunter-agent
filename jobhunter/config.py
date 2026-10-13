"""Load config.yaml, companies.yaml and .env (all cached)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


@lru_cache(maxsize=1)
def load_env() -> None:
    """Load API keys from .env into the process environment."""
    load_dotenv(ROOT / ".env")


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    load_env()
    return _read_yaml(ROOT / "config.yaml")


@lru_cache(maxsize=1)
def load_companies() -> dict[str, Any]:
    return _read_yaml(ROOT / "companies.yaml")
