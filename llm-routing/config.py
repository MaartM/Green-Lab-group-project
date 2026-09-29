from pathlib import Path

HERE = Path(__file__).resolve().parent

SMALL_MODEL = "qwen3.5:2b-q4_K_M"
BIG_MODEL = "qwen3.5:9b-q4_K_M"
ROUTER_THRESHOLD = 0.65
ROUTER_MODEL_PATH = None


def router_model_path() -> Path:
    if ROUTER_MODEL_PATH is not None:
        return Path(ROUTER_MODEL_PATH)
    models = HERE.parent / "data" / "router_model"
    return max(models.glob("router-*.joblib"), key=lambda p: p.stem.rsplit("-", 1)[-1],
               default=models / "router.joblib")


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

REMOTE_HOST = "glg2"
REMOTE_DIR = "/home/gl_team42/Green-Lab-group-project/llm-routing"
REMOTE_RESULTS_DIR = "/home/gl_team42/llm-routing-results"
REQUIRE_SAME_COMMIT = True
REMOTE_PYTHON = "/home/gl_team42/Green-Lab-group-project/.venv/bin/python"
ENERGIBRIDGE_CMD = "energibridge"
WARMUP_S = 300
SERVER_START_TIMEOUT_S = 120
SERVER_READY_TIMEOUT_S = 600
RUN_TIMEOUT_S = 3600
