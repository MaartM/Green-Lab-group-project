"""
Start and stop the Ollama instances per strategy.

  python llm-routing/ollama_server.py pull        # download both models
  python llm-routing/ollama_server.py up R        # start strategy R, wait for Enter, stop
  python llm-routing/ollama_server.py start R     # start strategy R and leave it running
  python llm-routing/ollama_server.py stop        # stop what `start` left running

`start` and `stop` are separate commands because the laptop calls them in
separate SSH sessions: the servers must outlive the session that started them.
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
PID_FILE = config.HERE / "ollama_servers.pid"

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
    # PCI_BUS_ID makes CUDA number the GPUs like nvidia-smi and EnergiBridge do.
    # CUDA's default order differs on glg2, which would swap the GPUs in the results.
    env = {**os.environ,
           "CUDA_DEVICE_ORDER": "PCI_BUS_ID",
           "CUDA_VISIBLE_DEVICES": str(model["gpu"]),
           "OLLAMA_HOST": f"127.0.0.1:{model['port']}",
           "OLLAMA_KEEP_ALIVE": "-1",
           "OLLAMA_NUM_PARALLEL": "1"}
    # Output goes to a log file and input comes from /dev/null, so a detached
    # server holds nothing open that would keep the SSH session from closing.
    log = open(config.HERE / f"ollama_{name}.log", "a")
    process = subprocess.Popen(["ollama", "serve"], env=env, start_new_session=True,
                               stdin=subprocess.DEVNULL, stdout=log, stderr=log)
    running.append(process)
    while not is_up(name):
        time.sleep(0.5)

def ask(name: str, question: str) -> dict:
    """Ask one model one question. Router training labelling and the experiment both use this."""
    return request(name, "/api/chat", {
        "model": config.MODELS[name]["tag"],
        "messages": [{"role": "system", "content": config.SYSTEM_PROMPT},
                     {"role": "user", "content": question}],
        "stream": False,
        "think": config.THINK,
        "keep_alive": -1,
        "options": config.OPTIONS,
    })

def warm_up(name: str) -> None:
    tag = config.MODELS[name]["tag"]
    ask(name, config.WARMUP_QUESTION)
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

def start_detached(strategy: str) -> None:
    start_strategy(strategy)
    PID_FILE.write_text("".join(f"{process.pid}\n" for process in running))

def stop_detached() -> None:
    # These servers were started by an earlier process, so there is no Popen
    # to wait on: poll until each is gone, so its port and VRAM are free again.
    for pid in map(int, PID_FILE.read_text().split()):
        os.killpg(pid, signal.SIGTERM)
        while is_alive(pid):
            time.sleep(0.2)
    PID_FILE.unlink()

def is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False

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
    elif sys.argv[1:2] == ["start"]:
        start_detached(sys.argv[2])
    elif sys.argv[1:2] == ["stop"]:
        stop_detached()
    else:
        sys.exit(__doc__)
