#!/usr/bin/env bash
# Start the local vLLM server that config.vllm.yaml points at (scorer + smart agent, one model).
#
#   WSL2 (Ubuntu) with an NVIDIA GPU:  python3 -m venv ~/vllm && ~/vllm/bin/pip install vllm==0.31.0   (once)
#   (0.31.0 is built for CUDA 13: Windows NVIDIA driver 580 or newer; same version as docker-compose.vllm.yml)
#                                      source ~/vllm/bin/activate && bash scripts/vllm_serve.sh
#   Docker:                            docker compose -f docker-compose.vllm.yml up vllm   (runs this file)
#
# Sized for a 16 GB card: Qwen3-14B in 4-bit AWQ (~10 GB of weights) leaves ~3-4 GB for the KV cache.
# Per token of context that cache takes 2 (K, V) x 40 layers x 8 KV heads x 128 dims = 81,920 values:
# 160 KB in fp16, 80 KB in fp8, so fp8 fits ~40K tokens: one 32K agent context, or ~10 scoring prompts
# of ~4K tokens at once (vLLM queues the rest of the 16 parallel requests).
# Out of memory at start: MAX_LEN=16384, or MODEL=Qwen/Qwen3-8B-AWQ (more room, weaker answers).
# fp8 KV cache refused by your GPU / vLLM: KV_DTYPE=auto MAX_LEN=16384.
set -euo pipefail

MODEL="${MODEL:-Qwen/Qwen3-14B-AWQ}"
NAME="${NAME:-qwen3-local}"              # = llm.model in config.vllm.yaml, whatever MODEL is
MAX_LEN="${MAX_LEN:-32768}"              # the agent's context window
KV_DTYPE="${KV_DTYPE:-fp8}"
GPU_UTIL="${GPU_UTIL:-0.90}"             # share of VRAM vLLM takes; lower it if Windows needs more
MAX_SEQS="${MAX_SEQS:-16}"               # = llm.max_workers in config.vllm.yaml

exec vllm serve "$MODEL" \
  --served-model-name "$NAME" \
  --host 0.0.0.0 --port 8000 \
  --max-model-len "$MAX_LEN" \
  --kv-cache-dtype "$KV_DTYPE" \
  --gpu-memory-utilization "$GPU_UTIL" \
  --max-num-seqs "$MAX_SEQS" \
  --enable-auto-tool-choice --tool-call-parser hermes \
  --reasoning-parser qwen3
