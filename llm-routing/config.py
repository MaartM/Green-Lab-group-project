from pathlib import Path

HERE = Path(__file__).resolve().parent

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
