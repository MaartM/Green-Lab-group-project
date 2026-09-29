import csv
import json
import re
import sys
import time
import config
import ollama_server

NUMBER = r"-?\d[\d,]*\.?\d*"


def load_router():
    import joblib
    return joblib.load(config.router_model_path())


def choose_model(strategy, question, router):
    """Returns (model, p_small_ok). p_small_ok is the router's P(small model answers correctly), R only."""
    if strategy == "S":
        return "small", None
    if strategy == "L":
        return "large", None
    p_small_ok = float(router.predict_proba([question])[0, 1])
    return ("small" if p_small_ok > config.ROUTER_THRESHOLD else "large"), p_small_ok


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


def main():
    if sys.argv[1:2] == ["check-router"]:
        t = time.perf_counter()
        load_router()
        print(f"router OK: {config.router_model_path()} ({time.perf_counter() - t:.2f}s to load)")
        return

    strategy, out_path = sys.argv[1], sys.argv[2]
    questions = [json.loads(line) for line in open(config.QUESTIONS_FILE)]

    router = None
    if strategy == "R":
        t = time.perf_counter()
        router = load_router()
        print(f"router {config.router_model_path().name} loaded in {time.perf_counter() - t:.2f}s", file=sys.stderr, flush=True)

    with open(out_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["qid", "model", "p_small_ok", "routing_s", "latency_s", "completion_tokens",
                         "correct", "response"])

        for q in questions:
            start = time.perf_counter()
            model, p_small_ok = choose_model(strategy, q["question"], router)
            routed = time.perf_counter()
            result = ask(model, q["question"])
            latency = time.perf_counter() - start # includes routing time

            correct = extract_answer(result["response"]) == float(q["reference_answer"])
            writer.writerow([q["qid"], model, "" if p_small_ok is None else f"{p_small_ok:.4f}",
                             f"{routed - start:.6f}", latency, result["eval_count"], int(correct),
                             result["response"]])


if __name__ == "__main__":
    main()
