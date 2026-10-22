# Local LLM (vLLM) and Docker

Two independent, optional setups:

- **vLLM**: score jobs on a local model, free per call, so more jobs get an LLM score per run and more
  of them are scored at once. The smart agent stays on LM Studio.
- **Docker**: the dashboard and the search in a container, for a demo or a portfolio. Daily use on the
  owner's Windows PC stays `streamlit run dashboard.py`.

Nothing changes until you turn one on. The default stays Claude Haiku for scoring and LM Studio for the agent.

---

## 1. vLLM for the scorer, LM Studio for the agent

### What changes when it is on

| Setting | `config.yaml` (default) | with `config.vllm.yaml` |
|---|---|---|
| scorer (`llm`) | Claude Haiku (API, paid per job) | `qwen3-local` on vLLM, thinking off (JSON answer only) |
| requests at once (`llm.max_workers`) | 6 | 16 (vLLM batches them on the GPU) |
| jobs scored per run (`matching.llm_top_n`) | 60 | 200 |
| lowest pre-score sent to the LLM (`min_prescore_for_llm`) | 15 | 10 |
| smart agent (`agent.llm`) | LM Studio, Qwen3.8 27B | unchanged |
| who scores the agent's picks (`agent.scorer`) | `main` (Claude Haiku) | `agent` (the 27B itself) |

Why the split: scoring is many short, parallel requests with a fixed rubric, where vLLM's batching pays
off and a 14B model is enough. The agent is one long conversation that plans searches, where model
size matters. vLLM keeps every weight on the GPU, so the largest model it fits on 16 GB is about 14B
(the 27B is ~18.7 GB as AWQ); LM Studio (llama.cpp) fits the 27B with ~3-bit GGUF quants and a
quantized KV cache.

### One GPU, one model at a time

A 16 GB card cannot hold both servers, so switch between them:

| Run | vLLM | LM Studio |
|---|---|---|
| regular search (`python run_agent.py`, dashboard button) | running | model unloaded (`lms unload --all`) |
| smart agent (`--agent`, dashboard toggle) | stopped (Ctrl+C, or `docker compose ... stop vllm`) | 27B loaded |

During an agent run the 27B scores the jobs it saves (`agent.scorer: agent`), so nothing calls vLLM.
Those jobs get `scored_by = agent:qwen/qwen3.8-27b`, regular ones `llm:qwen3-local`: two models, two
scales; compare them with `scripts/agent_report.py`. If vLLM is down during a regular run, scoring
fails per job (logged) and those jobs keep their heuristic score until the next run with it up.

### Why the 14B model fits 16 GB

Qwen3-14B in 4-bit AWQ is about 10 GB of weights. With `--gpu-memory-utilization 0.90` vLLM takes
14.4 GB, so roughly 3–4 GB are left for the KV cache (the per-token attention memory). Per token:

$$2\ (K,V) \times 40\ \text{layers} \times 8\ \text{KV heads} \times 128\ \text{dims} = 81{,}920\ \text{values}
\;\Rightarrow\; 160\ \text{KB in fp16},\ 80\ \text{KB in fp8}$$

With an fp8 cache that is about 40K tokens: about 10 scoring prompts of ~4K tokens at the same time.
vLLM queues the rest of the 16 requests, so nothing fails, they just wait.

### Setup on Windows (WSL2), once

1. NVIDIA driver on Windows, version 580 or newer (the normal Game Ready / Studio driver; WSL2 uses it,
   no CUDA install in Linux). vLLM 0.31.0 is built for CUDA 13, which needs it. Check with `nvidia-smi`.
2. PowerShell as admin: `wsl --install -d Ubuntu`, then reboot and open "Ubuntu".
3. In Ubuntu:
   ```bash
   sudo apt update && sudo apt install -y python3-venv
   python3 -m venv ~/vllm && ~/vllm/bin/pip install vllm==0.31.0     # pinned: the flags in scripts/vllm_serve.sh are checked against it
   ```
4. Start the server (the first start downloads the model, ~10 GB):
   ```bash
   source ~/vllm/bin/activate
   cd /mnt/c/<path to>/job-hunter-agent
   bash scripts/vllm_serve.sh
   ```
   Ready when it prints `Application startup complete`. Leave the window open.

Docker instead of WSL2 pip (needs Docker Desktop with the WSL2 backend):
`docker compose -f docker-compose.yml -f docker-compose.vllm.yml up vllm`.

### Turn it on and off

- On: add `JOBHUNTER_CONFIG=config.vllm.yaml` to `.env`.
- Off (back to Claude Haiku as the scorer, also for the agent's picks): delete that line.

`JOBHUNTER_CONFIG` names files merged over `config.yaml` (comma-separated, in order); only what differs
is in them. It applies to the CLI and the dashboard (restart the dashboard after changing `.env`).

### Check that it works

```bash
curl http://127.0.0.1:8000/v1/models                    # lists "qwen3-local"
python run_agent.py --sources remotive --limit 20       # log: "llm: scoring N of M jobs", no errors
# stop vLLM, load the 27B in LM Studio, then:
python run_agent.py --agent --goal 3 --dry-run          # log: "agent: qwen/qwen3.8-27b, scorer: qwen/qwen3.8-27b"
```

The dashboard's smart-agent toggle checks LM Studio (the agent's server), not vLLM, and warns when it
does not answer.

### Scores on a new scale

Neither local model scores like Claude Haiku. `scored_by` records the model (`llm:qwen3-local` for
regular runs, `agent:qwen/qwen3.8-27b` for agent picks), so after a few runs and some statuses in the
dashboard compare them: `python scripts/agent_report.py --since <first vLLM day>`. If local scores run
high or low, adjust `agent.min_match_score` and `notify.min_score` in `config.vllm.yaml`.

### Tuning (environment variables of `scripts/vllm_serve.sh`)

| Problem | Try |
|---|---|
| out of memory at start | `MAX_LEN=8192 bash scripts/vllm_serve.sh`, or `GPU_UTIL=0.85` |
| fp8 KV cache refused (older GPU / vLLM) | `KV_DTYPE=auto` |
| still too big, or want more parallel scoring | `MODEL=Qwen/Qwen3-8B-AWQ` (more room, weaker answers); the config keeps working, the served name stays `qwen3-local` |
| more / fewer requests at once | `MAX_SEQS=24` and `llm.max_workers: 24` in `config.vllm.yaml` (keep them equal) |
| Windows cannot reach `127.0.0.1:8000` | in WSL2 run `hostname -I` and use `http://<that ip>:8000/v1` in `config.vllm.yaml`, or enable mirrored networking in `.wslconfig` |

---

## 2. Docker (demo / portfolio)

```bash
docker compose up --build           # http://localhost:8501
```

- Your CV: put it in `./cv` (or upload it in the dashboard's Profile tab).
- Jobs live in the `data` Docker volume (`docker compose down -v` wipes them), not in `./data`, so a
  demo never touches your real database.
- Keys: `.env` is passed in when it exists; without one, every job gets the free heuristic score.
- `config.yaml` is mounted read-only: edit it on the host and start a new run, no rebuild needed.

With a local vLLM server in the same compose project (NVIDIA GPU):

```bash
docker compose -f docker-compose.yml -f docker-compose.vllm.yml up --build
```

The app then uses `config.vllm.yaml` with `config.docker.yaml` on top: the scorer is the `vllm` service
(`http://vllm:8000`), the smart agent is LM Studio on the Windows host (`http://host.docker.internal:1234`).
The same one-GPU rule applies: stop the `vllm` service before an agent run.

Not available inside the container: opening Claude Code from the dashboard ("prepare with Claude" still
writes the brief to download), and Windows desktop notifications.

CI builds the image and checks that the dashboard answers (`.github/workflows/tests.yml`, job `docker`).

| File | What |
|---|---|
| `Dockerfile` | Python 3.11 slim, non-root user, health check on Streamlit's `/_stcore/health` |
| `.dockerignore` | keeps `.env`, `cv/`, `data/`, `users/` and the tests out of the image |
| `docker-compose.yml` | the app: port 8501 on localhost, `./cv` mounted, `data` / `users` volumes |
| `docker-compose.vllm.yml` | adds the `vllm` service (GPU) and points the app at it |
| `config.vllm.yaml` / `config.docker.yaml` | the vLLM settings / the server's address inside compose |
| `scripts/vllm_serve.sh` | the vLLM command line, shared by WSL2 and Docker |
