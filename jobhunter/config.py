"""Load config.yaml, companies.yaml and .env (all cached), and resolve per-user folders.

Users: the owner ("" — the default) uses the repo's own cv/, data/ and config.yaml, exactly as before.
A named user (JOBHUNTER_USER=dana, or `run_agent.py --user dana`) lives in users/dana/:
    cv/            their CV
    data/          their jobs.db, run lock, logs and tailored files
    config.yaml    optional: only the settings that differ from the main config.yaml

JOBHUNTER_CONFIG (environment or .env) names extra files merged over config.yaml for everyone, in order,
comma-separated, relative to the repo: e.g. config.vllm.yaml to score with a local vLLM server.
"""
from __future__ import annotations

import copy
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


def active_user() -> str:
    """The user this process works for; "" is the owner. The dashboard passes users explicitly instead,
    because one Streamlit process serves every browser session."""
    return os.environ.get("JOBHUNTER_USER", "").strip()


def _user(user: str | None) -> str:
    return active_user() if user is None else user


def users_dir() -> Path:
    """Parent folder of the named users. JOBHUNTER_USERS_DIR overrides it (tests)."""
    return Path(os.environ.get("JOBHUNTER_USERS_DIR") or ROOT / "users")


def user_root(user: str | None = None) -> Path:
    """Base folder of a user: the repo itself for the owner, users/<name>/ otherwise."""
    user = _user(user)
    return users_dir() / user if user else ROOT


def data_dir(user: str | None = None) -> Path:
    return user_root(user) / "data"


def run_dir(user: str | None = None) -> Path:
    """Where run.lock, stop.flag and run logs live. For the owner JOBHUNTER_RUN_DIR overrides it, so
    tests never see (or clear) the lock of a real search that is running."""
    user = _user(user)
    if not user and os.environ.get("JOBHUNTER_RUN_DIR"):
        return Path(os.environ["JOBHUNTER_RUN_DIR"])
    return data_dir(user)


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """`override` on top of `base`; nested dicts merge, everything else (lists too) is replaced."""
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


@lru_cache(maxsize=1)
def load_env() -> None:
    """Load API keys from .env into the process environment."""
    load_dotenv(ROOT / ".env")


def load_config(user: str | None = None) -> dict[str, Any]:
    """config.yaml, plus the user's own config.yaml on top for a named user. Cached: do not mutate."""
    return _load_config(_user(user))


def overlay_paths() -> list[Path]:
    """The files JOBHUNTER_CONFIG names, in merge order (read after load_env, so .env can set it)."""
    names = [n.strip() for n in os.environ.get("JOBHUNTER_CONFIG", "").split(",") if n.strip()]
    paths = [ROOT / n for n in names]                    # an absolute name stays absolute
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"JOBHUNTER_CONFIG names {path}, which does not exist")
    return paths


@lru_cache(maxsize=16)
def _load_config(user: str) -> dict[str, Any]:
    load_env()
    cfg = _read_yaml(ROOT / "config.yaml")
    for path in overlay_paths():
        cfg = deep_merge(cfg, _read_yaml(path))
    if user:
        overlay = user_root(user) / "config.yaml"
        if overlay.exists():
            cfg = deep_merge(cfg, _read_yaml(overlay))
        cfg["profile"] = {**cfg.get("profile", {}), "cv_dir": str(user_root(user) / "cv")}
    return cfg


load_config.cache_clear = _load_config.cache_clear      # type: ignore[attr-defined]


@lru_cache(maxsize=1)
def load_companies() -> dict[str, Any]:
    return _read_yaml(ROOT / "companies.yaml")
