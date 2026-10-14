"""Named users (e.g. a partner who wants their own search): created from an uploaded CV.

The owner ("") keeps the repo's own cv/, data/ and config.yaml. Every other user gets users/<id>/ with
their CV, their own jobs.db and a small config.yaml that turns on `auto_from_cv`, so the search terms
come from their CV instead of the owner's hand-tuned queries (see personalize.py). Paths: config.py."""
from __future__ import annotations

import json
import re
from pathlib import Path

from jobhunter.config import load_config, user_root, users_dir
from jobhunter.cv import CV_EXTENSIONS

OWNER = ""
_SLUG = re.compile(r"[^a-z0-9]+")


class UserError(ValueError):
    """Bad input from the add-user form; the message is shown to the person (Hebrew)."""


def slugify(name: str) -> str:
    """ASCII folder id: "Dana Levi" -> "dana-levi". Hebrew-only names give "" (the caller numbers them)."""
    return _SLUG.sub("-", name.lower()).strip("-")[:30]


def list_users() -> list[str]:
    """Named user ids, sorted. The owner is not in the list."""
    root = users_dir()
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if p.is_dir() and (p / "cv").is_dir())


def display_name(user: str) -> str:
    """The name typed when the user was created (config `display_name`), else the folder id."""
    return str(load_config(user).get("display_name") or user) if user else ""


def _new_id(name: str) -> str:
    base = slugify(name) or "user"
    taken = set(list_users())
    if base not in taken and base != "owner":
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"


def save_cv(user: str, filename: str, data: bytes) -> Path:
    """Store an uploaded CV in the user's cv folder. The newest file there is the one that is read."""
    name = Path(filename).name
    if Path(name).suffix.lower() not in CV_EXTENSIONS:
        raise UserError("קובץ קורות החיים צריך להיות PDF, DOCX או TXT.")
    if not data:
        raise UserError("הקובץ ריק.")
    folder = user_root(user) / "cv" if user else _owner_cv_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_bytes(data)
    return path


def _owner_cv_dir() -> Path:
    cv_dir = Path(load_config(OWNER)["profile"]["cv_dir"])
    return cv_dir if cv_dir.is_absolute() else user_root(OWNER) / cv_dir


def starter_config(display: str, titles: list[str]) -> str:
    """users/<id>/config.yaml for a new user. JSON strings are valid YAML and keep Hebrew as is."""
    queries = ", ".join(json.dumps(t, ensure_ascii=False) for t in titles)
    return (
        f"# Settings for {display} only. Anything not set here comes from the main config.yaml.\n"
        f"display_name: {json.dumps(display, ensure_ascii=False)}\n"
        "# Job titles, role filter and experience limit come from this CV (jobhunter/personalize.py),\n"
        "# not from the owner's hand-tuned search settings.\n"
        "auto_from_cv: true\n"
        "search:\n"
        "  # Job titles to search for. Empty = the titles the CV suggests (needs an LLM).\n"
        f"  queries: [{queries}]\n"
    )


def parse_titles(text: str) -> list[str]:
    """Job titles typed in the form, one per line or comma-separated."""
    return [t.strip() for t in re.split(r"[,\n]", text or "") if t.strip()]


def create_user(display: str, cv_filename: str, cv_data: bytes, titles: list[str] | None = None) -> str:
    """Create users/<id>/ from the add-user form. Returns the new id."""
    display = display.strip()
    if not display:
        raise UserError("נא לכתוב שם.")
    titles = [t.strip() for t in titles or [] if t.strip()]
    user = _new_id(display)
    save_cv(user, cv_filename, cv_data)            # validates the file before anything else is written
    (user_root(user) / "config.yaml").write_text(starter_config(display, titles), encoding="utf-8")
    load_config.cache_clear()                      # type: ignore[attr-defined]
    return user
