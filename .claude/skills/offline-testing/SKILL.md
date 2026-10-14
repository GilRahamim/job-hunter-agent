---
name: offline-testing
description: Testing strategy for the Job Hunter project — recorded API fixtures per job source, a fake LLM for deterministic scoring tests, temp SQLite databases, and the verification checklist for each phase. Use this whenever writing or running tests under tests/, recording a fixture, mocking the LLM or network, or verifying that a phase of the implementation plan is really done.
---

# Offline testing

Goal: `pytest -q` runs in seconds, with no network and no API keys, and catches the bugs that actually happen here — API shape drift, filters dropping good jobs, and lost application statuses.

## Layout
```
tests/
  conftest.py              # fixtures: tmp db, fake llm, sample profile, load_fixture()
  fixtures/
    greenhouse_jfrog.json  lever_cloudinary.json  ashby_moonactive.json
    smartrecruiters_armis.json  remotive.json  remoteok.json  himalayas.json
    wwr_backend.rss  jobspy_sample.csv  serpapi_sample.json
  test_collectors.py  test_filters.py  test_matcher.py  test_db.py  test_pipeline.py
```

Isolation: tests never touch the owner's real `data/`. Set `JOBHUNTER_DB` to a `tmp_path` file for the DB. An autouse fixture in `conftest.py` sets `JOBHUNTER_RUN_DIR` to `tmp_path / "run"`, which holds `run.lock`, `stop.flag` and the run logs (`config.run_dir()`). Without it, a real search running on the PC makes the dashboard tests see an active run, and a test that clicks the run button empties the live run log. Read these paths through `run_dir()` / `stop.stop_path()` at call time, never as import-time constants: tests set the env var after modules are imported. The same fixture points `JOBHUNTER_USERS_DIR` at `tmp_path / "users"`, removes `JOBHUNTER_USER` (every test starts as the owner) and clears the `load_config` cache, which is keyed by user id, not by folder. Create named users with `users.create_user(...)` inside a test; their DB is `db.db_path(user=<id>)`.

## Recording fixtures
Write `scripts/record_fixtures.py` that fetches each source once and saves the **trimmed** raw response (keep ~5 items; for list endpoints keep the envelope keys). Commit fixtures. Re-record only when an API changes, and diff the keys when you do — that diff is the bug report.

For JobSpy, save `df.head(10).to_csv(...)` and test the DataFrame → `Job` conversion from the CSV, not `scrape_jobs` itself.

## Mocking the network
Collectors take their data through `base.get_session()`. In tests, monkeypatch the fetch function (or use `responses` / `requests-mock`) to return fixture content. Test both the happy path and a 404/timeout → `CollectorResult.error` is set and no exception escapes.

## Fake LLM
```python
class FakeStructuredLLM:
    """Deterministic stand-in for llm.with_structured_output(Model)."""
    def __init__(self, model_cls, fn): self.model_cls, self.fn = model_cls, fn
    def invoke(self, messages): return self.model_cls(**self.fn(messages))

class FakeLLM:
    def __init__(self, scorer): self.scorer = scorer
    def with_structured_output(self, model_cls): return FakeStructuredLLM(model_cls, self.scorer)
```
The scorer can look at the job title in the prompt and return a score (e.g. "Senior" → 30, "Python" → 80). Add a variant that raises on the first call to test retries, and one that always raises to test the prescore fallback.

LangChain also ships `GenericFakeChatModel` in `langchain_core.language_models.fake_chat_models` — usable for plain text, but structured output is simpler with the class above.

## Must-have tests
- **db**: re-upsert keeps `status` and `notes`; dedupe_key catches the same role from two sources; WAL read while writing doesn't error.
- **filters**: all location cases from `job-matching/references/patterns.md`; role and exclude keywords; senior drop toggle; age filter keeps undated jobs.
- **matcher**: prescore ranks an obviously matching job above an unrelated one; years-gap penalty applies; LLM failure → prescore kept, `scored_by="heuristic"`.
- **collectors**: each fixture parses to ≥1 `Job` with non-empty title, company, url; Greenhouse description is unescaped plain text (no `&lt;`); dates are ISO.
- **pipeline**: run the compiled graph with fixtures + fake LLM + tmp DB → jobs saved, a `runs` row with stats exists, a second run adds 0 new jobs.

## Optional live smoke test
Mark with `@pytest.mark.live` and skip by default (`-m "not live"` in `pytest.ini`). One test per source that fetches for real and asserts ≥1 job — run it manually when something looks off: `pytest -m live -q`.

## Phase verification
Before saying a phase is done: run `pytest -q`, run the phase's acceptance command from `docs/IMPLEMENTATION_PLAN.md`, and paste both outputs. "Should work" is not evidence.
