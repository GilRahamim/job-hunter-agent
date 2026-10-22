# Local LLM (vLLM) and Docker

Two independent, optional setups:

- **vLLM**: score jobs and run the smart agent on a local model, free per call, so more jobs get an
  LLM score per run and more of them are scored at once.
- **Docker**: the dashboard and the search in a container, for a demo or a portfolio. Daily use on the
  owner's Windows PC stays `streamlit run dashboard.py`.

Nothing changes until you turn one on. The default stays Claude Haiku for scoring and LM Studio for the agent.

---

## 1. vLLM: one local server for the scorer and the agent

### What changes when it is on

| Setting | `config.yaml` (default) | with `config.vllm.yaml` |
|---|---|---|
| scorer (`llm`) | Claude Haiku (API, paid per job) | `qwen3-local` on vLLM, thinking off (JSON answer only) |
| requests at once (`llm.max_workers`) | 6 | 16 (vLLM batches them on the GPU) |
| jobs scored per run (`matching.llm_top_n`) | 60 | 200 |
| lowest pre-score sent to the LLM (`min_prescore_for_llm`) | 15 | 10 |
| smart agent (`agent.llm`) | LM Studio, Qwen 27B | the same vLLM model, thinking on |

One model serves both because a 16 GB GPU cannot hold LM Studio's 27B model and a vLLM model at once.
The agent drops from 27B to 14B: it plans a little less well, which the precision report will show.

### Why the 14B model fits 16 GB

Qwen3-14B in 4-bit AWQ is about 10 GB of weights. With `--gpu-memory-utilization 0.90` vLLM takes
14.4 GB, so roughly 3–4 GB are left for the KV cache (the per-token attention memory). Per token:

$$2\ (K,V) \times 40\ \text{layers} \times 8\ \text{KV heads} \times 128\ \text{dims} = 81{,}920\ \text{values}
\;\Rightarrow\; 160\ \text{KB in fp16},\ 80\ \text{KB in fp8}$$

With an fp8 cache that is about 40K tokens: one 32K agent context, or about 10 scoring prompts of ~4K
tokens at the same time. vLLM queues the rest of the 16 requests, so nothing fails, they just wait.

### Setup on Windows (WSL2), once

1. NVIDIA driver on Windows (the normal Game Ready / Studio driver; WSL2 uses it, no CUDA install in Linux).
2. PowerShell as admin: `wsl --install -d Ubuntu`, then reboot and open "Ubuntu".
3. In Ubuntu:
   ```bash
   sudo apt update && sudo apt install -y python3-venv
   python3 -m venv ~/vllm && ~/vllm/bin/pip install vllm
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
- Off (back to Claude Haiku + LM Studio): delete that line.

`JOBHUNTER_CONFIG` names files merged over `config.yaml` (comma-separated, in order); only what differs
is in them. It applies to the CLI and the dashboard (restart the dashboard after changing `.env`).

### Check that it works

```bash
curl http://127.0.0.1:8000/v1/models                    # lists "qwen3-local"
python run_agent.py --sources remotive --limit 20       # log: "llm: scoring N of M jobs", no errors
python run_agent.py --agent --goal 3 --dry-run          # log: "agent: qwen3-local, scorer: qwen3-local"
```

The dashboard's smart-agent toggle checks the same server and warns when it does not answer.

### Scores on a new scale

A 14B local model does not score like Claude Haiku. `scored_by` records the model (`llm:qwen3-local`),
so after a few runs and some statuses in the dashboard compare them:
`python scripts/agent_report.py --since <first vLLM day>`. If local scores run high or low, adjust
`agent.min_match_score` and `notify.min_score` in `config.vllm.yaml`.

### Tuning (environment variables of `scripts/vllm_serve.sh`)

| Problem | Try |
|---|---|
| out of memory at start | `MAX_LEN=16384 bash scripts/vllm_serve.sh`, or `GPU_UTIL=0.85` |
| fp8 KV cache refused (older GPU / vLLM) | `KV_DTYPE=auto MAX_LEN=16384` |
| still too big, or want more parallel scoring | `MODEL=Qwen/Qwen3-8B-AWQ` (more room, weaker answers); the config keeps working, the served name stays `qwen3-local` |
| more / fewer requests at once | `MAX_SEQS=24` and `llm.max_workers: 24` in `config.vllm.yaml` (keep them equal) |
| Windows cannot reach `127.0.0.1:8000` | in WSL2 run `hostname -I` and use `http://<that ip>:8000/v1` in `config.vllm.yaml`, or enable mirrored networking in `.wslconfig` |

If the server is down during a run, scoring fails per job (logged, retried) and those jobs keep their
heuristic score; the next run with the server up scores them.

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

The app then uses `config.vllm.yaml` with `config.docker.yaml` on top (the server is `http://vllm:8000`).

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
