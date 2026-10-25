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


def test_vllm_config_scores_on_vllm_and_leaves_the_agent_on_lm_studio(monkeypatch):
    import yaml
    plain_agent = yaml.safe_load((ROOT / "config.yaml").read_text(encoding="utf-8"))["llm"]   # LM Studio
    cfg = overlay(monkeypatch, "config.vllm.yaml")
    main, agent = cfg["llm"], llm.agent_llm_config(cfg)["llm"]
    assert main["provider"] == "openai" and main["base_url"] == "http://127.0.0.1:8000/v1"
    assert main["max_workers"] > 6 and cfg["matching"]["llm_top_n"] > 60
    assert main["extra_body"]["chat_template_kwargs"]["enable_thinking"] is False   # scoring: JSON only
    for key in ("base_url", "model", "max_tokens"):                          # config.yaml's LM Studio model
        assert agent[key] == plain_agent[key]
    assert agent["extra_body"] == {}                                         # thinking off stays with the scorer
    assert cfg["agent"]["scorer"] == "agent"                                 # agent runs never call vLLM
    model = llm.get_llm(cfg)                                                 # built offline, no key needed
    assert model.openai_api_base == "http://127.0.0.1:8000/v1" and model.model_name == main["model"]
    assert model.extra_body == main["extra_body"]
    assert model.openai_api_key.get_secret_value() == llm.LOCAL_API_KEY


def test_docker_overlay_points_the_scorer_at_compose_and_the_agent_at_the_host(monkeypatch):
    cfg = overlay(monkeypatch, "config.vllm.yaml,config.docker.yaml")
    assert cfg["llm"]["base_url"] == "http://vllm:8000/v1"
    assert llm.agent_llm_config(cfg)["llm"]["base_url"] == "http://host.docker.internal:1234/v1"
