"""
Send the questions to the model(s) of one strategy and log one row per question.

  python llm-routing/run_queries.py <S|L|R> <out.csv>
"""

import csv
import json
import sys
import time
import config
import ollama_server
from answers import is_correct


def choose_model(strategy, question):
    if strategy == "S":
        return "small"
    if strategy == "L":
        return "large"
    # R: STUB for now.
    return "small" if len(question.split()) < 45 else "large"


strategy, out_path = sys.argv[1], sys.argv[2]
questions = [json.loads(line) for line in open(config.QUESTIONS_FILE)]

with open(out_path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["qid", "model", "latency_s", "completion_tokens", "correct", "response"])

    for q in questions:
        start = time.perf_counter()
        model = choose_model(strategy, q["question"])
        result = ollama_server.ask(model, q["question"])
        latency = time.perf_counter() - start

        response = result["message"]["content"]
        correct = is_correct(response, q["answer"])
        writer.writerow([q["qid"], model, latency, result["eval_count"], int(correct), response])
