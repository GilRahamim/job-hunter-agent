#!/usr/bin/env bash
# Start the local vLLM server that config.vllm.yaml points at (the scorer; the smart agent is LM Studio).
#
#   WSL2 (Ubuntu) with an NVIDIA GPU:  python3 -m venv ~/vllm && ~/vllm/bin/pip install vllm==0.31.0   (once)
#   (0.31.0 is built for CUDA 13: Windows NVIDIA driver 580 or newer; same version as docker-compose.vllm.yml)
#                                      source ~/vllm/bin/activate && bash scripts/vllm_serve.sh
#   Docker:                            docker compose -f docker-compose.vllm.yml up vllm   (runs this file)
#
# Sized for a 16 GB card: Qwen3-14B in 4-bit AWQ (~10 GB of weights) leaves ~3-4 GB for the KV cache.
# Per token of context that cache takes 2 (K, V) x 40 layers x 8 KV heads x 128 dims = 81,920 values:
# 160 KB in fp16 (measured on an RTX 5080: 20,896 tokens, ~5 scoring prompts of ~4K at once; vLLM
# queues the rest of the 16 parallel requests). fp8 would halve it, but on the RTX 5080 (sm120) the
# fp8 cache crashed FlashInfer's warmup with "CUDA error: unknown error", so fp16 is the default.
# Out of memory at start: MAX_LEN=8192, or MODEL=Qwen/Qwen3-8B-AWQ (more room, weaker answers).
# Twice the parallel scoring on a GPU where it works: KV_DTYPE=fp8.
set -euo pipefail

MODEL="${MODEL:-Qwen/Qwen3-14B-AWQ}"
NAME="${NAME:-qwen3-local}"              # = llm.model in config.vllm.yaml, whatever MODEL is
MAX_LEN="${MAX_LEN:-16384}"              # one scoring prompt (~4K) with room to spare; the agent is not here
KV_DTYPE="${KV_DTYPE:-auto}"            # auto = the model's dtype (fp16); see fp8 above
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
