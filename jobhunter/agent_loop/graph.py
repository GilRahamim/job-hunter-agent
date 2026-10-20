"""Tool-using agent loop (ReAct style): the model picks the next tool until it reaches the goal,
stops on its own, or hits the step limit. The fixed pipeline in jobhunter/agent.py stays the default."""
from __future__ import annotations

import logging
import time
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from jobhunter import db
from jobhunter.agent_loop.tools import AgentContext, allowed_sources, make_tools
from jobhunter.config import load_config
from jobhunter.cv import load_profile as load_cv_profile
from jobhunter.filters import junior_reason
from jobhunter.llm import get_llm
from jobhunter.matcher import choices_text, explanation_language, scored_row
from jobhunter.models import JobMatch
from jobhunter.prompts import AGENT_NUDGE, AGENT_START, AGENT_SYSTEM
from jobhunter.stop import stop_requested

log = logging.getLogger(__name__)

MAX_NUDGES = 1
MAX_TOOL_OUTPUT_LOG = 200
KEEP_FULL_POSTINGS = 1        # older read_posting outputs are cut to their header (small local contexts)
POSTING_CUT_NOTE = "[full text removed to save context; call read_posting again if needed]"


class LoopState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    steps: int
    nudges: int
    stop_reason: str


class AgentUnavailable(RuntimeError):
    pass


def agent_llm_config(cfg: dict[str, Any]) -> dict[str, Any]:
    """config with `llm` replaced by llm + agent.llm overrides (e.g. a local Ollama model)."""
    return {**cfg, "llm": {**cfg["llm"], **(cfg["agent"].get("llm") or {})}}


def verdict_for(score: int) -> str:
    return "strong" if score >= 75 else "good" if score >= 60 else "stretch" if score >= 40 else "poor"


def compact_history(messages: list[BaseMessage], keep: int = KEEP_FULL_POSTINGS) -> list[BaseMessage]:
    """What the model is shown: all messages, but only the last `keep` postings in full.
    The graph state keeps everything; only the model's view is trimmed."""
    postings = [i for i, m in enumerate(messages) if isinstance(m, ToolMessage) and m.name == "read_posting"
                and "\nDescription:\n" in str(m.content)]
    cut = set(postings[:-keep] if keep else postings)
    out = []
    for i, m in enumerate(messages):
        if i in cut:
            head = str(m.content).split("\nDescription:\n", 1)[0]
            m = m.model_copy(update={"content": f"{head}\n{POSTING_CUT_NOTE}"})
        out.append(m)
    return out


def build_graph(llm: Any, ctx: AgentContext):
    tools = make_tools(ctx)
    by_name = {t.name: t for t in tools}
    model = llm.bind_tools(tools)
    max_steps = ctx.settings["max_steps"]

    def agent_node(state: LoopState) -> dict:
        if stop_requested():
            return {"stop_reason": "stopped_by_user"}
        try:
            reply = model.invoke(compact_history(state["messages"]))
        except Exception as e:  # noqa: BLE001 - provider errors end the loop; results so far are kept
            log.error("agent model call failed: %s", e)
            return {"stop_reason": f"model error: {type(e).__name__}: {e}"}
        step = state.get("steps", 0) + 1
        for call in getattr(reply, "tool_calls", None) or []:
            log.info("step %d: %s(%s)", step, call["name"], call.get("args"))
        if not getattr(reply, "tool_calls", None):
            log.info("step %d: model replied without a tool call: %.200s", step, reply.content)
        return {"messages": [reply], "steps": step}

    def tools_node(state: LoopState) -> dict:
        out = []
        for call in state["messages"][-1].tool_calls:
            tool = by_name.get(call["name"])
            if tool is None:
                content = f"ERROR: unknown tool {call['name']!r}. Tools: {', '.join(by_name)}."
            else:
                try:
                    content = str(tool.invoke(call.get("args") or {}))
                except Exception as e:  # noqa: BLE001 - bad arguments go back to the model
                    content = f"ERROR: invalid arguments for {call['name']}: {e}"
            log.debug("tool %s -> %.*s", call["name"], MAX_TOOL_OUTPUT_LOG, content)
            out.append(ToolMessage(content=content, tool_call_id=call["id"], name=call["name"]))
        return {"messages": out}

    def nudge_node(state: LoopState) -> dict:
        return {"messages": [HumanMessage(AGENT_NUDGE)], "nudges": state.get("nudges", 0) + 1}

    def after_agent(state: LoopState) -> str:
        if state.get("stop_reason"):
            return END
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        if ctx.goal_reached():
            return "goal_reached"
        if state.get("nudges", 0) < MAX_NUDGES and state.get("steps", 0) < max_steps \
                and "DONE" not in str(last.content):
            return "nudge"
        return "model_stopped"

    def after_tools(state: LoopState) -> str:
        if stop_requested():
            return "stopped_by_user"
        if ctx.goal_reached():
            return "goal_reached"
        if state.get("steps", 0) >= max_steps:
            return "step_limit"
        return "agent"

    def stop(reason: str):
        return lambda state: {"stop_reason": reason}

    g = StateGraph(LoopState)
    g.add_node("agent", agent_node)
    g.add_node("tools", tools_node)
    g.add_node("nudge", nudge_node)
    for reason in ("goal_reached", "step_limit", "model_stopped", "stopped_by_user"):
        g.add_node(reason, stop(reason))
        g.add_edge(reason, END)
    g.add_edge(START, "agent")
    g.add_conditional_edges("agent", after_agent)
    g.add_conditional_edges("tools", after_tools)
    g.add_edge("nudge", "agent")
    return g.compile()


def role_groups_text(groups: dict[str, list[str]]) -> str:
    if not groups:
        return "- the candidate's target roles (see get_profile)"
    return "\n".join(f"- {g}: {', '.join(titles)}" for g, titles in groups.items())


def experience_limit(years: float) -> str:
    return "no professional experience" if not years else f"at most {years:g} years of experience"


def initial_messages(ctx: AgentContext) -> list[BaseMessage]:
    s = ctx.settings
    years = ctx.config["filters"].get("max_required_years") or 0
    system = AGENT_SYSTEM.format(goal=s["goal_matches"], min_score=s["min_match_score"],
                                 sources=", ".join(allowed_sources(ctx.config)),
                                 max_searches=s["max_searches"],
                                 per_group=s.get("max_searches_per_group", s["max_searches"]),
                                 role_groups=role_groups_text(s.get("role_groups") or {}),
                                 junior_words=", ".join(ctx.config["filters"].get("junior_keywords")
                                                        or ["junior", "entry level", "graduate"]),
                                 max_years=f"{years:g}", experience_limit=experience_limit(years),
                                 language=explanation_language(ctx.config))
    return [SystemMessage(system),
            HumanMessage(AGENT_START.format(goal=s["goal_matches"], min_score=s["min_match_score"]))]


def result_rows(ctx: AgentContext, cv_hash: str, model: str) -> list[dict]:
    """Every candidate the agent saw; the ones it saved carry its score and reason. Jobs that turned
    out closed or experienced once read (save_match refused them) are left out."""
    rows = []
    for job_id, job in ctx.candidates.items():
        if job_id in ctx.closed or junior_reason(job, ctx.config):
            continue
        m = ctx.matches.get(job_id)
        match = JobMatch(score=m["score"], verdict=verdict_for(m["score"]), reasons=m["reason"]) if m else None
        row = scored_row(job, ctx.prescores[job_id], match, cv_hash, model)
        if m:
            row["scored_by"] = f"agent:{model}"
        rows.append(row)
    return rows


def run(config: dict[str, Any] | None = None, **options: Any) -> dict[str, Any]:
    """Run the agent loop once. Options: goal, max_steps, dry_run, db_path.
    Returns {"stats", "rows", "health", "matches"}."""
    cfg = agent_llm_config(config or load_config())
    if options.get("goal"):
        cfg["agent"] = {**cfg["agent"], "goal_matches": options["goal"]}
    if options.get("max_steps"):
        cfg["agent"] = {**cfg["agent"], "max_steps": options["max_steps"]}
    path, dry = options.get("db_path"), bool(options.get("dry_run"))
    if cfg.get("auto_from_cv"):
        raise AgentUnavailable("the agent loop is tuned for the owner's search (junior CS roles); "
                               "users created from a CV use the standard search (run without --agent)")

    llm = get_llm(cfg)
    if llm is None or not hasattr(llm, "bind_tools"):
        raise AgentUnavailable("the agent needs an LLM with tool calling: set llm.provider / agent.llm "
                               "in config.yaml and the key in .env, or run the pipeline without --agent")
    model = cfg["llm"]["model"]
    started = time.monotonic()
    profile, cv_hash, _ = load_cv_profile(cfg, llm, path)
    ids, keys = db.existing_ids_and_keys(path)
    choices = choices_text(db.status_examples(int(cfg["matching"].get("feedback_examples") or 0), path))
    ctx = AgentContext(config=cfg, profile=profile, known_ids=ids, known_keys=keys, choices=choices)
    run_id = None if dry else db.start_run(path)
    log.info("agent: %s | goal %d matches >= %d | max %d steps, %d searches", model,
             ctx.settings["goal_matches"], ctx.settings["min_match_score"], ctx.settings["max_steps"],
             ctx.settings["max_searches"])

    stop_reason = "crashed"
    try:
        final = build_graph(llm, ctx).invoke(
            {"messages": initial_messages(ctx), "steps": 0, "nudges": 0},
            {"recursion_limit": ctx.settings["max_steps"] * 2 + 2 * MAX_NUDGES + 10})
        stop_reason = final.get("stop_reason") or "model_stopped"
        steps = final.get("steps", 0)
    except Exception as e:
        log.exception("agent run crashed")
        if run_id:
            db.finish_run(run_id, {"mode": f"agent:{model}", "error": f"{type(e).__name__}: {e}"},
                          ctx.health, path)
        raise RuntimeError(f"agent crashed: {e}") from e

    rows = result_rows(ctx, cv_hash, model)
    stats = {
        "mode": f"agent:{model}", "stop_reason": stop_reason, "steps": steps,
        "searches": ctx.searches, "collected": ctx.collected, "kept": len(ctx.candidates),
        "filtered_by_reason": dict(ctx.drop_reasons), "read": len(ctx.read),
        "agent_matches": len(ctx.matches), "strong_matches": ctx.strong_matches(),
        "errors": [f"{h['source']}: {h['error']}" for h in ctx.health if h["error"]],
        "duration_s": round(time.monotonic() - started, 1), "dry_run": dry,
    }
    if not dry:
        db.upsert_jobs(rows, path)
        db.finish_run(run_id, stats, ctx.health, path)
    log.info("agent stopped (%s) after %d steps: %d saved matches, %d candidates%s", stop_reason, steps,
             len(ctx.matches), len(rows), " (dry run: nothing written)" if dry else "")
    return {"stats": stats, "rows": rows, "health": ctx.health, "matches": ctx.matches}
