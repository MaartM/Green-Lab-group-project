"""
Send the questions to the model(s) of one strategy and log one row per question.

  python llm-routing/run_queries.py <S|L|R> <out.csv>
"""

import csv
import json
import re
import sys
import time
import config
import ollama_server

NUMBER = r"-?\d[\d,]*\.?\d*"


def choose_model(strategy, question):
    if strategy == "S":
        return "small"
    if strategy == "L":
        return "large"
    # R: STUB for now.
    return "small" if len(question.split()) < 45 else "large"


def extract_answer(response):
    if "####" in response:
        numbers = re.findall(NUMBER, response.split("####")[-1])[:1]
    else:
        numbers = re.findall(NUMBER, response)[-1:]
    if not numbers:
        return None
    return float(numbers[0].replace(",", "").rstrip("."))


def ask(model, question):
    return ollama_server.request(model, "/api/generate", {
        "model": config.MODELS[model]["tag"],
        "prompt": config.PROMPT.format(question=question),
        "stream": False,
        "think": config.THINK,
        "options": config.OPTIONS,
    })


strategy, out_path = sys.argv[1], sys.argv[2]
questions = [json.loads(line) for line in open(config.QUESTIONS_FILE)]

with open(out_path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["qid", "model", "latency_s", "completion_tokens", "correct", "response"])

    for q in questions:
        start = time.perf_counter()
        model = choose_model(strategy, q["question"])
        result = ask(model, q["question"])
        latency = time.perf_counter() - start

        correct = extract_answer(result["response"]) == float(q["reference_answer"])
        writer.writerow([q["qid"], model, latency, result["eval_count"], int(correct), result["response"]])
