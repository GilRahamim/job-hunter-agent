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
    must not make dashboard tests think a run is active, and tests must not touch its files."""
    monkeypatch.setenv("JOBHUNTER_RUN_DIR", str(tmp_path / "run"))


@pytest.fixture
def fixture():
    return load_fixture
