"""Provider-agnostic chat model. Returns None when the LLM is disabled or has no key."""
from __future__ import annotations

import logging
import os
from typing import Any

from jobhunter.config import load_env

log = logging.getLogger(__name__)

_KEY_ENV = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google_genai": "GOOGLE_API_KEY",
    "ollama": None,                    # local, no key
}
# llm settings handled here; any other key (base_url, max_tokens, num_ctx, ...) goes to the model
_OWN_KEYS = {"provider", "model", "temperature", "max_workers", "anthropic_workspace_id"}
LOCAL_API_KEY = "local"                # placeholder for OpenAI-compatible local servers (LM Studio)


def _has_key(provider: str) -> bool:
    if provider not in _KEY_ENV:
        return False
    env = _KEY_ENV[provider]
    return env is None or bool(os.environ.get(env))


def get_llm(cfg: dict[str, Any]) -> Any | None:
    """A LangChain chat model, or None -> callers fall back to heuristics."""
    load_env()
    llm_cfg = cfg["llm"]
    provider = llm_cfg["provider"]
    local = provider == "openai" and bool(llm_cfg.get("base_url"))
    if provider == "none" or not (local or _has_key(provider)):
        if provider != "none":
            log.warning("LLM provider %r has no API key in .env; using heuristics only", provider)
        return None
    from langchain.chat_models import init_chat_model

    kwargs: dict[str, Any] = {k: v for k, v in llm_cfg.items() if k not in _OWN_KEYS}
    if local:
        kwargs["api_key"] = LOCAL_API_KEY          # never send a real OpenAI key to a local server
    if provider == "anthropic" and llm_cfg.get("anthropic_workspace_id"):
        kwargs["default_headers"] = {"anthropic-workspace-id": llm_cfg["anthropic_workspace_id"]}
    return init_chat_model(llm_cfg["model"], model_provider=provider,
                           temperature=llm_cfg.get("temperature", 0), **kwargs)
