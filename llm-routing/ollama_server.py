"""
Start and stop the Ollama instances per strategy.

  python llm-routing/ollama_server.py pull        # download both models
  python llm-routing/ollama_server.py up R        # start strategy R, wait for Enter, stop
"""

import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
import config

running: list[subprocess.Popen] = []

def request(name: str, path: str, payload: dict | None = None) -> dict:
    port = config.MODELS[name]["port"]
    data = None if payload is None else json.dumps(payload).encode()
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", data) as resp:
        return json.loads(resp.read())

def is_up(name: str) -> bool:
    try:
        request(name, "/api/version")
        return True
    except OSError:
        return False

def start(name: str) -> None:
    model = config.MODELS[name]
    assert not is_up(name), f"port {model['port']} already in use"
    env = {**os.environ,
           "CUDA_VISIBLE_DEVICES": str(model["gpu"]),
           "OLLAMA_HOST": f"127.0.0.1:{model['port']}",
           "OLLAMA_KEEP_ALIVE": "-1",
           "OLLAMA_NUM_PARALLEL": "1"}
    process = subprocess.Popen(["ollama", "serve"], env=env, start_new_session=True)
    running.append(process)
    while not is_up(name):
        time.sleep(0.5)

def warm_up(name: str) -> None:
    tag = config.MODELS[name]["tag"]
    request(name, "/api/generate", {"model": tag, "prompt": config.WARMUP_PROMPT, "stream": False,
                                    "options": config.OPTIONS})
    loaded = request(name, "/api/ps")["models"]
    assert any(m["name"] == tag and m["size_vram"] == m["size"] for m in loaded), f"{tag} not fully in VRAM"

def start_strategy(strategy: str) -> None:
    for name in config.STRATEGY_MODELS[strategy]:
        start(name)
        warm_up(name)

def stop_all() -> None:
    while running:
        process = running.pop()
        os.killpg(process.pid, signal.SIGTERM)
        process.wait()

if __name__ == "__main__":
    if sys.argv[1:2] == ["pull"]:
        for name, model in config.MODELS.items():
            start(name)
            print(f"Pulling {model['tag']} ...")
            request(name, "/api/pull", {"model": model["tag"], "stream": False})
            stop_all()
    elif sys.argv[1:2] == ["up"]:
        start_strategy(sys.argv[2])
        input(f"Strategy {sys.argv[2]} up. Press Enter to stop.")
        stop_all()
    else:
        sys.exit(__doc__)
