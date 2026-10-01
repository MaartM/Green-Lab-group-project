from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent

# SSH host alias of the testbed (see ~/.ssh/config).
TESTBED_HOST = "glg2"
# Testbed folders mirror this repository, so paths like ROUTER_FILE work on both sides.
TESTBED_ROOT = "green-lab"
TESTBED_DIR = f"{TESTBED_ROOT}/llm-routing"
TESTBED_PYTHON = ".venv/bin/python"

MODELS = {
    "small": {"tag": "qwen3.5:2b-q4_K_M", "gpu": 1, "port": 11501},
    "large": {"tag": "qwen3.5:9b-q4_K_M", "gpu": 0, "port": 11500},
}
# Strategy R uses the small model when P(small model correct) > ROUTER_THRESHOLD.
ROUTER_FILE = REPO_ROOT / "data" / "router_model" / "router.joblib"
ROUTER_THRESHOLD = 0.55

STRATEGY_MODELS = {
    "S": ["small"],
    "L": ["large"],
    "R": ["small", "large"],
}

# How every question is asked, in router labelling and in the experiment (see ollama_server.ask).
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
# Machine warm-up before the first run, so no run is measured on a cold testbed.
WARMUP_SECONDS = 300
