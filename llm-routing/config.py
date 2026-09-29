from pathlib import Path

HERE = Path(__file__).resolve().parent

# The testbed is driven from the laptop over SSH. TESTBED_HOST is a host alias
# from ~/.ssh/config, which also takes care of the glgate jump host.
# TESTBED_DIR is where the experiment files go, relative to the testbed home.
TESTBED_HOST = "glg2"
TESTBED_DIR = "llm-routing"

SMALL_MODEL = "qwen3.5:2b-q4_K_M"
BIG_MODEL = "qwen3.5:9b-q4_K_M"
ROUTER_THRESHOLD = 0.65

MODELS = {
    "small": {"tag": "qwen3.5:0.8b", "gpu": 1, "port": 11501},
    "large": {"tag": "qwen3.5:9b",   "gpu": 0, "port": 11500},
}

STRATEGY_MODELS = {
    "S": ["small"],
    "L": ["large"],
    "R": ["small", "large"],
}

OPTIONS = {
    "temperature": 0,
    "seed": 42,
    "num_predict": 512,
    "num_ctx": 2048,
}
THINK = False
QUESTIONS_FILE = HERE / "questions.jsonl"
WARMUP_PROMPT = "What is 2 + 3? Answer with a number."
PROMPT = ("Solve the following math problem step by step. "
          "End with the final numeric answer on its own line in the form '#### <number>'.\n\n{question}")
