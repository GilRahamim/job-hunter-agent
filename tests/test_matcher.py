import pytest

from jobhunter import matcher
from jobhunter.config import load_config
from jobhunter.models import CandidateProfile, Job, JobMatch


@pytest.fixture(autouse=True)
def no_backoff(monkeypatch):
    monkeypatch.setattr(matcher, "BACKOFF_SECONDS", 0)


@pytest.fixture
def cfg():
    return load_config()


@pytest.fixture
def profile():
    return CandidateProfile(
        headline="Junior AI engineer", seniority="junior", years_experience=0,
        skills=["Python", "LangChain", "LangGraph", "RAG", "SQL", "Docker"],
        projects=["RAG chatbot with LangChain and ChromaDB"],
        target_roles=["AI Engineer"])


def job(title, desc, **kw):
    return Job("t", title, "Acme", f"https://x/{title.replace(' ', '-')}", description=desc, **kw)


GOOD = job("Junior AI Engineer", "Build RAG pipelines with Python, LangChain and LangGraph. SQL and Docker.")
BAD = job("Receptionist Software Trainer", "Greet visitors, schedule meetings and order office supplies.")
SENIOR = job("AI Engineer", "Python, LangChain, RAG, SQL, Docker. 8+ years of experience required.")


# ---------------------------------------------------------------- prescore

def test_prescore_ranks_matching_job_above_unrelated(profile):
    good, bad = matcher.prescore(profile, [GOOD, BAD])
    assert good > bad and 0 <= bad <= good <= 100


def test_prescore_years_gap_penalty(profile):
    plain = job("AI Engineer", SENIOR.description.replace("8+ years of experience required.", ""))
    penalized, unpenalized = matcher.prescore(profile, [SENIOR, plain])
    assert unpenalized - penalized > 15        # 8 years vs 0 + 2 -> capped 25-point penalty


def test_prescore_handles_empty_and_single(profile):
    assert matcher.prescore(profile, []) == []
    assert len(matcher.prescore(profile, [GOOD])) == 1


@pytest.mark.parametrize("text,expected", [
    ("3+ years of experience", 3), ("3-5 years", 3), ("at least 5 years and 2 years of SQL", 5),
    ("דרושות 4 שנות ניסיון", 4), ("no mention", 0), ("10 yrs", 10),
])
def test_required_years(text, expected):
    assert matcher.required_years(text) == expected


def test_select_for_llm_threshold_and_cap(cfg):
    cfg = {**cfg, "matching": {**cfg["matching"], "llm_top_n": 2, "min_prescore_for_llm": 20}}
    assert matcher.select_for_llm([50, 10, 90, 30, 19], cfg) == [2, 0]


# ---------------------------------------------------------------- LLM scoring

class FakeLLM:
    """Stand-in for llm.with_structured_output(JobMatch); scorer sees the prompt text."""

    def __init__(self, scorer):
        self.scorer = scorer
        self.calls = []

    def with_structured_output(self, cls):
        outer = self

        class S:
            def invoke(self, messages):
                text = messages[1][1]
                outer.calls.append(text)
                return outer.scorer(text)
        return S()


def by_title(text):
    score = 30 if "Title: Senior" in text else 85
    return JobMatch(score=score, verdict="strong" if score >= 75 else "poor", reasons="r",
                    matching_skills=["Python"], missing_skills=[])


def test_llm_score_preserves_order_and_parses(profile, cfg):
    jobs = [GOOD, job("Senior AI Engineer", "x")]
    results = matcher.llm_score(FakeLLM(by_title), profile, jobs, cfg)
    assert [r.score for r in results] == [85, 30]


def test_prompt_truncates_description_and_uses_language(profile, cfg):
    long = job("AI Engineer", "x" * 20000, is_remote=True, remote_region="EMEA")
    system, user = matcher.build_messages(profile, long, cfg)
    assert len(user[1]) < matcher.MAX_DESCRIPTION_CHARS + 1500
    assert "remote; region: EMEA" in user[1]
    assert "in Hebrew" in system[1]
    en = {**cfg, "profile": {**cfg["profile"], "explanation_language": "en"}}
    assert "in English" in matcher.build_messages(profile, long, en)[0][1]


def test_retry_then_success(profile, cfg):
    state = {"n": 0}

    def flaky(text):
        state["n"] += 1
        if state["n"] == 1:
            raise RuntimeError("429")
        return by_title(text)

    res = matcher.llm_score(FakeLLM(flaky), profile, [GOOD], cfg)
    assert res[0].score == 85 and state["n"] == 2


@pytest.mark.parametrize("error, fatal", [
    ("Error code: 400 - {'message': 'Your credit balance is too low to access the Anthropic API.'}", True),
    ("Error code: 401 - {'type': 'authentication_error'}", True),
    ("Error code: 429 - {'error': {'code': 'insufficient_quota'}}", True),
    ("Error code: 429 - rate_limit_error", False),
    ("Error code: 529 - overloaded_error", False),
    ("1 validation error for JobMatch: input_value='OAuth authentication and API key rotation'", False),
    # other providers (init_chat_model): the class name comes first, as in the errors list
    ("AuthenticationError: invalid x-api-key", True),
    ("PermissionDenied: 403 Your project has been denied access", True),
    ("ClientError: 403 PERMISSION_DENIED. {'error': {'code': 403}}", True),
    ("ClientError: 400 INVALID_ARGUMENT. {'error': {'message': 'API key not valid. Please pass a valid "
     "API key.', 'details': [{'reason': 'API_KEY_INVALID'}]}}", True),
    ("HTTPStatusError: Client error '401 Unauthorized' for url 'https://api.mistral.ai/v1/chat'", True),
    ("ClientError: 429 RESOURCE_EXHAUSTED. You exceeded your current quota", False),    # often per minute
    ("ResponseError: model 'qwen3' not found (status code: 404)", False),
    ("ValidationError: 1 validation error for JobMatch: input_value='handle 401 Unauthorized responses'",
     False),
    ("OutputParserException: Invalid json output: rotate keys when the API key not valid", False),
])
def test_fatal_llm_errors_are_billing_and_auth_only(error, fatal):
    assert matcher.fatal_llm_error(error) is fatal


def test_an_auth_error_known_by_its_class_is_not_retried(profile, cfg):
    class AuthenticationError(Exception):
        pass

    calls = []

    def bad_key(text):
        calls.append(1)
        raise AuthenticationError("invalid x-api-key")

    errors: list[str] = []
    assert matcher.llm_score(FakeLLM(bad_key), profile, [GOOD], cfg, errors) == [None]
    assert len(calls) == 1 and errors == ["AuthenticationError: invalid x-api-key"]


def test_failure_returns_none_and_falls_back_to_prescore(profile, cfg):
    def boom(text):
        raise RuntimeError("down")

    def mixed(text):
        return boom(text) if "Receptionist" in text else by_title(text)

    errors: list[str] = []
    res = matcher.llm_score(FakeLLM(mixed), profile, [GOOD, BAD], cfg, errors)
    assert res[0] is not None and res[1] is None          # one bad job does not fail the batch
    assert errors == ["RuntimeError: down"]               # the reason reaches the run stats
    row = matcher.scored_row(BAD, 12.34, res[1], "hash1", "m")
    assert row["score"] == 12.3 and row["scored_by"] == "heuristic" and row["cv_hash"] == "hash1"
    row = matcher.scored_row(GOOD, 40.0, res[0], "hash1", "claude-x")
    assert row["score"] == 85 and row["scored_by"] == "llm:claude-x" and row["prescore"] == 40.0
    assert row["matching_skills"] == ["Python"]


def test_preferences_reach_the_prompt_only_when_set(profile, cfg):
    cfg = {**cfg, "profile": {**cfg["profile"], "preferences": "Open to banks and NOC roles."}}
    _, user = matcher.build_messages(profile, GOOD, cfg)
    assert "<candidate_preferences>\nOpen to banks and NOC roles." in user[1]
    cfg["profile"]["preferences"] = "  "
    assert "<candidate_preferences>" not in matcher.build_messages(profile, GOOD, cfg)[1][1]


def test_choices_reach_the_prompt_only_when_the_user_marked_jobs(profile, cfg):
    assert matcher.choices_text({"liked": [], "disliked": []}) == ""
    choices = matcher.choices_text({"liked": ["Data Analyst @ Acme"], "disliked": []})
    assert "chose to pursue: Data Analyst @ Acme" in choices and "not relevant: -" in choices
    _, user = matcher.build_messages(profile, GOOD, cfg, choices)
    assert user[1].endswith(choices)
    seen = FakeLLM(by_title)
    matcher.llm_score(seen, profile, [GOOD], cfg, choices=choices)
    assert "<candidate_choices>" in seen.calls[0]
