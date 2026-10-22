import pytest

from jobhunter import llm
from jobhunter.config import ROOT, load_config


def overlay(monkeypatch, value):
    monkeypatch.setenv("JOBHUNTER_CONFIG", value)
    load_config.cache_clear()
    return load_config()


def test_no_overlay_is_config_yaml_as_is(monkeypatch):
    import yaml
    plain = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))
    assert overlay(monkeypatch, "") == plain


def test_overlays_merge_in_order_over_config_yaml(tmp_path, monkeypatch):
    (tmp_path / "a.yaml").write_text("llm: {model: a, max_workers: 9}\nmatching: {llm_top_n: 99}\n")
    (tmp_path / "b.yaml").write_text("llm: {model: b}\n")
    cfg = overlay(monkeypatch, f"{tmp_path / 'a.yaml'}, {tmp_path / 'b.yaml'}")
    assert cfg["llm"]["model"] == "b" and cfg["llm"]["max_workers"] == 9      # later file wins
    assert cfg["matching"]["llm_top_n"] == 99
    assert cfg["llm"]["temperature"] == 0 and cfg["search"]                  # the rest is config.yaml


def test_a_missing_overlay_is_a_clear_error(monkeypatch):
    with pytest.raises(FileNotFoundError, match="JOBHUNTER_CONFIG.*nope.yaml"):
        overlay(monkeypatch, "nope.yaml")


def test_vllm_config_scores_and_runs_the_agent_on_one_local_server(monkeypatch):
    cfg = overlay(monkeypatch, "config.vllm.yaml")
    main, agent = cfg["llm"], llm.agent_llm_config(cfg)["llm"]
    assert main["provider"] == agent["provider"] == "openai"
    assert main["base_url"] == agent["base_url"] == "http://127.0.0.1:8000/v1"
    assert main["model"] == agent["model"]                                   # one model on the GPU
    assert main["max_workers"] > 6 and cfg["matching"]["llm_top_n"] > 60
    assert main["extra_body"]["chat_template_kwargs"]["enable_thinking"] is False   # scoring: JSON only
    assert agent["extra_body"]["chat_template_kwargs"]["enable_thinking"] is True   # the agent plans
    model = llm.get_llm(cfg)                                                 # built offline, no key needed
    assert model.openai_api_base == "http://127.0.0.1:8000/v1" and model.model_name == main["model"]
    assert model.extra_body == main["extra_body"]
    assert model.openai_api_key.get_secret_value() == llm.LOCAL_API_KEY


def test_docker_overlay_points_both_models_at_the_compose_service(monkeypatch):
    cfg = overlay(monkeypatch, "config.vllm.yaml,config.docker.yaml")
    assert cfg["llm"]["base_url"] == llm.agent_llm_config(cfg)["llm"]["base_url"] == "http://vllm:8000/v1"
