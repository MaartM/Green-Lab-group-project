from pathlib import Path

HERE = Path(__file__).resolve().parent

# The testbed is driven from the laptop over SSH. TESTBED_HOST is a host alias
# from ~/.ssh/config, which also takes care of the glgate jump host.
# The files the testbed needs are copied into TESTBED_ROOT (relative to the
# testbed home) with the same layout as in this repository, so paths such as
# ROUTER_FILE work on both sides. Commands run in TESTBED_DIR, with the Python
# environment created there by RunnerConfig.
REPO_ROOT = HERE.parent
TESTBED_HOST = "glg2"
TESTBED_ROOT = "green-lab"
TESTBED_DIR = f"{TESTBED_ROOT}/llm-routing"
TESTBED_PYTHON = ".venv/bin/python"

MODELS = {
    "small": {"tag": "qwen3.5:2b-q4_K_M", "gpu": 1, "port": 11501},
    "large": {"tag": "qwen3.5:9b-q4_K_M", "gpu": 0, "port": 11500},
}
# Strategy R sends a question to the small model when the router's predicted
# probability that the small model answers it correctly is above the threshold.
ROUTER_FILE = HERE.parent / "data" / "router_model" / "router.joblib"
ROUTER_THRESHOLD = 0.55

STRATEGY_MODELS = {
    "S": ["small"],
    "L": ["large"],
    "R": ["small", "large"],
}

# How every question is asked, in labelling and in the experiment alike
# (see ollama_server.ask).
SYSTEM_PROMPT = ("Solve the math word problem using at most three short calculation lines. "
                 "Do not repeat the question. On the final line write exactly #### followed "
                 "by the numeric answer, without units or commas.")
OPTIONS = {
    "temperature": 0,
    "seed": 42,
    "num_predict": 512,
    "num_ctx": 4096,
}
THINK = False
QUESTIONS_FILE = HERE / "questions.jsonl"
WARMUP_QUESTION = "What is 2 + 3?"
# Machine warm-up before the first run, so early runs are not measured on a
# cold testbed.
WARMUP_SECONDS = 300
