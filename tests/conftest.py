import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str):
    text = (FIXTURES / name).read_text(encoding="utf-8")
    return json.loads(text) if name.endswith(".json") else text


@pytest.fixture(autouse=True)
def _own_run_dir(tmp_path, monkeypatch):
    """Lock, stop flag and run logs go to a temp folder: a real search running on this PC
    must not make dashboard tests think a run is active, and tests must not touch its files.
    Named users live in a temp users/ folder too, and every test starts as the owner."""
    from jobhunter.config import load_config

    monkeypatch.setenv("JOBHUNTER_RUN_DIR", str(tmp_path / "run"))
    monkeypatch.setenv("JOBHUNTER_USERS_DIR", str(tmp_path / "users"))
    monkeypatch.delenv("JOBHUNTER_USER", raising=False)
    load_config.cache_clear()          # user configs are cached by user id, not by folder
    yield
    load_config.cache_clear()


@pytest.fixture
def fixture():
    return load_fixture
