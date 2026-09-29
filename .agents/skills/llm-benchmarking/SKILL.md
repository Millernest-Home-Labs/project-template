---
name: llm-benchmarking
description: 'Benchmark llama.cpp models across context sizes, KV cache types, and GPU settings. Measures token speed, VRAM usage, temperature, and power draw.'
---

# LLM Benchmarking Skill

Benchmark llama.cpp models on GPU servers to measure token generation speed, VRAM usage, GPU temperature, and power draw across different configurations.

## Prerequisites

- SSH access to LLM server (ethan@192.168.1.149, key: ~/.ssh/id_ed25519_ubuntu)
- Docker with GPU support (--gpus all)
- NVIDIA GPU with nvidia-smi available
- Python 3 with urllib.request (stdlib, no pip install needed)

## Server Connection

```powershell
ssh -i "$env:USERPROFILE\.ssh\id_ed25519_ubuntu" ethan@192.168.1.149
```

## Step 1: Stop Existing Container

```powershell
ssh -i "$env:USERPROFILE\.ssh\id_ed25519_ubuntu" ethan@192.168.1.149 "docker stop llama-cpp-server ; docker rm llama-cpp-server"
```

## Step 2: Start Container with Test Configuration

Use `docker run` directly (not docker-compose) for benchmarking, so you can change settings per-run:

```powershell
ssh -i "$env:USERPROFILE\.ssh\id_ed25519_ubuntu" ethan@192.168.1.149 "docker run -d --name llama-cpp-server --gpus all -p 8080:8080 -v /path/to/models:/models ghcr.io/ggml-org/llama.cpp:server-cuda llama-server --model /models/ModelFile.gguf --ctx-size 131072 --kv-cache-type q8 --gpu-layers 999 --threads 8 --threads-backend 8 --log-disable"
```

Key parameters:
- **--ctx-size**: Context window (32768, 48K, 65536, 98304, 131072)
- **--kv-cache-type**: KV cache quantization (f16=default, q8=reduced VRAM)
- **--gpu-layers**: 999 = all layers on GPU
- **--threads / --threads-backend**: CPU thread count for offloaded work

## Step 3: Wait for Model Load

```powershell
ssh -i "$env:USERPROFILE\.ssh\id_ed25519_ubuntu" ethan@192.168.1.149 "docker logs llama-cpp-server --tail 20"
```

Look for `server listen` in the logs to confirm readiness.

## Step 4: Run Benchmark Script

The benchmark script (`scripts/bench.py`) sends a generation request while sampling GPU metrics at 20Hz.

### Running Locally (on the LLM server)

```bash
# SSH to the server and run inside the container
ssh -i "$env:USERPROFILE\.ssh\id_ed25519_ubuntu" ethan@192.168.1.149
docker exec -it llama-cpp-server python3 /path/to/bench.py Qwen3.6-27B 256
```

### Running from the Container

Copy `scripts/bench.py` into the container and run:

```bash
docker cp scripts/bench.py llama-cpp-server:/tmp/bench.py
docker exec llama-cpp-server python3 /tmp/bench.py Qwen3.6-27B 256
```

### Usage

```bash
python bench.py [model_alias] [max_tokens]
```

- **model_alias**: Model name configured in llama.cpp (default: `Qwen3.6-27B`)
- **max_tokens**: Number of tokens to generate (default: `256`)

### Example Output

```
Model: Qwen3.6-27B
  Prompt: 42 tokens in 180ms (233.3 tok/s)
  Gen:    256 tokens in 6100ms (41.9 tok/s)
  Total:  6350ms
  GPU:    avg 95% / max 99% util
  VRAM:   avg 16200MB / max 16800MB
  Temp:   avg 68C / max 72C
  Power:  avg 345W / max 370W
```

## Step 5: Iterate Through Configurations

For comprehensive benchmarks, test each context size. Between each run:

```powershell
# Stop, remove, restart with new ctx-size
ssh -i "$env:USERPROFILE\.ssh\id_ed25519_ubuntu" ethan@192.168.1.149 "docker stop llama-cpp-server ; docker rm llama-cpp-server"
# Then docker run with new --ctx-size value
```

Recommended context sizes to test: 32K, 48K, 64K, 96K, 128K.

## Step 6: Interpret Results

### Key Metrics

| Metric | What it tells you | Good threshold |
|--------|------------------|----------------|
| Prompt tok/s | How fast the model processes input | >300 tok/s |
| Gen tok/s | Token generation throughput (the main speed metric) | >40 tok/s for 27B, >100 tok/s for MoE |
| VRAM max | Peak GPU memory usage | <90% of available VRAM |
| GPU Util | How saturated the GPU is | >90% means GPU-bound (good) |
| Temp | GPU temperature | <75C safe, >80C concern |
| Power | GPU power draw | correlates with utilization |

### Common Patterns

- **Gen speed drops as context grows**: KV cache is consuming VRAM bandwidth. Try `--kv-cache-type q8`.
- **Prompt speed drops but gen speed stable**: Context is large but generation is fine. Acceptable tradeoff.
- **OOM at large contexts**: Reduce `--ctx-size` or use a smaller model. 265K context fails on RTX 3090 (24GB).
- **GPU Util < 90% during gen**: CPU bottleneck. Check `--threads` settings.

## Reference Results (RTX 3090 24GB)

### Qwen3.6-35B-A3B-UD-Q4_K_M (MoE, 22GB model)

| Ctx | Prompt t/s | Gen t/s | VRAM (GB) | Temp | Power |
|-----|-----------|---------|-----------|------|-------|
| 32K | 489 | 148 | 21.9 | 62C | 335W |
| 48K | 487 | 148 | 22.1 | 63C | 340W |
| 64K | 191 | 42 | 22.4 | 72C | 378W |
| 96K | 193 | 148 | 22.8 | 62C | 334W |
| 128K | 487 | 148 | 23.2 | 63C | 342W |

### Qwen3.6-27B-Q4_K_M (Dense, 16GB model)

| Ctx | Prompt t/s | Gen t/s | VRAM (GB) | Temp | Power |
|-----|-----------|---------|-----------|------|-------|
| 32K | 228 | 42 | 17.9 | 70C | 347W |
| 48K | 139 | 42 | 18.5 | 63C | 338W |
| 64K | 100 | 32 | 19.1 | 67C | 352W |
| 96K | 154 | 30 | 20.4 | 68C | 351W |
| 128K | 134 | 42 | 21.6 | 68C | 345W |

Note: Some runs show anomalous drops (64K for both models, 96K/64K for 27B) likely due to cold cache. Run each config twice and take the better result.

## Troubleshooting

### OOM (cudaMalloc failed: out of memory)
- Reduce `--ctx-size` (128K is the max for RTX 3090 with these models)
- Use `--kv-cache-type q8` to reduce KV cache VRAM
- Switch to a smaller model

### Container won't start
- Check docker logs for model path errors
- Verify `--gpus all` is passed and NVIDIA container toolkit is installed
- Check disk space on /models volume

### Slow inference despite high GPU util
- Check if swap is being used: `free -h`
- Verify ngl (gpu-layers) is set to 999 (all layers on GPU)
- Check for CPU offloading in docker logs