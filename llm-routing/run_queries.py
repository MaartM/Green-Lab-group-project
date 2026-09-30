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


def load_router():
    import joblib
    router = joblib.load(config.ROUTER_FILE)
    small_correct = list(router.classes_).index(1)
    return lambda question: float(router.predict_proba([question])[0][small_correct])


def choose_model(strategy, question, predict):
    """Return the model to use and, for strategy R, the router's probability."""
    if strategy == "S":
        return "small", None
    if strategy == "L":
        return "large", None
    probability = predict(question)
    return ("small" if probability > config.ROUTER_THRESHOLD else "large"), probability


strategy, out_path = sys.argv[1], sys.argv[2]
questions = [json.loads(line) for line in open(config.QUESTIONS_FILE)]
predict = load_router() if strategy == "R" else None

with open(out_path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["qid", "model", "p_small_correct", "latency_s", "completion_tokens", "correct", "response"])

    for q in questions:
        # The routing decision is part of each question's latency.
        start = time.perf_counter()
        model, probability = choose_model(strategy, q["question"], predict)
        result = ollama_server.ask(model, q["question"])
        latency = time.perf_counter() - start

        response = result["message"]["content"]
        correct = is_correct(response, q["answer"])
        writer.writerow([q["qid"], model, probability, latency, result["eval_count"], int(correct), response])
