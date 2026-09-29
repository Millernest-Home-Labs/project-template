#!/usr/bin/env python3
"""
LLM Benchmark Script for llama.cpp

Benchmarks a running llama.cpp server by sending a generation request while
sampling GPU metrics (utilization, VRAM, temperature, power) at 20Hz.

Usage:
    python bench.py [model_alias] [max_tokens]

Examples:
    python bench.py Qwen3.6-27B 256
    python bench.py Qwen3.6-35B-A3B-UD 512
"""

import json
import time
import subprocess
import urllib.request
import threading
import sys

# Configuration
url = "http://localhost:8080/v1/chat/completions"
headers = {"Content-Type": "application/json"}

# GPU sampling state
gpu_samples = []
sampling = False


def sample_gpu():
    """Background thread: sample nvidia-smi at ~20Hz."""
    while sampling:
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,memory.used,memory.free,temperature.gpu,power.draw",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=2,
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(",")
                gpu_samples.append({
                    "time": time.time(),
                    "gpu_util": float(parts[0]),
                    "mem_used": float(parts[1]),
                    "mem_free": float(parts[2]),
                    "temp": float(parts[3]),
                    "power": float(parts[4]),
                })
        except Exception:
            pass
        time.sleep(0.05)


def benchmark(model_alias, max_tokens=256):
    """Run a single benchmark pass against the llama.cpp server."""

    # Build the OpenAI-compatible request
    data = json.dumps({
        "model": model_alias,
        "messages": [{
            "role": "user",
            "content": "Write a detailed technical explanation of how transformers work in deep learning. Cover attention mechanisms, feed-forward networks, and layer normalization in depth."
        }],
        "max_tokens": max_tokens,
        "stream": False,
    }).encode()

    # Start GPU sampling
    gpu_samples.clear()
    sampling = True
    gpu_thread = threading.Thread(target=sample_gpu, daemon=True)
    gpu_thread.start()

    # Send the request
    req = urllib.request.Request(url, data=data, headers=headers)
    start = time.time()
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    elapsed = (time.time() - start) * 1000

    # Stop GPU sampling
    sampling = False
    gpu_thread.join(timeout=2)

    # Parse timing results from llama.cpp response
    t = result.get("timings", {})
    prompt_tok = t.get("prompt_n", 0)
    prompt_ms = t.get("prompt_ms", 0)
    gen_tok = t.get("predicted_n", 0)
    gen_ms = t.get("predicted_ms", 0)

    prompt_speed = prompt_tok / max(prompt_ms, 1) * 1000
    gen_speed = gen_tok / max(gen_ms, 1) * 1000

    # Aggregate GPU metrics
    if gpu_samples:
        avg_util = sum(s["gpu_util"] for s in gpu_samples) / len(gpu_samples)
        max_util = max(s["gpu_util"] for s in gpu_samples)
        avg_mem = sum(s["mem_used"] for s in gpu_samples) / len(gpu_samples)
        max_mem = max(s["mem_used"] for s in gpu_samples)
        avg_temp = sum(s["temp"] for s in gpu_samples) / len(gpu_samples)
        max_temp = max(s["temp"] for s in gpu_samples)
        avg_power = sum(s["power"] for s in gpu_samples) / len(gpu_samples)
        max_power = max(s["power"] for s in gpu_samples)
    else:
        avg_util = max_util = avg_mem = max_mem = 0
        avg_temp = max_temp = avg_power = max_power = 0

    # Print results
    print(f"Model: {model_alias}")
    print(f"  Prompt: {prompt_tok} tokens in {prompt_ms:.0f}ms ({prompt_speed:.1f} tok/s)")
    print(f"  Gen:    {gen_tok} tokens in {gen_ms:.0f}ms ({gen_speed:.1f} tok/s)")
    print(f"  Total:  {elapsed:.0f}ms")
    print(f"  GPU:    avg {avg_util:.0f}% / max {max_util:.0f}% util")
    print(f"  VRAM:   avg {avg_mem:.0f}MB / max {max_mem:.0f}MB")
    print(f"  Temp:   avg {avg_temp:.0f}C / max {max_temp:.0f}C")
    print(f"  Power:  avg {avg_power:.0f}W / max {max_power:.0f}W")

    return {
        "model": model_alias,
        "prompt_tokens": prompt_tok,
        "prompt_ms": prompt_ms,
        "prompt_speed": prompt_speed,
        "gen_tokens": gen_tok,
        "gen_ms": gen_ms,
        "gen_speed": gen_speed,
        "total_ms": elapsed,
        "gpu_avg_util": avg_util,
        "gpu_max_util": max_util,
        "vram_avg_mb": avg_mem,
        "vram_max_mb": max_mem,
        "temp_avg_c": avg_temp,
        "temp_max_c": max_temp,
        "power_avg_w": avg_power,
        "power_max_w": max_power,
    }


if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else "Qwen3.6-27B"
    tokens = int(sys.argv[2]) if len(sys.argv) > 2 else 256
    benchmark(model, tokens)
